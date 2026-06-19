const header = document.querySelector(".site-header");
const menu = document.querySelector("#site-menu");
const navToggle = document.querySelector(".nav-toggle");
const currentPage = document.body.dataset.page;

const satworxKnowledge = {
    contact: "You can contact Satworx at sailohithsahu@gmail.com, call +91 7735941720, or use the alternate number +91 9182213541.",
    office: "Satworx office location is available on Google Maps: https://maps.app.goo.gl/rDAXZzVSRwPW9jtV6?g_st=ac",
    services: "Satworx builds company websites, web applications, dashboards, portals, APIs, automation systems, cloud setups, AI/data workflows, cybersecurity improvements, UI/UX, and managed support plans.",
    process: "A good Satworx project starts with your goal, users, required features, deadline, budget range, and reference websites. Then Satworx can plan discovery, design, build, QA, deployment, and support.",
    pricing: "Pricing depends on scope, timeline, features, and support needs. Start by sharing the requirement through the contact form so Satworx can suggest the right plan.",
    technology: "Satworx works with practical technologies such as Python, JavaScript, HTML, CSS, APIs, SQL databases, cloud deployment, automation, analytics, and security practices.",
};

function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function setHeaderState() {
    header?.classList.toggle("scrolled", window.scrollY > 8);
}

window.addEventListener("scroll", setHeaderState, { passive: true });
setHeaderState();

document.querySelectorAll("[data-nav]").forEach((link) => {
    if (link.dataset.nav === currentPage) {
        link.classList.add("active");
    }
});

navToggle?.addEventListener("click", () => {
    const isOpen = menu.classList.toggle("open");
    document.body.classList.toggle("menu-open", isOpen);
    navToggle.setAttribute("aria-expanded", String(isOpen));
});

document.querySelectorAll(".nav-menu a").forEach((link) => {
    link.addEventListener("click", () => {
        menu?.classList.remove("open");
        document.body.classList.remove("menu-open");
        navToggle?.setAttribute("aria-expanded", "false");
    });
});

document.querySelectorAll("[data-year]").forEach((node) => {
    node.textContent = new Date().getFullYear();
});

const revealObserver = new IntersectionObserver(
    (entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                revealObserver.unobserve(entry.target);
            }
        });
    },
    { threshold: 0.14 }
);

document.querySelectorAll(".reveal").forEach((node) => revealObserver.observe(node));

const countObserver = new IntersectionObserver(
    (entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            animateCount(entry.target);
            countObserver.unobserve(entry.target);
        });
    },
    { threshold: 0.5 }
);

document.querySelectorAll("[data-count]").forEach((node) => countObserver.observe(node));

function animateCount(node) {
    const target = Number(node.dataset.count || "0");
    const duration = 1100;
    const start = performance.now();

    function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        node.textContent = Math.round(target * eased);
        if (progress < 1) {
            requestAnimationFrame(tick);
        }
    }

    requestAnimationFrame(tick);
}

async function loadServices() {
    const grid = document.querySelector("[data-services-grid]");
    if (!grid) return;

    try {
        const response = await fetchJson("/api/services");
        if (!response.ok) return;
        const data = await response.json();
        const icons = ["code-2", "cloud-cog", "brain", "shield-check", "pen-tool", "life-buoy"];
        grid.innerHTML = data.services
            .map((service, index) => {
                const tags = service.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
                return `
                    <article class="service-card reveal visible">
                        <i data-lucide="${icons[index] || "box"}"></i>
                        <h3>${escapeHtml(service.title)}</h3>
                        <p>${escapeHtml(service.summary)}</p>
                        <div>${tags}</div>
                    </article>
                `;
            })
            .join("");
        const count = document.querySelector("#service-count");
        if (count) count.textContent = `${data.services.length} core services`;
        refreshIcons();
    } catch (error) {
        console.warn("Could not load services API.", error);
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

const contactForm = document.querySelector("[data-contact-form]");
const formStatus = document.querySelector("[data-form-status]");

contactForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = contactForm.querySelector("button[type='submit']");
    const data = Object.fromEntries(new FormData(contactForm).entries());
    setStatus("Sending your inquiry...", "");
    button.disabled = true;

    try {
        const response = await fetchJson("/api/contact", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            cache: "no-store",
            body: JSON.stringify(data),
        });

        let result = {};
        try {
            result = await response.json();
        } catch (parseError) {
            result = {};
        }

        if (result.email_sent === false || (result.email_error && result.email_error.toString().trim())) {
            const emailError = result.email_error || result.message || "Your inquiry was received, but email delivery failed.";
            setStatus(`Your inquiry was saved, but email delivery failed: ${emailError}`, "error");
            return;
        }

        if (!response.ok) {
            const message = result.message || `The Satworx backend returned ${response.status}.`;
            setStatus(message, "error");
            return;
        }

        const statusMessage = result.message || "Thanks. Your Satworx inquiry has been received.";
        setStatus(statusMessage, "success");
        contactForm.reset();
    } catch (error) {
        console.error("Satworx contact form request failed:", error);
        try {
            await submitContactViaHiddenForm(data);
            setStatus("Your inquiry was submitted to the Satworx backend. The page used a form fallback because fetch was not available.", "success");
            contactForm.reset();
            return;
        } catch (fallbackError) {
            console.error("Satworx contact form fallback failed:", fallbackError);
        }
        setStatus("Could not send the inquiry to the Satworx backend. Make sure app.py is running and reload the page.", "error");
    } finally {
        button.disabled = false;
    }
});

