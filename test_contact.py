#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8000/api/contact"

DEFAULT_PAYLOAD = {
    "name": "Satworx CLI Test",
    "email": "cli-test@example.com",
    "company": "Satworx",
    "service": "Website Development",
    "budget": "Budget not set",
    "message": "This is a local CLI test for /api/contact.",
}


def build_payload(namespace):
    return {
        "name": namespace.name,
        "email": namespace.email,
        "company": namespace.company,
        "service": namespace.service,
        "budget": namespace.budget,
        "message": namespace.message,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Send a local POST request to the Satworx /api/contact endpoint."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Full contact API URL")
    parser.add_argument("--name", default=DEFAULT_PAYLOAD["name"], help="Lead name")
    parser.add_argument("--email", default=DEFAULT_PAYLOAD["email"], help="Lead email")
    parser.add_argument("--company", default=DEFAULT_PAYLOAD["company"], help="Company name")
    parser.add_argument("--service", default=DEFAULT_PAYLOAD["service"], help="Requested service")
    parser.add_argument("--budget", default=DEFAULT_PAYLOAD["budget"], help="Budget description")
    parser.add_argument("--message", default=DEFAULT_PAYLOAD["message"], help="Lead message")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP request timeout in seconds")

    args = parser.parse_args()
    payload = build_payload(args)
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        args.url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"Sending POST to {args.url}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            print(f"\nStatus: {response.status} {response.reason}")
            print(response_body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"\nHTTP Error: {exc.code} {exc.reason}")
        print(body)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"\nRequest failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
