from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import smtplib
from pathlib import Path
from urllib.parse import urlparse
import datetime as dt
import json
import mimetypes
import os
import re
import sqlite3
import threading
import uuid
import webbrowser
from email.message import EmailMessage
from urllib.parse import parse_qs


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_FILE = DATA_DIR / "satworx.db"


def load_local_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (key not in os.environ or not os.environ[key].strip()):
            os.environ[key] = value


load_local_env()

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", f"http://127.0.0.1:{PORT}").rstrip("/")
OPEN_BROWSER = os.environ.get("OPEN_BROWSER", "1") == "1"
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1") == "1"
LEADS_LOCK = threading.Lock()
RATE_LOCK = threading.Lock()
REQUEST_LOG = {}
ALLOWED_STATIC_SUFFIXES = {".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico"}
MAX_FIELD_LENGTHS = {
    "name": 80,
    "email": 120,
    "company": 120,
    "service": 80,
    "budget": 80,
    "message": 1600,
}
SERVICES = [
    {
        "title": "Custom Software Engineering",
        "summary": "Web platforms, portals, dashboards, and internal tools designed around the way your team actually works.",
        "tags": ["Python", "JavaScript", "APIs", "SaaS"],
    },
    {
        "title": "Cloud And DevOps",
        "summary": "Secure deployments, CI/CD pipelines, monitoring, containerization, and cloud cost optimization.",
        "tags": ["AWS", "Azure", "Docker", "Automation"],
    },
    {
        "title": "AI And Data Intelligence",
        "summary": "Decision dashboards, forecasting, document automation, and practical AI workflows for operations teams.",
        "tags": ["Analytics", "AI", "ETL", "BI"],
    },
    {
        "title": "Cybersecurity Readiness",
        "summary": "Access control, secure coding reviews, API hardening, audits, and incident response preparation.",
        "tags": ["Zero Trust", "Audit", "Risk", "Compliance"],
    },
    {
        "title": "Product UI And UX",
        "summary": "Modern interfaces, design systems, prototypes, and user journeys that make complex products feel clear.",
        "tags": ["UX", "Design Systems", "Research"],
    },
    {
        "title": "Managed Support",
        "summary": "Ongoing feature delivery, performance care, technical support, and roadmap partnership after launch.",
        "tags": ["SLA", "Maintenance", "Growth"],
    },
]


COMPANY = {
    "name": "Satworx",
    "headline": "Software strategy, engineering, and automation for growing teams.",
    "email": "sailohithsahu@gmail.com",
    "phone": "+91 7735941720",
    "alternate_phone": "+91 9182213541",
    "location": "Satworx office",
    "map": "https://maps.app.goo.gl/rDAXZzVSRwPW9jtV6?g_st=ac",
    "stats": [
        {"label": "Delivery sprints", "value": 120},
        {"label": "Cloud workloads", "value": 48},
        {"label": "Client NPS", "value": 96},
    ],
}


ADMIN_EMAIL = os.environ.get("TO_EMAIL", COMPANY["email"])
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME or ADMIN_EMAIL).strip()


ASSISTANT_TOPICS = {
    "services": (
        "Satworx services include custom software engineering, website development, web apps, dashboards, "
        "cloud and DevOps, AI and data intelligence, cybersecurity readiness, product UI/UX, automation, "
        "and managed support."
    ),
    "process": (
        "The usual project flow is discovery, solution design, build sprint, QA, deployment, and ongoing "
        "support. Share your goal, users, deadline, must-have features, and any reference websites."
    ),
    "contact": (
        "You can contact Satworx at sailohithsahu@gmail.com, call +91 7735941720, or use the alternate "
        "number +91 9182213541."
    ),
    "office": (
        "Satworx office location is available on Google Maps: "
        "https://maps.app.goo.gl/rDAXZzVSRwPW9jtV6?g_st=ac"
    ),
    "pricing": (
        "Pricing depends on scope. Satworx can start with planning, then recommend a fixed sprint or "
        "managed delivery plan after understanding features, timeline, and support needs."
    ),
    "technology": (
        "Satworx works with practical tools such as Python, JavaScript, HTML, CSS, APIs, SQL, cloud "
        "deployment, automation, analytics, and security practices."
    ),
}