function setStatus(message, type) {
    if (!formStatus) return;
    formStatus.textContent = message;
    formStatus.className = `form-status ${type}`.trim();
}

function submitContactViaHiddenForm(data) {
    return new Promise((resolve, reject) => {
        const frameName = "satworx-submit-frame";
        let iframe = document.querySelector(`iframe[name="${frameName}"]`);
        if (!iframe) {
            iframe = document.createElement("iframe");
            iframe.name = frameName;
            iframe.style.display = "none";
            document.body.appendChild(iframe);
        }

        const origin = location.protocol === "file:" ? "http://127.0.0.1:8000" : `${location.protocol}//${location.host}`;
        const form = document.createElement("form");
        form.method = "POST";
        form.action = `${origin}/api/contact`;
        form.target = frameName;
        form.style.display = "none";

        Object.entries(data).forEach(([name, value]) => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = name;
            input.value = value;
            form.appendChild(input);
        });

        const timeout = setTimeout(() => {
            cleanup();
            reject(new Error("Backend did not respond in time."));
        }, 6000);

        function cleanup() {
            clearTimeout(timeout);
            iframe.removeEventListener("load", onLoad);
            form.remove();
        }

        function onLoad() {
            cleanup();
            resolve();
        }

        iframe.addEventListener("load", onLoad, { once: true });
        document.body.appendChild(form);
        form.submit();
    });
}

const chatBox = document.querySelector(".chat-box");
const chatLaunch = document.querySelector(".chat-launch");
const chatClose = document.querySelector(".chat-close");
const chatForm = document.querySelector("[data-chat-form]");
const chatMessages = document.querySelector("[data-chat-messages]");

chatLaunch?.addEventListener("click", () => {
    chatBox.classList.add("open");
    chatBox.setAttribute("aria-hidden", "false");
    chatForm?.querySelector("input")?.focus();
});

chatClose?.addEventListener("click", () => {
    chatBox.classList.remove("open");
    chatBox.setAttribute("aria-hidden", "true");
});

chatForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = chatForm.elements.message;
    const message = input.value.trim();
    if (!message) return;

    appendChat("user", message);
    input.value = "";
    const thinking = appendChat("bot", "Satworx is checking that for you...");

    try {
        const response = await fetchJson("/api/assistant", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });
        const result = await response.json();
        thinking.textContent = result.reply || result.message || "I can help with Satworx services and contact details.";
    } catch (error) {
        thinking.textContent = localAssistantReply(message);
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
});

function apiPath(path) {
    if (location.protocol === "file:") {
        return `http://127.0.0.1:8000${path}`;
    }
    return path;
}

async function fetchJson(path, init = {}) {
    const candidates = location.protocol === "file:"
        ? [`http://127.0.0.1:8000${path}`, `http://localhost:8000${path}`]
        : [path];
    let lastError;

    for (const candidate of candidates) {
        try {
            const response = await fetch(candidate, init);
            return response;
        } catch (error) {
            lastError = error;
        }
    }

    throw lastError || new Error("Unable to reach Satworx backend.");
}

function localAssistantReply(message) {
    const text = message.toLowerCase();
    const replies = [];

    if (hasAny(text, ["contact", "email", "mail", "phone", "call", "meeting", "number"])) replies.push(satworxKnowledge.contact);
    if (hasAny(text, ["address", "office", "location", "map", "direction"])) replies.push(satworxKnowledge.office);
    if (hasAny(text, ["service", "build", "software", "website", "webpage", "app", "cloud", "ai", "data", "security", "support", "automation", "dashboard"])) replies.push(satworxKnowledge.services);
    if (hasAny(text, ["process", "start", "requirement", "plan", "deadline", "project", "how"])) replies.push(satworxKnowledge.process);
    if (hasAny(text, ["price", "cost", "budget", "quote", "proposal"])) replies.push(satworxKnowledge.pricing);
    if (hasAny(text, ["technology", "stack", "python", "javascript", "api", "database", "backend", "frontend"])) replies.push(satworxKnowledge.technology);

    if (!replies.length) {
        replies.push("I can help with Satworx services, website or app development, project planning, pricing, contact details, office location, backend, database, and support.");
        replies.push(satworxKnowledge.contact);
    }

    return replies.filter((reply, index) => replies.indexOf(reply) === index).join("\n\n");
}

function hasAny(text, words) {
    return words.some((word) => text.includes(word));
}

function appendChat(type, text) {
    const node = document.createElement("div");
    node.className = type === "user" ? "user-message" : "bot-message";
    node.textContent = text;
    chatMessages.appendChild(node);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return node;
}

document.querySelectorAll(".feature-card, .service-card, .package-card, .value-card").forEach((card) => {
    card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        if (card.classList.contains("featured")) {
            card.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(20, 110, 245, 0.18), rgba(11, 16, 24, 0.98) 42%)`;
        } else {
            card.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(20, 110, 245, 0.08), rgba(255, 255, 255, 0.96) 34%)`;
        }
    });

    card.addEventListener("pointerleave", () => {
        card.style.background = "";
    });
});

window.addEventListener("load", () => {
    refreshIcons();
    loadServices();
});
