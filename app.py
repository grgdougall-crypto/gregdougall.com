import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from urllib import error as url_error
from urllib import request as url_request

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix


BASE_DIR = Path(__file__).resolve().parent
RESEND_ENDPOINT = "https://api.resend.com/emails"
MAX_REQUEST_BYTES = 16 * 1024
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 10 * 60
ALLOWED_REASONS = {
    "Job opportunity",
    "Recruiting / hiring",
    "Project collaboration",
    "Freelance / consulting",
    "Technical conversation",
    "Other",
}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

_rate_buckets = defaultdict(deque)
_rate_lock = threading.Lock()


def _json_error(message, status):
    return jsonify({"ok": False, "error": message}), status


def _rate_limit_exceeded(client_ip):
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    with _rate_lock:
        attempts = _rate_buckets[client_ip]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= RATE_LIMIT_ATTEMPTS:
            return True
        attempts.append(now)
        return False


def _validate_contact_payload(payload):
    if not isinstance(payload, dict):
        return None, "Send the form as a JSON object."

    allowed_fields = {"name", "email", "company", "reason", "message", "website"}
    if any(key not in allowed_fields for key in payload):
        return None, "The form contains an unsupported field."

    values = {}
    limits = {"name": 120, "email": 254, "company": 160, "reason": 80, "message": 5000, "website": 200}
    for field, limit in limits.items():
        value = payload.get(field, "")
        if not isinstance(value, str):
            return None, f"{field.capitalize()} must be text."
        value = value.strip()
        if len(value) > limit:
            return None, f"{field.capitalize()} is too long."
        values[field] = value

    if values["website"]:
        return None, "Unable to accept this submission."
    if not values["name"]:
        return None, "Name is required."
    if not values["email"] or not EMAIL_PATTERN.fullmatch(values["email"]):
        return None, "Enter a valid email address."
    if values["reason"] not in ALLOWED_REASONS:
        return None, "Choose a valid reason for reaching out."
    if len(values["message"]) < 20:
        return None, "Message must be at least 20 characters."
    if any("\r" in values[field] or "\n" in values[field] for field in ("name", "email", "company", "reason")):
        return None, "The form contains invalid characters."

    return values, None


def _email_config():
    config = {
        "api_key": os.getenv("RESEND_API_KEY", "").strip(),
        "to_email": os.getenv("CONTACT_TO_EMAIL", "").strip(),
        "from_email": os.getenv("CONTACT_FROM_EMAIL", "").strip(),
        "from_name": os.getenv("CONTACT_FROM_NAME", "").strip(),
    }
    return config if all(config.values()) else None


def send_contact_email(config, contact):
    company = contact["company"] or "Not provided"
    email_payload = {
        "from": f'{config["from_name"]} <{config["from_email"]}>',
        "to": [config["to_email"]],
        "reply_to": contact["email"],
        "subject": f'Website contact: {contact["reason"]}',
        "text": (
            f'Name: {contact["name"]}\n'
            f'Email: {contact["email"]}\n'
            f'Company or organization: {company}\n'
            f'Reason: {contact["reason"]}\n\n'
            f'Message:\n{contact["message"]}'
        ),
    }
    outbound = url_request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(email_payload).encode("utf-8"),
        headers={
            "Authorization": f'Bearer {config["api_key"]}',
            "Content-Type": "application/json",
            "User-Agent": "gregdougall.com-contact/1.0",
        },
        method="POST",
    )
    with url_request.urlopen(outbound, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError("Email provider rejected the request.")


@app.get("/")
@app.get("/index.html")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/contact")
@app.get("/contact.html")
def contact_page():
    return send_from_directory(BASE_DIR, "contact.html")


@app.get("/projects/gnojo")
@app.get("/projects/gnojo.html")
def gnojo_page():
    return send_from_directory(BASE_DIR / "projects", "gnojo.html")


@app.get("/projects/ai-operations-assistant")
@app.get("/projects/ai-operations-assistant.html")
def ai_operations_assistant_page():
    return send_from_directory(BASE_DIR / "projects", "ai-operations-assistant.html")


@app.get("/projects/ai-corral")
@app.get("/projects/ai-corral.html")
def ai_corral_page():
    return send_from_directory(BASE_DIR / "projects", "ai-corral.html")


@app.get("/static/<path:filename>")
def static_file(filename):
    return send_from_directory(BASE_DIR / "static", filename)


@app.get("/favicon.ico")
def favicon():
    return "", 204


@app.post("/api/contact")
def contact_api():
    if _rate_limit_exceeded(request.remote_addr or "unknown"):
        return _json_error("Too many messages have been submitted. Please try again later.", 429)
    if request.mimetype != "application/json":
        return _json_error("Send the form as JSON.", 415)

    contact, validation_error = _validate_contact_payload(request.get_json(silent=True))
    if validation_error:
        return _json_error(validation_error, 400)

    config = _email_config()
    if config is None:
        app.logger.error("Contact delivery is unavailable because required configuration is missing.")
        return _json_error("Message delivery is temporarily unavailable. Please try again later.", 500)

    try:
        send_contact_email(config, contact)
    except url_error.HTTPError as exc:
        try:
            provider_body = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            provider_body = "Provider response body unavailable."
        sensitive_values = [*config.values(), contact["name"], contact["email"], contact["company"], contact["message"]]
        for sensitive_value in sorted(filter(None, sensitive_values), key=len, reverse=True):
            provider_body = provider_body.replace(sensitive_value, "[redacted]")
        app.logger.warning("Resend request failed with HTTP %s: %s", exc.code, provider_body[:1000])
        return _json_error("Your message could not be sent. Please try again later.", 502)
    except url_error.URLError as exc:
        reason = exc.reason
        app.logger.warning("Resend request failed with %s: %s", type(reason).__name__, reason)
        return _json_error("Your message could not be sent. Please try again later.", 502)
    except TimeoutError:
        app.logger.warning("Resend provider request timed out.")
        return _json_error("Your message could not be sent. Please try again later.", 502)
    except RuntimeError as exc:
        app.logger.warning("Resend request failed: %s", exc)
        return _json_error("Your message could not be sent. Please try again later.", 502)

    return jsonify({"ok": True, "message": "Your message was sent. Thanks for reaching out."})


@app.errorhandler(413)
def request_too_large(_error):
    return _json_error("The submission is too large.", 400)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