def json_response(handler, status, payload):
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    add_cors_headers(handler)
    handler.end_headers()
    handler.wfile.write(body)


def add_cors_headers(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Max-Age", "3600")
    handler.send_header("Access-Control-Allow-Private-Network", "true")


def redirect_response(handler, location):
    handler.send_response(301)
    handler.send_header("Location", location)
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()


def not_found(handler):
    return json_response(handler, 404, {"ok": False, "message": "Page not found"})


def init_database():
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                service TEXT,
                budget TEXT,
                message TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_messages (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            )
            """
        )
        conn.commit()


def read_request_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length > 100_000:
        raise ValueError("Request body is too large.")
    raw = handler.rfile.read(length).decode("utf-8")
    content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/json":
        return json.loads(raw or "{}")
    if content_type in {"application/x-www-form-urlencoded", "multipart/form-data", ""}:
        parsed = parse_qs(raw, keep_blank_values=True)
        return {key: values[0] if values else "" for key, values in parsed.items()}
    return json.loads(raw or "{}")


def check_rate_limit(handler, limit=30, window_seconds=300):
    client_ip = handler.client_address[0]
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    with RATE_LOCK:
        recent = [stamp for stamp in REQUEST_LOG.get(client_ip, []) if now - stamp < window_seconds]
        if len(recent) >= limit:
            REQUEST_LOG[client_ip] = recent
            return False
        recent.append(now)
        REQUEST_LOG[client_ip] = recent
        return True


def clean_contact_payload(payload):
    cleaned = {}
    for field, max_length in MAX_FIELD_LENGTHS.items():
        value = str(payload.get(field, "")).strip()
        cleaned[field] = value[:max_length]
    return cleaned


def save_lead(payload):
    init_database()
    DATA_DIR.mkdir(exist_ok=True)
    with LEADS_LOCK:
        lead = {
            "id": str(uuid.uuid4()),
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "name": payload["name"],
            "email": payload["email"],
            "company": payload.get("company", ""),
            "service": payload.get("service", ""),
            "budget": payload.get("budget", ""),
            "message": payload["message"],
        }
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """
                INSERT INTO leads (id, created_at, name, email, company, service, budget, message)
                VALUES (:id, :created_at, :name, :email, :company, :service, :budget, :message)
                """,
                lead,
            )
            conn.commit()
        return lead


def validate_contact(payload):
    required = ["name", "email", "message"]
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return f"Please complete: {', '.join(missing)}."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", payload["email"]):
        return "Please enter a valid business email."
    if len(payload["message"].strip()) < 12:
        return "Please add a little more detail about your project."
    return None


def assistant_reply(message):
    text = message.lower()
    matched = []

    if any(word in text for word in ["price", "cost", "budget", "quote", "proposal"]):
        matched.append(ASSISTANT_TOPICS["pricing"])
    if any(word in text for word in ["service", "build", "software", "website", "webpage", "app", "cloud", "ai", "data", "security", "support", "automation", "dashboard"]):
        matched.append(ASSISTANT_TOPICS["services"])
    if any(word in text for word in ["process", "start", "requirement", "plan", "deadline", "project", "how"]):
        matched.append(ASSISTANT_TOPICS["process"])
    if any(word in text for word in ["contact", "email", "mail", "phone", "call", "meeting", "number"]):
        matched.append(ASSISTANT_TOPICS["contact"])
    if any(word in text for word in ["address", "office", "location", "map", "direction"]):
        matched.append(ASSISTANT_TOPICS["office"])
    if any(word in text for word in ["technology", "stack", "python", "javascript", "api", "database", "backend", "frontend"]):
        matched.append(ASSISTANT_TOPICS["technology"])
    if any(word in text for word in ["job", "career", "hiring", "resume"]):
        matched.append("Career openings are shared project-by-project. Send your profile through the contact page with your skills and experience.")

    if not matched:
        matched.append(
            "Satworx builds professional websites, web applications, dashboards, automation systems, APIs, "
            "cloud setups, and support plans. Ask about services, pricing, process, contact details, office "
            "location, or technology stack."
        )

    return "\n\n".join(dict.fromkeys(matched))


def save_assistant_message(question, answer):
    init_database()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO assistant_messages (id, created_at, question, answer)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), dt.datetime.now(dt.timezone.utc).isoformat(), question, answer),
        )
        conn.commit()


def email_notifications_enabled():
    return all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM])


def smtp_configuration_status():
    missing = []
    if not SMTP_HOST:
        missing.append("SMTP_HOST")
    if not SMTP_USERNAME:
        missing.append("SMTP_USERNAME")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not SMTP_FROM:
        missing.append("SMTP_FROM")
    return missing


def gmail_password_is_valid():
    host = SMTP_HOST.lower()
    if "gmail.com" not in host and "googlemail.com" not in host:
        return True
    password = smtp_login_password()
    return bool(re.fullmatch(r"[A-Za-z0-9]{16}", password))


def smtp_login_password():
    password = SMTP_PASSWORD.strip()
    if "gmail.com" in SMTP_HOST.lower() or "googlemail.com" in SMTP_HOST.lower():
        return re.sub(r"[\s-]+", "", password)
    return password


def gmail_password_guidance_message():
    password = smtp_login_password()
    if len(password) != 16 or not re.fullmatch(r"[A-Za-z0-9]{16}", password):
        return (
            "The current SMTP_PASSWORD in .env is not a valid 16-character Gmail App Password. "
            "Generate a new App Password in Google Account > Security > App passwords, then paste that "
            "16-character value here. Do not use your normal Google account password."
        )
    return None


def gmail_auth_error_message(exc):
    detail = str(exc).lower()
    is_gmail = "gmail.com" in SMTP_HOST.lower() or "googlemail.com" in SMTP_HOST.lower()
    is_bad_credentials = any(
        marker in detail
        for marker in ("535", "badcredentials", "username and password not accepted", "authentication failed")
    )

    if is_gmail and is_bad_credentials:
        return (
            "Gmail SMTP authentication failed. Use a 16-character Gmail App Password in SMTP_PASSWORD "
            "(not your normal Google account password). If needed, enable 2-Step Verification and "
            "generate the App Password from Google Account > Security > App passwords."
        )

    if is_bad_credentials:
        return "SMTP authentication failed. Check the SMTP username and password in the server settings."

    return None


def send_contact_email(lead):
    if not email_notifications_enabled():
        missing = smtp_configuration_status()
        if missing:
            return False, f"SMTP is not configured. Missing: {', '.join(missing)}."
        return False, "SMTP email delivery is disabled."

    if not gmail_password_is_valid():
        guidance = gmail_password_guidance_message()
        return False, guidance or (
            "Gmail SMTP requires a 16-character Google App Password in SMTP_PASSWORD. "
            "Use the App Password from Google Account > Security > App passwords, not your normal Gmail login password."
        )

    try:
        message = EmailMessage()
        message["Subject"] = f"New Satworx inquiry from {lead['name']}"
        message["From"] = SMTP_FROM
        message["To"] = ADMIN_EMAIL
        message["Reply-To"] = lead["email"]
        message.set_content(
            "\n".join(
                [
                    "New Satworx contact inquiry",
                    "",
                    f"Name: {lead['name']}",
                    f"Email: {lead['email']}",
                    f"Company: {lead.get('company', '') or '-'}",
                    f"Service: {lead.get('service', '') or '-'}",
                    f"Budget: {lead.get('budget', '') or '-'}",
                    "",
                    "Message:",
                    lead["message"],
                    "",
                    f"Lead ID: {lead['id']}",
                    f"Created at: {lead['created_at']}",
                ]
            )
        )

        use_ssl = not SMTP_USE_TLS or SMTP_PORT == 465
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) if use_ssl else smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS and not use_ssl:
                server.ehlo()
                server.starttls()
                server.ehlo()
            server.login(SMTP_USERNAME, smtp_login_password())
            server.send_message(message)

        return True, None
    except Exception as exc:
        friendly_error = gmail_auth_error_message(exc)
        if friendly_error:
            return False, friendly_error

        error_detail = str(exc)
        if "gmail.com" in SMTP_HOST.lower() or "googlemail.com" in SMTP_HOST.lower():
            return False, (
                "Gmail SMTP delivery failed. Check the Gmail App Password and SMTP settings in the server "
                "configuration, then restart the app."
            )
        return False, error_detail


class SatworxHandler(BaseHTTPRequestHandler):
    server_version = "Satworx"
    sys_version = ""

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' https://images.unsplash.com data:; "
            "connect-src 'self' http://127.0.0.1:8000; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/health":
            return json_response(self, 200, {"ok": True, "service": "Satworx API"})
        if path == "/api/services":
            return json_response(self, 200, {"services": SERVICES})
        if path == "/api/company":
            return json_response(self, 200, COMPANY)
        if path == "/api/knowledge":
            return json_response(self, 200, {"company": COMPANY, "services": SERVICES, "topics": ASSISTANT_TOPICS})
        if path == "/api/routes":
            return json_response(
                self,
                200,
                {
                    "base_url": PUBLIC_BASE_URL,
                    "routes": {
                        "home": f"{PUBLIC_BASE_URL}/home",
                        "about": f"{PUBLIC_BASE_URL}/about",
                        "services": f"{PUBLIC_BASE_URL}/services",
                        "contact": f"{PUBLIC_BASE_URL}/contact",
                    },
                },
            )

        clean_redirects = {
            "/": "/home",
            "/index.html": "/home",
            "/about.html": "/about",
            "/service": "/services",
            "/services.html": "/services",
            "/contact.html": "/contact",
            "/contacts": "/contact",
        }
        if path in clean_redirects:
            return redirect_response(self, clean_redirects[path])

        page_routes = {
            "/home": "index.html",
            "/about": "about.html",
            "/services": "services.html",
            "/contact": "contact.html",
        }
        if path in page_routes:
            return self.serve_file(ROOT / page_routes[path])

        requested = (ROOT / parsed.path.lstrip("/")).resolve()
        if (
            ROOT in requested.parents
            and requested.is_file()
            and requested.suffix.lower() in ALLOWED_STATIC_SUFFIXES
            and DATA_DIR not in requested.parents
        ):
            return self.serve_file(requested)

        return not_found(self)

    def do_OPTIONS(self):
        self.send_response(204)
        add_cors_headers(self)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if not check_rate_limit(self):
            return json_response(self, 429, {"ok": False, "message": "Too many requests. Please try again later."})
        try:
            payload = read_request_body(self)
        except (json.JSONDecodeError, ValueError) as exc:
            return json_response(self, 400, {"ok": False, "message": str(exc)})

        if parsed.path == "/api/contact":
            payload = clean_contact_payload(payload)
            error = validate_contact(payload)
            if error:
                return json_response(self, 422, {"ok": False, "message": error})
            lead = save_lead(payload)
            email_sent, email_error = send_contact_email(lead)
            if not email_sent and not email_error:
                missing = smtp_configuration_status()
                if missing:
                    email_error = f"SMTP is not configured. Missing: {', '.join(missing)}."
                else:
                    email_error = "SMTP email delivery is disabled."

            status_message = "Thanks. Your Satworx inquiry has been received."
            if not email_sent:
                print(f"Contact email delivery failed for lead {lead['id']}: {email_error}")

            return json_response(
                self,
                201,
                {
                    "ok": True,
                    "message": status_message,
                    "lead_id": lead["id"],
                    "delivered_to": ADMIN_EMAIL,
                    "email_sent": email_sent,
                    "email_error": email_error,
                },
            )

        if parsed.path == "/api/assistant":
            message = str(payload.get("message", "")).strip()
            if not message:
                return json_response(self, 422, {"ok": False, "message": "Ask a question first."})
            reply = assistant_reply(message)
            save_assistant_message(message, reply)
            return json_response(self, 200, {"ok": True, "reply": reply})

        return not_found(self)

    def serve_file(self, file_path):
        if not file_path.exists():
            return not_found(self)
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {format % args}")


if __name__ == "__main__":
    init_database()
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("application/javascript", ".js")
    server = ThreadingHTTPServer((HOST, PORT), SatworxHandler)
    local_url = f"http://127.0.0.1:{PORT}/home"
    public_url = f"{PUBLIC_BASE_URL}/home"
    print(f"Satworx local URL: {local_url}")
    print(f"Satworx public URL after domain setup: {public_url}")
    missing_smtp = smtp_configuration_status()
    if missing_smtp:
        print(f"SMTP not ready. Missing: {', '.join(missing_smtp)}")
    if OPEN_BROWSER and HOST in {"127.0.0.1", "localhost"}:
        threading.Timer(0.6, lambda: webbrowser.open(local_url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Satworx server.")
        server.server_close()
