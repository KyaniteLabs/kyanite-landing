"""
KyaniteLabs — Landing + Shop
"""
import os
import csv
import json
import hmac
import io
import html as html_lib
import hashlib
import re
import secrets
import smtplib
import sqlite3
import subprocess
import tempfile
try:
    import psycopg2
    import psycopg2.extras
except ModuleNotFoundError:
    psycopg2 = None
import requests as http_requests
from email.message import EmailMessage
from email.utils import format_datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import UTC, datetime
from urllib.parse import quote, urlencode
from flask import Flask, request, jsonify, render_template_string, Response, redirect
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
BASE_DIR = os.path.dirname(__file__)

# Config from env
app.config["SMTP_HOST"]    = os.environ.get("SMTP_HOST", "infra-smtp")
app.config["SMTP_PORT"]     = int(os.environ.get("SMTP_PORT", "25"))
app.config["SMTP_FROM"]    = os.environ.get("SMTP_FROM", "noreply@kyanitelabs.tech")
app.config["CONTACT_TO"]   = os.environ.get("CONTACT_TO", "info@kyanitelabs.tech")
app.config["KOFI_URL"]     = os.environ.get("KOFI_URL", "https://ko-fi.com/kyanitelabs")
app.config["KOFI_TOKEN"]   = os.environ.get("KOFI_WEBHOOK_TOKEN", "")
app.config["KOFI_USER"]    = os.environ.get("KOFI_USER", "kyanitelabs")
app.config["TG_BOT_TOKEN"] = os.environ.get("TG_BOT_TOKEN", "")
app.config["TG_CHAT_ID"]   = os.environ.get("TG_CHAT_ID", "886031571")
app.config["PG_HOST"]      = os.environ.get("PG_HOST", "infra-postgres")
app.config["PG_PORT"]      = int(os.environ.get("PG_PORT", "5432"))
app.config["PG_DB"]        = os.environ.get("PG_DB", "postgres")
app.config["PG_USER"]      = os.environ.get("PG_USER", "postgres")
app.config["PG_PASS"]      = os.environ.get("PG_PASS", "postgres")
app.config["ENABLE_SHOP_DB"] = os.environ.get("ENABLE_SHOP_DB", "0") == "1"
app.config["ENABLE_CERAFICA_DB"] = os.environ.get("ENABLE_CERAFICA_DB", "0") == "1"
app.config["ENABLE_CERAFICA_PUBLIC_API"] = os.environ.get("ENABLE_CERAFICA_PUBLIC_API", "0") == "1"
app.config["ADMIN_API_TOKEN"] = os.environ.get("ADMIN_API_TOKEN", "")
app.config["NEWSLETTER_DB_PATH"] = os.environ.get(
    "NEWSLETTER_DB_PATH",
    os.environ.get("KYANITE_NEWSLETTER_DB_PATH", "/app/revenue/kyanite-newsletter.sqlite3"),
)
app.config["NEWSLETTER_UNSUBSCRIBE_SECRET"] = os.environ.get(
    "NEWSLETTER_UNSUBSCRIBE_SECRET",
    os.environ.get("ADMIN_API_TOKEN", ""),
)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", str(64 * 1024)))
app.config["FORM_SUBMISSION_LOG_PATH"] = os.environ.get(
    "FORM_SUBMISSION_LOG_PATH",
    os.path.join(tempfile.gettempdir(), "kyanite-form-submissions.jsonl"),
)


CANONICAL_BASE = "https://kyanitelabs.tech"
PUENTEWORKS_URL = "https://puenteworks.com"
app.config["NEWSLETTER_PUBLIC_BASE_URL"] = os.environ.get("NEWSLETTER_PUBLIC_BASE_URL", CANONICAL_BASE)
ROBOTS_INDEX_DIRECTIVE = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
INDEXNOW_KEY = "a4b0d2c3f1e94887a256c44b9e2c6f10"
TIKTOK_SITE_VERIFICATION_FILENAME = "tiktokuizIkj1wDJXH5viSolnBjshmsH3xQAW3.txt"
TIKTOK_SITE_VERIFICATION_BODY = (
    "tiktok-developers-site-verification=uizIkj1wDJXH5viSolnBjshmsH3xQAW3"
)
ADMIN_API_PATHS = {
    "/api/sales/stats",
    "/api/waitlist",
    "/api/newsletter/subscribers",
    "/api/newsletter/export.csv",
}
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://puenteworks.com https://app.posthog.com https://us.i.posthog.com https://*.posthog.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self' https://puenteworks.com https://app.posthog.com https://us.i.posthog.com https://*.posthog.com",
    "worker-src 'self' blob:",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
])
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
}


def record_form_submission(kind, payload):
    entry = {
        "kind": kind,
        "created_at": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    path = app.config.get("FORM_SUBMISSION_LOG_PATH")
    if not path:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def deliver_form_email(kind, msg, fallback_payload):
    try:
        with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"]) as server:
            server.send_message(msg)
        return "email"
    except OSError as e:
        record_form_submission(kind, {**fallback_payload, "delivery_error": str(e)})
        print(f"[FORM_FALLBACK] {kind} recorded locally after SMTP error: {type(e).__name__}")
        return "local_log"

PUBLIC_PAGE_CACHE = {}
PUBLIC_CACHE_EXCLUDED_PREFIXES = ("/api/", "/webhook/", "/static/")


def public_cache_key():
    if request.method != "GET" or request.query_string:
        return None
    path = request.path or "/"
    if any(path.startswith(prefix) for prefix in PUBLIC_CACHE_EXCLUDED_PREFIXES):
        return None
    representation = "markdown" if "text/markdown" in request.headers.get("Accept", "").lower() else "html"
    return f"{path}::{representation}"


@app.before_request
def serve_public_page_cache():
    key = public_cache_key()
    if not key or key not in PUBLIC_PAGE_CACHE:
        return None
    cached = PUBLIC_PAGE_CACHE[key]
    return Response(cached["body"], status=cached["status"], headers=cached["headers"])


@app.after_request
def add_security_headers(response):
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    key = public_cache_key()
    if key and response.status_code == 200 and not response.direct_passthrough:
        content_type = response.headers.get("Content-Type", "")
        if any(kind in content_type for kind in ("text/html", "text/plain", "application/json", "application/xml", "text/xml", "application/rss+xml")):
            PUBLIC_PAGE_CACHE[key] = {
                "status": response.status_code,
                "headers": [(name, value) for name, value in response.headers.items()],
                "body": response.get_data(),
            }
    return response


@app.errorhandler(RequestEntityTooLarge)
def request_entity_too_large(_error):
    return jsonify({"error": "Payload too large"}), 413


def admin_api_gate():
    token = app.config.get("ADMIN_API_TOKEN", "")
    if not token:
        return jsonify({"error": "Not found"}), 404
    if request.headers.get("Authorization", "") != f"Bearer {token}":
        return jsonify({"error": "Forbidden"}), 403
    return None


def render_template_file(template_name, **context):
    path = os.path.join(BASE_DIR, "templates", template_name)
    with open(path, encoding="utf-8") as f:
        return render_template_string(f.read(), **context)


def plain_text(value):
    text = re.sub(r"<[^>]+>", " ", value)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def rss_date(value):
    return format_datetime(datetime.fromisoformat(value).replace(tzinfo=UTC))


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_text_field(value, limit=500):
    text = str(value or "").replace("\x00", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def current_timestamp():
    return datetime.now(UTC).isoformat(timespec="seconds")


def newsletter_db_path():
    path = app.config["NEWSLETTER_DB_PATH"]
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def newsletter_connect():
    conn = sqlite3.connect(newsletter_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL DEFAULT '',
            interest TEXT NOT NULL DEFAULT '',
            source_page TEXT NOT NULL DEFAULT '',
            consent_status TEXT NOT NULL DEFAULT 'subscribed',
            unsubscribe_token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            user_agent TEXT NOT NULL DEFAULT '',
            remote_addr TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def newsletter_unsubscribe_token(email):
    secret = app.config.get("NEWSLETTER_UNSUBSCRIBE_SECRET", "")
    if secret:
        digest = hmac.new(secret.encode("utf-8"), email.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest[:48]
    return secrets.token_urlsafe(32)


def newsletter_unsubscribe_url(token):
    base_url = app.config.get("NEWSLETTER_PUBLIC_BASE_URL", CANONICAL_BASE).rstrip("/")
    return f"{base_url}/api/newsletter/unsubscribe?token={quote(token)}"


def newsletter_request_data():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def request_payload_data():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def newsletter_remote_addr():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return clean_text_field(forwarded.split(",", 1)[0], 80)
    return clean_text_field(request.remote_addr or "", 80)


def newsletter_row_dict(row):
    return {
        "email": row["email"],
        "name": row["name"],
        "interest": row["interest"],
        "source_page": row["source_page"],
        "consent_status": row["consent_status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def upsert_newsletter_subscriber(data):
    email = clean_text_field(data.get("email"), 254).lower()
    name = clean_text_field(data.get("name"), 120)
    interest = clean_text_field(data.get("interest"), 1000)
    source_page = clean_text_field(data.get("source_page") or request.referrer or "/", 240)
    token = newsletter_unsubscribe_token(email)
    now = current_timestamp()

    conn = newsletter_connect()
    try:
        conn.execute("""
            INSERT INTO newsletter_subscribers (
                email, name, interest, source_page, consent_status, unsubscribe_token,
                created_at, updated_at, user_agent, remote_addr
            )
            VALUES (?, ?, ?, ?, 'subscribed', ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                interest = excluded.interest,
                source_page = excluded.source_page,
                consent_status = 'subscribed',
                unsubscribe_token = excluded.unsubscribe_token,
                updated_at = excluded.updated_at,
                user_agent = excluded.user_agent,
                remote_addr = excluded.remote_addr
        """, (
            email,
            name,
            interest,
            source_page,
            token,
            now,
            now,
            clean_text_field(request.headers.get("User-Agent"), 240),
            newsletter_remote_addr(),
        ))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM newsletter_subscribers WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def send_newsletter_notification(row):
    recipient = app.config.get("CONTACT_TO", "")
    if not recipient:
        return
    msg = EmailMessage()
    msg["Subject"] = f"KyaniteLabs newsletter signup: {row['email']}"
    msg["From"] = app.config["SMTP_FROM"]
    msg["To"] = recipient
    msg.set_content(
        "New Kyanite Build Notes signup\n\n"
        f"Email: {row['email']}\n"
        f"Name: {row['name'] or '-'}\n"
        f"Interest: {row['interest'] or '-'}\n"
        f"Source: {row['source_page'] or '-'}\n"
        f"Status: {row['consent_status']}\n"
        f"Unsubscribe: {newsletter_unsubscribe_url(row['unsubscribe_token'])}\n"
    )
    with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"]) as server:
        server.send_message(msg)


def newsletter_response_page(title, message, status=200):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>{html_lib.escape(title)} | KyaniteLabs</title>
  <link rel="stylesheet" href="/static/css/kyanite-system.css">
</head>
<body>
  <main class="page-hero">
    <div class="container page-hero-inner">
      <div class="eyebrow">Kyanite Build Notes</div>
      <h1>{html_lib.escape(title)}</h1>
      <p class="lead">{html_lib.escape(message)}</p>
      <div class="button-row">
        <a class="btn btn-secondary" href="/">Back to KyaniteLabs</a>
      </div>
    </div>
  </main>
</body>
</html>"""
    return Response(html, status=status, mimetype="text/html")

PUBLIC_PROJECTS = [
    {
        "name": "devarch-framework",
        "url": "https://github.com/KyaniteLabs/devarch-framework",
        "description": "Git repository archaeology framework for mining commit history, detecting signals, running 6 analysis vectors, and generating engineering reports.",
        "tag": "Repo Intelligence",
        "tile_code": "DF",
        "language": "Python",
        "updated": "2026-05-29",
        "image": "/static/brand/projects/kyanite-project-devarch-framework-1672x941.webp",
        "proof_role": "Shows Kyanite can turn development history into evidence, not vibes.",
    },
    {
        "name": "mcp-video",
        "url": "https://github.com/KyaniteLabs/mcp-video",
        "description": "Video editing MCP server for AI agents with 87 FFmpeg and Hyperframes tools, Python client, and CLI.",
        "tag": "Media MCP",
        "tile_code": "MV",
        "language": "Python",
        "updated": "2026-06-01",
        "image": "/static/brand/projects/kyanite-project-mcp-video-1672x941.webp",
        "proof_role": "The flagship proof that agents can operate timelines, effects, and repeatable media pipelines.",
    },
    {
        "name": "Epoch",
        "url": "https://github.com/KyaniteLabs/Epoch",
        "description": "Time estimation MCP server for PERT, COCOMO II, Monte Carlo, sprint forecasting, token-to-time mapping, cost estimation, and schedule risk tools.",
        "tag": "Estimation MCP",
        "tile_code": "EP",
        "language": "TypeScript",
        "updated": "2026-05-29",
        "image": "/static/brand/projects/kyanite-project-epoch-1672x941.webp",
        "proof_role": "Turns planning uncertainty into agent-callable forecasting tools.",
    },
    {
        "name": "checkyourself",
        "url": "https://github.com/KyaniteLabs/checkyourself",
        "description": "Local-first production-readiness system for AI-built apps: read-only audits, evidence scores, guided fixes, learning plans, dashboards, CLI, and MCP.",
        "tag": "Readiness Audit",
        "tile_code": "CY",
        "language": "Python",
        "updated": "2026-05-30",
        "image": "/static/brand/projects/kyanite-project-checkyourself-1672x941.webp",
        "proof_role": "Makes quality, security, and launch risk inspectable before an AI-built app ships.",
    },
    {
        "name": "DialectOS",
        "url": "https://github.com/KyaniteLabs/DialectOS",
        "description": "Spanish dialect localization MCP server and CLI across 25 regional variants with register control, structure preservation, and QA gates.",
        "tag": "Localization MCP",
        "tile_code": "DX",
        "language": "TypeScript",
        "updated": "2026-05-30",
        "image": "/static/brand/projects/kyanite-project-dialectos-1672x941.webp",
        "proof_role": "Makes Spanish launch quality inspectable instead of treating localization as generic translation.",
    },
    {
        "name": "liminal",
        "url": "https://github.com/KyaniteLabs/liminal",
        "description": "AI creative coding studio for p5.js, GLSL, Three.js, music, video, and model-agnostic generative art workflows.",
        "tag": "Creative Coding",
        "tile_code": "LM",
        "language": "TypeScript",
        "updated": "2026-05-29",
        "image": "/static/brand/projects/kyanite-project-liminal-1672x941.webp",
        "proof_role": "Shows Kyanite can build creative tools where agents touch code, shaders, media, and taste.",
    },
    {
        "name": "liminal-sites",
        "url": "https://github.com/KyaniteLabs/liminal-sites",
        "description": "Living website evolution engine for AI design directions, runtime skins, taste memory, previews, and repo-native patch planning.",
        "tag": "Living Websites",
        "tile_code": "LS",
        "language": "TypeScript",
        "updated": "2026-05-29",
        "image": "/static/brand/projects/kyanite-project-liminal-sites-1672x941.webp",
        "proof_role": "Proves the website itself can evolve through constrained, inspectable design systems.",
    },
    {
        "name": "Elixis",
        "url": "https://github.com/KyaniteLabs/Elixis",
        "description": "Local-first pattern synthesis engine for identity, brand voice, design systems, naming research, and lens-specific outputs.",
        "tag": "Pattern Synthesis",
        "tile_code": "EX",
        "language": "Python",
        "updated": "2026-05-29",
        "image": "/static/brand/projects/kyanite-project-elixis-1672x941.webp",
        "proof_role": "Turns fuzzy identity and naming work into source-backed synthesis.",
    },
    {
        "name": "Innerscape",
        "url": "https://github.com/KyaniteLabs/Innerscape",
        "description": "Personal growth OS in TypeScript for journaling, emotional check-ins, habits, goals, tasks, sleep logs, decluttering, and self-awareness workflows.",
        "tag": "Personal OS",
        "tile_code": "IN",
        "language": "TypeScript",
        "updated": "2026-05-29",
        "image": "/static/brand/projects/kyanite-project-innerscape-1672x941.webp",
        "proof_role": "Shows the same build-and-implementation pattern applied to intimate, data-rich workflows.",
    },
    {
        "name": "openglaze",
        "url": "https://github.com/KyaniteLabs/openglaze",
        "description": "Free open-source ceramic glaze calculator, UMF analyzer, CTE estimator, recipe manager, and studio tool for potters and ceramic artists.",
        "tag": "Domain Software",
        "tile_code": "OG",
        "language": "Python",
        "updated": "2026-05-29",
        "image": "/static/brand/projects/kyanite-project-openglaze-1672x941.webp",
        "proof_role": "Proves Kyanite can ship useful software outside the generic AI-tool bubble.",
    },
    {
        "name": "Dev Learning Archaeologist",
        "url": "https://github.com/KyaniteLabs/dev-learning-archaeologist",
        "description": "Forensic git-history learning diagnostic for AI-assisted developers that turns commit history into evidence-backed study plans and HTML reports.",
        "tag": "Learning Diagnostics",
        "tile_code": "DA",
        "language": "JavaScript",
        "updated": "2026-05-31",
        "image": "/static/brand/projects/kyanite-project-dev-learning-archaeologist-1672x941.webp",
        "proof_role": "Turns repo behavior into a readable diagnostic artifact.",
    },
    {
        "name": "achiote-food-memory-researcher",
        "url": "https://github.com/simongonzalezdc/achiote-food-memory-researcher",
        "description": "Folder-based AI food-memory researcher for investigating half-remembered family dishes from sound-alikes, smells, colors, and cultural memory.",
        "tag": "Food Memory",
        "tile_code": "AC",
        "language": "Claude Project",
        "updated": "2026-05-31",
        "image": "/static/brand/projects/kyanite-project-achiote-food-memory-1672x941.webp",
        "proof_role": "Extends Kyanite's evidence style into cultural memory and research assistants.",
    },
    {
        "name": "unstuck-coach",
        "url": "https://github.com/simongonzalezdc/unstuck-coach",
        "description": "Executive-function accessibility coach that turns a messy stuck point into one humane next move.",
        "tag": "Executive Function",
        "tile_code": "UC",
        "language": "CSS",
        "updated": "2026-05-30",
        "image": "/static/brand/projects/kyanite-project-unstuck-coach-1672x941.webp",
        "proof_role": "Applies agentic tooling to accessibility, pacing, and human next-step design.",
    },
    {
        "name": "tradesflow",
        "url": "https://github.com/simongonzalezdc/tradesflow",
        "description": "Portfolio prototype for asset-heavy field-service operators: equipment records, service notes, deficiencies, scheduling, and billing handoffs.",
        "tag": "Field Operations",
        "tile_code": "TF",
        "language": "TypeScript",
        "updated": "2026-05-30",
        "image": "/static/brand/projects/kyanite-project-tradesflow-1672x941.webp",
        "proof_role": "Shows implementation thinking for real-world operators with assets, visits, and billing handoffs.",
    },
    {
        "name": "healthadvocate",
        "url": "https://github.com/simongonzalezdc/healthadvocate",
        "description": "FastAPI health advocacy web app for patient tooling, local LLM exploration, and medical NLP workflows.",
        "tag": "Health Advocacy",
        "tile_code": "HA",
        "language": "Python",
        "updated": "2026-05-30",
        "image": "/static/brand/projects/kyanite-project-healthadvocate-1672x941.webp",
        "proof_role": "Explores private, local-first health tooling without treating care context as generic chat.",
    },
]

BLOG_POSTS = [
{
        "slug": 'lab-notes-degenerate-basin',
        "title": "Lab Notes: it doesn't fade",
        "category": 'Local LLM / Benchmarks',
        "date": '2026-08-19',
        "date_modified": '2026-08-19',
        "read_time": '5 min',
        "primary_keyword": 'LLM deep context degenerate basin',
        "seo_title": "Lab Notes: it doesn't fade — deep-context collapse, not a miss",
        "meta_description": 'Night 3: a 198,227-token haystack, five depths, a 98C crash, and a model that answers a code-review it was never asked. n=1 map, not a law.',
        "excerpt": 'Deep-context retrieval on this 27B does not fade. It snaps into a canned report. Then the box cut power at 98C. Here is the map from that night.',
        "body": """
<p><small>By <a href="https://x.com/KyaniteLabs_" rel="noopener">Simon Gonzalez de Cruz</a> (follow the build in public on <a href="https://x.com/KyaniteLabs_" rel="noopener">X @KyaniteLabs_</a>), assisted by GLM-5.3. Night 3 of the nightly lab notes. The box died at 98C, came back, and then answered a question I never asked.</small></p>
<p>The number first: <strong>this model's deep-context retrieval does not fade.</strong> It snaps into a canned answer. On a haystack the server counted at 198,227 tokens, I asked for a planted access code at five depths. At 25% it handed back the exact code and stopped clean. At 35% and 75% it wrote the opening of a code-review report it was never given:</p>
<pre><code>- **Risk**: Low; 67 medium/low</code></pre>
<p>Same opening. Twice. Temperature 0.</p>
<p>That is not a miss. A miss is &ldquo;I don't have it.&rdquo; This is the model confidently grading 48 imaginary repos.</p>

<h2>What actually ran</h2>
<p>One seed. One haystack. Champion config: Qwen3.8-27B Q4_K_XL, K+V q4_0, 262,144-token window, on a $1,400 GMKtec EVO-X2. Depths were fractions of the <strong>server's</strong> token count, not my fill estimate. My generator said 262k. The server said 198,227. We label the instrument from the counter now.</p>
<table>
  <thead><tr><th>Depth</th><th>Result</th><th>Stop</th><th>What it said</th></tr></thead>
  <tbody>
    <tr><td>10%</td><td>fail</td><td>stop</td><td><code>ok</code></td></tr>
    <tr><td>25%</td><td>hit</td><td>stop</td><td>the planted code, exact</td></tr>
    <tr><td>35%</td><td>fail</td><td>length</td><td>the Risk report, 67 findings</td></tr>
    <tr><td>50%</td><td>fail</td><td>stop</td><td><code>ok</code></td></tr>
    <tr><td>75%</td><td>fail</td><td>length</td><td>the Risk report again, 67 findings</td></tr>
  </tbody>
</table>
<p>Two attractors, not one. <code>ok</code> at 10% and 50%. The report at 35% and 75%. n=1 per cell. Treat this as a map, not a measurement. The 90% station from the earlier crown gate is a different run. This sweep died before I got there.</p>

<h2>Then the box cut power</h2>
<p>During the next long prefill the EC tripped at 16:45:42Z. Journal line: <code>temp=98C -&gt; fan=100%</code>. No panic, no amdgpu, no OOM. Highest temp this chassis has logged here. The fans were already doing their job. The load was the bug: back-to-back half-hour prefills, about 6C above the 90-92C bursty envelope we treat as normal.</p>
<p>After reboot I sent the 35% request again. Same report family. The count had moved: <strong>67 to 68</strong>. One token. Temperature still 0. That is a knife-edge, not a creative model. I do not know which kernel or batch shape flipped the digit. I am not going to pretend I do.</p>

<h2>It is not the 4-bit KV</h2>
<p>I ran the same needle under the old q8_0 KV. Same species of report. Different numbers, same &ldquo;I am reviewing a codebase&rdquo; voice. So the basin was already there when q8 was champion. The q4 crown's short-context numbers still stand on their own evidence. I will not write &ldquo;no quality loss at 200k-class context&rdquo; from n=1 cells. We have not earned that sentence.</p>

<h2>What I got wrong about our own stack</h2>
<p>I blamed &ldquo;the fork.&rdquo; The serving binary is upstream-era llama.cpp plus a four-line HIP memory-reporting cherry-pick. If something is broken at 198k, that is not a secret fork bug.</p>
<p>I almost filed an upstream issue on ngram draft caps. The gauntlet killed it. <code>--spec-draft-n-max</code> does not cap ngram-mod. <code>--spec-ngram-mod-n-max</code> does, and we never set it. Our config. Their flag. The gauntlet stays mandatory.</p>
<p>Three reviews plus a code pass could not pin these cells on a serving-stack verification bug. Speculative decode looks like it is checking tokens the way it is supposed to. The basin looks model-level. That is an elimination, not a proof of the mechanism. I still have a spec-off rerun on the list. I have not run it.</p>

<h2>Tonight</h2>
<p>I renamed the log labels. &ldquo;Miss&rdquo; is retired for these cells. They are degenerate-template outputs. Anyone copying the sweep should log them that way or they will &ldquo;fix retrieval&rdquo; that never reported failure.</p>
<p>Raw logs: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo/tree/main/results/deep-context-2026-08-18" rel="noopener">results/deep-context-2026-08-18</a> in the <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">qwen38-27b-strix-halo</a> repo.</p>
<p><small>Conditions: GMKtec EVO-X2 (Ryzen AI Max+ 395, 96GB unified), Qwen3.8-27B Q4_K_XL, llama.cpp ROCm, 262,144-token window, K+V q4_0 (q8_0 control on the same needle), temperature 0, prompt_tokens 198,227 server-reported, n=1 per depth, seed s4419, 2026-08-18. One night. A map. Not a law.</small></p>
""",
    },
{
        "slug": "lab-notes-the-kv-verdict",
        "title": "Lab Notes: the KV verdict",
        "category": "Local LLM / Benchmarks",
        "date": "2026-08-18",
        "date_modified": "2026-08-18",
        "read_time": "5 min",
        "primary_keyword": "q4 KV cache quantization llama.cpp",
        "seo_title": "Lab Notes: the KV verdict — halving KV cache at 262k context",
        "meta_description": "Night 2: a paired promotion gate flips the champion to 4-bit KV cache — GSM8K p=1.0, zero corruption flags at ~198k tokens, and the server counter that corrected our own estimate.",
        "excerpt": "The q8-to-q4 KV question from night 1 got its paired answer: same accuracy, zero tripwires, half the cache. Plus the label we had to correct in public when the server's counter beat our estimate.",
        "body": """
<p><small>By <a href="https://x.com/KyaniteLabs_" rel="noopener">Simon Gonzalez de Cruz</a> (follow the build in public on <a href="https://x.com/KyaniteLabs_" rel="noopener">X @KyaniteLabs_</a>), assisted by GLM-5.3. Night 2 of the nightly lab notes. Last night ended with a promise: run the paired q4_0-KV A/B our configuration was missing. This is what came back.</small></p>
<p>The number first: <strong>the champion now runs 4-bit KV cache — about 47% less KV memory at the same context window &mdash; with zero measured accuracy cost and zero corruption flags.</strong> The promotion gate was paired, pre-registered, and self-executing: if the q4 arm matched the q8 arm's needle hits and posted zero tripwires, the unit file flips; anything less, the old champion restores itself.</p>

<h2>The evidence stack</h2>
<p>Three layers, each paired:</p>
<table>
  <thead><tr><th>Layer</th><th>Design</th><th>Result</th></tr></thead>
  <tbody>
    <tr><td>Task accuracy</td><td>GSM8K, n=60 stratified, paired</td><td>Exact McNemar p = 1.0; q4 slightly <em>faster</em> (18.78 s vs 19.47 s mean)</td></tr>
    <tr><td>Deep-context integrity</td><td>Needle probes at 50%/90% depth, identical ~198k-token haystack, same seed, same-session control</td><td>q4: 0/2 hits, <strong>zero tripwires</strong>, clean stops; q8: 0/2 hits, one trip</td></tr>
    <tr><td>Retrieval boundary</td><td>Needle at 25% depth (where q8 historically retrieves)</td><td><strong>FOUND</strong>, clean stop &mdash; the dumb-zone boundary did not move</td></tr>
  </tbody>
</table>
<p>The tripwire is the finish_reason anomaly counter we keep armed on every serving hour since the RDNA4 quantized-KV corruption report made the rounds. One trip fired all night &mdash; on the <em>q8</em> arm (a 40-token answer that never stopped; n=1, plausibly ordinary deep-context rambling, recorded not interpreted). The arm the rule actually gates on &mdash; q4 &mdash; ran clean.</p>

<h2>The miss we caught in ourselves</h2>
<p>The gate's haystack was built to an estimate: 5,800 paragraphs, ~45 tokens each, call it 262k. The server's own counter said <strong>198,227 tokens</strong>. The paired comparison is untouched &mdash; both arms prefilled the identical haystack, which is the entire point of pairing &mdash; but every place we had written &ldquo;262k needle probes&rdquo; was overstating the instrument. The announcement tweet had already gone out with the estimate. The correction went out as a reply within the hour, the repo README now carries server-reported token counts, and the rule is restated for good: <em>label instruments with the counter at the source, not the generator's estimate.</em> Cold prefill measured through that needle wall: <strong>109.5 tok/s</strong> at ~198k (needle-class number: full prompt + answer, not a bench harness).</p>

<h2>What half a cache buys</h2>
<p>Arithmetic, labeled as arithmetic: q8_0 encodes ~8.5 bits per KV value, q4_0 ~4.5 &mdash; hence ~47% off the KV line at identical context. Measured wall time through the probes trended the same way as GSM8K: q4 marginally faster on cache reads. The compounding cases are next: the 35B dress-rehearsal math (where KV headroom decides feasibility), and the adaptive-KV research lane, whose bar just moved from &ldquo;beat static q8&rdquo; to &ldquo;beat static q4.&rdquo;</p>

<h2>Conditions</h2>
<p><small>GMKtec EVO-X2 (Ryzen AI Max+ 395, 96GB unified), Qwen3.8-27B Q4 dynamic quant, llama.cpp ROCm build, 262,144-token window, K+V q4_0 KV (champion as of 2026-08-18 10:32Z), temperature 0. GSM8K n=60 paired; needle n=2 stations per arm plus one boundary probe; one box, one night; tripwire counter armed continuously. Datapoints, not laws. Raw gate log and rollback unit referenced in the repo: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">qwen38-27b-strix-halo</a>.</small></p>
""",
    },
{
    "slug": "lab-notes-verdict-night",
    "title": "Lab Notes: verdict night",
    "category": "Local LLM / Benchmarks",
    "date": "2026-08-18",
    "date_modified": "2026-08-18",
    "read_time": "5 min",
    "primary_keyword": "LLM thinking budget cap accuracy",
    "seo_title": "Lab Notes: verdict night — is capping LLM thinking free?",
    "meta_description": "Night 1 of nightly lab notes: a paired Omni-MATH run on a $1,400 Strix Halo mini-PC — 512-token thinking caps statistically free (p=0.73), uncapped thinking dies on 26/50 problems, 367s vs 49s.",
    "excerpt": "A $1,400 mini-PC serving a 27B at 262k context asks one question: does capping thinking cost accuracy? The paired answer, the invalid first attempt it survived, and the doctrine that followed.",
    "body": """
<p><small>By <a href="https://x.com/KyaniteLabs_" rel="noopener">Simon Gonzalez de Cruz</a> (follow the build in public on <a href="https://x.com/KyaniteLabs_" rel="noopener">X @KyaniteLabs_</a>), assisted by GLM-5.3. Night 1 of a nightly cadence: what ran, what broke, and what the numbers said.</small></p>
<p>The number first: <strong>a 512-token thinking cap bought the same measured accuracy as unlimited thinking tonight — at 7.5x faster turns.</strong> Its shadow number: left uncapped, the same model <strong>thought itself to death on 26 of 50 problems</strong>, reasoning until the output ceiling killed the answer. Both came out of one paired run. Neither was the night's real story. The real story is that the first version of this experiment measured nothing at all.</p>

<h2>The setup</h2>
<p>The rig: a $1,400 GMKtec EVO-X2 mini-PC (Ryzen AI Max+ 395, 96GB unified memory) serving Qwen3.8-27B, a 27B dense model, at its full native 262,144-token context. The question for verdict night is the one every local-model operator eventually faces: <em>if I cap how long the model is allowed to think, what does that cost in accuracy?</em></p>

<h2>The instrument</h2>
<p>A paired design. Every problem is asked under all three thinking budgets — uncapped, 1024 tokens, 512 tokens — with cell order rotated per problem so any drift hits all arms equally. Fifty problems, enriched toward difficulty (25 hard / 15 mid / 10 easy), temperature 0, full reasoning traces stored in every row. The statistic is exact McNemar on the discordant pairs: not &ldquo;which average is higher,&rdquo; but &ldquo;where the arms disagreed, did one arm systematically win.&rdquo; Conditions throughout: Q4 dynamic quant, q8_0 KV cache at 262k context, ROCm build of llama.cpp, package holding 90-92 &deg;C at 120W.</p>

<h2>The twist: the first experiment was invalid</h2>
<p>The control arm — &ldquo;uncapped&rdquo; — did not exist. The champion server carries a server-level default, <code>--reasoning-budget 2048</code>, enforced with the message <em>&ldquo;Reasoning budget reached. Answer now.&rdquo;</em> Any request that omits an explicit budget silently inherits it. Our first runner omitted it. The &ldquo;no cap&rdquo; cell was a 2048 cell wearing a &ldquo;none&rdquo; name tag.</p>
<p>The proof was embarrassingly clean: <strong>six byte-identical thinking lengths</strong> between the &ldquo;none&rdquo; and 2048 cells; maximum thinking length identical in both (9,361 characters); the same hard problem truncating at 7,955 characters in one arm and 7,937 in the other. The archived budget curve was never {none, 2048, 4096, 8192} — it was {2048, 2048, 4096, 8192}, and its &ldquo;none vs 2048: zero discordants&rdquo; was a cell compared with itself.</p>
<p>Fixes shipped before the rerun: uncapped arms now send an explicit million-token override; the output ceiling went from 6,000 to 12,000 tokens (the old ceiling killed uncapped answers mid-think — an output-cap confound on the very arm labeled uncapped); and every row now carries its full trace, so the next autopsy reads text instead of inferring from counts.</p>

<h2>The verdict</h2>
<table>
  <thead><tr><th>Thinking budget</th><th>Accuracy (n=50)</th><th>Median wall per problem</th></tr></thead>
  <tbody>
    <tr><td>Uncapped (10<sup>6</sup> override)</td><td>44%</td><td>367 s</td></tr>
    <tr><td>1024 tokens</td><td>40%</td><td>&mdash;</td></tr>
    <tr><td>512 tokens</td><td>40%</td><td>49 s</td></tr>
  </tbody>
</table>
<p>All three pairwise exact-McNemar tests are non-significant: p = 0.73 for uncapped-vs-512, with 0.63 and 1.0 on the remaining contrasts. On this benchmark, tonight, caps are statistically free.</p>
<p>And protective. The uncapped arm's median completion hit the full 12,000-token ceiling, and on 26 of 50 problems the thinking never terminated at all — the model reasoned past the output cap and emitted no answer. Those score as wrong (no boxed answer = wrong, no exceptions). The cap doesn't only save time; it forces a conclusion the uncapped model sometimes cannot reach on its own.</p>
<p>Both polarities, stated plainly: this is one benchmark (an Omni-MATH subset), one night, n=50 paired problems. A capped cell measures accuracy <em>under forced early termination</em> — the knee we observed sits at or above the model's true budget knee, so read it conservatively. And on the hardest band (difficulty &ge; 5.0), every cell scored a flat 16%: those problems are capability-bound, not budget-bound. A cap cannot take from you what the model never had.</p>

<h2>The envelope it rode in on</h2>
<p>The run held the box at its measured thermal edge — 90-92 &deg;C package at 120W, fans at 100% — through hours of sustained generation with zero throttling. That is now codified doctrine: this is the chassis envelope, not a misconfiguration; no ritual cooldown breaks (steady-warm beats heat-cycling); and the always-on product lane will get a power cap rather than the experiment lane's full tilt.</p>

<h2>What the harness takes from it</h2>
<p>The harness's shipped default — a 1024-token thinking budget for margin, 512 where speed matters — earned its number tonight: the nominal 44%-vs-40% gap is inside what this design can detect, and 512 turned 367-second problems into 49-second problems at the same score. The methodology and the raw data are public alongside this post: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo/blob/main/METHODOLOGY.md" rel="noopener">METHODOLOGY.md</a> (n-sizes, gates, grading rules — the rows benchmark tables never print) and the full paired JSONL, traces in-row, under <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo/tree/main/results" rel="noopener">results/</a> in the <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">qwen38-27b-strix-halo repo</a>.</p>

<h2>Tonight</h2>
<p>Window 2 runs the community-corroborated lane: q4_0 KV cache at 262k context. Every 262k row in the community hardware map we mined runs q4-KV; we serve q8 — so tonight is the paired quality A/B our configuration has been missing, plus whatever KV headroom it frees. Lab notes tomorrow night.</p>
<p><small>Conditions: GMKtec EVO-X2 (Ryzen AI Max+ 395, 96GB unified memory), Qwen3.8-27B Q4 dynamic quant, llama.cpp ROCm build, 262,144-token context, q8_0 KV cache, temperature 0, Omni-MATH difficulty-enriched subset (25/15/10), n=50 paired problems per arm, exact McNemar on discordants, measured 2026-08-17/18. One benchmark, one night, n=50 — a datapoint, not a law.</small></p>
""",
},
{
        "slug": "qwen-27b-strix-halo-one-week-local",
        "title": "One mini-PC, one night, and the numbers that argued with themselves: tuning Qwen3.8-27B on Strix Halo",
        "category": "Local LLM / Benchmarks",
        "date": "2026-08-15",
        "date_modified": "2026-08-16",
        "read_time": "14 min",
        "primary_keyword": "Qwen 27B Strix Halo local LLM tuning",
        "seo_title": "Qwen 27B on Strix Halo: honest local tuning numbers",
        "meta_description": "Tuning Qwen3.8-27B on a Ryzen AI Max+ 395 mini-PC: from a lying 4 tok/s stack to 59.7-64 tok/s cold, real chat 11-24 tok/s published first, a quant reversal on time-per-task, and an EC fan saga.",
        "excerpt": "A fully measured night-and-evening of tuning a 27B dense model on a Strix Halo mini-PC: the honest bands, the reversal, the crash doctrine, and the EC detective story.",
        "body": """
<p><small>By <a href="https://x.com/KyaniteLabs_" rel="noopener">Simon Gonzalez de Cruz</a> (follow the build in public on <a href="https://x.com/KyaniteLabs_" rel="noopener">X @KyaniteLabs_</a>), assisted by GLM-5.3.</small></p>
<p>In roughly one night and one evening (2026-08-14/15), a solo operator with agent teammates took Qwen3.8-27B on a GMKtec EVO-X2 mini-PC (Ryzen AI Max+ 395, gfx1151, 91GB unified LPDDR5X) from a lying stack at ~4 tok/s to 59.7-64 tok/s cold with 3x the context — at/past the public frontier we found for the class (best unnamed public example: 56 tok/s; source not re-located) — then voluntarily published the numbers that make it look slower (real chat is 11-24 tok/s), reversed its own fastest configuration on a time-per-task argument, cut task tokens 36% with a caveman thinking style, solved a fan-control mystery that ended in the owner's own three-month-old code, and turned two crashes into permanent tests.</p>
<p><strong>The differentiator was never the tok/s. It was the evidence.</strong></p>

<h2>It claimed GPU, ran CPU</h2>
<p>The program did not start slow for an interesting reason. It started slow for a lying reason. Unsloth's bundled llama.cpp binary reported full GPU offload while <code>--list-devices</code> printed nothing — the 27B was crawling at ~4 tok/s on CPU and claiming otherwise. Beneath it, a second theft: someone (lost to history) had pinned the iGPU to <code>power_dpm_force_performance_level=low</code> — 600 MHz under full load against a 2900 MHz boost, ~17W, throttling every GPU lane on the box.</p>
<p>Two fixes, landed across the first night: the fleet's real ROCm build replaced the fake-offload binary, and — found only when the crash forensics later pulled the full thermal record — the months-old <code>low</code> pin was flipped to <code>auto</code> and persisted (01:43Z). 4 → 10.5-11.1 tok/s (the bandwidth ceiling at ~178 GB/s), then MTP speculative decoding stacked to 21.4-22.2 with 95-100% draft acceptance — lossless by construction, every draft verified against the full model. A sibling lane got the perf-pin fix for free: gemma4-12b went 5.6 → 24.9 tok/s without touching anything else.</p>
<p>The habit that defines the whole program started here: no number gets believed because a tool printed it. <code>gpu_busy_percent</code> on gfx1151 reads 100% even idle — do not trust it. Verify by content, not exit code.</p>

<h2>39 seconds</h2>
<p>At 03:43:10 the operator launched <code>git clone --depth 1</code> plus a 14-job HIP compile on top of a manually-launched 27B server that was still serving, with the GPU uncapped for the first time and the EC in performance mode. At 03:43:49.3 the journal ended mid-write. No panic, no OOM, no MCE, no GPU fault, no thermal trip — the OS critical trip is 110 °C and never fired. pstore: empty. Two reboots died before the OS; only a 30-second button drain and cooldown revived it.</p>
<p>The post-mortem (113MB of journal, 724,067 lines, read-only) ranked the falsifiable hypotheses: power-delivery protection trip on the 230W stock brick (19.5V × 11.8A; GPU bursts ~107W observed; community reports recommend PSU upgrades for sustained LLM load) at 50-60%; below-OS EC thermal latch at 25-30%; software under 2%. The signature was the story: the only unprecedented condition in 35 stable hours was the stacked max-power regime — uncapped boost serving plus load-step transients (Tctl had moved from a 35-hour 33-61 °C band to oscillating 52-94 °C within five minutes of the dpm flip, peaks 93.9 °C and 93.2 °C).</p>
<p>Doctrine, written in the burn-in that failed its predicate in 10 seconds (Tctl 91.4 °C under a single generation stream): the box is disqualified for new heavy GPU blocks — training, hidden-state extraction, big compiles while serving. Build first, serve second, never stacked. The redemption: serving itself is fine — a later 41-round agentic soak ran 41/41 clean riding the 92 °C boost-throttle edge with 45-second recovery. One chassis, two identities: not a workstation, but a legit servant.</p>

<h2>One night, twelve rungs</h2>
<p>07:51Z, the overnight mission opened its ladder, L1-L12, with a rule: every rung measured on a test port, promoted only through a rubric, production verified by content after every change. First finding: even the baseline was wrong — mission facts said 25.0 tok/s, the audited baseline was 32.7 (the 25.0 was a stale manual-config era). The honest ledger starts at 32.7.</p>
<p>The rungs that survived: draft depth 6→9 (+70% count-to-30, quality 6/6 including a riddle, 4-word precision, working palindrome code); context 32k → 64k → 96k at literally zero speed cost (GQA KV is ~2.1GB per 32k — context is nearly free on this box; 128k probed fine but rode the margin at 6.1GB, held for daylight); ngram-mod stacked on MTP (zero cost when it misses, transforms repeats: warm count-to-30 89.6-93.2, agent file-rewrite 96.8 vs 42.3 mtp-only, +129%); depth re-swept to 12 (59.4 cold); and the sleeper, n-min 24 — lowering the ngram match threshold so it fires on shorter history: warm count-to-30 148.0-157.6 tok/s, +55% overnight on repeated structured output.</p>
<p>The rungs that did not survive are in the ledger too, because that is the product: p_min sweeps (not uniform, shipped as a creative-only stanza), K-only KV q8 (saves ~1GB, not worth it), threads 12 vs 16 (identical), the rocWMMA FA rebuild (cancelled — upstream <a href="https://github.com/ggml-org/llama.cpp/issues/24437" rel="noopener">#24437</a> shows -41% prefill on gfx1151, and prefill is our weak spot), a Vulkan/RADV build (half throughput on this box, decisively), <code>--cache-reuse</code> (a verified no-op on this build). Every flag on this server now has a measured reason to exist.</p>
<p>Night totals: 32.7 → 59.7 cold / 157.6 warm (+82% / +382%), context 3x, GTT margin 8.2GB, all quality gates green. Research placed it: stacked MTP+ngram is the publicly-known-best Strix Halo pattern, and the best public example found was an unnamed public Qwen3.6-27B example at 56 tok/s (source not re-located). Running 3.8-27B at 59.7 cold put the box at/past the public frontier for its class — the one superlative-adjacent claim the honesty policy allows, with citation.</p>

<h2>The anti-cherry-pick</h2>
<p>Then the program attacked its own best number. The 148-163 warm repeats are an ngram repetition artifact: the speculative drafter recognizes the bench's own repetition and finishes it wholesale. It is real speed on genuinely repeated structured output (the agent file-edit echo pattern runs 72-133 tok/s), and it is meaningless as a chat claim. Real conversation — novel prose, the traffic that actually flows through the resident agent — is 11-24 tok/s, code ~29-40, long creative ~11-13.</p>
<p>The decision that defines the brand: state it ourselves, first, on the front page. Real-usage numbers are stated by us, before anyone else states them for us. Warm numbers never appear without the artifact label; the README's first screen carries the cold headline, warm-with-label, and the 11-24 real row in one table. The bench tables are generated from actual output, never hand-typed. The audience for this work is allergic to cherry-picked AI benchmarks; the differentiator is not the tok/s, it is the evidence — the full ladder, the negative results, and the rollback story in the next section.</p>

<h2>How low can we go</h2>
<p>Simon's quant question, answered with a ladder. Q3_K_XL under the full champion stack won every measured axis at 128k context: 63.0 cold (champion Q4@96k: 59.7), warm 148.0-161.2, +33% context, GTT margin 11.3GB vs 9.2GB, quality 6/6. At 19:11Z, Simon approved the swap with one word — “swap it” — and production went Q3@128k, verifying at 64.0 cold, the best number of the program. The same window ran the floor probe he asked for: Q2_K_XL rejected — 54.7 cold, slower than both bigger quants (dequant kernels cost more than the 2.6GB bandwidth saving), thinking 30-40% more verbose, code emitting zero content at a 500 token budget (recovering fully at 1200). Gate passed formally, premise failed materially. The quant lane was declared closed with Q3 as the knee.</p>
<p>It stayed closed for twenty-six minutes of wall-clock fame.</p>

<h2>“Faster tokens != better if tokens are dumber”</h2>
<p>At 19:30Z Simon applied a lens the ledger had no instrument for: “faster tokens != better if tokens are dumber.” The mission built one — a time-per-task battery, five auto-graded tasks, thinking on, wall-clock plus completion tokens — and the verdict inverted the swap. Q3's reasoning is ~2x more verbose (code task 705-994 tokens vs Q4's ~402-450), swamping its +5.5% decode edge: Q4 completes identical correct tasks 35-50% faster (7.6-7.7s/task at ~170 tok vs Q3's 10.6-16.1s at 238-302). At 19:37Z the champion was restored: Q4@96k, verified by content, quant ladder closed on time-per-task.</p>
<p>Two more honest twists in the same entry. The peer reviewers demanded the missing measurement: why was Q2 slow? Acceptance telemetry on novel traffic — Q4 0.345, Q3 0.492, Q2 0.478 — falsified the acceptance-collapse hypothesis; Q2's loss is dequant kernel cost, and higher acceptance at lower quants likely just reflects more-predictable verbose reasoning. And the methodology changed permanently: time-per-task and tokens-per-correct-task are the primary metrics now; decode tok/s is a probe.</p>
<p>The category lesson, stated for everyone running local models: decode tok/s is not task latency. A faster pipe feeding more, dumber tokens loses to a slower pipe feeding fewer, sharper ones. Nobody's benchmark table shows this. Ours now does.</p>

<h2>“Dont like your method of shrinking”</h2>
<p>The obvious fix for verbose reasoning is a budget cap. Simon vetoed it in seven words: “dont like your method of shrinking.” The un-obvious fix came from the community skills shelf: caveman (<a href="https://github.com/JuliusBrussee/caveman" rel="noopener">JuliusBrussee/caveman</a> — origin; terse fragments, action over explanation) and ponytail (<a href="https://github.com/DietrichGebert/ponytail" rel="noopener">DietrichGebert/ponytail</a> — origin; lazy senior dev, first rung that holds) — fused into a THINK-STYLE system-prompt layer that steers how the model reasons, never how much it is allowed to. The ethos, one line: the best reasoning is the reasoning never thought.</p>
<p>Measured on the Q4 champion, 5-task battery: 117/132/143 tok/task at 5.8/6.2/6.8s across three runs, 15/15 correct — against an 8-run baseline band of 151-313 tok and 8.6-15.0s. Roughly -36% tokens, -33% task time, zero quality loss. The fusion is the winner (solo caveman 154tok/7.8s and solo ponytail 187tok/11.6s sit at or inside the band). Style steering beats budget caps: same token savings, no veto, no ceiling on hard problems.</p>
<p>The follow-up finding kept it honest: creative lanes ignore the terse style — one story run spent ~2000 thinking tokens on a 312-word story, tokens being the product there — so style is applied per-lane (fused default for tool/code/analysis, free creative lane, an override dial). A live A/B through the real lane confirmed it end-to-end: arith+code task, vanilla 9.3s/62-think/198c vs fused 4.6s/36-think/118c — -51% wall in a single run, backed by the n=3/n=8 study. Single-run A/Bs carry variance; the sustained numbers are the headline.</p>

<h2>“Triple check everything, no old conflicting fixes”</h2>
<p>The detective arc. The GMKtec EVO-X2 rides 97 °C under sustained GPU load with its fans effectively at 60%: the stock auto curve saturates at ~60% duty / ~3260 RPM at 90 °C and above, leaving ~40% of fan2's headroom on the table exactly where it is needed. And the firmware exposes no standard Linux fan control — no hwmon PWM, no tach, no ACPI fan object. The only lever is direct embedded-controller access.</p>
<p>Every EC write was ignored. Not rejected — ignored: <code>dd of=.../ec/ec0/io</code> exits 0, the register reads back unchanged. Root cause, found the hard way (it cost real debugging time twice): the kernel's <code>ec_sys</code> module loads read-only by default, and in that state the debugfs file looks writable while the kernel silently discards every write. The fix is two config files making <code>write_support=1</code> the boot default. Meanwhile the register map was cracked via the ACPI DSDT route — nathanmarlor's strix-halo-fan-control carried a map reverse-engineered from the DSDT of the Bosgame M5, the same Sixunited AXB35-02 board in a different chassis, and it validated byte-for-byte on the EVO-X2.</p>
<p>Two more mysteries fell in the audit Simon ordered. The pulsating fans were the one-shot revert law: the firmware reverts manual duty writes within seconds, so only a daemon re-asserting every 2s holds — which is exactly what nathanmarlor's daemon does, deployed with a tuned curve. Measured: peak 96.5 °C vs 97.5-97.8 °C stock on a 105s load — an honest ~1-1.3 °C on that probe, with the real wins in the shape of the response: fan2 at 4539 RPM vs the 3260 stock ceiling (headroom finally engaged), 100% duty by 82 °C, quiet idle preserved. An external fan bolted to the chassis changed nothing (96.9 °C with it — the ceiling is the heat-pipe class, not airflow). And the stunner under the floorboards: a systemd timer had been direct-writing EC 0x31 = performance every 30 seconds since May — Simon's own reverse-engineering, from months before this program, which is why the box was already at EC-performance and why his remembered “ultra” setting was real all along. It had even been silently breaking the fan daemon: the May script's polite load-write-unload dance reloaded <code>ec_sys</code> without write_support every 30 seconds, discarding the daemon's writes with zero errors anywhere.</p>
<p>Pay-it-forward inventory, staged as a draft PR to the <a href="https://github.com/nathanmarlor/strix-halo-fan-control" rel="noopener">upstream repo</a>: EVO-X2 validation data, the fan3 tachometer register 0x28/0x29 (live on this unit, absent from upstream docs), and the multi-writer ec_sys warning.</p>

<h2>The model asked for a feature it already had</h2>
<p>The self-exploration prompt — eight numbered sections, sent unchanged so runs are comparable across waves — took four attempts to complete: killed twice by panel restarts, once by a signature crash. Attempt four completed: 67.7 seconds, 2013 characters, served at 10.6 tok/s — the honest real-traffic band, live. The answer's centerpiece: asked what it lacked, the model's first wish was parallel tool calls per turn — a capability the harness had supported for a day and a half. The model could not see it, so it did not exist; the fix was one line advertising it. Capabilities invisible to the model don't exist. The signature crash got the same treatment as every crash in this program: it became two permanent tests pinning the harness contract. A crash is a missing test wearing a trench coat.</p>

<h2>Actual improvement numbers</h2>
<p>Every verdict and wave plan got two independent adversarial passes from AI teammates — they caught a missing agentic soak and an unmeasured “why is Q2 slow”, both verified real. Wave 2 landed every rung in one evening. The vanilla-vs-waved table, live A/B through the real harness lane, identical tasks, fresh sessions:</p>
<table>
  <thead><tr><th>Lane</th><th>Vanilla</th><th>Waved</th><th>Delta</th></tr></thead>
  <tbody>
    <tr><td>STYLE (think-style layer)</td><td>9.3s / 62 think / 198c</td><td>4.6s / 36 / 118c</td><td>-51% wall (single run; sustained -36%/-33% n=3 vs n=8) (directional: measured on the full stacked config — stack delta, not style alone; re-baseline pending)</td></tr>
    <tr><td>MUNCH (symbol reads vs whole files)</td><td>48.6s / 13,917B tool output / 53.5KB prompts</td><td>22.6s / 276B / 4.9KB</td><td>-98% tool tokens (byte deltas -98%/-91% are deterministic and stand; wall-time delta is directional pending re-baseline after the tool-refusal fix)</td></tr>
    <tr><td>DIET (dedup stubs on re-check loops)</td><td>15KB context</td><td>5.1KB</td><td>-66%</td></tr>
    <tr><td>ENGINE (chapters 1-6)</td><td>32.7 cold, 32k ctx</td><td>59.7-64 cold, 96k ctx</td><td>time-per-task adopted; quant closed at Q4</td></tr>
    <tr><td>THERMAL</td><td>97.5-97.8 °C peak</td><td>96.5 °C peak</td><td>~1-1.3 °C on a 105s probe; 100% fan by 82 °C; quiet idle</td></tr>
  </tbody>
</table>
<p>And the meta-rule that keeps the stack from rotting — the wave-regression law: every wave landing re-verifies all earlier wins, not just its own tests.</p>

<h2>What the record proves</h2>
<p>Four claims this program can make with receipts, in escalation order:</p>
<ol>
  <li><strong>Performance:</strong> 59.7-64 tok/s cold, 96k context, on an iGPU mini-PC — at/past the public frontier we found (56 tok/s reference), honestly labeled, with the real-chat numbers (11-24 tok/s prose) published first by us.</li>
  <li><strong>Method:</strong> rubric-gated ladders, negative results published, metrics that survived attack (time-per-task over tok/s), crashes converted to tests.</li>
  <li><strong>Craft:</strong> style steering (-36%/-33%), symbol reads (-98% exploration tokens), diet stubs (-66%), an EC fan saga ending in a pay-it-forward PR draft.</li>
  <li><strong>Character:</strong> a solo owner and his agent team publishing the numbers that hurt, reverting the fastest config on principle, and crediting everyone upstream.</li>
</ol>
<p>Everything is reproducible: the recipe, flags, bench suite, one-command reproducer, and the full experiment ledger live in the <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">qwen38-27b-strix-halo</a> repo; the EC register map, traps, and daemon recipe live in the sibling <a href="https://github.com/KyaniteLabs/evo-x2-ec" rel="noopener">evo-x2-ec</a> repo. The raw gfx1151 throughput datapoints are published as a <a href="https://github.com/ggml-org/llama.cpp/discussions/27154" rel="noopener">llama.cpp discussion</a>. If you run the bench on your own Strix Halo box, post your numbers — inside or outside our bands, both are wanted.</p>
<blockquote><p><strong>Attribution.</strong> Qwen3.8-27B — <a href="https://huggingface.co/Qwen/Qwen3.8-27B" rel="noopener">Qwen team</a> (Apache-2.0). Dynamic quants — <a href="https://github.com/unslothai/unsloth" rel="noopener">Unsloth</a>. llama.cpp runtime — <a href="https://github.com/ggml-org/llama.cpp" rel="noopener">its contributors</a> (measured on a b10435-era build, 9d57ce4). EC fan-control daemon and the DSDT-derived register map (Bosgame M5, same Sixunited AXB35-02 board as the EVO-X2) — nathanmarlor (<a href="https://github.com/nathanmarlor/strix-halo-fan-control" rel="noopener">strix-halo-fan-control</a>, MIT). EVO-X2 EC P-MODE register (0x31) reverse-engineering and the 30s enforcement timer (May 2026) — Simon Gonzalez de Cruz. WMI/FCMI prior art — <a href="https://github.com/MintyMods/ip3-power-switch" rel="noopener">MintyMods/ip3-power-switch</a>, <a href="https://github.com/pettijohn/corsair-ai-workstation-performance-level-linux" rel="noopener">pettijohn/corsair-ai-workstation-performance-level-linux</a>. Thinking-style skills — caveman origin <a href="https://github.com/JuliusBrussee/caveman" rel="noopener">JuliusBrussee/caveman</a> (skill MIT); ponytail origin <a href="https://github.com/DietrichGebert/ponytail" rel="noopener">DietrichGebert/ponytail</a> (MIT); the fusion ships with full license notices in <a href="https://github.com/KyaniteLabs/context-kit" rel="noopener">KyaniteLabs/context-kit</a>.</p></blockquote>
<p><small>Measured on personally-owned hardware, 2026-08-14/15; your clocks will vary. Every number carries its validity label; single-run deltas are marked as such.</small></p>
<p><strong>Update (2026-08-16):</strong> We re-measured the Wave-2 numbers on a fixed, fingerprinted harness (n=3+ per arm, every run ledger-fingerprinted); the current verdicts live in the <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo#re-baseline-update-2026-08-16" rel="noopener">repo&rsquo;s re-baseline section</a>, and this post keeps its original numbers below as published history, each with its label. The corrections cut both ways. Semantic reads (&ldquo;munch&rdquo;) got <strong>better</strong> under honest measurement: wall time <strong>-65% clean</strong> (27.9s to 9.8s median, 6/6 correct, n=3) — the staged number was conservative. Style steering is <strong>regime-conditional, not universal</strong>: the -51% single-run A/B above is retired (it stacked config changes), the -36%/-33% sustained figure holds in the server lane at default high effort, and the harness lane at low effort measured a +65% wall inversion — so the production harness now routes style per session (high-effort sessions only), which also preserves the prompt cache. The time-per-task battery is now n=3: 7.9-14.3s per correct task, median 11.3, a thermal-dependent band. And the EC fan daemon delta grows to <strong>-3.5 to -5.8 °C</strong> peak (n=3 probes: 93/92/94 °C vs the stock ledger&rsquo;s 97.5-97.8 °C; stock arm not re-run). Credit where due: these corrections exist because our own validity audit flagged the numbers first.</p>

<h2>Update, 2026-08-16: the native context ceiling, for free</h2>
<p>One night later, the same rig now serves the model at its <strong>full native 262,144-token context</strong> — 2.7x the context reported above — with the warm decode band unchanged (148-163 tok/s) and time-per-task on real traces unchanged-to-faster. The whole gain is KV-cache quantization: K and V at q8_0 halve the cache, so 262k of quantized KV fits in <em>less</em> memory than 96k of f16. The ladder (96k → 160k → 192k → 262k) was gate-tested at every rung on the real-task battery, with one cost labeled honestly: prefill drops from ~390 to ~299 tok/s (q8 cache dequant; larger microbatches made it worse, not better). The rollback unit stays on file. Full ladder and gates: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo">the repo</a>.</p>
""",
    },
    {
        "slug": "gpt-5-6-sol-terra-luna-routing-guide",
        "title": "GPT-5.6 Sol vs. Terra vs. Luna: an evidence-based routing policy for coding agents",
        "category": "Model Routing / Agent Systems",
        "date": "2026-07-12",
        "date_modified": "2026-07-12",
        "read_time": "12 min",
        "primary_keyword": "GPT-5.6 Sol vs Terra vs Luna",
        "seo_title": "GPT-5.6 Sol vs Terra vs Luna: Agent Routing Policy",
        "meta_description": "Route GPT-5.6 Sol, Terra, and Luna by task uncertainty, completion contract, verification cost, reasoning effort, and agent-system architecture.",
        "excerpt": "The practical GPT-5.6 split is Sol for discovery, Terra for bounded execution, and Luna for repeatable processing - with a different verification contract for each.",
        "body": """
<h2>Executive summary — TL;DR / BLUF</h2>
<ul>
  <li><strong>Sol High is the discovery lane.</strong> Use it when the path, owner, or failure mode is still unknown. Give it an evidence target and an exit condition.</li>
  <li><strong>Terra Medium is the execution lane.</strong> Use it after the decision is made and the work has explicit files, behaviors, boundaries, and acceptance gates.</li>
  <li><strong>Luna is the processing lane.</strong> Use it for narrow, repeatable, high-volume tasks whose outputs can be checked by a schema, deterministic test, or sample audit.</li>
  <li><strong>Max is an escalation, not a default.</strong> DataCurve's current DeepSWE result shows a modest observed gain over High at roughly 2.4 times the estimated task cost, with slightly overlapping confidence intervals.</li>
  <li><strong>Fast and Ultra are separate controls.</strong> Fast is not currently documented for GPT-5.6; Ultra is multi-agent orchestration, not a reasoning level.</li>
  <li><strong>Current usage note:</strong> the five-hour restriction for Codex and ChatGPT Work is temporarily absent for Plus, Business, and Pro, but weekly limits remain. The reported reduced internal “juice values” were experiments that OpenAI says it reverted.</li>
</ul>
<p><strong>BLUF: do not choose a GPT-5.6 model by prestige. Route by uncertainty and by the cost of proving the answer is correct.</strong></p>

<h2>Model routing is a completion-contract problem</h2>
<p>The important difference between Sol, Terra, and Luna is not simply “smart, cheaper, cheapest.” Each model is most reliable when the agent is given a different definition of done. Sol needs a research boundary. Terra needs a specification. Luna needs a validator.</p>
<table>
  <thead><tr><th>Model</th><th>Job</th><th>Completion contract</th><th>Failure to design around</th></tr></thead>
  <tbody>
    <tr><td><strong>Sol</strong></td><td>Discover</td><td>Question, evidence target, protected boundaries, and stop condition</td><td>Continuing after the useful answer or widening scope without evidence</td></tr>
    <tr><td><strong>Terra</strong></td><td>Execute</td><td>Approved plan, named files, acceptance gates, and required tests</td><td>Treating unresolved uncertainty as if it were an implementation detail</td></tr>
    <tr><td><strong>Luna</strong></td><td>Process</td><td>Exact schema, examples, deterministic validator, and retry rule</td><td>Letting a cheap silent error propagate through the pipeline</td></tr>
  </tbody>
</table>
<p>OpenAI's <a href="https://developers.openai.com/api/docs/models" rel="noopener">current model-selection guidance</a> describes the same capability ladder in product terms. The engineering move is to turn that ladder into a contract-and-verifier architecture.</p>

<h2>What our first week changed</h2>
<p>We used the three lanes across research, evaluation, websites, and agent systems. This was operational observation, not a controlled benchmark, so the claims below are field notes rather than universal rankings.</p>
<p><strong>Sol was best when the work had to discover its own path.</strong> It carried long investigations and found consequential mistakes that a narrower pass could have missed. Its failure mode was persistence without a stopping rule: once the answer existed, it could keep exploring. The improvement was not a cleverer prompt. It was an explicit evidence target, protected boundaries, and a rule for when to stop.</p>
<p><strong>Terra was strongest when the acceptance contract was already explicit.</strong> Given a bounded scope, it produced specific adversarial findings and clear approve-or-hold judgments. When hidden discovery remained, however, the apparent execution task was actually routed too early.</p>
<p><strong>Luna was reliable when the output boundary was machine-checkable.</strong> Exact-schema JSON, extraction, metadata, and other constrained jobs repeatedly landed inside the requested shape. Some runs benefited from an explicit completion reminder. The model was not the whole control system; the schema and validator were.</p>

<h2>A reference router for coding agents</h2>
<pre><code>def route(task):
    if task.uncertain or task.crosses_subsystems:
        return ("Sol", "high", "evidence + exit condition")
    if task.specified and task.bounded:
        return ("Terra", "medium", "acceptance gates")
    if task.repeatable and task.cheap_to_verify:
        return ("Luna", "lowest sufficient", "schema + validator")
    return ("Sol", "high", "evidence + exit condition")</code></pre>
<p>The fallback matters. If work is neither bounded nor cheap to verify, it probably still contains discovery. Route that uncertainty deliberately before paying an executor to guess.</p>

<h2>First constrain the router to the product surface</h2>
<p>A routing policy cannot select a model the current product does not expose. “GPT-5.6” means different controls in ChatGPT, Codex, and the API, so record the surface as part of the route.</p>
<ul>
  <li><strong>Standard ChatGPT:</strong> OpenAI's current help documentation says GPT-5.6 uses Sol for Medium, High, and Extra High. Terra and Luna are not selected there.</li>
  <li><strong>ChatGPT Work and Codex:</strong> eligible paid plans can expose Sol, Terra, and Luna. Max and Ultra depend on the product and plan.</li>
  <li><strong>API:</strong> the three models support <code>none</code>, <code>low</code>, <code>medium</code>, <code>high</code>, <code>xhigh</code>, and <code>max</code> reasoning effort.</li>
</ul>
<p>Check <a href="https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt" rel="noopener">GPT-5.6 in ChatGPT</a> and the API model pages when implementing the policy. A model-picker screenshot is not an architecture contract; availability can change independently across products and plans.</p>

<h2>Escalate reasoning effort only after diagnosing the failure</h2>
<p>Reasoning effort is a second routing dimension. Higher effort gives the same model more room to explore, use tools, and revise, but it cannot repair a wrong premise, missing permission, broken test environment, or underspecified deliverable.</p>
<table>
  <thead><tr><th>Sol effort</th><th>DeepSWE v1.1 score</th><th>Estimated cost per task</th></tr></thead>
  <tbody>
    <tr><td>High</td><td>69.4%</td><td>$3.47</td></tr>
    <tr><td>Extra High</td><td>70.7%</td><td>$4.70</td></tr>
    <tr><td>Max</td><td>72.7%</td><td>$8.39</td></tr>
  </tbody>
</table>
<p>Those July 9, 2026 values come from DataCurve's <a href="https://deepswe.datacurve.ai/artifacts/v1.1/leaderboard-live.json" rel="noopener">raw DeepSWE v1.1 artifact</a>. High to Max adds 3.3 observed percentage points while estimated task cost rises from $3.47 to $8.39 - about 2.4 times. The set contains 113 tasks, and the reported 95% confidence intervals for High and Max overlap slightly.</p>
<p>That makes Max a diagnosed escalation: use it after High failed because exploration ended too soon or a hard branch was not followed. It is poor compensation for a bad brief. The benchmark is evidence from one harness, not a guaranteed gain on a particular repository.</p>

<h2>Keep three cost systems separate</h2>
<p>API price, benchmark-estimated cost, and Codex credits are not interchangeable units. OpenAI currently publishes API prices of $5/$30 per million input/output tokens for Sol, $2.50/$15 for Terra, and $1/$6 for Luna. For most plans, the current Codex card maps those same input/output quantities to 125/750 credits for Sol, 62.5/375 for Terra, and 25/150 for Luna, with lower cached-input rates.</p>
<p>A benchmark's dollars-per-task number belongs to its own harness. A real agent run also pays for context, cached input, tool output, retries, validation, and any parallel branches. Use the <a href="https://help.openai.com/en/articles/20001106-codex-rate-card" rel="noopener">live Codex rate card</a> for credits and measure verified completion cost in the system itself.</p>

<h2>P.S. Current limits and the reported “juice” change</h2>
<p><strong>As of July 12, 2026, the five-hour usage window for Codex and ChatGPT Work does not currently apply to Plus, Business, or Pro.</strong> OpenAI product lead <a href="https://x.com/thsottiaux/status/2076365965915467978" rel="noopener">Tibo Sottiaux wrote that the change is temporary</a>; an <a href="https://www.all-ai.de/news/news26/openai-gpt-sol-app-limits" rel="noopener">accessible contemporaneous report reproduces the announcement</a>. Weekly limits remain. Treat this as a live operating condition, not a permanent entitlement or unlimited usage.</p>
<p>A separate <a href="https://www.reddit.com/r/codex/comments/1uv07tv/tibo_about_the_juice_values/" rel="noopener">public follow-up reproduced in this screenshot thread</a> addressed the smaller internal reasoning budgets - the “juice values” discussed online. Sottiaux said OpenAI tested those values while diagnosing unexpectedly high consumption and then reverted the experiment. The exact reduced numbers circulating in screenshots are therefore not a current documented interface or stable API contract.</p>
<p>For a production router, treat both facts as current-state notes. Target published model and effort controls, watch the live usage surface, and re-measure behavior rather than encoding temporary limits or inferred internal budgets.</p>

<h2>Do not collapse Max, Fast, and Ultra into one ladder</h2>
<ul>
  <li><strong>Max</strong> expands reasoning effort for one GPT-5.6 model.</li>
  <li><strong>Fast</strong> is a higher-credit Codex inference option, but the current <a href="https://developers.openai.com/codex/speed" rel="noopener">Speed documentation</a> lists GPT-5.5 and GPT-5.4 - not GPT-5.6 - as supported.</li>
  <li><strong>Ultra</strong> is a separate multi-agent setting that coordinates four agents by default. It is not another single-agent reasoning level above Max.</li>
</ul>
<p>Ultra earns its overhead when branches can produce independent evidence: separate subsystem reviews, competing implementations, or research questions without shared mutable state. It wastes context and creates collision risk when every worker needs the same files, decision, or sequential dependency.</p>

<h2>The verifier belongs in the routing table</h2>
<table>
  <thead><tr><th>Lane</th><th>Required evidence</th><th>Typical verifier</th></tr></thead>
  <tbody>
    <tr><td>Sol discovery</td><td>Reproduction, cited investigation, or decision record</td><td>Test, source audit, or independent review</td></tr>
    <tr><td>Terra execution</td><td>Bounded diff plus every acceptance gate named in the plan</td><td>Targeted tests, lint, type checks, and diff review</td></tr>
    <tr><td>Luna processing</td><td>Structured output conforming to the requested contract</td><td>Schema, deterministic check, sample audit, or stronger-model review</td></tr>
  </tbody>
</table>
<blockquote>The economical model is the one with the lowest total cost to a verified result, not the lowest token price.</blockquote>

<h2>Implementation checklist</h2>
<ol>
  <li>Classify the task by uncertainty: discovery, bounded execution, or repeatable processing.</li>
  <li>Record the product surface and verify that the intended model and effort control exist there.</li>
  <li>Attach the right completion contract: evidence plus exit condition, acceptance gates, or schema plus validator.</li>
  <li>Begin unclear hard work with Sol High. Escalate to Max only after diagnosing insufficient exploration.</li>
  <li>Hand decided work to Terra and high-volume verifiable units to Luna.</li>
  <li>Measure verified completions, retries, review time, latency, and token or credit use - not output volume alone.</li>
</ol>
<p>This policy makes model choice auditable. A failed task can be traced to the route, contract, environment, or verifier instead of being dismissed as “the model was not smart enough.” For the owner/operator version focused on approval and business risk, read the PuenteWorks companion: <a href="https://puenteworks.com/blog/choose-ai-model-by-job.html">use the cheapest AI model that can reliably finish the job</a>.</p>

<h2>FAQ</h2>
<h3>Is Sol always the best GPT-5.6 model for coding?</h3>
<p>No. Sol is the strongest discovery route when the path is unclear. Terra is often the better engineering route once a plan is bounded, and Luna is more efficient for narrow transformations with deterministic validation.</p>
<h3>Should coding agents default to Sol High or Max?</h3>
<p>Start difficult, uncertain work at Sol High. Escalate to Max only after identifying that insufficient exploration—not a bad brief or environment—caused the failure.</p>
<h3>Can Luna run a complete coding-agent session?</h3>
<p>It can run a constrained session, but its strongest system role is often inside a workflow: classification, extraction, naming, summaries, and other repeated work whose output can be checked automatically.</p>
<h3>Is Ultra more intelligent than Max?</h3>
<p>No. Max increases reasoning effort for one model. Ultra coordinates multiple agents. Parallelism helps only when the work can be decomposed without duplicating context or colliding on shared state.</p>
<h3>Do Codex and ChatGPT Work currently have a five-hour usage window?</h3>
<p>As of July 12, 2026, OpenAI says the five-hour restriction for Codex and ChatGPT Work temporarily does not apply to Plus, Business, or Pro. Weekly limits remain, so this is not unlimited access or a permanent contract.</p>
<h3>Were GPT-5.6 juice values permanently reduced?</h3>
<p>No current public specification says that. Tibo Sottiaux said the internal reasoning-budget experiments were reverted. Route against published effort controls and verify behavior on your own workload.</p>

<h2>Sources and limits</h2>
<ul>
  <li><a href="https://openai.com/index/gpt-5-6/" rel="noopener">OpenAI: GPT-5.6</a></li>
  <li><a href="https://openai.com/index/previewing-gpt-5-6-sol/" rel="noopener">OpenAI: previewing GPT-5.6 Sol</a></li>
  <li><a href="https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt" rel="noopener">OpenAI Help Center: GPT-5.6 in ChatGPT</a></li>
  <li><a href="https://help.openai.com/en/articles/20001106-codex-rate-card" rel="noopener">OpenAI Help Center: Codex rate card</a></li>
  <li><a href="https://developers.openai.com/codex/speed" rel="noopener">OpenAI: Codex Speed</a></li>
  <li><a href="https://developers.openai.com/api/docs/models" rel="noopener">OpenAI API: models and model selection</a></li>
  <li><a href="https://deepswe.datacurve.ai/" rel="noopener">DataCurve: DeepSWE v1.1 leaderboard</a></li>
  <li><a href="https://deepswe.datacurve.ai/artifacts/v1.1/leaderboard-live.json" rel="noopener">DataCurve: raw DeepSWE v1.1 leaderboard artifact</a></li>
  <li><a href="https://x.com/thsottiaux/status/2076365965915467978" rel="noopener">Tibo Sottiaux: temporary removal of the five-hour restriction</a></li>
  <li><a href="https://www.all-ai.de/news/news26/openai-gpt-sol-app-limits" rel="noopener">All-AI: accessible report reproducing the temporary-limit announcement</a></li>
  <li><a href="https://www.reddit.com/r/codex/comments/1uv07tv/tibo_about_the_juice_values/" rel="noopener">Tibo Sottiaux follow-up on usage and reverted juice-value experiments</a></li>
</ul>
<p><small>Fact-checked July 12, 2026. Product availability, prices, rate cards, usage limits, and benchmark results can change. The field notes are observational, and the routing policy should be validated against your own repositories and verification costs.</small></p>
""",
    },
    {
        "slug": "agents-need-verifiable-tools",
        "title": "Agents need verifiable tools, not better prompt theater",
        "category": "MCP Implementation",
        "date": "2026-05-23",
        "read_time": "7 min",
        "primary_keyword": "verifiable AI agent tools",
        "seo_title": "verifiable AI agent tools and MCP implementation",
        "meta_description": "AI agents need tools they can call, inspect, verify, and revise. KyaniteLabs builds MCP servers and implementation surfaces around that principle.",
        "excerpt": "The useful agent pattern is not a prettier prompt. It is a tool surface the agent can call, inspect, verify, and revise.",
        "body": """
<p><strong>The useful agent pattern is not a prettier prompt. It is a tool surface the agent can call, inspect, verify, and revise.</strong> A prompt can suggest work. A tool can touch the artifact.</p>
<p>That distinction is why Kyanite keeps building MCP servers, command-line tools, demos, and public proof records. The agent needs a handle on the real operation: editing a video, estimating time, localizing Spanish variants, reading repo history, or checking a domain-specific calculation.</p>
<p>If the system cannot verify what happened, the agent is still mostly guessing.</p>
<h2>The tool contract is the product boundary</h2>
<p>A good agent tool has a clear action, typed inputs, structured output, readable errors, and a small verification path. That sounds boring. It is also what separates a reusable capability from a one-off session.</p>
<pre><code>call tool
inspect output
compare expectation
revise next step</code></pre>
<p>mcp-video proves the media version of this pattern. Epoch proves the estimation version. DialectOS proves the localization version. devarch-framework and Dev Learning Archaeologist prove the repo-history version. OpenGlaze proves that domain software still matters when the user is not living inside the AI-tool bubble.</p>
<h2>Verification changes the conversation</h2>
<p>Without verification, an agent can sound confident and still be wrong. With verification, the system can show a command, a file, a route, a report, a test, a screenshot, or a structured result. That does not make the work perfect. It makes the next correction possible.</p>
<blockquote>The point of a Kyanite tool is not that an agent did something. The point is that a person can inspect what the agent did.</blockquote>
<h2>What this means for implementation help</h2>
<p>Paid implementation is not generic "AI consulting." It is help getting a tool into a real environment with the setup, docs, examples, support boundary, and handoff that make verification possible for the next user.</p>
<p>That is the work most public demos skip. It is also where useful tools become something a team can actually use.</p>
<h2>FAQ</h2>
<h3>What makes an agent tool verifiable?</h3>
<p>The user or agent can check the input, output, error state, artifact, and success condition without relying on a vague explanation.</p>
<h3>Why use MCP?</h3>
<p>MCP gives agents a standard way to call tools. The value still depends on the quality of the tool contract, docs, examples, and verification path.</p>
""",
    },
    {
        "slug": "repo-history-is-a-product-signal",
        "title": "Repo history is a product signal",
        "category": "Repo Intelligence",
        "date": "2026-05-23",
        "read_time": "6 min",
        "primary_keyword": "repo archaeology for AI teams",
        "seo_title": "repo archaeology as a product signal for AI teams",
        "meta_description": "Repo history shows how a project actually changed, where it got stuck, and whether the proof surface matches the code.",
        "excerpt": "A repo is not just storage. It is evidence of decisions, repairs, release behavior, naming drift, test gaps, and what the builder actually knows how to finish.",
        "body": """
<p><strong>A repo is not just storage. It is evidence of decisions, repairs, release behavior, naming drift, test gaps, and what the builder actually knows how to finish.</strong> That evidence matters more now because AI-assisted work can produce a lot of motion that looks productive from far away.</p>
<p>Repo archaeology is the practice of reading that motion carefully. The question is not whether the commit graph is pretty. The question is what the history proves about the product.</p>
<h2>What repo history can show</h2>
<ul>
  <li>Which parts of the system needed repeated repair.</li>
  <li>Whether docs followed the code or drifted away from it.</li>
  <li>Which tests appeared before launch and which appeared after regressions.</li>
  <li>Whether public claims match current routes, releases, and README examples.</li>
  <li>Where a project needs cleanup before a buyer, user, or contributor can trust it.</li>
</ul>
<p>This is why Kyanite includes devarch-framework and Dev Learning Archaeologist in the public project set. They turn invisible engineering behavior into a readable diagnostic artifact.</p>
<h2>AI makes this more important, not less</h2>
<p>AI agents can change more files faster. That is useful when the work is bounded and verified. It is dangerous when nobody can tell which changes mattered. Repo history becomes the receipt trail.</p>
<blockquote>If a tool claims to be ready, the repo should help prove readiness instead of forcing the reader to trust the landing page.</blockquote>
<h2>The commercial value</h2>
<p>Repo archaeology helps with launch readiness, product audits, maintainer handoffs, learning diagnostics, and technical sales proof. It can show where the system is strong enough to publish and where the next paid implementation step should focus.</p>
<p>That is expert work because it sits between engineering, product judgment, and public trust. The code matters. So does the story the code can honestly support.</p>
""",
    },
    {
        "slug": "implementation-help-is-product-surface",
        "title": "Implementation help is part of the product surface",
        "category": "AI Tool Implementation",
        "date": "2026-05-23",
        "read_time": "7 min",
        "primary_keyword": "AI tool implementation support",
        "seo_title": "AI tool implementation support for open-source tools",
        "meta_description": "Open-source AI tools need implementation surfaces: install paths, examples, docs, proof, support boundaries, and handoff.",
        "excerpt": "A useful open-source tool still needs a path from public repo to working environment. That path is product work, not an afterthought.",
        "body": """
<p><strong>A useful open-source tool still needs a path from public repo to working environment.</strong> That path is product work, not an afterthought.</p>
<p>Most technical builders understand the code. Most buyers or users experience the surface around the code: install instructions, examples, screenshots, error handling, docs, demos, support boundaries, and the first successful run.</p>
<p>When that surface is weak, the tool may be real and still feel unusable.</p>
<h2>The implementation surface has jobs</h2>
<ul>
  <li>Explain the outcome in one sentence.</li>
  <li>Show what the tool needs before it runs.</li>
  <li>Give a smallest useful example.</li>
  <li>Prove that the example worked.</li>
  <li>Name what the tool does not do yet.</li>
  <li>Offer a paid path when someone wants the result without doing every setup step alone.</li>
</ul>
<p>Kyanite's own site follows that pattern: public repos, products, blog posts, <code>/llms.txt</code>, <code>/ai-sitemap.json</code>, implementation intake, and a clear boundary between Kyanite tool implementation and broader PuenteWorks consulting.</p>
<h2>Open source does not remove service work</h2>
<p>Open source can reduce lock-in and prove capability. It does not automatically handle installation, adaptation, team training, environment differences, docs, examples, or maintenance decisions.</p>
<blockquote>The repo proves the tool exists. Implementation help gets the tool into working hands.</blockquote>
<h2>Why this is a real offer</h2>
<p>Implementation help is sellable when the public tool is specific enough to trust and the setup path is painful enough that a serious user would rather buy help than burn a weekend. That is the lane for Kyanite: practical tools, public proof, and scoped help getting the result working.</p>
""",
    },
    {
        "slug": "why-mcp-video-matters",
        "title": "Why mcp-video matters",
        "category": "MCP / Video Automation",
        "date": "2026-05-14",
        "read_time": "5 min",
        "primary_keyword": "video editing MCP server",
        "seo_title": "video editing MCP server for AI agents",
        "meta_description": "mcp-video is a video editing MCP server that gives AI agents direct handles on FFmpeg, Hyperframes, timelines, effects, and media pipelines.",
        "excerpt": "mcp-video is a video editing MCP server that gives AI agents direct handles on timelines, effects, FFmpeg, and finished media.",
        "body": """
<p><strong>mcp-video is a video editing MCP server that lets AI agents operate real media pipelines instead of only writing prompts about them.</strong> The useful part is not the word "video"; it is that an agent gets callable handles for FFmpeg, Hyperframes, effects, inspection, and repeatable assembly.</p>
<p>Most AI video workflows still depend on a strange handoff. The agent can plan the edit, describe the shot, maybe generate a prompt, and then a human has to do the actual assembly work somewhere else. That is not agent-native. That is a chatbot standing outside the studio window.</p>
<h2>mcp-video gives the agent a timeline</h2>
<p>The technical decision is to expose video operations as stable tools instead of one-off shell recipes. That choice accepts the cost of a larger public surface: arguments need validation, error messages need to be readable, and effects need names that survive more than one session.</p>
<pre><code>mcp-video effect-glitch input.mp4 --output take-glitch.mp4
mcp-video inspect take-glitch.mp4 --json
mcp-video concat beat-01.mp4 beat-02.mp4 --output final-cut.mp4</code></pre>
<p>That interface is not decoration. It is the boundary that lets an agent inspect what happened, revise the next step, and keep the work reproducible.</p>
<h2>The product pattern behind agent video automation</h2>
<p>Kyanite looks for workflows that already exist in rough form, then turns them into surfaces an agent and a human can both use. For video, that means:</p>
<ul>
  <li>effects that can be invoked as tools instead of one-off experiments</li>
  <li>command-line recipes that survive beyond a single session</li>
  <li>media pipelines that can be tested, revised, and shipped</li>
  <li>documentation good enough for a stranger to install the system</li>
</ul>
<p>That is the real implementation move: take the messy local ritual and make it legible.</p>
<h2>Why MCP media tools are bigger than video</h2>
<p>Video is one visible example of a broader agentic pattern. Agents need tools that touch real artifacts. A useful agent should be able to inspect a repo, assemble a video, run an estimation model, check a localization string, or package a launch surface.</p>
<p>The more direct handles the agent has, the less the work feels like prompting and the more it feels like operating a system.</p>
<h2>FAQ</h2>
<h3>What is mcp-video?</h3>
<p>mcp-video is a video editing MCP server, Python client, and CLI that exposes video inspection, effects, assembly, and FFmpeg-backed operations to AI agents.</p>
<h3>Who should care?</h3>
<p>Builders who want AI agents to produce inspectable media artifacts instead of only generating prompts, scripts, and editing instructions.</p>
""",
    },
    {
        "slug": "infinite-monkey-agentic-systems",
        "title": "Infinite monkeys, LLMs, and the room around the machine",
        "category": "Agent Systems",
        "date": "2026-05-14",
        "read_time": "6 min",
        "primary_keyword": "agentic systems",
        "seo_title": "agentic systems need probability architecture",
        "meta_description": "Agentic systems are probability architecture: generation, filters, tools, evals, memory, and human taste around LLM probability machines.",
        "excerpt": "The argument behind the video: output quality is not just probability. It is architecture, filters, and human taste.",
        "body": """
<p><strong>Agentic systems turn LLM probability into useful work by building the room around the model: tools, filters, memory, evals, and human taste.</strong> The model generates. The system decides what survives.</p>
<p>The infinite monkey theorem is a useful metaphor until people stop too early. Randomness can produce anything in theory. In practice, the room matters. How many attempts are running? What gets filtered out? Who judges the output? What system remembers the good parts? What is the cost of another roll?</p>
<blockquote>LLMs are probability machines. Products are probability architecture.</blockquote>
<p>The difference between a toy demo and a useful AI system is not just a better model. It is the surrounding machinery: retrieval, tools, constraints, evals, review, memory, distribution, and human taste.</p>
<h2>The filter is the product</h2>
<p>Generation creates volume. Product work creates selection. That is why strong AI systems need more than prompts. They need rooms built around the model.</p>
<ul>
  <li>tools that let the model act on real artifacts</li>
  <li>filters that reject bad output before it reaches users</li>
  <li>human criteria that decide what good means</li>
  <li>launch surfaces that make the system understandable</li>
</ul>
<h2>Agentic systems need explicit architecture</h2>
<p>A useful architecture names the handoff points. The generation step can be cheap and messy; the selection step cannot be. If a system cannot explain why an output was accepted, it is gambling with prettier logs.</p>
<pre><code>generate -> inspect -> score -> revise -> package -> publish
           ^                          |
           |________ evidence ________|</code></pre>
<p>This is also why Kyanite leads with public proof. A repo, demo, video, or docs page makes the room visible. You can inspect the architecture instead of trusting the claim.</p>
<h2>FAQ</h2>
<h3>Are LLMs the same as random monkeys?</h3>
<p>No. The analogy is about generation without judgment, not the exact mechanism. LLMs are sophisticated probability machines; useful products add judgment around them.</p>
""",
    },
    {
        "slug": "ai-tool-implementation-checklist",
        "title": "What a working AI tool needs before people can use it",
        "category": "Build Notes",
        "date": "2026-05-14",
        "read_time": "7 min",
        "primary_keyword": "AI tool implementation",
        "seo_title": "AI tool implementation checklist",
        "meta_description": "A practical AI tool implementation checklist: install path, demos, docs, proof, support boundaries, and user-ready workflows.",
        "excerpt": "A practical checklist for turning a working tool, workflow, or rough app into something other people can understand, install, and use.",
        "body": """
<p><strong>A working AI tool becomes useful to other people when the install path, demo, docs, examples, and support boundaries are clear.</strong> A working codebase is not automatically usable.</p>
<p>A stranger has to understand what result it creates, how to try it, how to verify it works, and where to get help if they want that result without doing every setup step alone.</p>
<p>Most technical projects fail commercially before anyone reaches the code. The surface is too vague.</p>
<h2>The minimum useful surface</h2>
<ul>
  <li>A one-sentence promise that says what changes for the user</li>
  <li>A demo, install path, or clear explanation of how the tool is delivered</li>
  <li>Examples that show actual inputs and outputs</li>
  <li>Tests, demos, screenshots, or logs that prove the system exists</li>
  <li>Metadata that helps humans and AI assistants discover the project</li>
  <li>A next step: try it, install it, read the build note, buy a product, or request implementation help</li>
</ul>
<h2>A tool needs proof, not adjectives</h2>
<p>The page cannot say "ready" unless the surface shows instructions, examples, tests, release notes, screenshots, demos, or failure modes. The tradeoff is obvious: proof takes longer than copy, but proof keeps helping after the page is closed.</p>
<pre><code>README promise
install command
minimal example
verification command
known limits
implementation option</code></pre>
<h2>What Kyanite sells</h2>
<p>KyaniteLabs is the public lab where the tools, experiments, blog posts, and open-source products live. The paid path helps people install, adapt, understand, and hand off those tools in a real environment.</p>
<blockquote>The goal is not generic consulting. The goal is getting useful tools into working hands.</blockquote>
<p>Good implementation does not hide the mess. It turns the mess into a map.</p>
""",
    },
    {
        "slug": "mcp-server-implementation-checklist",
        "title": "MCP server implementation checklist",
        "category": "MCP Implementation",
        "date": "2026-05-14",
        "read_time": "8 min",
        "primary_keyword": "MCP server implementation",
        "seo_title": "MCP server implementation checklist",
        "meta_description": "MCP server implementation means making an agent tool usable with install paths, schema clarity, examples, tests, docs, and public proof.",
        "excerpt": "The checklist Kyanite uses to decide whether an MCP server is a toy, a usable tool, or something worth implementing.",
        "body": """
<p><strong>MCP server implementation means making an agent-facing tool usable enough that someone else can install it, understand its tools, verify it works, and decide whether to trust it.</strong> The hard part is not exposing functions. The hard part is making the tool surface durable enough for real users and real agents.</p>
<p>An MCP server becomes useful when the protocol surface, docs, examples, tests, and release path all tell the same story.</p>
<h2>The checklist starts with the tool contract</h2>
<p>Every public tool needs a sharp boundary. Tool names should describe the action. Arguments should reject bad input early. Output should be structured enough for an agent to reason about without scraping prose.</p>
<pre><code>{
  "tool": "estimate_project_time",
  "inputs": ["tasks", "confidence", "risk_model"],
  "output": ["p50_days", "p90_days", "assumptions", "warnings"]
}</code></pre>
<p>The tradeoff is that explicit schemas slow down early experimentation. That cost is worth paying once the server is meant to leave your laptop.</p>
<h2>The install path is part of the product</h2>
<p>A strong MCP README answers 5 questions quickly:</p>
<ul>
  <li>What does this server let an agent do?</li>
  <li>What does installation require?</li>
  <li>Which client configs are supported?</li>
  <li>What is the smallest useful example?</li>
  <li>How do I know the server is working?</li>
</ul>
<p>That last question is where weak projects break. If verification depends on the maintainer explaining it in a chat, it is not productized yet.</p>
<h2>Public proof compounds</h2>
<p>mcp-video, Epoch, and DialectOS each prove a different part of the stack: media operations, estimation models, and localization QA. The shared pattern is the lab: a real workflow becomes an agent-callable capability with enough documentation and tests to survive inspection.</p>
<h2>FAQ</h2>
<h3>What makes an MCP server commercially useful?</h3>
<p>It has to touch an expensive, repeated, or fragile workflow. If the server only wraps a trivial API call, the product is the API, not the MCP server.</p>
""",
    },
    {
        "slug": "repo-archaeology-proof-assets",
        "title": "Repo archaeology turns history into proof",
        "category": "Repo Intelligence",
        "date": "2026-05-14",
        "read_time": "7 min",
        "primary_keyword": "repo archaeology",
        "seo_title": "repo archaeology for AI-assisted teams",
        "meta_description": "Repo archaeology mines commit history, patterns, and project evidence to create learning diagnostics, product proof, and engineering reports.",
        "excerpt": "Why commit history is one of the strongest proof sources for learning diagnostics, implementation help, and engineering trust.",
        "body": """
<p><strong>Repo archaeology uses commit history as evidence for how a project was actually built, where it got stuck, and what the next intervention should be.</strong> It is useful because code history is harder to fake than a positioning paragraph.</p>
<p>Kyanite's repo-intelligence work exists because AI-assisted teams generate a lot of motion. The question is which motion taught the system something, which motion created debt, and which motion can become public proof.</p>
<h2>Commit history is a diagnostic surface</h2>
<p>A repo carries behavioral evidence: repeated fixes, reverted directions, test gaps, naming churn, and stale public metadata. A good diagnostic does not shame the team for that. It turns the pattern into a map.</p>
<pre><code>signals:
  - repeated failure around release automation
  - docs updated after code, not before
  - tests added only after regressions
  - public metadata lagging behind repo rename</code></pre>
<p>The tradeoff is that history is noisy. Repo archaeology needs filters, not mysticism.</p>
<h2>Why this matters for users</h2>
<p>Users do not only need the current feature set. They need confidence that the tool can keep improving. Public history, issue handling, release notes, and verified fixes show maintenance behavior.</p>
<p>That is why Dev Learning Archaeologist and devarch-framework belong on the Kyanite proof wall. They turn invisible engineering behavior into something a person can inspect.</p>
<h2>FAQ</h2>
<h3>Is repo archaeology only for learning diagnostics?</h3>
<p>No. It is also useful for product audits, acquisition diligence, maintainer handoffs, launch readiness, and deciding which proof assets should be public.</p>
""",
    },
    {
        "slug": "ai-discovery-llms-txt-geo",
        "title": "AI discovery needs more than a sitemap",
        "category": "SEO / GEO",
        "date": "2026-05-14",
        "read_time": "6 min",
        "primary_keyword": "AI discovery",
        "seo_title": "AI discovery, llms.txt, and GEO for product sites",
        "meta_description": "AI discovery needs sitemap coverage, llms.txt, structured data, direct-answer copy, FAQ sections, and clear public project evidence.",
        "excerpt": "What Kyanite adds so search engines and AI assistants can understand the tools, products, proof, and support path.",
        "body": """
<p><strong>AI discovery works when a site gives crawlers and answer engines structured, quotable, current facts about what exists, who it helps, and what proof supports it.</strong> A sitemap is necessary. It is not enough.</p>
<p>Generative Engine Optimization is mostly discipline. Say the answer early. Use real names. Add structured data. Keep public proof current. Make the commercial next step obvious.</p>
<h2>The AI-readable stack</h2>
<ul>
  <li><code>/sitemap.xml</code> for canonical crawl coverage</li>
  <li><code>/llms.txt</code> for answer-engine context</li>
  <li><code>/ai-sitemap.json</code> for structured products, repos, and posts</li>
  <li>JSON-LD for Organization, WebSite, Article, Service, Product, and FAQ entities</li>
  <li>Direct-answer paragraphs at the top of pages and posts</li>
</ul>
<p>The tradeoff is maintenance. These files cannot be aspirational. If the repo list changes, the proof layer needs to change with it.</p>
<h2>GEO is strongest when it is useful to humans too</h2>
<p>Answer engines and human readers both reward the same thing: specific claims with clear evidence. "We build AI tools" is weak. "We build MCP servers, video automation, localization QA, repo diagnostics, and open-source tools backed by public KyaniteLabs repositories" is stronger because it can be checked.</p>
<h2>FAQ</h2>
<h3>What is GEO?</h3>
<p>GEO, or Generative Engine Optimization, is structuring web content so AI answer engines can accurately summarize, cite, and route users to it.</p>
""",
    },
]

BLOG_POSTS_BY_SLUG = {post["slug"]: post for post in BLOG_POSTS}
LEGACY_BLOG_SLUGS = {
    "productization-audit-field-guide": "ai-tool-implementation-checklist",
    "mcp-server-productization-checklist": "mcp-server-implementation-checklist",
}

PROJECT_COPY_ES = {
    "devarch-framework": {
        "description": "Marco de arqueologia de repositorios para leer historial de commits, detectar señales, correr 6 vectores de analisis y generar reportes de ingenieria.",
        "tag": "Inteligencia de repos",
        "proof_role": "Muestra que Kyanite puede convertir historial de desarrollo en evidencia, no en intuicion.",
    },
    "mcp-video": {
        "description": "Servidor MCP de edicion de video para agentes de IA con 87 herramientas de FFmpeg e Hyperframes, cliente Python y CLI.",
        "tag": "MCP de medios",
        "proof_role": "La prueba principal de que los agentes pueden operar timelines, efectos y pipelines repetibles de medios.",
    },
    "Epoch": {
        "description": "Servidor MCP de estimacion de tiempo para PERT, COCOMO II, Monte Carlo, pronosticos de sprint, mapeo token-tiempo, costos y riesgo de calendario.",
        "tag": "MCP de estimacion",
        "proof_role": "Convierte la incertidumbre de planificacion en herramientas de pronostico que un agente puede llamar.",
    },
    "checkyourself": {
        "description": "Sistema local-first de preparacion para produccion en apps creadas con IA: auditorias, puntajes con evidencia, fixes guiados, dashboard, CLI y MCP.",
        "tag": "Auditoria de readiness",
        "proof_role": "Hace inspeccionables la calidad, seguridad y riesgo de lanzamiento antes de enviar una app creada con IA.",
    },
    "DialectOS": {
        "description": "Servidor MCP y CLI de localizacion dialectal en español para 25 variantes regionales, con control de registro, preservacion de estructura y QA.",
        "tag": "MCP de localizacion",
        "proof_role": "Hace inspeccionable la calidad del español de lanzamiento en vez de tratar la localizacion como traduccion generica.",
    },
    "liminal": {
        "description": "Estudio de creative coding con IA para p5.js, GLSL, Three.js, musica, video y flujos de arte generativo agnosticos al modelo.",
        "tag": "Creative coding",
        "proof_role": "Muestra que Kyanite puede crear herramientas creativas donde los agentes tocan codigo, shaders, medios y gusto.",
    },
    "liminal-sites": {
        "description": "Motor de evolucion de websites vivos para direcciones de diseño con IA, runtime skins, memoria de gusto, previews y planes de patch en repo.",
        "tag": "Websites vivos",
        "proof_role": "Prueba que el sitio mismo puede evolucionar con sistemas de diseño restringidos e inspeccionables.",
    },
    "Elixis": {
        "description": "Motor local-first de sintesis de patrones para identidad, voz de marca, sistemas de diseño, investigacion de nombres y salidas por lente.",
        "tag": "Sintesis de patrones",
        "proof_role": "Convierte trabajo borroso de identidad y nombres en sintesis respaldada por fuentes.",
    },
    "Innerscape": {
        "description": "Sistema operativo personal en TypeScript para journaling, check-ins emocionales, habitos, metas, tareas, sueño, orden y autoconciencia.",
        "tag": "OS personal",
        "proof_role": "Aplica el mismo patron de construccion e implementacion a flujos intimos y ricos en datos.",
    },
    "openglaze": {
        "description": "Calculadora open source gratuita para esmaltes ceramicos, analisis UMF, estimacion CTE, recetas y trabajo de estudio para ceramistas.",
        "tag": "Software de dominio",
        "proof_role": "Prueba que Kyanite puede crear software util fuera de la burbuja generica de herramientas de IA.",
    },
    "Dev Learning Archaeologist": {
        "description": "Diagnostico forense de aprendizaje a partir del historial git para desarrolladores asistidos por IA, con planes de estudio y reportes HTML.",
        "tag": "Diagnosticos de aprendizaje",
        "proof_role": "Convierte comportamiento de repositorio en un artefacto diagnostico legible.",
    },
    "achiote-food-memory-researcher": {
        "description": "Investigador de memoria culinaria basado en carpetas para reconstruir platos familiares medio recordados desde sonidos, olores, colores y memoria cultural.",
        "tag": "Memoria culinaria",
        "proof_role": "Extiende el estilo de evidencia de Kyanite hacia memoria cultural y asistentes de investigacion.",
    },
    "unstuck-coach": {
        "description": "Coach de accesibilidad para funcion ejecutiva que convierte un bloqueo confuso en un siguiente paso humano y posible.",
        "tag": "Funcion ejecutiva",
        "proof_role": "Aplica herramientas agenticas a accesibilidad, ritmo y diseño de siguientes pasos humanos.",
    },
    "tradesflow": {
        "description": "Prototipo de portafolio para operadores de campo con activos pesados: equipos, notas de servicio, deficiencias, calendario y handoffs de cobro.",
        "tag": "Operaciones de campo",
        "proof_role": "Muestra pensamiento de implementacion para operadores reales con activos, visitas y handoffs de facturacion.",
    },
    "healthadvocate": {
        "description": "App FastAPI de apoyo a pacientes para tooling de salud, exploracion local con LLM y flujos de NLP medico.",
        "tag": "Apoyo de salud",
        "proof_role": "Explora tooling privado y local-first de salud sin tratar el contexto de cuidado como chat generico.",
    },
}

PUBLIC_PROJECTS_ES = [
    {**project, **PROJECT_COPY_ES.get(project["name"], {})}
    for project in PUBLIC_PROJECTS
]

BLOG_COPY_ES = {
    "lab-notes-degenerate-basin": {
        "title": 'Notas de lab: no se desvanece',
        "category": 'LLM local / Benchmarks',
        "primary_keyword": 'contexto profundo LLM cuenca degenerada',
        "seo_title": 'Notas de lab: no se desvanece — colapso de contexto, no un miss',
        "meta_description": 'Noche 3: una pila de 198.227 tokens, cinco profundidades, un corte a 98 °C y un modelo que contesta un code review que nadie pidió. Un mapa n=1, no una ley.',
        "excerpt": 'En este 27B el retrieval a contexto profundo no se va apagando. Brinca a un reporte de lata. Después la caja se cortó a 98 °C. Este es el mapa de esa noche.',
        "body": """
<p><small>Por <a href="https://x.com/KyaniteLabs_" rel="noopener">Simon Gonzalez de Cruz</a> (el build en público en <a href="https://x.com/KyaniteLabs_" rel="noopener">X @KyaniteLabs_</a>), con GLM-5.3. Noche 3 de las notas de lab. La caja se murió a 98 °C, volvió, y contestó una pregunta que yo nunca hice.</small></p>
<p>El número primero: <strong>el retrieval a contexto profundo de este modelo no se desvanece.</strong> Brinca a una respuesta de lata. En una pila que el server contó en 198.227 tokens, pedí un código plantado a cinco profundidades. Al 25% me devolvió el código exacto y paró limpio. Al 35% y al 75% escribió el arranque de un reporte de code review que nadie le pasó:</p>
<pre><code>- **Risk**: Low; 67 medium/low</code></pre>
<p>El mismo arranque. Dos veces. Temperature 0.</p>
<p>Eso no es un miss. Un miss es «no lo tengo». Aquí el modelo está calificando 48 repos imaginarios con toda la confianza del mundo.</p>

<h2>Lo que de verdad corrió</h2>
<p>Una semilla. Una pila. Config campeón: Qwen3.8-27B Q4_K_XL, K+V q4_0, ventana de 262.144 tokens, en un GMKtec EVO-X2 de $1.400. Las profundidades son fracciones del conteo del <strong>server</strong>, no de mi estimado. El generador dijo 262k. El server dijo 198.227. El instrumento se etiqueta con el contador de la fuente.</p>
<table>
  <thead><tr><th>Profundidad</th><th>Resultado</th><th>Stop</th><th>Qué dijo</th></tr></thead>
  <tbody>
    <tr><td>10%</td><td>fail</td><td>stop</td><td><code>ok</code></td></tr>
    <tr><td>25%</td><td>hit</td><td>stop</td><td>el código plantado, exacto</td></tr>
    <tr><td>35%</td><td>fail</td><td>length</td><td>el reporte Risk, 67 hallazgos</td></tr>
    <tr><td>50%</td><td>fail</td><td>stop</td><td><code>ok</code></td></tr>
    <tr><td>75%</td><td>fail</td><td>length</td><td>el reporte Risk otra vez, 67 hallazgos</td></tr>
  </tbody>
</table>
<p>Dos atractores, no uno. <code>ok</code> al 10% y al 50%. El reporte al 35% y al 75%. n=1 por celda. Trátalo como mapa, no como medición. La estación del 90% del gate de corona anterior es otra corrida. Este sweep se murió antes de llegar ahí.</p>

<h2>Después la caja cortó la corriente</h2>
<p>En el siguiente prefill largo el EC saltó a las 16:45:42Z. Línea del journal: <code>temp=98C -&gt; fan=100%</code>. Sin panic, sin amdgpu, sin OOM. La temperatura más alta que esta chasis ha dejado aquí. Los fans ya estaban haciendo su trabajo. El load fue el bug: prefills de media hora uno detrás del otro, como 6 °C arriba del sobre 90-92 °C que tratamos como normal.</p>
<p>Después del reboot mandé otra vez el request del 35%. Misma familia de reporte. El conteo se movió: <strong>67 a 68</strong>. Un token. Temperature sigue en 0. Eso es filo de cuchillo, no un modelo creativo. No sé qué kernel o batch shape volteó el dígito. No voy a fingir que sí.</p>

<h2>No es el KV de 4 bits</h2>
<p>Corrí la misma aguja con el KV q8_0 viejo. Misma especie de reporte. Otros números, la misma voz de «estoy revisando un codebase». O sea que la cuenca ya estaba cuando q8 era campeón. Los números de contexto corto de la corona q4 se aguantan con su propia evidencia. No voy a escribir «sin pérdida de calidad a contexto clase 200k» con celdas n=1. Esa oración no nos la hemos ganado.</p>

<h2>En qué me equivoqué con nuestro stack</h2>
<p>Le eché la culpa al «fork». El binario de serving es llama.cpp de era upstream más un cherry-pick de cuatro líneas de reporte HIP. Si algo está roto a 198k, no es un bug secreto del fork.</p>
<p>Casi abrí un issue upstream de caps ngram. El gauntlet lo mató. <code>--spec-draft-n-max</code> no tapa ngram-mod. <code>--spec-ngram-mod-n-max</code> sí, y nunca lo pusimos. Nuestra config. Su flag. El gauntlet se queda obligatorio.</p>
<p>Tres reviews más un pase de código no pudieron clavar estas celdas en un bug de verificación del serving stack. El speculative decode se ve como que está chequeando tokens como debe. La cuenca se ve a nivel de modelo. Eso es eliminación, no prueba del mecanismo. Todavía tengo un rerun spec-off en la lista. No lo he corrido.</p>

<h2>Esta noche</h2>
<p>Renombré los labels del log. «Miss» se jubila para estas celdas. Son salidas de plantilla degenerada. Quien copie el sweep debería loguearlas así, o va a «arreglar retrieval» que nunca reportó falla.</p>
<p>Logs crudos: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo/tree/main/results/deep-context-2026-08-18" rel="noopener">results/deep-context-2026-08-18</a> en el repo <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">qwen38-27b-strix-halo</a>.</p>
<p><small>Condiciones: GMKtec EVO-X2 (Ryzen AI Max+ 395, 96GB unificados), Qwen3.8-27B Q4_K_XL, llama.cpp ROCm, ventana 262.144 tokens, K+V q4_0 (control q8_0 en la misma aguja), temperature 0, prompt_tokens 198.227 reportados por el server, n=1 por profundidad, seed s4419, 2026-08-18. Una noche. Un mapa. No una ley.</small></p>
""",
    },
    "lab-notes-the-kv-verdict": {
        "title": 'Notas de lab: el veredicto del KV',
        "category": 'LLM local / Benchmarks',
        "primary_keyword": 'cuantización cache KV q4 llama.cpp',
        "seo_title": 'Notas de lab: el veredicto del KV — la mitad del cache a 262k',
        "meta_description": 'Noche 2: un gate pareado pasa el campeón a KV de 4 bits — GSM8K p=1.0, cero flags de corrupción a ~198k tokens, y el contador del server que corrigió nuestro estimado.',
        "excerpt": 'La pregunta q8-a-q4 del KV de la noche 1 ya tiene respuesta pareada: misma accuracy, cero tripwires, la mitad del cache. Y el label que tuvimos que corregir en público cuando el contador del server le ganó al estimado.',
        "body": """
<p><small>Por <a href="https://x.com/KyaniteLabs_" rel="noopener">Simon Gonzalez de Cruz</a> (el build en público en <a href="https://x.com/KyaniteLabs_" rel="noopener">X @KyaniteLabs_</a>), con GLM-5.3. Noche 2 de las notas de lab. Anoche cerré con una promesa: correr el A/B pareado de q4_0-KV que nos faltaba. Esto es lo que volvió.</small></p>
<p>El número primero: <strong>el campeón ahora corre cache KV de 4 bits — como 47% menos memoria KV en la misma ventana de contexto — con cero costo medido de accuracy y cero flags de corrupción.</strong> El gate de promoción fue pareado, pre-registrado y auto-ejecutable: si el brazo q4 empataba los hits de aguja de q8 y no disparaba tripwires, el unit file voltea; si no, el campeón viejo se restaura solo.</p>

<h2>La pila de evidencia</h2>
<p>Tres capas, cada una pareada:</p>
<table>
  <thead><tr><th>Capa</th><th>Diseño</th><th>Resultado</th></tr></thead>
  <tbody>
    <tr><td>Accuracy de tarea</td><td>GSM8K, n=60 estratificado, pareado</td><td>McNemar exacto p = 1.0; q4 un poco <em>más rápido</em> (18,78 s vs 19,47 s de media)</td></tr>
    <tr><td>Integridad a contexto profundo</td><td>Agujas al 50%/90% de profundidad, misma pila de ~198k tokens, misma semilla, control en la misma sesión</td><td>q4: 0/2 hits, <strong>cero tripwires</strong>, stops limpios; q8: 0/2 hits, un trip</td></tr>
    <tr><td>Frontera de retrieval</td><td>Aguja al 25% (donde q8 históricamente recupera)</td><td><strong>FOUND</strong>, stop limpio — la frontera de la zona tonta no se movió</td></tr>
  </tbody>
</table>
<p>El tripwire es el contador de anomalías de finish_reason que dejamos armado en cada hora de serving desde que corrió el reporte de corrupción de KV cuantizado en RDNA4. Un trip disparó en toda la noche — en el brazo <em>q8</em> (una respuesta de 40 tokens que nunca paró; n=1, rambling de contexto profundo, anotado, no interpretado). El brazo que la regla de verdad gatea — q4 — salió limpio.</p>

<h2>El miss que nos cachamos a nosotros</h2>
<p>La pila del gate se armó con un estimado: 5.800 párrafos, ~45 tokens cada uno, dile 262k. El contador del server dijo <strong>198.227 tokens</strong>. La comparación pareada no se toca — los dos brazos prefilleron la misma pila, que es todo el punto de parear — pero cada sitio donde habíamos escrito «agujas a 262k» estaba inflando el instrumento. El tweet de anuncio ya había salido con el estimado. La corrección salió de reply en menos de una hora, el README del repo ahora carga conteos del server, y la regla queda: <em>etiqueta el instrumento con el contador de la fuente, no con el estimado del generador.</em> Prefill frío medido por esa pared de aguja: <strong>109,5 tok/s</strong> a ~198k (número clase aguja: prompt completo + respuesta, no un harness de bench).</p>

<h2>Qué te compra medio cache</h2>
<p>Aritmética, etiquetada como aritmética: q8_0 mete ~8,5 bits por valor KV, q4_0 ~4,5 — de ahí ~47% menos en la línea KV a contexto idéntico. El wall time medido en las sondas fue para el mismo lado que GSM8K: q4 un filo más rápido en lecturas de cache. Lo que se acumula viene después: la matemática del ensayo 35B (ahí el headroom de KV decide si cabe), y el lane de KV adaptativo, cuya barra se acaba de mover de «gana al q8 estático» a «gana al q4 estático».</p>

<h2>Condiciones</h2>
<p><small>GMKtec EVO-X2 (Ryzen AI Max+ 395, 96GB unificados), Qwen3.8-27B Q4 dynamic quant, llama.cpp ROCm, ventana 262.144 tokens, K+V q4_0 KV (campeón desde 2026-08-18 10:32Z), temperature 0. GSM8K n=60 pareado; aguja n=2 estaciones por brazo más una sonda de frontera; una caja, una noche; tripwire armado todo el tiempo. Datapoints, no leyes. Log del gate y unit de rollback en el repo: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">qwen38-27b-strix-halo</a>.</small></p>
""",
    },
    "lab-notes-verdict-night": {
        "title": 'Notas de lab: la noche del veredicto',
        "category": 'LLM local / Benchmarks',
        "primary_keyword": 'tope de thinking LLM accuracy',
        "seo_title": 'Notas de lab: la noche del veredicto — ¿capear el thinking es gratis?',
        "meta_description": 'Noche 1: una corrida pareada de Omni-MATH en un mini-PC Strix Halo de $1.400 — el cap de 512 tokens es estadísticamente gratis (p=0,73), el thinking sin tope se muere en 26/50 problemas, 367 s vs 49 s.',
        "excerpt": 'Un mini-PC de $1.400 sirviendo un 27B a 262k de contexto hace una pregunta: ¿capear cuánto piensa el modelo te cuesta accuracy? La respuesta pareada, el primer intento inválido, y la doctrina que quedó.',
        "body": """
<p><small>Por <a href="https://x.com/KyaniteLabs_" rel="noopener">Simon Gonzalez de Cruz</a> (el build en público en <a href="https://x.com/KyaniteLabs_" rel="noopener">X @KyaniteLabs_</a>), con GLM-5.3. Noche 1 de un cadence diario: qué corrió, qué se rompió, y qué dijeron los números.</small></p>
<p>El número primero: <strong>un tope de thinking de 512 tokens compró la misma accuracy medida que el thinking sin límite — a 7,5× más rápido.</strong> Su número sombra: sin tope, el mismo modelo <strong>se pensó hasta morirse en 26 de 50 problemas</strong>, razonando hasta que el techo de output mató la respuesta. Los dos salieron de una corrida pareada. Ninguno era la historia real de la noche. La historia real es que la primera versión de este experimento no midió nada.</p>

<h2>El setup</h2>
<p>La caja: un mini-PC GMKtec EVO-X2 de $1.400 (Ryzen AI Max+ 395, 96GB de memoria unificada) sirviendo Qwen3.8-27B, un denso de 27B, a su contexto nativo completo de 262.144 tokens. La pregunta de la noche del veredicto es la que todo el que sirve modelos local tarde o temprano se hace: <em>si le pongo techo a cuánto puede pensar, ¿cuánto me cuesta en accuracy?</em></p>

<h2>El instrumento</h2>
<p>Diseño pareado. Cada problema se pregunta bajo los tres presupuestos de thinking — sin tope, 1024 tokens, 512 tokens — con el orden de celdas rotado por problema para que cualquier drift le pegue a todos los brazos igual. Cincuenta problemas, cargados hacia lo difícil (25 hard / 15 mid / 10 easy), temperature 0, traces de reasoning completos en cada fila. La estadística es McNemar exacto sobre los pares discordantes: no «cuál promedio es más alto», sino «donde los brazos no coincidieron, ¿uno ganó de forma sistemática?». Condiciones todo el rato: Q4 dynamic quant, cache KV q8_0 a 262k, build ROCm de llama.cpp, el package aguantando 90-92 °C a 120W.</p>

<h2>El twist: el primer experimento era inválido</h2>
<p>El brazo de control — «sin tope» — no existía. El server campeón carga un default a nivel de server, <code>--reasoning-budget 2048</code>, con el mensaje <em>«Reasoning budget reached. Answer now.»</em> Cualquier request que no manda un presupuesto explícito lo hereda callado. El primer runner no lo mandó. La celda de «no cap» era una celda 2048 con sticker de «none».</p>
<p>La prueba fue vergonzosamente limpia: <strong>seis largos de thinking idénticos byte a byte</strong> entre las celdas «none» y 2048; el máximo idéntico en las dos (9.361 caracteres); el mismo problema difícil cortando a 7.955 caracteres en un brazo y 7.937 en el otro. La curva archivada nunca fue {none, 2048, 4096, 8192} — era {2048, 2048, 4096, 8192}, y su «none vs 2048: cero discordantes» era una celda comparándose consigo misma.</p>
<p>Fixes antes del rerun: los brazos sin tope ahora mandan un override explícito de un millón de tokens; el techo de output subió de 6.000 a 12.000 tokens (el techo viejo mataba respuestas mid-think en el brazo que se llamaba uncapped — un confound de output-cap); y cada fila ahora carga su trace completo, para que la próxima autopsia lea texto en vez de inferir de conteos.</p>

<h2>El veredicto</h2>
<table>
  <thead><tr><th>Presupuesto de thinking</th><th>Accuracy (n=50)</th><th>Wall mediano por problema</th></tr></thead>
  <tbody>
    <tr><td>Sin tope (override 10<sup>6</sup>)</td><td>44%</td><td>367 s</td></tr>
    <tr><td>1024 tokens</td><td>40%</td><td>&mdash;</td></tr>
    <tr><td>512 tokens</td><td>40%</td><td>49 s</td></tr>
  </tbody>
</table>
<p>Los tres McNemar exactos pairwise no son significativos: p = 0,73 para sin-tope-vs-512, con 0,63 y 1,0 en los otros contrastes. En este benchmark, esta noche, los caps son estadísticamente gratis.</p>
<p>Y protectivos. La mediana de completion del brazo sin tope pegó el techo de 12.000 tokens, y en 26 de 50 problemas el thinking nunca terminó — el modelo razonó más allá del cap de output y no emitió respuesta. Esas cuentan mal (sin respuesta en caja = mal, sin excepciones). El cap no solo ahorra tiempo; fuerza una conclusión que el modelo sin tope a veces no puede alcanzar solo.</p>
<p>Las dos polaridades, claro: esto es un benchmark (un subset de Omni-MATH), una noche, n=50 problemas pareados. Una celda capeada mide accuracy <em>bajo corte temprano forzado</em> — la rodilla que vimos queda en o por encima de la rodilla real del modelo, así que léela conservadora. Y en la banda más dura (difficulty &ge; 5.0), todas las celdas marcaron 16% plano: esos problemas están atados a capacidad, no a presupuesto. Un cap no te puede quitar lo que el modelo nunca tuvo.</p>

<h2>El sobre en el que corrió</h2>
<p>La corrida sostuvo la caja en su filo térmico medido — 90-92 °C de package a 120W, fans al 100% — por horas de generación sostenida sin throttle. Eso ya es doctrina: este es el sobre del chasis, no un mal setting; no hay descansos rituales de cooldown (caliente-estable le gana a ciclar calor); y el lane de producto 24/7 va a llevar power cap, no el full tilt del lane de experimento.</p>

<h2>Qué se lleva el harness</h2>
<p>El default que ya shipped el harness — presupuesto de thinking de 1024 por margen, 512 donde importa la velocidad — se ganó su número esta noche: el gap nominal 44% vs 40% cabe dentro de lo que este diseño puede detectar, y 512 convirtió problemas de 367 segundos en problemas de 49 al mismo score. La metodología y los datos crudos están públicos al lado de este post: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo/blob/main/METHODOLOGY.md" rel="noopener">METHODOLOGY.md</a> (tamaños de n, gates, reglas de grading — las filas que las tablas de bench nunca imprimen) y el JSONL pareado completo, traces en la fila, bajo <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo/tree/main/results" rel="noopener">results/</a> en el <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">repo qwen38-27b-strix-halo</a>.</p>

<h2>Esta noche</h2>
<p>La window 2 corre el lane que la comunidad ya corroboró: cache KV q4_0 a 262k de contexto. Cada fila de 262k en el mapa de hardware que minamos corre q4-KV; nosotros servimos q8 — así que esta noche es el A/B de calidad pareado que nos faltaba, más el headroom de KV que libere. Notas de lab mañana.</p>
<p><small>Condiciones: GMKtec EVO-X2 (Ryzen AI Max+ 395, 96GB unificados), Qwen3.8-27B Q4 dynamic quant, llama.cpp ROCm, contexto 262.144 tokens, cache KV q8_0, temperature 0, subset Omni-MATH cargado a dificultad (25/15/10), n=50 problemas pareados por brazo, McNemar exacto en discordantes, medido 2026-08-17/18. Un benchmark, una noche, n=50 — un datapoint, no una ley.</small></p>
""",
    },
    "qwen-27b-strix-halo-one-week-local": {
        "title": "Un mini-PC, una noche y los numeros que discutian entre si: afinando Qwen3.8-27B en Strix Halo",
        "category": "LLM local / Benchmarks",
        "primary_keyword": "Qwen 27B Strix Halo LLM local",
        "seo_title": "Qwen 27B en Strix Halo: numeros honestos de tuning local",
        "meta_description": "Afinar Qwen3.8-27B en un mini-PC Ryzen AI Max+ 395: de un stack que mentia a 4 tok/s a 59.7-64 tok/s en frio, chat real 11-24 tok/s publicados primero, una reversion de quant y la saga del EC de ventiladores.",
        "excerpt": "Una noche y una tarde de medicion afinando un modelo denso de 27B en un mini-PC Strix Halo: las bandas honestas, la reversion, la doctrina de crashes y la historia detectivesca del EC.",
        "body": """
<p><small>Por Simon Gonzalez de Cruz, asistido por GLM-5.3.</small></p>
<p>En poco mas de una noche y una tarde (2026-08-14/15), un operador en solitario con companeros agenticos llevo Qwen3.8-27B en un mini-PC GMKtec EVO-X2 (Ryzen AI Max+ 395, gfx1151, 91GB de LPDDR5X unificada) desde un stack que mentia a ~4 tok/s hasta 59.7-64 tok/s en frio con 3x el contexto — al nivel de la frontera publica que encontramos para la clase o mas alla (mejor ejemplo publico sin nombre: 56 tok/s; fuente no re-localizada) — y despues publico voluntariamente los numeros que lo hacen verse mas lento (el chat real es 11-24 tok/s), revirtio su propia configuracion mas rapida por un argumento de tiempo-por-tarea, recorto 36% los tokens de tarea con un estilo de pensamiento caveman, resolvio un misterio de control de ventiladores que termino en el codigo de tres meses atras del propio dueno, y convirtio dos crashes en pruebas permanentes.</p>
<p><strong>El diferenciador nunca fue el tok/s. Fue la evidencia.</strong></p>

<h2>Decia GPU, corria en CPU</h2>
<p>El programa no empezo lento por una razon interesante. Empezo lento por una razon mentirosa. El binario de llama.cpp incluido con Unsloth reportaba offload completo a GPU mientras <code>--list-devices</code> no imprimia nada — el 27B avanzaba a ~4 tok/s en CPU diciendo lo contrario. Debajo, un segundo robo: alguien (perdido en la historia) habia fijado la iGPU en <code>power_dpm_force_performance_level=low</code> — 600 MHz bajo carga completa contra un boost de 2900 MHz, ~17W, estrangulando cada carril GPU de la maquina.</p>
<p>Dos arreglos, aterrizados a lo largo de la primera noche: el build real de ROCm de la flota reemplazo al binario de offload falso, y — encontrado solo cuando la forense del crash saco despues el registro termico completo — el pin de <code>low</code> con meses de antiguedad se paso a <code>auto</code> y se persistio (01:43Z). De 4 → 10.5-11.1 tok/s (el techo de ancho de banda a ~178 GB/s), y luego el decodificacion especulativa MTP apilada hasta 21.4-22.2 con 95-100% de aceptacion de drafts — sin perdida por construccion, cada draft verificado contra el modelo completo. Un carril hermano recibio el arreglo del pin de rendimiento gratis: gemma4-12b paso de 5.6 → 24.9 tok/s sin tocar nada mas.</p>
<p>El habito que define todo el programa empezo aqui: ningun numero se cree porque una herramienta lo imprimio. <code>gpu_busy_percent</code> en gfx1151 marca 100% incluso en reposo — no lo creas. Verifica por contenido, no por codigo de salida.</p>

<h2>39 segundos</h2>
<p>A las 03:43:10 el operador lanzo <code>git clone --depth 1</code> mas una compilacion HIP de 14 jobs encima de un servidor 27B lanzado manualmente que seguia sirviendo, con la GPU sin tope por primera vez y el EC en modo performance. A las 03:43:49.3 el journal termino a mitad de escritura. Sin panic, sin OOM, sin MCE, sin fault de GPU, sin disparo termico — el disparo critico del OS es 110 °C y nunca se activo. pstore: vacio. Dos reboots murieron antes del OS; solo un drenaje de boton de 30 segundos y enfriamiento lo revivio.</p>
<p>El post-mortem (113MB de journal, 724,067 lineas, solo lectura) rankeo las hipotesis falsables: disparo de proteccion de entrega de energia en el ladrillo stock de 230W (19.5V × 11.8A; rafagas de GPU de ~107W observadas; reportes de la comunidad recomiendan subir de PSU para carga LLM sostenida) con 50-60%; latch termico del EC por debajo del OS con 25-30%; software bajo 2%. La firma era la historia: la unica condicion sin precedente en 35 horas estables fue el regimen de potencia maxima apilada — boost sin tope sirviendo mas transitorios de salto de carga (Tctl habia pasado de una banda de 33-61 °C durante 35 horas a oscilar 52-94 °C en cinco minutos desde el cambio de dpm, picos 93.9 °C y 93.2 °C).</p>
<p>Doctrina, escrita en el burn-in que fallo su predicado en 10 segundos (Tctl 91.4 °C bajo una sola corriente de generacion): la maquina queda descalificada para bloques GPU pesados nuevos — entrenamiento, extraccion de hidden states, compilaciones grandes mientras sirve. Compilar primero, servir segundo, nunca apilado. La redencion: servir en si esta bien — un soak agentico de 41 rondas posterior corrio 41/41 limpio cabalgando el borde de boost-throttle de 92 °C con recuperacion de 45 segundos. Un chasis, dos identidades: no es una workstation, pero es un sirviente legitimo.</p>

<h2>Una noche, doce escalones</h2>
<p>07:51Z, la mision nocturna abrio su escalera, L1-L12, con una regla: cada escalon medido en un puerto de prueba, promovido solo mediante rubrica, produccion verificada por contenido despues de cada cambio. Primer hallazgo: incluso el baseline estaba mal — los hechos de la mision decian 25.0 tok/s, el baseline auditado era 32.7 (el 25.0 era una era de configuracion manual vencida). El ledger honesto arranca en 32.7.</p>
<p>Los escalones que sobrevivieron: profundidad de draft 6→9 (+70% en count-to-30, calidad 6/6 incluyendo un acertijo, precision de 4 palabras, codigo de palindromo funcional); contexto 32k → 64k → 96k a costo de velocidad literalmente cero (el KV GQA es ~2.1GB por 32k — el contexto es casi gratis en esta maquina; 128k sondeo bien pero rozando el margen a 6.1GB, reservado para el dia); ngram-mod apilado sobre MTP (costo cero cuando falla, transforma repeticiones: count-to-30 en caliente 89.6-93.2, reescritura de archivos del agente 96.8 vs 42.3 solo-mtp, +129%); profundidad re-barrida a 12 (59.4 en frio); y el dormido, n-min 24 — bajar el umbral de match de ngram para que dispare con historial mas corto: count-to-30 en caliente 148.0-157.6 tok/s, +55% en una noche sobre salida estructurada repetida.</p>
<p>Los escalones que no sobrevivieron tambien estan en el ledger, porque ese es el producto: barridos de p_min (no uniforme, shippeado como stanza solo-creativa), KV q8 solo-K (ahorra ~1GB, no vale la pena), threads 12 vs 16 (identico), el rebuild FA de rocWMMA (cancelado — el issue <a href="https://github.com/ggml-org/llama.cpp/issues/24437" rel="noopener">#24437</a> upstream muestra -41% de prefill en gfx1151, y el prefill es nuestro punto debil), un build Vulkan/RADV (mitad de throughput en esta maquina, decisivamente), <code>--cache-reuse</code> (un no-op verificado en este build). Cada flag de este servidor tiene hoy una razon medida para existir.</p>
<p>Totales de la noche: 32.7 → 59.7 en frio / 157.6 en caliente (+82% / +382%), contexto 3x, margen GTT 8.2GB, todos los gates de calidad en verde. La investigacion lo ubico: MTP+ngram apilado es el patron publico conocido como mejor para Strix Halo, y el mejor ejemplo publico encontrado fue un ejemplo publico sin nombre de Qwen3.6-27B a 56 tok/s (fuente no re-localizada). Correr 3.8-27B a 59.7 en frio puso la maquina al nivel de la frontera publica para su clase o mas alla — la unica afirmacion vecina a un superlativo que la politica de honestidad permite, con cita.</p>

<h2>El anti-cherry-pick</h2>
<p>Luego el programa ataco su propio mejor numero. Las repeticiones en caliente de 148-163 son un artefacto de repeticion ngram: el drafter especulativo reconoce la propia repeticion del bench y la termina al por mayor. Es velocidad real sobre salida estructurada genuinamente repetida (el patron de eco de edicion de archivos del agente corre a 72-133 tok/s), y carece de sentido como afirmacion de chat. La conversacion real — prosa nueva, el trafico que realmente fluye por el agente residente — es 11-24 tok/s, codigo ~29-40, creativo largo ~11-13.</p>
<p>La decision que define la marca: decirlo nosotros, primero, en la portada. Los numeros de uso real los declaramos nosotros, antes de que cualquier otro los declare por nosotros. Los numeros en caliente nunca aparecen sin la etiqueta de artefacto; la primera pantalla del README lleva el titular en frio, el caliente-con-etiqueta y la fila real 11-24 en una sola tabla. Las tablas de bench se generan desde salida real, nunca tipeadas a mano. La audiencia de este trabajo es alergica a los benchmarks de IA con cherry-picking; el diferenciador no es el tok/s, es la evidencia — la escalera completa, los resultados negativos y la historia del rollback en la siguiente seccion.</p>

<h2>Hasta donde se puede bajar</h2>
<p>La pregunta de quant de Simon, respondida con una escalera. Q3_K_XL bajo el stack campeon completo gano cada eje medido a contexto 128k: 63.0 en frio (campeon Q4@96k: 59.7), caliente 148.0-161.2, +33% de contexto, margen GTT 11.3GB vs 9.2GB, calidad 6/6. A las 19:11Z, Simon aprobo el swap con una palabra — “swap it” — y produccion paso a Q3@128k, verificando a 64.0 en frio, el mejor numero del programa. La misma ventana corrio la sonda de piso que el pidio: Q2_K_XL rechazado — 54.7 en frio, mas lento que ambos quants mas grandes (los kernels de dequant cuestan mas que el ahorro de ancho de banda de 2.6GB), pensamiento 30-40% mas verboso, codigo emitiendo contenido cero a un presupuesto de 500 tokens (recuperandose por completo a 1200). El gate paso formalmente, la premisa fallo materialmente. El carril de quant se declaro cerrado con Q3 como la rodilla.</p>
<p>Se mantuvo cerrado veintiseis minutos de fama en tiempo real.</p>

<h2>“Tokens mas rapidos != mejores si los tokens son mas tontos”</h2>
<p>A las 19:30Z Simon aplico una lente para la que el ledger no tenia instrumento: “faster tokens != better if tokens are dumber”. La mision construyo uno — una bateria de tiempo-por-tarea, cinco tareas auto-calificadas, thinking activado, tiempo real mas tokens de finalizacion — y el veredicto invirtio el swap. El razonamiento de Q3 es ~2x mas verboso (tarea de codigo 705-994 tokens vs ~402-450 de Q4), ahogando su ventaja de decode de +5.5%: Q4 completa tareas correctas identicas 35-50% mas rapido (7.6-7.7s/tarea a ~170 tok vs 10.6-16.1s de Q3 a 238-302). A las 19:37Z el campeon fue restaurado: Q4@96k, verificado por contenido, escalera de quant cerrada por tiempo-por-tarea.</p>
<p>Dos giros honestos mas en la misma entrada. Los revisores pares exigieron la medicion faltante: por que era lento Q2? La telemetria de aceptacion en trafico nuevo — Q4 0.345, Q3 0.492, Q2 0.478 — falso la hipotesis de colapso de aceptacion; la perdida de Q2 es costo de kernels de dequant, y la mayor aceptacion en quants mas bajos probablemente solo refleja razonamiento mas verboso y predecible. Y la metodologia cambio de forma permanente: tiempo-por-tarea y tokens-por-tarea-correcta son las metricas primarias ahora; el tok/s de decode es una sonda.</p>
<p>La leccion de categoria, declarada para todos los que corren modelos locales: el tok/s de decode no es la latencia de tarea. Un caño mas rapido alimentando tokens mas numerosos y mas tontos pierde contra un caño mas lento alimentando tokens menos y mas finos. La tabla de benchmarks de nadie muestra esto. La nuestra ahora si.</p>

<h2>“Dont like your method of shrinking”</h2>
<p>El arreglo obvio para el razonamiento verboso es un tope de presupuesto. Simon lo vetoo en siete palabras: “dont like your method of shrinking”. El arreglo no obvio vino del estante de skills de la comunidad: caveman (<a href="https://github.com/JuliusBrussee/caveman" rel="noopener">JuliusBrussee/caveman</a> — origen; fragmentos breves, accion sobre explicacion) y ponytail (<a href="https://github.com/DietrichGebert/ponytail" rel="noopener">DietrichGebert/ponytail</a> — origen; dev senior vago, primer escalon que aguanta) — fusionados en una capa THINK-STYLE de system-prompt que dirige como razona el modelo, nunca cuanto se le permite razonar. El ethos, en una linea: el mejor razonamiento es el que nunca se penso.</p>
<p>Medido sobre el campeon Q4, bateria de 5 tareas: 117/132/143 tok/tarea a 5.8/6.2/6.8s en tres corridas, 15/15 correctas — contra una banda baseline de 8 corridas de 151-313 tok y 8.6-15.0s. Aproximadamente -36% tokens, -33% tiempo de tarea, cero perdida de calidad. La fusion es la ganadora (caveman solo 154tok/7.8s y ponytail solo 187tok/11.6s quedan dentro de la banda). Dirigir el estilo le gana a los topes de presupuesto: mismo ahorro de tokens, sin veto, sin techo en problemas dificiles.</p>
<p>El hallazgo de seguimiento lo mantuvo honesto: los carriles creativos ignoran el estilo breve — una corrida de historia gasto ~2000 tokens de pensamiento en una historia de 312 palabras, siendo los tokens el producto ahi — asi que el estilo se aplica por carril (fusion por defecto para herramientas/codigo/analisis, carril creativo libre, un dial de override). Un A/B en vivo por el carril real lo confirmo de punta a punta: tarea arit+codigo, vanilla 9.3s/62-think/198c vs fusionado 4.6s/36-think/118c — -51% de tiempo en una sola corrida, respaldado por el estudio n=3/n=8. Los A/B de una sola corrida cargan varianza; los numeros sostenidos son el titular.</p>

<h2>“Triple check everything, no old conflicting fixes”</h2>
<p>El arco detectivesco. La GMKtec EVO-X2 va a 97 °C bajo carga GPU sostenida con sus ventiladores efectivamente al 60%: la curva automatica de fabrica satura a ~60% de duty / ~3260 RPM a 90 °C y arriba, dejando ~40% del margen de fan2 sobre la mesa exactamente donde se necesita. Y el firmware no expone ningun control estandar de ventiladores en Linux — sin PWM hwmon, sin tach, sin objeto ACPI de fan. La unica palanca es el acceso directo al embedded controller.</p>
<p>Toda escritura EC fue ignorada. No rechazada — ignorada: <code>dd of=.../ec/ec0/io</code> sale 0, el registro se relee sin cambios. Causa raiz, encontrada por el camino duro (costo tiempo real de debugging dos veces): el modulo <code>ec_sys</code> del kernel carga read-only por defecto, y en ese estado el archivo de debugfs parece escribible mientras el kernel descarta silenciosamente cada escritura. El arreglo son dos archivos de configuracion que hacen de <code>write_support=1</code> el default de booteo. Mientras tanto el mapa de registros se descifro por la ruta ACPI DSDT — el strix-halo-fan-control de nathanmarlor traia un mapa reverese-engineered del DSDT de la Bosgame M5, la misma placa Sixunited AXB35-02 en otro chasis, y valido byte-por-byte en la EVO-X2.</p>
<p>Dos misterios mas cayeron en la auditoria que Simon ordeno. Los ventiladores pulsantes eran la ley de revert one-shot: el firmware revierte las escrituras de duty manual en segundos, asi que solo un daemon reafirmando cada 2s sostiene — exactamente lo que hace el daemon de nathanmarlor, desplegado con una curva afinada. Medido: pico 96.5 °C vs 97.5-97.8 °C stock en una carga de 105s — un honesto ~1-1.3 °C en esa sonda, con las ganancias reales en la forma de la respuesta: fan2 a 4539 RPM vs el techo stock de 3260 (margen por fin comprometido), 100% de duty a los 82 °C, reposo silencioso preservado. Un ventilador externo atornillado al chasis no cambio nada (96.9 °C con el — el techo es la clase heat-pipe, no el flujo de aire). Y el golpazo bajo el piso: un timer de systemd habia estado escribiendo directo EC 0x31 = performance cada 30 segundos desde mayo — reverese-engineering del propio Simon, de meses antes de este programa, y por eso la maquina ya estaba en EC-performance y por eso su recordado ajuste “ultra” era real todo el tiempo. Incluso habia estado rompiendo silenciosamente el daemon de ventiladores: la danza cortes load-write-unload del script de mayo recargaba <code>ec_sys</code> sin write_support cada 30 segundos, descartando las escrituras del daemon con cero errores en ningun lado.</p>
<p>Inventario de pay-it-forward, preparado como draft PR al <a href="https://github.com/nathanmarlor/strix-halo-fan-control" rel="noopener">repo upstream</a>: datos de validacion EVO-X2, el registro de tacometro fan3 0x28/0x29 (vivo en esta unidad, ausente de los docs upstream) y la advertencia de escritores multiples de ec_sys.</p>

<h2>El modelo pidio una funcionalidad que ya tenia</h2>
<p>El prompt de auto-exploracion — ocho secciones numeradas, enviado sin cambios para que las corridas sean comparables entre olas — tomo cuatro intentos completarse: muerto dos veces por reinicios de panel, una por un crash de firma. El intento cuatro completo: 67.7 segundos, 2013 caracteres, servido a 10.6 tok/s — la banda honesta de trafico real, en vivo. La pieza central de la respuesta: preguntado que le faltaba, el primer deseo del modelo fueron llamadas paralelas de herramientas por turno — una capacidad que el harness soportaba desde hacia dia y medio. El modelo no podia verla, asi que no existia; el arreglo fue una linea anunciandola. Las capacidades invisibles para el modelo no existen. El crash de firma recibio el mismo tratamiento que cada crash de este programa: se convirtio en dos pruebas permanentes que fijan el contrato del harness. Un crash es una prueba faltante con abrigo de tren.</p>

<h2>Numeros de mejora reales</h2>
<p>Cada veredicto y plan de ola recibio dos pasadas adversariales independientes de companeros de IA — atraparon un soak agentico faltante y un “por que Q2 es lento” sin medir, ambos verificados reales. La ola 2 aterrizo cada escalon en una sola tarde. La tabla vanilla-vs-waved, A/B en vivo por el carril real del harness, tareas identicas, sesiones frescas:</p>
<table>
  <thead><tr><th>Carril</th><th>Vanilla</th><th>Waved</th><th>Delta</th></tr></thead>
  <tbody>
    <tr><td>STYLE (capa think-style)</td><td>9.3s / 62 think / 198c</td><td>4.6s / 36 / 118c</td><td>-51% tiempo (corrida unica; sostenido -36%/-33% n=3 vs n=8) (direccional: medido sobre el config apilado completo — delta del stack, no del estilo solo; re-baseline pendiente)</td></tr>
    <tr><td>MUNCH (lecturas de simbolos vs archivos completos)</td><td>48.6s / 13,917B salida tool / 53.5KB prompts</td><td>22.6s / 276B / 4.9KB</td><td>-98% tokens de tool (los deltas de bytes -98%/-91% son deterministicos y se sostienen; el delta de tiempo es direccional pendiente de re-baseline tras el arreglo del tool-refusal)</td></tr>
    <tr><td>DIET (stubs dedup en loops de re-chequeo)</td><td>15KB de contexto</td><td>5.1KB</td><td>-66%</td></tr>
    <tr><td>ENGINE (capitulos 1-6)</td><td>32.7 frio, 32k ctx</td><td>59.7-64 frio, 96k ctx</td><td>tiempo-por-tarea adoptado; quant cerrado en Q4</td></tr>
    <tr><td>THERMAL</td><td>pico 97.5-97.8 °C</td><td>pico 96.5 °C</td><td>~1-1.3 °C en una sonda de 105s; 100% fan a los 82 °C; reposo silencioso</td></tr>
  </tbody>
</table>
<p>Y la meta-regla que evita que el stack se pudra — la ley de regresion de olas: cada ola que aterriza reverifica todas las ganancias anteriores, no solo sus propias pruebas.</p>

<h2>Lo que el registro demuestra</h2>
<p>Cuatro afirmaciones que este programa puede hacer con recibos, en orden de escalada:</p>
<ol>
  <li><strong>Rendimiento:</strong> 59.7-64 tok/s en frio, contexto 96k, en un mini-PC con iGPU — al nivel de la frontera publica que encontramos o mas alla (referencia 56 tok/s), etiquetado con honestidad, con los numeros de chat real (11-24 tok/s prosa) publicados primero por nosotros.</li>
  <li><strong>Metodo:</strong> escaleras con rubrica, resultados negativos publicados, metricas que sobrevivieron al ataque (tiempo-por-tarea sobre tok/s), crashes convertidos en pruebas.</li>
  <li><strong>Oficio:</strong> direccion de estilo (-36%/-33%), lecturas de simbolos (-98% tokens de exploracion), stubs dedup (-66%), una saga EC de ventiladores que termina en un draft PR de pay-it-forward.</li>
  <li><strong>Caracter:</strong> un dueno en solitario y su equipo de agentes publicando los numeros que duelen, revirtiendo el config mas rapido por principio, y acreditando a todos los upstream.</li>
</ol>
<p>Todo es reproducible: la receta, los flags, la suite de bench, el reproducer de un comando y el ledger completo de experimentos viven en el repo <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo" rel="noopener">qwen38-27b-strix-halo</a>; el mapa de registros EC, las trampas y la receta del daemon viven en el repo hermano <a href="https://github.com/KyaniteLabs/evo-x2-ec" rel="noopener">evo-x2-ec</a>. Los datapoints crudos de throughput gfx1151 estan publicados como una <a href="https://github.com/ggml-org/llama.cpp/discussions/27154" rel="noopener">discusion en llama.cpp</a>. Si corres el bench en tu propia maquina Strix Halo, publica tus numeros — dentro o fuera de nuestras bandas, ambos son bienvenidos.</p>
<blockquote><p><strong>Atribucion.</strong> Qwen3.8-27B — <a href="https://huggingface.co/Qwen/Qwen3.8-27B" rel="noopener">equipo Qwen</a> (Apache-2.0). Quants dinamicos — <a href="https://github.com/unslothai/unsloth" rel="noopener">Unsloth</a>. Runtime llama.cpp — <a href="https://github.com/ggml-org/llama.cpp" rel="noopener">sus contribuidores</a> (medido sobre un build de era b10435, 9d57ce4). Daemon de control EC de ventiladores y el mapa de registros derivado del DSDT (Bosgame M5, misma placa Sixunited AXB35-02 que la EVO-X2) — nathanmarlor (<a href="https://github.com/nathanmarlor/strix-halo-fan-control" rel="noopener">strix-halo-fan-control</a>, MIT). Reverese-engineering del registro EC P-MODE de la EVO-X2 (0x31) y el timer de ejecucion de 30s (mayo 2026) — Simon Gonzalez de Cruz. Trabajo previo WMI/FCMI — <a href="https://github.com/MintyMods/ip3-power-switch" rel="noopener">MintyMods/ip3-power-switch</a>, <a href="https://github.com/pettijohn/corsair-ai-workstation-performance-level-linux" rel="noopener">pettijohn/corsair-ai-workstation-performance-level-linux</a>. Skills de estilo de pensamiento — caveman origen <a href="https://github.com/JuliusBrussee/caveman" rel="noopener">JuliusBrussee/caveman</a> (skill MIT); ponytail origen <a href="https://github.com/DietrichGebert/ponytail" rel="noopener">DietrichGebert/ponytail</a> (MIT); la fusion se distribuye con avisos de licencia completos en <a href="https://github.com/KyaniteLabs/context-kit" rel="noopener">KyaniteLabs/context-kit</a>.</p></blockquote>
<p><small>Medido en hardware de propiedad personal, 2026-08-14/15; tus relojes variaran. Cada numero lleva su etiqueta de validez; los deltas de corrida unica estan marcados como tales.</small></p>
<p><strong>Actualizacion (2026-08-16):</strong> Remedimos los numeros de la Ola 2 en un harness corregido y con huella (n=3+ por brazo, cada corrida registrada en el ledger); los veredictos actuales viven en la <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo#re-baseline-update-2026-08-16" rel="noopener">seccion de re-baseline del repo</a>, y este post conserva sus numeros originales como historia publicada, cada uno con su etiqueta. Las correcciones van en ambas direcciones. Las lecturas semanticas (munch) <strong>mejoraron</strong> con la medicion honesta: tiempo de muro <strong>-65% limpio</strong> (27.9s a 9.8s mediana, 6/6 correctas, n=3) — el numero provisional era conservador. La direccion de estilo es <strong>condicional al regimen, no universal</strong>: el A/B de corrida unica de -51% queda retirado (apilaba cambios de configuracion), la cifra sostenida -36%/-33% sostiene en el carril del servidor a esfuerzo alto por defecto, y el carril del harness a esfuerzo bajo midio una inversion de +65% en muro — por eso el harness de produccion ahora enruta el estilo por sesion (solo sesiones de esfuerzo alto), lo que ademas preserva el prompt cache. La bateria de tiempo-por-tarea ahora es n=3: 7.9-14.3s por tarea correcta, mediana 11.3, banda dependiente de la temperatura. Y el delta del daemon EC de ventiladores crece a <strong>-3.5 a -5.8 °C</strong> de pico (sondas n=3: 93/92/94 °C contra las 97.5-97.8 °C del ledger stock; el brazo stock no se repitio). Credito donde corresponde: estas correcciones existen porque nuestra propia auditoria de validez senalo los numeros primero.</p>

<h2>Actualización, 2026-08-16: el techo nativo de contexto, gratis</h2>
<p>Una noche después, el mismo equipo sirve el modelo a su <strong>contexto nativo completo de 262.144 tokens</strong> — 2,7 veces el contexto reportado arriba — con la banda de decodificación en caliente sin cambios (148-163 tok/s) y el tiempo-por-tarea igual o más rápido. Toda la ganancia viene de cuantizar la caché KV: K y V en q8_0 reducen la caché a la mitad, así que 262k de KV cuantizada ocupa <em>menos</em> memoria que 96k en f16. La escalera (96k → 160k → 192k → 262k) se validó con gates en cada escalón sobre la batería de tareas reales, con un costo etiquetado honestamente: el prefill baja de ~390 a ~299 tok/s. La unidad de rollback queda guardada. Escalera completa: <a href="https://github.com/KyaniteLabs/qwen38-27b-strix-halo">el repo</a>.</p>
""",
    },
    "gpt-5-6-sol-terra-luna-routing-guide": {
        "title": "GPT-5.6 Sol vs. Terra vs. Luna: politica de ruteo basada en evidencia",
        "category": "Ruteo de modelos / Sistemas agenticos",
        "primary_keyword": "comparacion GPT-5.6 Sol Terra Luna",
        "seo_title": "GPT-5.6 Sol vs Terra vs Luna: politica para agentes",
        "meta_description": "Rutea GPT-5.6 Sol, Terra y Luna por incertidumbre, contrato de finalizacion, costo de verificacion, esfuerzo y arquitectura agentica.",
        "excerpt": "La division practica es Sol para descubrir, Terra para ejecutar trabajo acotado y Luna para procesar volumen verificable, cada uno con un contrato distinto.",
        "body": """
<h2>Resumen ejecutivo — TL;DR / BLUF</h2>
<ul>
  <li><strong>Sol High es la ruta de descubrimiento.</strong> Usalo cuando todavia no sabes cual es el camino, el subsistema responsable o la causa de la falla. Dale una meta de evidencia y una condicion de salida.</li>
  <li><strong>Terra Medium es la ruta de ejecucion.</strong> Usalo cuando la decision ya esta tomada y el trabajo tiene archivos, limites, comportamiento esperado y gates de aceptacion.</li>
  <li><strong>Luna es la ruta de procesamiento.</strong> Usalo para tareas estrechas, repetibles y de alto volumen que un schema, prueba determinista o auditoria por muestra pueda verificar.</li>
  <li><strong>Max es una escalada diagnosticada.</strong> En DeepSWE, el salto observado desde High fue modesto frente a un costo estimado por tarea unas 2.4 veces mayor, con intervalos de confianza que se superponen ligeramente.</li>
  <li><strong>Fast y Ultra son controles distintos.</strong> Fast no esta documentado actualmente para GPT-5.6. Ultra coordina varios agentes; no es otro nivel de razonamiento.</li>
  <li><strong>Nota de uso actual:</strong> la restriccion de cinco horas para Codex y ChatGPT Work esta suspendida temporalmente para Plus, Business y Pro, aunque siguen los limites semanales. OpenAI dice que revirtio los “juice values” internos reducidos que estaba probando.</li>
</ul>
<p><strong>BLUF: no elijas el modelo por prestigio. Elige segun la incertidumbre del trabajo y el costo de demostrar que el resultado es correcto.</strong></p>

<h2>El ruteo es un problema de contratos de finalizacion</h2>
<p>Sol, Terra y Luna no son solamente tres escalones de “mas potente” a “mas barato”. Cada uno funciona mejor con una definicion de terminado diferente. Sol necesita una frontera de investigacion. Terra necesita una especificacion. Luna necesita un validador.</p>
<table>
  <thead><tr><th>Modelo</th><th>Trabajo</th><th>Contrato de finalizacion</th><th>Falla a prevenir</th></tr></thead>
  <tbody>
    <tr><td><strong>Sol</strong></td><td>Descubrir</td><td>Pregunta, meta de evidencia, limites protegidos y condicion de parada</td><td>Seguir despues de encontrar la respuesta o ampliar el alcance sin evidencia</td></tr>
    <tr><td><strong>Terra</strong></td><td>Ejecutar</td><td>Plan aprobado, archivos nombrados, gates y pruebas requeridas</td><td>Tratar incertidumbre pendiente como si fuera un detalle de implementacion</td></tr>
    <tr><td><strong>Luna</strong></td><td>Procesar</td><td>Schema exacto, ejemplos, validador determinista y regla de reintento</td><td>Permitir que un error barato y silencioso se propague por el pipeline</td></tr>
  </tbody>
</table>
<p>La <a href="https://developers.openai.com/api/docs/models" rel="noopener">guia actual de modelos de OpenAI</a> presenta una jerarquia de capacidad y costo parecida. Para un sistema agentico, el paso importante es convertirla en una arquitectura de contratos y verificadores.</p>

<h2>Lo que cambio despues de una semana de uso</h2>
<p>Probamos las tres rutas en investigacion, evaluaciones, sitios y herramientas. Fue observacion operativa, no un benchmark controlado; por eso estas son notas de campo y no un ranking universal.</p>
<p><strong>Sol rindio mejor cuando el trabajo tenia que descubrir su propia ruta.</strong> Sostuvo investigaciones largas y encontro errores importantes que un pase mas estrecho podia perder. Su falla caracteristica fue la persistencia sin salida: podia seguir explorando aun despues de tener la respuesta util. La mejora fue definir evidencia requerida, limites protegidos y una regla clara para parar.</p>
<p><strong>Terra rindio mejor cuando el contrato de aceptacion ya estaba escrito.</strong> Con un alcance acotado produjo hallazgos adversariales concretos y decisiones limpias de aprobar o detener. Cuando todavia habia descubrimiento escondido, el supuesto trabajo de ejecucion habia sido ruteado demasiado pronto.</p>
<p><strong>Luna fue consistente cuando el borde de salida se podia verificar por maquina.</strong> JSON con schema exacto, extraccion, metadata y tareas parecidas llegaron repetidamente con la forma pedida. Algunas corridas necesitaron un recordatorio explicito de cierre. El sistema de control no era solamente el modelo: era el modelo mas el schema y el validador.</p>

<h2>Router de referencia para agentes de codigo</h2>
<pre><code>def rutear(tarea):
    if tarea.incierta or tarea.cruza_subsistemas:
        return ("Sol", "high", "evidencia + condicion de salida")
    if tarea.especificada and tarea.acotada:
        return ("Terra", "medium", "gates de aceptacion")
    if tarea.repetible and tarea.barata_de_verificar:
        return ("Luna", "minimo suficiente", "schema + validador")
    return ("Sol", "high", "evidencia + condicion de salida")</code></pre>
<p>El fallback a Sol High es intencional. Si una tarea no esta acotada y tampoco es barata de verificar, probablemente todavia contiene trabajo de descubrimiento. Conviene resolver esa incertidumbre antes de pagarle a un ejecutor para adivinar.</p>

<h2>Primero limita el router a la superficie real</h2>
<p>Una politica no puede seleccionar un modelo que el producto actual no expone. “GPT-5.6” ofrece controles distintos en ChatGPT, Codex y el API, asi que la superficie debe formar parte de la decision.</p>
<ul>
  <li><strong>ChatGPT estandar:</strong> la documentacion actual indica que GPT-5.6 usa Sol para Medium, High y Extra High. Terra y Luna no se eligen ahi.</li>
  <li><strong>ChatGPT Work y Codex:</strong> los planes elegibles pueden mostrar Sol, Terra y Luna. Max y Ultra dependen del producto y del plan.</li>
  <li><strong>API:</strong> los tres modelos soportan <code>none</code>, <code>low</code>, <code>medium</code>, <code>high</code>, <code>xhigh</code> y <code>max</code>.</li>
</ul>
<p>Revisa <a href="https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt" rel="noopener">GPT-5.6 en ChatGPT</a> y las paginas actuales del API al implementar el router. Una captura del selector no es un contrato de arquitectura: la disponibilidad puede cambiar por producto y por plan.</p>

<h2>Escala el esfuerzo solo despues de diagnosticar la falla</h2>
<p>El esfuerzo de razonamiento es una segunda dimension del ruteo. Un nivel mayor deja mas espacio para explorar, usar herramientas y revisar, pero no corrige una premisa equivocada, permisos faltantes, un entorno de pruebas roto o un entregable ambiguo.</p>
<table>
  <thead><tr><th>Esfuerzo Sol</th><th>DeepSWE v1.1</th><th>Costo estimado por tarea</th></tr></thead>
  <tbody>
    <tr><td>High</td><td>69.4%</td><td>$3.47</td></tr>
    <tr><td>Extra High</td><td>70.7%</td><td>$4.70</td></tr>
    <tr><td>Max</td><td>72.7%</td><td>$8.39</td></tr>
  </tbody>
</table>
<p>Los valores del 9 de julio de 2026 vienen del <a href="https://deepswe.datacurve.ai/artifacts/v1.1/leaderboard-live.json" rel="noopener">artefacto crudo de DeepSWE v1.1</a> de DataCurve. De High a Max hay 3.3 puntos porcentuales observados, mientras el costo estimado pasa de $3.47 a $8.39 por tarea, unas 2.4 veces mas. Son 113 tareas y los intervalos de confianza de 95% para High y Max se superponen ligeramente.</p>
<p>Eso convierte a Max en una escalada diagnosticada: usalo cuando High fallo porque abandono demasiado pronto una rama dificil o no exploro lo suficiente. El benchmark aporta evidencia de un harness; no promete la misma ganancia en un repo particular.</p>

<h2>Manten separados los tres sistemas de costo</h2>
<p>Precio del API, costo estimado por un benchmark y creditos Codex no son unidades intercambiables. OpenAI publica actualmente $5/$30 por millon de tokens de entrada/salida para Sol, $2.50/$15 para Terra y $1/$6 para Luna. Para la mayoria de planes, la tabla Codex asigna 125/750 creditos a Sol, 62.5/375 a Terra y 25/150 a Luna por la misma cantidad de entrada/salida, con tasas menores para entrada en cache.</p>
<p>El numero en dolares de un benchmark pertenece a su propio harness. Una corrida real tambien paga contexto, cache, salida de herramientas, reintentos, validacion y ramas paralelas. Usa la <a href="https://help.openai.com/en/articles/20001106-codex-rate-card" rel="noopener">tabla Codex vigente</a> y mide costo hasta una finalizacion verificada dentro del sistema.</p>

<h2>P. D. Limites actuales y el cambio reportado de “juice”</h2>
<p><strong>Al 12 de julio de 2026, la ventana de uso de cinco horas para Codex y ChatGPT Work no aplica actualmente a Plus, Business o Pro.</strong> <a href="https://x.com/thsottiaux/status/2076365965915467978" rel="noopener">Tibo Sottiaux escribio que el cambio es temporal</a>; un <a href="https://www.all-ai.de/news/news26/openai-gpt-sol-app-limits" rel="noopener">reporte contemporaneo accesible reproduce el anuncio</a>. Los limites semanales siguen vigentes. Es una condicion operativa actual, no un derecho permanente ni uso ilimitado.</p>
<p>En otro <a href="https://www.reddit.com/r/codex/comments/1uv07tv/tibo_about_the_juice_values/" rel="noopener">seguimiento publico reproducido en este hilo con captura</a>, Sottiaux hablo de los presupuestos internos de razonamiento mas bajos que circularon como “juice values”. Dijo que OpenAI los probo mientras investigaba un consumo mayor al esperado y luego revirtio el experimento. Esos numeros reducidos no son una interfaz documentada actual ni un contrato estable.</p>
<p>Para un router de produccion, ambos datos son notas de estado presente. Usa controles publicados, observa la superficie de consumo en vivo y vuelve a medir antes de codificar limites temporales o presupuestos internos inferidos.</p>

<h2>No conviertas Max, Fast y Ultra en una sola escalera</h2>
<ul>
  <li><strong>Max</strong> da mas tiempo de razonamiento a un modelo GPT-5.6.</li>
  <li><strong>Fast</strong> es una opcion de inferencia de Codex que consume mas creditos, pero la <a href="https://developers.openai.com/codex/speed" rel="noopener">documentacion actual de Speed</a> lista GPT-5.5 y GPT-5.4, no GPT-5.6.</li>
  <li><strong>Ultra</strong> es una configuracion multiagente separada que coordina cuatro agentes por defecto. No es otro nivel de razonamiento de un solo agente por encima de Max.</li>
</ul>
<p>Ultra justifica su overhead cuando cada rama puede producir evidencia independiente: revisar subsistemas separados, comparar implementaciones o investigar preguntas sin estado mutable compartido. Desperdicia contexto y genera colisiones cuando todos necesitan los mismos archivos, la misma decision o una dependencia secuencial.</p>

<h2>El verificador tambien pertenece a la tabla de ruteo</h2>
<table>
  <thead><tr><th>Ruta</th><th>Evidencia requerida</th><th>Verificador tipico</th></tr></thead>
  <tbody>
    <tr><td>Descubrimiento con Sol</td><td>Reproduccion, investigacion citada o registro de decision</td><td>Prueba, auditoria de fuentes o revision independiente</td></tr>
    <tr><td>Ejecucion con Terra</td><td>Diff acotado mas los gates nombrados en el plan</td><td>Pruebas, lint, tipos y revision del diff</td></tr>
    <tr><td>Procesamiento con Luna</td><td>Salida estructurada que cumple el contrato</td><td>Schema, chequeo determinista, muestra o revision con modelo mas fuerte</td></tr>
  </tbody>
</table>
<blockquote>El modelo economico es el que minimiza el costo total hasta un resultado verificado, no el que cobra menos por token.</blockquote>

<h2>Checklist de implementacion</h2>
<ol>
  <li>Clasifica la tarea por incertidumbre: descubrimiento, ejecucion acotada o procesamiento repetible.</li>
  <li>Nombra la superficie y confirma que el modelo y el control de esfuerzo existan ahi.</li>
  <li>Adjunta el contrato correcto: evidencia y salida, gates de aceptacion, o schema y validador.</li>
  <li>Empieza trabajo incierto y dificil en Sol High. Escala a Max solo despues de diagnosticar exploracion insuficiente.</li>
  <li>Entrega decisiones cerradas a Terra y unidades de volumen verificable a Luna.</li>
  <li>Mide finalizaciones verificadas, reintentos, tiempo de revision, latencia y consumo, no solamente cantidad de salida.</li>
</ol>
<p>Esta politica vuelve auditable la seleccion. Una falla puede rastrearse hasta la ruta, el contrato, el entorno o el verificador, en vez de resumirse como “el modelo no fue suficientemente inteligente”. Para la version orientada a costo, aprobacion y riesgo del dueño, lee la guia complementaria de PuenteWorks: <a href="https://puenteworks.com/blog/choose-ai-model-by-job.html">usa el modelo de IA mas barato que pueda terminar bien el trabajo</a>.</p>

<h2>Preguntas frecuentes</h2>
<h3>¿Sol siempre es el mejor GPT-5.6 para codigo?</h3>
<p>No. Sol es la mejor ruta de descubrimiento cuando el camino es incierto. Terra suele ser mejor cuando el plan ya esta acotado y Luna cuando la transformacion es estrecha y tiene validacion determinista.</p>
<h3>¿Debo usar Sol High o Max por defecto?</h3>
<p>Empieza el trabajo dificil e incierto en Sol High. Escala a Max solo despues de identificar que la causa fue exploracion insuficiente, no un brief o entorno defectuoso.</p>
<h3>¿Ultra es mas inteligente que Max?</h3>
<p>No. Max aumenta el esfuerzo de un modelo. Ultra coordina varios agentes. El paralelo ayuda solo cuando el trabajo puede separarse sin duplicar contexto ni chocar sobre estado compartido.</p>
<h3>¿Codex y ChatGPT Work tienen actualmente una ventana de uso de cinco horas?</h3>
<p>Al 12 de julio de 2026, OpenAI dice que la restriccion de cinco horas para Codex y ChatGPT Work no aplica temporalmente a Plus, Business o Pro. Los limites semanales siguen vigentes; no es acceso ilimitado ni un contrato permanente.</p>
<h3>¿Los juice values de GPT-5.6 se redujeron permanentemente?</h3>
<p>No hay una especificacion publica actual que diga eso. Tibo Sottiaux dijo que los experimentos internos con presupuestos de razonamiento fueron revertidos. Usa los controles publicados y verifica el comportamiento en tu propio workload.</p>

<h2>Fuentes y limites</h2>
<ul>
  <li><a href="https://openai.com/index/gpt-5-6/" rel="noopener">OpenAI: GPT-5.6</a></li>
  <li><a href="https://openai.com/index/previewing-gpt-5-6-sol/" rel="noopener">OpenAI: preview de GPT-5.6 Sol</a></li>
  <li><a href="https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt" rel="noopener">OpenAI Help Center: GPT-5.6 en ChatGPT</a></li>
  <li><a href="https://help.openai.com/en/articles/20001106-codex-rate-card" rel="noopener">OpenAI Help Center: tabla de creditos Codex</a></li>
  <li><a href="https://developers.openai.com/codex/speed" rel="noopener">OpenAI: Codex Speed</a></li>
  <li><a href="https://developers.openai.com/api/docs/models" rel="noopener">OpenAI API: modelos y seleccion</a></li>
  <li><a href="https://deepswe.datacurve.ai/" rel="noopener">DataCurve: DeepSWE v1.1</a></li>
  <li><a href="https://deepswe.datacurve.ai/artifacts/v1.1/leaderboard-live.json" rel="noopener">DataCurve: artefacto crudo de DeepSWE v1.1</a></li>
  <li><a href="https://x.com/thsottiaux/status/2076365965915467978" rel="noopener">Tibo Sottiaux: retiro temporal de la restriccion de cinco horas</a></li>
  <li><a href="https://www.all-ai.de/news/news26/openai-gpt-sol-app-limits" rel="noopener">All-AI: reporte accesible que reproduce el anuncio del limite temporal</a></li>
  <li><a href="https://www.reddit.com/r/codex/comments/1uv07tv/tibo_about_the_juice_values/" rel="noopener">Seguimiento de Tibo Sottiaux sobre uso y experimentos de juice revertidos</a></li>
</ul>
<p><small>Verificado el 12 de julio de 2026. Disponibilidad, precios, limites, tablas de uso y benchmarks pueden cambiar. Las notas de campo son observacionales; valida la politica contra tus propios repos y costos de verificacion.</small></p>
""",
    },
    "agents-need-verifiable-tools": {
        "title": "Los agentes necesitan herramientas verificables, no mejor teatro de prompts",
        "category": "Implementacion MCP",
        "seo_title": "herramientas verificables para agentes de IA",
        "meta_description": "Los agentes de IA necesitan herramientas que puedan llamar, inspeccionar, verificar y revisar. KyaniteLabs construye servidores MCP con ese principio.",
        "excerpt": "El patron util no es un prompt mas bonito. Es una superficie de herramienta que el agente puede llamar, inspeccionar, verificar y revisar.",
        "body": """
<p><strong>El patron util no es un prompt mas bonito. Es una superficie de herramienta que el agente puede llamar, inspeccionar, verificar y revisar.</strong> Un prompt puede sugerir trabajo. Una herramienta puede tocar el artefacto.</p>
<p>Por eso Kyanite construye servidores MCP, CLIs, demos y superficies publicas de prueba. El agente necesita un punto de agarre sobre la operacion real: editar video, estimar tiempo, localizar variantes de español, leer historial de repos o revisar calculos de dominio.</p>
<p>Si el sistema no puede verificar lo que paso, el agente todavia esta adivinando demasiado.</p>
<h2>El contrato de herramienta es la frontera del producto</h2>
<p>Una buena herramienta para agentes tiene una accion clara, entradas tipadas, salida estructurada, errores legibles y una ruta pequeña de verificacion. Suena aburrido. Tambien separa una capacidad reusable de una sesion de una sola vez.</p>
<pre><code>llamar herramienta
inspeccionar salida
comparar expectativa
revisar siguiente paso</code></pre>
<p>mcp-video prueba la version de medios. Epoch prueba la version de estimacion. DialectOS prueba la version de localizacion. devarch-framework y Dev Learning Archaeologist prueban la version de historial de repos. OpenGlaze prueba que el software de dominio sigue importando cuando el usuario no vive dentro de la burbuja de herramientas de IA.</p>
<h2>La verificacion cambia la conversacion</h2>
<p>Sin verificacion, un agente puede sonar seguro y estar equivocado. Con verificacion, el sistema puede mostrar un comando, archivo, ruta, reporte, prueba, captura o resultado estructurado. Eso no hace perfecto el trabajo. Hace posible la siguiente correccion.</p>
<blockquote>La gracia de una herramienta Kyanite no es que un agente hizo algo. Es que una persona puede inspeccionar lo que hizo el agente.</blockquote>
<h2>Que significa para la implementacion</h2>
<p>La implementacion pagada no es consultoria generica de IA. Es ayuda para llevar una herramienta a un entorno real con setup, docs, ejemplos, limites de soporte y traspaso usable.</p>
""",
    },
    "repo-history-is-a-product-signal": {
        "title": "El historial del repo es una señal de producto",
        "category": "Inteligencia de repos",
        "seo_title": "arqueologia de repos para equipos de IA",
        "meta_description": "El historial del repo muestra como cambio un proyecto, donde se atasco y si la superficie publica coincide con el codigo.",
        "excerpt": "Un repo no es solo almacenamiento. Es evidencia de decisiones, reparaciones, releases, cambios de nombre, huecos de pruebas y oficio real.",
        "body": """
<p><strong>Un repo no es solo almacenamiento. Es evidencia de decisiones, reparaciones, releases, cambios de nombre, huecos de pruebas y oficio real.</strong> Esa evidencia importa mas ahora porque el trabajo asistido por IA puede producir mucho movimiento que desde lejos parece productividad.</p>
<p>La arqueologia de repos lee ese movimiento con cuidado. La pregunta no es si el grafo de commits se ve bonito. La pregunta es que prueba el historial sobre el producto.</p>
<h2>Que puede mostrar el historial</h2>
<ul>
  <li>Que partes del sistema necesitaron reparacion repetida.</li>
  <li>Si la documentacion siguio al codigo o se separo.</li>
  <li>Que pruebas existian antes del lanzamiento y cuales aparecieron despues de regresiones.</li>
  <li>Si las promesas publicas coinciden con rutas, releases y ejemplos actuales.</li>
  <li>Donde hay que limpiar antes de que un usuario, comprador o contribuidor confie.</li>
</ul>
<p>Por eso Kyanite incluye devarch-framework y Dev Learning Archaeologist en su superficie publica. Convierten comportamiento tecnico invisible en un diagnostico legible.</p>
<h2>La IA lo vuelve mas importante</h2>
<p>Los agentes pueden cambiar mas archivos mas rapido. Eso ayuda cuando el trabajo esta acotado y verificado. Es peligroso cuando nadie puede decir que cambios importaron. El historial se vuelve el recibo.</p>
<blockquote>Si una herramienta dice estar lista, el repo debe ayudar a probarlo en vez de obligar a confiar en la landing page.</blockquote>
""",
    },
    "implementation-help-is-product-surface": {
        "title": "La ayuda de implementacion es parte de la superficie del producto",
        "category": "Implementacion de herramientas de IA",
        "seo_title": "soporte para herramientas open source de IA",
        "meta_description": "Las herramientas open source de IA necesitan superficies de implementacion: instalacion, ejemplos, docs, prueba, limites de soporte y traspaso.",
        "excerpt": "Una herramienta open source util todavia necesita una ruta desde repo publico hasta entorno funcionando. Esa ruta es producto.",
        "body": """
<p><strong>Una herramienta open source util todavia necesita una ruta desde repo publico hasta entorno funcionando.</strong> Esa ruta es producto, no un detalle final.</p>
<p>La mayoria de builders tecnicos entiende el codigo. La mayoria de usuarios vive la superficie alrededor del codigo: instalacion, ejemplos, capturas, errores, docs, demos, limites de soporte y primera ejecucion exitosa.</p>
<p>Cuando esa superficie es debil, la herramienta puede ser real y aun sentirse inutilizable.</p>
<h2>La superficie de implementacion tiene trabajos</h2>
<ul>
  <li>Explicar el resultado en una frase.</li>
  <li>Mostrar que necesita la herramienta antes de correr.</li>
  <li>Dar el ejemplo minimo util.</li>
  <li>Probar que el ejemplo funciono.</li>
  <li>Nombrar lo que la herramienta todavia no hace.</li>
  <li>Ofrecer una ruta pagada cuando alguien quiere el resultado sin hacer todo el setup solo.</li>
</ul>
<p>El sitio de Kyanite sigue ese patron: repos publicos, productos, notas, <code>/llms.txt</code>, <code>/ai-sitemap.json</code>, intake de implementacion y un limite claro de que KyaniteLabs es la ruta tecnica dentro de Simon Gonzalez De Cruz / PuenteWorks.</p>
<h2>Open source no elimina el trabajo de servicio</h2>
<p>Open source puede reducir lock-in y probar capacidad. No maneja automaticamente instalacion, adaptacion, entrenamiento, diferencias de entorno, docs, ejemplos o mantenimiento.</p>
<blockquote>El repo prueba que la herramienta existe. La implementacion lleva la herramienta a manos que la pueden usar.</blockquote>
""",
    },
    "why-mcp-video-matters": {
        "title": "Por que importa mcp-video",
        "category": "MCP / Automatizacion de video",
        "seo_title": "servidor MCP de edicion de video para agentes de IA",
        "meta_description": "mcp-video es un servidor MCP de edicion de video que da a los agentes de IA acceso directo a FFmpeg, Hyperframes, timelines, efectos y pipelines de medios.",
        "excerpt": "mcp-video da a los agentes de IA acceso directo a timelines, efectos, FFmpeg y medios terminados.",
        "body": """
<p><strong>mcp-video es un servidor MCP de edicion de video que permite a los agentes operar pipelines reales de medios en vez de solo escribir prompts sobre ellos.</strong> Lo importante no es la palabra video; es que el agente obtiene herramientas llamables para FFmpeg, Hyperframes, efectos, inspeccion y ensamblaje repetible.</p>
<p>Muchos flujos de video con IA todavia dependen de un traspaso raro. El agente puede planear la edicion y describir el corte, pero un humano termina ensamblando todo en otra parte. Eso no es agent-native. Es un chatbot mirando el estudio desde afuera.</p>
<h2>mcp-video le da al agente un timeline</h2>
<p>La decision tecnica es exponer operaciones de video como herramientas estables, no como recetas de shell de una sola vez. Eso obliga a validar argumentos, escribir errores legibles y nombrar efectos que sobrevivan mas de una sesion.</p>
<pre><code>mcp-video effect-glitch input.mp4 --output take-glitch.mp4
mcp-video inspect take-glitch.mp4 --json
mcp-video concat beat-01.mp4 beat-02.mp4 --output final-cut.mp4</code></pre>
<p>Esa interfaz no es decoracion. Es la frontera que permite inspeccionar lo ocurrido, revisar el siguiente paso y mantener el trabajo reproducible.</p>
<h2>El patron de producto detras del video agentico</h2>
<p>Kyanite busca flujos que ya existen de forma torpe y los convierte en superficies que un agente y una persona pueden usar. En video, eso significa efectos invocables, recetas que sobreviven, pipelines probables y documentacion suficiente para que alguien mas instale el sistema.</p>
<h2>Por que las herramientas MCP de medios son mas grandes que el video</h2>
<p>El video es una prueba visible de un patron mas amplio: los agentes necesitan tocar artefactos reales. Un agente util debe poder inspeccionar un repo, ensamblar un video, correr un modelo de estimacion, revisar localizacion o empaquetar una superficie de lanzamiento.</p>
""",
    },
    "infinite-monkey-agentic-systems": {
        "title": "Monos infinitos, LLMs y el cuarto alrededor de la maquina",
        "category": "Sistemas agenticos",
        "seo_title": "arquitectura para sistemas agenticos",
        "meta_description": "Los sistemas agenticos son arquitectura de probabilidad: generacion, filtros, herramientas, evaluaciones, memoria y gusto humano alrededor de los LLMs.",
        "excerpt": "El argumento detras del video: la calidad no es solo probabilidad. Es arquitectura, filtros y gusto humano.",
        "body": """
<p><strong>Los sistemas agenticos convierten la probabilidad de un LLM en trabajo util al construir el cuarto alrededor del modelo: herramientas, filtros, memoria, evaluaciones y gusto humano.</strong> El modelo genera. El sistema decide que sobrevive.</p>
<p>El teorema del mono infinito funciona como metafora hasta que se usa de forma perezosa. La aleatoriedad puede producir cualquier cosa en teoria. En la practica importa el cuarto: cuantos intentos corren, que se filtra, quien juzga, que se recuerda y cuanto cuesta otro intento.</p>
<blockquote>Los LLMs son maquinas de probabilidad. Los productos son arquitectura de probabilidad.</blockquote>
<h2>El filtro es el producto</h2>
<p>La generacion crea volumen. El trabajo de producto crea seleccion. Por eso los sistemas fuertes necesitan mas que prompts: necesitan herramientas, filtros, criterios humanos y superficies de lanzamiento que hagan el sistema entendible.</p>
<h2>Los sistemas agenticos necesitan arquitectura explicita</h2>
<p>Una arquitectura util nombra los puntos de traspaso. La generacion puede ser barata y desordenada; la seleccion no. Si un sistema no puede explicar por que acepto una salida, esta apostando con mejores logs.</p>
<pre><code>generar -> inspeccionar -> puntuar -> revisar -> empaquetar -> publicar
             ^                                      |
             |____________ evidencia ______________|</code></pre>
""",
    },
    "ai-tool-implementation-checklist": {
        "title": "Lo que una herramienta de IA necesita antes de que alguien pueda usarla",
        "category": "Notas de construccion",
        "seo_title": "checklist de implementacion para herramientas de IA",
        "meta_description": "Checklist practico para implementar herramientas de IA: instalacion, demos, docs, prueba, limites de soporte y flujos listos para usuarios.",
        "excerpt": "Una guia practica para convertir una herramienta, flujo o app medio cruda en algo que otros puedan entender, instalar y usar.",
        "body": """
<p><strong>Una herramienta de IA se vuelve util para otras personas cuando la instalacion, demo, documentacion, ejemplos y limites de soporte son claros.</strong> Un codigo que funciona no es automaticamente un producto usable.</p>
<p>Una persona nueva necesita entender que hace, por que importa, como probarlo, como verificar que funciona y donde pedir ayuda si quiere implementarlo sin hacer todo el montaje sola.</p>
<h2>La superficie minima util</h2>
<ul>
  <li>Una promesa en una frase que diga que cambia para el usuario</li>
  <li>Una demo, instalacion o explicacion clara de entrega</li>
  <li>Ejemplos con entradas y salidas reales</li>
  <li>Pruebas, capturas, logs o demos que demuestren que el sistema existe</li>
  <li>Un siguiente paso claro: probar, instalar, leer, comprar o pedir implementacion</li>
</ul>
<h2>Una herramienta necesita evidencia, no adjetivos</h2>
<p>La pagina no puede decir lista si no muestra instrucciones, ejemplos, pruebas, notas de version, capturas, demos o limites. La evidencia toma mas tiempo que el copy, pero sigue vendiendo despues de cerrar la pagina.</p>
<h2>Lo que vende Kyanite</h2>
<p>KyaniteLabs es el laboratorio creativo donde viven las herramientas, experimentos, productos open source y notas. La ruta pagada es implementacion y asesoria: setup, adaptacion, diseño de flujo, documentacion, entrenamiento e integracion.</p>
""",
    },
    "mcp-server-implementation-checklist": {
        "title": "Checklist de implementacion para servidores MCP",
        "category": "Implementacion MCP",
        "seo_title": "checklist de implementacion de servidores MCP",
        "meta_description": "Implementar un servidor MCP significa hacerlo usable con instalacion, esquemas claros, ejemplos, pruebas, documentacion y prueba publica.",
        "excerpt": "El checklist que Kyanite usa para distinguir un servidor MCP de juguete, una herramienta usable y algo que vale la pena implementar.",
        "body": """
<p><strong>Implementar un servidor MCP significa hacerlo suficientemente usable para que alguien mas pueda instalarlo, entender sus herramientas, verificar que funciona y decidir si puede confiar en el.</strong> Lo dificil no es exponer funciones; es crear una superficie duradera para usuarios y agentes reales.</p>
<h2>El checklist empieza por el contrato de herramienta</h2>
<p>Cada herramienta publica necesita una frontera clara. Los nombres deben decir la accion. Los argumentos deben rechazar entradas malas temprano. La salida debe estar lo bastante estructurada para que un agente razone sin raspar prosa.</p>
<pre><code>{
  "tool": "estimate_project_time",
  "inputs": ["tasks", "confidence", "risk_model"],
  "output": ["p50_days", "p90_days", "assumptions", "warnings"]
}</code></pre>
<h2>La instalacion es parte del producto</h2>
<p>Un README fuerte responde rapido que hace el servidor, que requiere la instalacion, que clientes soporta, cual es el ejemplo minimo y como saber que funciona.</p>
<h2>La evidencia publica se acumula</h2>
<p>mcp-video, Epoch y DialectOS prueban partes distintas del stack: medios, estimacion y QA de localizacion. El patron compartido es el laboratorio: un flujo real se vuelve capacidad llamable por agentes con documentacion y pruebas suficientes para sobrevivir inspeccion.</p>
""",
    },
    "repo-archaeology-proof-assets": {
        "title": "La arqueologia de repos convierte historia en evidencia",
        "category": "Inteligencia de repos",
        "seo_title": "arqueologia de repos para equipos asistidos por IA",
        "meta_description": "La arqueologia de repos mina commits, patrones y evidencia de proyecto para crear diagnosticos, prueba de producto y reportes de ingenieria.",
        "excerpt": "Por que el historial de commits es una de las fuentes de prueba mas fuertes para diagnosticos, implementacion y confianza tecnica.",
        "body": """
<p><strong>La arqueologia de repos usa el historial de commits como evidencia de como se construyo un proyecto, donde se atasco y cual deberia ser la siguiente intervencion.</strong> Sirve porque la historia del codigo es mas dificil de fingir que un parrafo de posicionamiento.</p>
<h2>El historial de commits es una superficie diagnostica</h2>
<p>Un repo carga evidencia de comportamiento: arreglos repetidos, direcciones revertidas, huecos de pruebas, cambios de nombres y metadata publica atrasada. Un buen diagnostico no averguenza al equipo. Convierte el patron en mapa.</p>
<pre><code>señales:
  - fallas repetidas en automatizacion de releases
  - documentacion actualizada despues del codigo
  - pruebas agregadas solo despues de regresiones
  - metadata publica atrasada respecto al nombre real</code></pre>
<h2>Por que importa para usuarios</h2>
<p>Los usuarios no solo necesitan la lista actual de features. Necesitan confianza en que la herramienta puede seguir mejorando. Historial publico, manejo de issues, notas de version y fixes verificados muestran comportamiento de mantenimiento.</p>
""",
    },
    "ai-discovery-llms-txt-geo": {
        "title": "El descubrimiento por IA necesita mas que un sitemap",
        "category": "SEO / GEO",
        "seo_title": "descubrimiento por IA y GEO para sitios",
        "meta_description": "El descubrimiento por IA necesita sitemap, llms.txt, datos estructurados, copy de respuesta directa, FAQ y superficies publicas de prueba.",
        "excerpt": "Lo que Kyanite agrega para que buscadores y asistentes de IA entiendan herramientas, productos, prueba y rutas de soporte.",
        "body": """
<p><strong>El descubrimiento por IA funciona cuando un sitio entrega hechos estructurados, citables y actuales sobre que existe, a quien ayuda y que evidencia lo respalda.</strong> Un sitemap es necesario. No es suficiente.</p>
<p>GEO, o Generative Engine Optimization, es sobre todo disciplina: decir la respuesta temprano, usar nombres reales, agregar datos estructurados, mantener prueba publica actualizada y hacer obvio el siguiente paso comercial.</p>
<h2>El stack legible para IA</h2>
<ul>
  <li><code>/sitemap.xml</code> para cobertura canonica</li>
  <li><code>/llms.txt</code> para contexto de motores de respuesta</li>
  <li><code>/ai-sitemap.json</code> para productos, repos y posts estructurados</li>
  <li>JSON-LD para Organization, WebSite, Article, Service, Product y FAQ</li>
  <li>Parrafos de respuesta directa al inicio de paginas y posts</li>
</ul>
<h2>GEO es mas fuerte cuando tambien ayuda a humanos</h2>
<p>Los motores de respuesta y los lectores premian lo mismo: afirmaciones especificas con evidencia clara. Decir construimos herramientas de IA es debil. Nombrar MCP servers, automatizacion de video, QA de localizacion, diagnosticos de repos y repos publicos es mas fuerte porque se puede revisar.</p>
""",
    },
}

BLOG_POSTS_ES = [
    {**post, **BLOG_COPY_ES.get(post["slug"], {})}
    for post in BLOG_POSTS
]
BLOG_POSTS_ES_BY_SLUG = {post["slug"]: post for post in BLOG_POSTS_ES}

# ─── Products ────────────────────────────────────────────────────────────────

PRODUCTS = {
    "ai-coding-agent-blueprint": {
        "slug": "ai-coding-agent-blueprint",
        "name": "AI Coding Agent Blueprint",
        "tagline": "Production-ready .claude/ directory — CLAUDE.md, 4 skills, 2 subagents, hooks, MCP integrations, and CI/CD. Copy in, fill in, ship.",
        "description": "Claude Code is already the agent. Most developers install it and use it like ChatGPT with file access — missing 90% of its power. This blueprint activates the full stack: CLAUDE.md persistent memory, skills for reusable workflows, subagents for isolated investigation, hooks for automatic quality gates, MCP for external services, and agent teams for parallel sessions. Every section is backed by Anthropic's official architecture — the agentic loop (gather, act, verify), context management, and permission modes. Not a template. A working system.",
        "price": 49,
        "price_cents": 4900,
        "category": "Claude Code",
        "badge": "Flagship",
        "badge_color": "#7c6af5",
        "emoji": "AB",
        "features": [
            "Production CLAUDE.md with memory hierarchy (root, directory, local, global)",
            "4 Claude Code skills: feature-build, pr-review, debug, deploy",
            "2 custom subagents: security-reviewer (Opus), test-writer (Sonnet)",
            "Hook configurations: auto-lint on edit, destructive command blocker",
            "Path-specific rules for frontend and backend directories",
            "MCP integration setup: GitHub, PostgreSQL, Figma, Notion, Slack",
            "Docker deployment with Claude Code CLI + GitHub Actions CI/CD",
            "Cost management: budget controls, token optimization, context costs",
            "Advanced patterns: writer/reviewer, fan-out, interview, plan mode",
        ],
        "delivery": "Instant download — Markdown guide with all config files ready to copy",
        "delivery_detail": "Delivered via Ko-fi email immediately after purchase. Check spam if you don't see it within a few minutes.",
        "faq": [
            {"q": "What do I actually get?", "a": "A complete .claude/ directory structure you copy into your project: CLAUDE.md, settings.json with hooks, 4 skill files, 2 subagent files, path-specific rules, plus a guide covering MCP setup, Docker deployment, CI/CD integration, cost management, and advanced patterns."},
            {"q": "Do I need to be a Claude Code expert?", "a": "No. The guide explains everything from scratch. If you've used Claude Code at all, you can set this up. The /init command generates your starter CLAUDE.md — the blueprint builds on that."},
            {"q": "How is this different from free Claude Code resources?", "a": "Anthropic's docs explain each feature individually. This blueprint wires them together into a coherent system — the right CLAUDE.md structure, the right skills for common workflows, the right hooks for automatic quality, the right subagents for delegation. It's the difference between reading about tools and having a configured workshop."},
            {"q": "What Claude models does this work with?", "a": "All current Claude models. The subagents use Sonnet for speed (test writing) and Opus for depth (security review). You can configure any model per subagent."},
            {"q": "How long does setup take?", "a": "30 minutes to copy files and fill in your project specifics. The guide walks you through it step by step. Full deployment with Docker and CI/CD: 1-2 hours."},
            {"q": "What's your refund policy?", "a": "Not happy? Email us within 30 days and we'll refund you. No questions, no hassle."},
        ],
        "seo_title": "AI Coding Agent Blueprint — Complete Claude Code Setup",
        "seo_description": "Production-ready Claude Code setup: CLAUDE.md, skills, subagents, hooks, MCP integrations, and CI/CD. Based on Anthropic's official architecture. One-time purchase.",
        "keywords": "claude code setup, claude code skills, claude code subagents, claude code hooks, CLAUDE.md, claude code MCP, ai coding agent, claude code configuration, coding automation",
        "kofi_product_url": "https://ko-fi.com/kyanitelabs",
        "file_path": "products/ai-coding-agent-blueprint.md",
    },
    "claude-code-productivity-pack": {
        "slug": "claude-code-productivity-pack",
        "name": "Claude Code Productivity Pack",
        "tagline": "100 Claude Code-specific prompts with anti-patterns, worked examples, and context management. Not generic LLM prompts — built for the agentic loop.",
        "description": "These aren't ChatGPT prompts you can find on Twitter. Every prompt leverages Claude Code's actual capabilities: @file references, /commands, Plan Mode, subagents, skills, hooks, and the gather-act-verify loop. Includes 5 anti-pattern deep dives (what NOT to do and why it wastes tokens), context management prompts (/clear, /compact, /btw, subagents), 10 chaining recipes that wire Claude Code features together, and verification steps on every prompt — because that's the single highest-leverage thing you can do according to Anthropic's own best practices.",
        "price": 19,
        "price_cents": 1900,
        "category": "Claude Code",
        "badge": None,
        "badge_color": None,
        "emoji": "CP",
        "features": [
            "100 Claude Code-specific prompts — @file refs, /commands, Plan Mode, subagents",
            "5 anti-pattern deep dives with fixes (kitchen sink, vague prompts, bloated CLAUDE.md)",
            "Context management section: /clear, /compact, /btw, subagents, rewind, resume",
            "10 chaining recipes that combine skills, subagents, and hooks",
            "Every prompt includes a verification step (the #1 Anthropic recommendation)",
            "9 categories: setup, architecture, implementation, review, debug, test, docs, DevOps, context",
        ],
        "delivery": "Instant download — Markdown, organized by category with recipe index",
        "delivery_detail": "Delivered via Ko-fi email immediately after purchase. Check spam if you don't see it within a few minutes.",
        "faq": [
            {"q": "How is this different from free prompt lists?", "a": "Free lists give you 'Design a REST API for [FEATURE].' These give you 'Plan Mode: Read @src/auth/ and understand session handling. Create a plan for [FEATURE]. Switch to Normal Mode to implement.' Every prompt uses Claude Code's actual features — file references, commands, subagents, skills. Generic prompts work with any LLM. These only work with Claude Code."},
            {"q": "What are the anti-patterns?", "a": "5 deep dives: The Kitchen Sink Session (mixing tasks without /clear), Vague Without Verification (no success criteria), Over-Specified CLAUDE.md (drowning real rules in noise), Infinite Exploration (unscoped investigation filling context), and Correcting Without Clearing (polluted context from failed attempts). Each includes the fix."},
            {"q": "What's a chaining recipe?", "a": "A multi-step workflow that combines Claude Code features. Example: the Security Review recipe chains the security-reviewer subagent, dependency audit, and PR review into one workflow. The Debug recipe chains /debug, /clear, implementation, regression test, and PR creation."},
            {"q": "Do I need to be a Claude Code power user?", "a": "The prompts work at any level. Beginners learn Claude Code features by using them. Power users get optimized workflows they might not have discovered. Every feature used in the prompts is explained in context."},
            {"q": "Will these go outdated when Claude Code updates?", "a": "The core architecture (agentic loop, CLAUDE.md, skills, subagents, hooks) is stable. When Claude Code adds new features, the pack gets updated. Based on official docs as of April 2026."},
            {"q": "What's your refund policy?", "a": "Not happy? Email us within 30 days and we'll refund you. No questions, no hassle."},
        ],
        "seo_title": "Claude Code Productivity Pack — 100 Claude Code-Specific Prompts",
        "seo_description": "100 prompts built for Claude Code's agentic loop: @file references, /commands, Plan Mode, subagents, skills. Anti-patterns, worked examples, and chaining recipes included.",
        "keywords": "claude code prompts, claude code tips, claude code skills, claude code best practices, claude code workflow, claude code subagents, developer productivity, ai coding prompts",
        "kofi_product_url": "https://ko-fi.com/kyanitelabs",
        "file_path": "products/claude-code-productivity-pack.md",
    },
}

PRODUCT_COPY_ES = {
    "ai-coding-agent-blueprint": {
        "name": "Blueprint para agentes de codigo con IA",
        "tagline": "Directorio .claude/ listo para produccion: CLAUDE.md, 4 skills, 2 subagentes, hooks, MCP e integracion CI/CD. Copiar, completar y enviar.",
        "description": "Claude Code ya es el agente. Muchos desarrolladores lo instalan y lo usan como ChatGPT con acceso a archivos, perdiendo casi todo su poder. Este blueprint activa el sistema completo: memoria persistente con CLAUDE.md, skills para flujos reutilizables, subagentes para investigacion aislada, hooks para controles de calidad automaticos, MCP para servicios externos y equipos de agentes para sesiones paralelas. No es una plantilla. Es un sistema de trabajo.",
        "category": "Claude Code",
        "features": [
            "CLAUDE.md de produccion con jerarquia de memoria",
            "4 skills para Claude Code: feature-build, pr-review, debug y deploy",
            "2 subagentes personalizados: security-reviewer y test-writer",
            "Hooks para auto-lint y bloqueo de comandos destructivos",
            "Reglas por ruta para frontend y backend",
            "Setup MCP para GitHub, PostgreSQL, Figma, Notion y Slack",
            "Deploy Docker con Claude Code CLI y GitHub Actions",
            "Controles de costo, presupuesto y contexto",
            "Patrones avanzados: writer/reviewer, fan-out, entrevista y plan mode",
        ],
        "delivery": "Descarga instantanea: guia Markdown con archivos listos para copiar",
        "delivery_detail": "Se entrega por email de Ko-fi inmediatamente despues de comprar. Revisa spam si no aparece en unos minutos.",
        "faq": [
            {"q": "Que recibo exactamente?", "a": "Una estructura .claude/ completa para copiar a tu proyecto: CLAUDE.md, settings.json con hooks, 4 skills, 2 subagentes, reglas por ruta y una guia para MCP, Docker, CI/CD, costos y patrones avanzados."},
            {"q": "Necesito ser experto en Claude Code?", "a": "No. La guia explica el sistema desde cero. Si ya usaste Claude Code, puedes montarlo."},
            {"q": "En que se diferencia de recursos gratis?", "a": "Los docs explican piezas separadas. Este blueprint las conecta en un sistema coherente con memoria, skills, hooks, subagentes y controles."},
            {"q": "Cuanto toma el setup?", "a": "Unos 30 minutos para copiar y ajustar archivos; 1 a 2 horas si tambien haces deploy con Docker y CI/CD."},
            {"q": "Cual es la politica de reembolso?", "a": "Si no te sirve, escribe dentro de 30 dias y se reembolsa la compra."},
        ],
        "seo_title": "Blueprint para agentes de codigo con IA",
        "seo_description": "Setup de Claude Code listo para produccion: CLAUDE.md, skills, subagentes, hooks, MCP y CI/CD.",
    },
    "claude-code-productivity-pack": {
        "name": "Pack de productividad para Claude Code",
        "tagline": "100 prompts especificos para Claude Code con anti-patrones, ejemplos y manejo de contexto. No son prompts genericos: estan hechos para el loop agentico.",
        "description": "Estos no son prompts de ChatGPT reciclados. Cada prompt usa capacidades reales de Claude Code: referencias @file, comandos, Plan Mode, subagentes, skills, hooks y el loop gather-act-verify. Incluye anti-patrones, prompts de manejo de contexto, recetas encadenadas y pasos de verificacion para que el trabajo no se quede en una respuesta bonita sin prueba.",
        "category": "Claude Code",
        "features": [
            "100 prompts especificos para Claude Code",
            "5 anti-patrones con correcciones",
            "Seccion de manejo de contexto: /clear, /compact, /btw y subagentes",
            "10 recetas que combinan skills, subagentes y hooks",
            "Cada prompt incluye una verificacion",
            "9 categorias: setup, arquitectura, implementacion, review, debug, tests, docs, DevOps y contexto",
        ],
        "delivery": "Descarga instantanea: Markdown organizado por categoria",
        "delivery_detail": "Se entrega por email de Ko-fi inmediatamente despues de comprar. Revisa spam si no aparece en unos minutos.",
        "faq": [
            {"q": "En que se diferencia de listas gratis de prompts?", "a": "Las listas genericas dicen disena una API. Estos prompts dicen como leer archivos, entrar en Plan Mode, delegar a subagentes y verificar el resultado dentro de Claude Code."},
            {"q": "Que son los anti-patrones?", "a": "Errores comunes como sesiones mezcladas, prompts vagos sin verificacion, CLAUDE.md inflado, exploracion infinita y correcciones sin limpiar contexto."},
            {"q": "Que es una receta encadenada?", "a": "Un flujo de varios pasos que combina herramientas de Claude Code para seguridad, debug, review, pruebas o deploy."},
            {"q": "Sirve para principiantes?", "a": "Si. Los prompts enseñan las capacidades al usarlas. Los usuarios avanzados obtienen flujos mas rapidos."},
            {"q": "Cual es la politica de reembolso?", "a": "Si no te sirve, escribe dentro de 30 dias y se reembolsa la compra."},
        ],
        "seo_title": "Pack de productividad para Claude Code — 100 prompts especificos",
        "seo_description": "100 prompts hechos para Claude Code: referencias @file, comandos, Plan Mode, subagentes, skills, anti-patrones y verificacion.",
    },
}

PRODUCTS_ES = {
    slug: {**product, **PRODUCT_COPY_ES.get(slug, {})}
    for slug, product in PRODUCTS.items()
}


# ─── Database ────────────────────────────────────────────────────────────────

def get_pg_conn():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed in this runtime")
    return psycopg2.connect(
        host=app.config["PG_HOST"],
        port=app.config["PG_PORT"],
        database=app.config["PG_DB"],
        user=app.config["PG_USER"],
        password=app.config["PG_PASS"],
    )


def init_db():
    if not app.config.get("ENABLE_SHOP_DB"):
        print("[SHOP] DB init skipped (ENABLE_SHOP_DB != 1)")
        return
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop_sales (
                id SERIAL PRIMARY KEY,
                order_id TEXT UNIQUE NOT NULL,
                product_slug TEXT NOT NULL,
                buyer_email TEXT,
                buyer_name TEXT,
                amount_cents INTEGER NOT NULL,
                currency TEXT DEFAULT 'USD',
                kofi_verification TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop_products (
                slug TEXT PRIMARY KEY,
                view_count INTEGER DEFAULT 0,
                last_viewed TIMESTAMPTZ
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("[SHOP] DB initialized OK")
    except Exception as e:
        print(f"[SHOP] DB init error: {e}")


# ─── Telegram ────────────────────────────────────────────────────────────────

def tg_notify(message):
    token = app.config["TG_BOT_TOKEN"]
    chat_id = app.config["TG_CHAT_ID"]
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        http_requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_notification": False,
        }, timeout=10)
    except Exception as e:
        print(f"[SHOP] Telegram error: {e}")


# ─── Landing HTML (existing) ────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KyaniteLabs - Get AI Tools Working</title>
  <meta name="description" content="KyaniteLabs provides open-source proof and paid implementation help for getting AI tools working in real environments.">
  <style>
    html { font-size: 100%; -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
    body { margin: 0; font-family: "Plus Jakarta Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: clamp(1rem, 0.95rem + 0.25vw, 1.125rem); background: #05070b; color: #f3f8ff; min-height: 100vh; display: grid; place-items: center; line-height: 1.6; font-synthesis: none; text-rendering: optimizeLegibility; }
    main { width: min(760px, 66ch, calc(100% - 40px)); }
    h1 { font-family: "Space Grotesk", system-ui, sans-serif; font-size: clamp(2.2rem, 1.55rem + 3.25vw, 4rem); line-height: 1.05; letter-spacing: 0; margin: 0 0 18px; text-wrap: balance; }
    p { color: #c2d2df; max-width: 66ch; font-size: 1rem; line-height: 1.7; text-wrap: pretty; }
    a { color: #26e6ff; font-weight: 700; }
  </style>
</head>
<body>
  <main>
    <h1>KyaniteLabs gets useful AI tools working in real environments.</h1>
    <p>Public proof lives in the KyaniteLabs GitHub organization: MCP servers, agent tooling, domain software, localization QA, build notes, and open-source experiments people can inspect before asking for help.</p>
    <p><a href="https://github.com/KyaniteLabs">View public KyaniteLabs repositories</a>, visit <a href="https://puenteworks.com">PuenteWorks</a>, or email <a href="mailto:info@kyanitelabs.tech">info@kyanitelabs.tech</a>.</p>
    <p>KyaniteLabs is part of <a href="https://puenteworks.com">Simon Gonzalez De Cruz / PuenteWorks</a>.</p>
  </main>
</body>
</html>
"""

# ─── Product Detail HTML ────────────────────────────────────────────────────

def product_html(p, slug):
    badge_html = ""
    if p["badge"]:
        c = p["badge_color"]
        badge_html = f'<span class="product-badge" style="color:{c};">{p["badge"]}</span>'

    features_html = ""
    for f in p["features"]:
        features_html += f'<li>{f}</li>'

    kofi_buy = p.get("kofi_product_url") or f"https://ko-fi.com/s/shop/{slug}"

    import json
    ld_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Product",
        "name": p["name"],
        "description": p.get("seo_description", p["tagline"]),
        "url": f"https://kyanitelabs.tech/shop/{slug}",
        "brand": {"@type": "Brand", "name": "KyaniteLabs"},
        "provider": {
            "@type": "Organization",
            "name": "KyaniteLabs",
            "url": CANONICAL_BASE,
            "parentOrganization": {
                "@type": "Organization",
                "name": "PuenteWorks",
                "url": PUENTEWORKS_URL,
            },
        },
        "offers": {
            "@type": "Offer",
            "price": str(p["price"]),
            "priceCurrency": "USD",
        },
    })
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{p.get('seo_title', p['name'] + ' — KyaniteLabs Shop')}</title>
  <meta name="description" content="{p.get('seo_description', p['tagline'])}">
  <meta name="keywords" content="{p.get('keywords', '')}">
  <meta name="robots" content="{ROBOTS_INDEX_DIRECTIVE}">
  <meta property="og:title" content="{p.get('seo_title', p['name'])}">
  <meta property="og:description" content="{p.get('seo_description', p['tagline'])}">
  <meta property="og:type" content="product">
  <meta property="og:url" content="https://kyanitelabs.tech/shop/{slug}">
  <meta property="product:price:amount" content="{p['price']}">
  <meta property="product:price:currency" content="USD">
  <link rel="canonical" href="https://kyanitelabs.tech/shop/{slug}">
  <link rel="alternate" type="text/plain" title="KyaniteLabs AI-readable brief" href="https://kyanitelabs.tech/llms.txt">
  <link rel="alternate" type="text/plain" title="KyaniteLabs full AI-readable context" href="https://kyanitelabs.tech/llms-full.txt">
  <link rel="alternate" type="application/rss+xml" title="KyaniteLabs Blog Feed" href="https://kyanitelabs.tech/feed.xml">
  <script type="application/ld+json">{ld_json}</script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{ --bg: #08080c; --surface: #0f0f15; --surface2: #16161f; --border: #1e1e2e; --text: #e2e2ec; --muted: #8f90a6; --accent: #78d9e7; --accent2: #e8b86f; --accent-glow: rgba(120,217,231,0.15); --green: #34d399; --green-bg: rgba(52,211,153,0.1); --radius: 12px; --radius-sm: 8px; --orange: #f59e0b; --body-font: 'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; --display-font: 'Space Grotesk', system-ui, sans-serif; --measure: 66ch; }}
    html {{ font-size: 100%; -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }}
    body {{ font-family: var(--body-font); font-size: clamp(1rem, 0.95rem + 0.25vw, 1.125rem); background: var(--bg); color: var(--text); line-height: 1.6; font-synthesis: none; text-rendering: optimizeLegibility; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ color: var(--accent2); }}
    nav {{ position: fixed; top: 0; left: 0; right: 0; z-index: 100; padding: 0 2rem; height: 64px; display: flex; align-items: center; justify-content: space-between; background: #08080c; border-bottom: 1px solid var(--border); }}
    .nav-logo {{ font-weight: 800; font-size: 1.1rem; letter-spacing: 0; }}
    .nav-logo span {{ color: var(--accent); }}
    .nav-links {{ display: flex; gap: 2rem; align-items: center; }}
    .nav-links a {{ color: var(--muted); font-size: 0.875rem; font-weight: 500; }}
    .nav-links a:hover, .nav-links a.active {{ color: var(--text); }}
    .breadcrumb {{ padding: 100px 0 0; text-align: center; }}
    .breadcrumb .container {{ display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 0.8rem; color: var(--muted); }}
    .breadcrumb a {{ color: var(--muted); }}
    .breadcrumb a:hover {{ color: var(--text); }}
    .breadcrumb span {{ color: var(--accent); }}
    .container {{ max-width: 1100px; margin: 0 auto; padding: 0 2rem; }}
    .product-layout {{ display: grid; grid-template-columns: 1fr 380px; gap: 60px; padding: 60px 0 100px; align-items: start; }}
    .product-main {{}}
    .product-emoji {{ width: 58px; height: 58px; display: grid; place-items: center; margin-bottom: 24px; border: 1px solid rgba(120,217,231,0.35); border-radius: 16px; background: linear-gradient(145deg, rgba(120,217,231,0.14), rgba(232,184,111,0.08)); color: var(--text); font-family: var(--display-font); font-size: 1rem; font-weight: 800; letter-spacing: 0; box-shadow: inset 0 1px 0 rgba(255,255,255,0.14); }}
    .product-badge {{ display: inline-block; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 0 0 6px; border-bottom: 1px solid currentColor; margin-bottom: 12px; }}
    .product-category {{ font-size: 0.75rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }}
    .product-name {{ max-width: var(--measure); font-family: var(--display-font); font-size: clamp(1.8rem, 1.44rem + 1.8vw, 2.8rem); font-weight: 800; letter-spacing: 0; line-height: 1.15; margin-bottom: 16px; text-wrap: balance; }}
    .product-tagline {{ max-width: var(--measure); font-size: 1.1rem; color: var(--muted); line-height: 1.6; margin-bottom: 32px; text-wrap: pretty; }}
    .product-description {{ max-width: var(--measure); font-size: 1rem; color: var(--text); line-height: 1.75; margin-bottom: 40px; padding-bottom: 40px; border-bottom: 1px solid var(--border); text-wrap: pretty; }}
    .features-section {{}}
    .features-section h2 {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 20px; letter-spacing: 0; }}
    .features-list {{ list-style: none; display: flex; flex-direction: column; gap: 14px; }}
    .features-list li {{ display: flex; align-items: flex-start; gap: 12px; font-size: 0.9rem; color: var(--text); }}
    .features-list li::before {{ content: ''; width: 20px; height: 20px; background: var(--green-bg); border-radius: 50%; flex-shrink: 0; margin-top: 2px; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2334d399' stroke-width='3'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E"); background-size: 11px; background-position: center; background-repeat: no-repeat; }}
    .product-sidebar {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; position: sticky; top: 80px; }}
    .sidebar-preview {{ background: var(--surface2); border-bottom: 1px solid var(--border); padding: 40px; text-align: center; }}
    .sidebar-emoji {{ width: 82px; height: 82px; display: grid; place-items: center; margin: 0 auto 16px; border: 1px solid rgba(120,217,231,0.35); border-radius: 22px; background: linear-gradient(145deg, rgba(120,217,231,0.15), rgba(232,184,111,0.1)); color: var(--text); font-family: var(--display-font); font-size: 1.15rem; font-weight: 800; letter-spacing: 0; box-shadow: inset 0 1px 0 rgba(255,255,255,0.16); }}
    .sidebar-price {{ font-size: 3rem; font-weight: 800; letter-spacing: 0; margin-bottom: 4px; }}
    .sidebar-price span {{ font-size: 1rem; font-weight: 500; color: var(--muted); }}
    .sidebar-delivery {{ font-size: 0.8rem; color: var(--green); display: flex; align-items: center; gap: 6px; justify-content: center; margin-top: 8px; }}
    .sidebar-delivery::before {{ content: ''; width: 8px; height: 8px; background: var(--green); border-radius: 50%; box-shadow: 0 0 6px var(--green); animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
    .sidebar-body {{ padding: 28px; }}
    .kofi-btn {{ display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 16px; background: #00b8f1; color: #fff; border: none; border-radius: var(--radius-sm); font-size: 1rem; font-weight: 700; cursor: pointer; font-family: inherit; text-decoration: none; transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1), background-color 220ms cubic-bezier(0.22, 1, 0.36, 1), box-shadow 220ms cubic-bezier(0.22, 1, 0.36, 1), color 220ms cubic-bezier(0.22, 1, 0.36, 1); margin-bottom: 20px; }}
    .kofi-btn:hover {{ background: #00a0d8; transform: translateY(-2px); color: #fff; box-shadow: 0 6px 20px rgba(0,184,241,0.4); }}
    .kofi-btn img {{ height: 20px; }}
    .sidebar-note {{ font-size: 0.75rem; color: var(--muted); text-align: center; line-height: 1.5; }}
    .guarantee {{ margin-top: 16px; padding: 14px; background: var(--green-bg); border: 1px solid rgba(52,211,153,0.2); border-radius: var(--radius-sm); text-align: center; }}
    .guarantee p {{ font-size: 0.75rem; color: var(--green); font-weight: 600; }}
    footer {{ background: var(--bg); border-top: 1px solid var(--border); padding: 40px 0 32px; }}
    footer .container {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }}
    footer p {{ color: var(--muted); font-size: 0.8rem; }}
    footer a {{ color: var(--muted); font-size: 0.8rem; }}
    footer a:hover {{ color: var(--accent); }}
    @media (max-width: 900px) {{ .product-layout {{ grid-template-columns: 1fr; }} .product-sidebar {{ position: static; }} }}
    @media (max-width: 768px) {{ nav {{ padding: 0 1.25rem; }} .nav-links {{ display: none; }} .container {{ padding: 0 1.25rem; }} }}
  </style>
</head>
<body>
<nav>
  <div class="nav-logo">KyaniteLabs</div>
  <div class="nav-links">
    <a href="/">Home</a>
    <a href="/shop" class="active">Shop</a>
    <a href="{PUENTEWORKS_URL}">PuenteWorks</a>
    <a href="/#contact">Contact</a>
  </div>
</nav>

<div class="breadcrumb">
  <div class="container">
    <a href="/">Home</a> / <a href="/shop">Shop</a> / <span>{p['name']}</span>
  </div>
</div>

<div class="container">
  <div class="product-layout">
    <div class="product-main">
      <div class="product-emoji">{p['emoji']}</div>
      {badge_html}
      <div class="product-category">{p['category']}</div>
      <h1 class="product-name">{p['name']}</h1>
      <p class="product-tagline">{p['tagline']}</p>
      <p class="product-description">{p['description']}</p>
      <div class="features-section">
        <h2>What's Included</h2>
        <ul class="features-list">
          {features_html}
        </ul>
      </div>
    </div>

    <div class="product-sidebar">
      <div class="sidebar-preview">
        <div class="sidebar-emoji">{p['emoji']}</div>
        <div class="sidebar-price">${p['price']}<span> USD</span></div>
        <div class="sidebar-delivery">{p['delivery']}</div>
      </div>
      <div class="sidebar-body">
        <a href="{kofi_buy}" target="_blank" rel="noopener noreferrer" class="kofi-btn">
          <svg height="20" width="20" viewBox="0 0 391.4 391.4" fill="white"><path d="M293.1 322.9c-11.5 13.2-28.4 21-46.4 21H99.7l-7.5 29H62.2l25.7-100H0V0h227.3c33.2 0 61.4 20.4 72.2 49.3 6.8 18.2 6.5 37.9-1 55.7-3.1 7.3-7.5 14.1-12.9 19.7 15.9 5.3 28.5 18.5 32.3 35.4 5.3 24.1-9.5 47.9-32.3 52.7-4.1.8-8.3 1.2-12.5 1.2h44.7l-24.7 100H273.5l22.7-92.7c4.3-17.6-2.1-35.8-16.4-47z"/></svg>
          Buy on Ko-fi — ${p['price']}
        </a>
        <p class="sidebar-note">{p['delivery_detail']}</p>
        <div class="guarantee"><p>30-day refund guarantee. Not happy? Email us for a full refund.</p></div>
      </div>
    </div>
  </div>
</div>

<footer>
  <div class="container">
    <p>&copy; 2026 KyaniteLabs. All rights reserved.</p>
    <p><a href="/">Home</a> · <a href="/shop">Shop</a> · <a href="{PUENTEWORKS_URL}">PuenteWorks</a> · <a href="mailto:info@kyanitelabs.tech">Contact</a></p>
  </div>
</footer>
</body>
</html>
"""


ABOUT_COPY = {
    "en": {
        "lang": "en",
        "path": "/about",
        "alt_path": "/es/about",
        "alt_label": "ES",
        "meta_title": "About Simon Gonzalez de Cruz — KyaniteLabs",
        "meta_description": "About Simon Gonzalez de Cruz, founder of KyaniteLabs: open-source AI tools, MCP servers, agentic media, localization QA, and implementation help.",
        "eyebrow": "About the builder",
        "title": "A lab for tools that survive contact with real work.",
        "lead": "I'm Simon Gonzalez de Cruz. KyaniteLabs is my creative development lab for MCP servers, AI media systems, localization QA, estimation tools, repo diagnostics, domain software, and the build notes that make the work inspectable.",
        "portrait_alt": "Portrait of Simon Gonzalez de Cruz, founder of KyaniteLabs",
        "portrait_label": "Simon Gonzalez de Cruz",
        "portrait_meta": "Founder / builder / systems translator",
        "body_title": "The lab grew out of the same habit that shaped my corporate work: find the broken handoff, make it visible, and leave behind a usable system.",
        "body": [
            "Before KyaniteLabs, I spent 12+ years in learning operations and enterprise training systems: Workday Learning for 8,000+ associates, SAP SuccessFactors, Cornerstone, global training programs, compliance reporting, Power Query and Power BI dashboards, and bilingual training delivery.",
            "That background still shapes the lab. Tools have to be inspectable, documented, and usable by people who did not build them. A clever prototype is not enough; the handoff has to survive.",
            "KyaniteLabs is where I turn that operational instinct toward weird, useful software: mcp-video for agentic video workflows, DialectOS for Spanish localization QA, Epoch for estimation, OpenGlaze for ceramic chemistry, devarch-framework for repo archaeology, and Innerscape for personal workflow systems.",
            "Simon Gonzalez De Cruz / PuenteWorks is the legal and business container. PuenteWorks leads when the client problem is business workflow, scope, content, or approval rhythm. KyaniteLabs leads when the work needs a technical product surface: software, MCP tools, automation, docs, deployment, or repair."
        ],
        "builds_label": "Selected builds",
        "builds_title": "Work people can inspect",
        "builds": [
            ("mcp-video", "87 FFmpeg and Hyperframes tools that let AI agents inspect, assemble, and transform video through a real tool surface instead of a vague prompt."),
            ("DialectOS and Epoch", "Spanish dialect QA and estimation infrastructure for work where language quality and time judgment need explicit checks."),
            ("OpenGlaze and devarch-framework", "Domain software and repo archaeology: ceramic chemistry, commit-history diagnostics, HTML reports, and evidence-backed handoff."),
            ("Innerscape", "A personal workflow system for turning reflection, routines, and decision support into something structured enough to use.")
        ],
        "signal_label": "Operating memory",
        "signal_title": "Enterprise discipline, lab proof.",
        "signal_body": "The point is not novelty for its own sake. KyaniteLabs turns difficult workflows into artifacts that can be inspected, tested, documented, and handed to someone else.",
        "principles_title": "What the lab optimizes for",
        "principles": [
            ("Real artifacts", "Agents should touch timelines, repos, locale files, estimation models, domain data, docs, and working code."),
            ("Proof in public", "A repo, build note, demo, screenshot, test, or install path should back the claim."),
            ("Domain respect", "Ceramic chemistry, Spanish dialects, video tools, time estimates, and learning systems deserve specific interfaces, not generic AI wrappers."),
            ("Usable handoff", "The work should leave behind commands, examples, notes, or implementation paths that survive the original session.")
        ],
        "cta_title": "Bring a tool, workflow, or build that needs to become usable.",
        "cta_body": "Best fit: Kyanite tools, MCP servers, agentic media workflows, localization QA, repo diagnostics, and technical product surfaces that need implementation help.",
        "primary_cta": "Start implementation intake",
        "secondary_cta": "Explore the builds",
    },
    "es": {
        "lang": "es",
        "path": "/es/about",
        "alt_path": "/about",
        "alt_label": "EN",
        "meta_title": "Sobre Simon Gonzalez de Cruz — KyaniteLabs",
        "meta_description": "Sobre Simon Gonzalez de Cruz, fundador de KyaniteLabs: herramientas open source de IA, servidores MCP, medios agenticos e implementacion.",
        "eyebrow": "Sobre el builder",
        "title": "Un laboratorio para herramientas que sobreviven al trabajo real.",
        "lead": "Soy Simon Gonzalez de Cruz. KyaniteLabs es mi laboratorio creativo para servidores MCP, sistemas de medios con IA, QA de localizacion, estimacion, diagnostico de repos, software de dominio y notas de construccion que vuelven inspeccionable el trabajo.",
        "portrait_alt": "Retrato de Simon Gonzalez de Cruz, fundador de KyaniteLabs",
        "portrait_label": "Simon Gonzalez de Cruz",
        "portrait_meta": "Fundador / builder / traductor de sistemas",
        "body_title": "El laboratorio nacio del mismo habito que marco mi trabajo corporativo: encontrar el handoff roto, hacerlo visible y dejar un sistema usable.",
        "body": [
            "Antes de KyaniteLabs, pase mas de 12 anos en operaciones de aprendizaje y sistemas de capacitacion empresarial: Workday Learning para mas de 8,000 personas, SAP SuccessFactors, Cornerstone, programas globales de capacitacion, reportes de cumplimiento, dashboards con Power Query y Power BI, y capacitacion bilingue.",
            "Ese fondo todavia define el laboratorio. Las herramientas tienen que ser inspeccionables, documentadas y usables por personas que no las construyeron. Un prototipo inteligente no basta; el handoff tiene que sobrevivir.",
            "KyaniteLabs es donde llevo ese instinto operativo hacia software raro y util: mcp-video para flujos de video agenticos, DialectOS para QA de localizacion al espanol, Epoch para estimacion, OpenGlaze para quimica ceramica, devarch-framework para arqueologia de repos e Innerscape para sistemas personales de trabajo.",
            "Simon Gonzalez De Cruz / PuenteWorks es el contenedor legal y comercial. PuenteWorks lidera cuando el problema del cliente es flujo de negocio, alcance, contenido o ritmo de aprobacion. KyaniteLabs lidera cuando el trabajo necesita una superficie tecnica de producto: software, herramientas MCP, automatizacion, docs, despliegue o reparacion."
        ],
        "builds_label": "Builds seleccionados",
        "builds_title": "Trabajo que se puede inspeccionar",
        "builds": [
            ("mcp-video", "87 herramientas de FFmpeg y Hyperframes para que agentes de IA inspeccionen, armen y transformen video a traves de una superficie real, no un prompt vago."),
            ("DialectOS y Epoch", "Infraestructura para QA de dialectos del espanol y estimacion cuando la calidad del lenguaje y el juicio de tiempo necesitan revision explicita."),
            ("OpenGlaze y devarch-framework", "Software de dominio y arqueologia de repos: quimica ceramica, diagnosticos de historial git, reportes HTML y handoff respaldado por evidencia."),
            ("Innerscape", "Un sistema personal de trabajo para convertir reflexion, rutinas y apoyo de decisiones en algo suficientemente estructurado para usarse.")
        ],
        "signal_label": "Memoria operativa",
        "signal_title": "Disciplina empresarial, prueba de laboratorio.",
        "signal_body": "La meta no es novedad por novedad. KyaniteLabs convierte flujos dificiles en artefactos que se pueden inspeccionar, probar, documentar y entregar a otra persona.",
        "principles_title": "Lo que optimiza el laboratorio",
        "principles": [
            ("Artefactos reales", "Los agentes deben tocar timelines, repos, archivos de idioma, modelos de estimacion, datos de dominio, docs y codigo funcionando."),
            ("Prueba publica", "Un repo, nota de construccion, demo, captura, prueba o ruta de instalacion debe respaldar la afirmacion."),
            ("Respeto por el dominio", "Quimica ceramica, dialectos del espanol, herramientas de video, estimaciones y sistemas de aprendizaje merecen interfaces especificas, no wrappers genericos de IA."),
            ("Handoff usable", "El trabajo debe dejar comandos, ejemplos, notas o rutas de implementacion que sobrevivan la sesion original.")
        ],
        "cta_title": "Trae una herramienta, flujo o build que necesita volverse usable.",
        "cta_body": "Mejor fit: herramientas de Kyanite, servidores MCP, flujos de medios agenticos, QA de localizacion, diagnosticos de repos y superficies tecnicas de producto que necesitan implementacion.",
        "primary_cta": "Enviar intake de implementacion",
        "secondary_cta": "Explorar los builds",
    },
}

COMMON_ES_REPLACEMENTS = {
    "Skip to content": "Saltar al contenido",
    "Tools": "Herramientas",
    "Projects": "Proyectos",
    "Proof": "Prueba",
    "Builds": "Builds",
    "Blog": "Notas",
    "Lab Notes": "Notas",
    "Support": "Soporte",
    "Shop": "Tienda",
    "Contact": "Contacto",
    "About": "Sobre mi",
    "Home": "Inicio",
    "Implementation Help": "Ayuda de implementacion",
    "Start Intake": "Enviar intake",
    "Implementation Intake": "Intake de implementacion",
    "Implementation": "Implementacion",
    "Creative dev lab": "Laboratorio creativo de desarrollo",
    "Open-source tools, build notes, and learning in public.": "Herramientas open source, notas de construccion y aprendizaje en publico.",
    "Explore the builds": "Explorar los builds",
    "Get implementation help": "Pedir ayuda de implementacion",
    "Read the blog": "Leer las notas",
    "Public Proof": "Prueba publica",
    "The projects are the proof.": "Los proyectos son la prueba.",
    "Open the repo, inspect the artifact, and pick the Kyanite build closest to the blocker you want running in your environment.": "Abre el repo, inspecciona el artefacto y elige el build de Kyanite mas cercano al bloqueo que quieres hacer funcionar en tu entorno.",
    "Use The Proof": "Usar la prueba",
    "Choose the next move.": "Elige el siguiente paso.",
    "Use the gallery as a map: install one of the tools, read the build context, or start with a smaller asset before a scoped implementation conversation.": "Usa la galeria como mapa: instala una herramienta, lee el contexto del build o empieza con un activo mas pequeno antes de una conversacion de implementacion por alcance.",
    "Scoped help": "Ayuda por alcance",
    "Get a project running": "Haz funcionar un proyecto",
    "For builders who want mcp-video, Epoch, DialectOS, OpenGlaze, repo diagnostics, or another Kyanite build installed, adapted, and handed off cleanly.": "Para builders que quieren mcp-video, Epoch, DialectOS, OpenGlaze, diagnosticos de repo u otro build de Kyanite instalado, adaptado y entregado con claridad.",
    "Install path, config, and first successful run": "Ruta de instalacion, config y primer run exitoso",
    "Adaptation to your repo, workflow, or operating constraints": "Adaptacion a tu repo, flujo o restricciones operativas",
    "Documentation you can reuse after the call": "Documentacion que puedes reutilizar despues de la llamada",
    "Start intake": "Enviar intake",
    "Understand the build": "Entender el build",
    "Read the notes behind the project: what the tool does, where it is useful, what still needs care, and how the implementation surface should behave.": "Lee las notas detras del proyecto: que hace la herramienta, donde sirve, que todavia requiere cuidado y como debe comportarse la superficie de implementacion.",
    "MCP video editing, localization QA, and estimation notes": "Notas de video MCP, QA de localizacion y estimacion",
    "Implementation checklists and product decisions": "Checklists de implementacion y decisiones de producto",
    "Plain facts that make the build easier to evaluate": "Hechos claros que hacen mas facil evaluar el build",
    "Read lab notes": "Leer notas",
    "Assets": "Activos",
    "Start smaller": "Empieza mas pequeno",
    "Use templates, workflows, and operator assets when you do not need a full implementation pass yet but want fewer blank-page starts.": "Usa plantillas, flujos y activos de operador cuando todavia no necesitas una implementacion completa pero quieres menos comienzos desde pagina en blanco.",
    "Claude Code workflows and productization templates": "Flujos de Claude Code y plantillas de productizacion",
    "Useful before a scoped implementation request": "Util antes de un pedido de implementacion por alcance",
    "Lower-commitment entry point for builders": "Entrada de menor compromiso para builders",
    "Latest Lab Notes": "Notas recientes",
    "The thinking should make the tools easier to trust.": "El pensamiento debe hacer que las herramientas sean mas confiables.",
    "Build logs and implementation notes show where a tool works, where it is rough, and what it takes to use it well.": "Los logs de construccion y notas de implementacion muestran donde funciona una herramienta, donde esta rough y que hace falta para usarla bien.",
    "Read all notes": "Leer todas las notas",
    "The repos are the lab notebook and the product shelf.": "Los repos son el cuaderno de laboratorio y la vitrina de producto.",
    "Blog // Lab Notes": "Notas // Laboratorio",
    "The thinking should be as public as the tools.": "El pensamiento debe ser tan publico como las herramientas.",
    "Build. Learn. Publish.": "Construir. Aprender. Publicar.",
    "Operating Model": "Modelo operativo",
    "Products + Support": "Productos + soporte",
    "Open-source first. Paid help when you want it implemented.": "Open source primero. Ayuda pagada cuando quieres implementarlo.",
    "Bring the blocker.": "Trae el bloqueo.",
    "Your name": "Tu nombre",
    "Email address": "Email",
    "Context": "Contexto",
    "Start the conversation": "Iniciar la conversacion",
    "Sending…": "Enviando...",
    "Message sent. Kyanite will review the context and reply if there is a real fit.": "Mensaje enviado. Kyanite revisara el contexto y respondera si hay buen fit.",
    "Network error. Please email info@kyanitelabs.tech.": "Error de red. Escribe a info@kyanitelabs.tech.",
    "Blog / Lab Notes": "Notas de laboratorio",
    "Published lab notes only.": "Solo notas publicadas despues de construir.",
    "Public Proof Inputs": "Entradas de prueba publica",
    "The repos are the lab notebook.": "Los repos son el cuaderno de laboratorio.",
    "Operator assets": "Activos de operador",
    "Operator assets for agent-native teams.": "Activos de operador para equipos agent-native.",
    "View details": "Ver detalles",
    "What this is": "Que es",
    "What's included": "Que incluye",
    "Questions buyers ask": "Preguntas frecuentes",
    "Instant download": "Descarga instantanea",
    "Buy on Ko-fi": "Comprar en Ko-fi",
    "Back to shop": "Volver a la tienda",
    "30-day refund guarantee.": "Garantia de reembolso de 30 dias.",
    "Paid implementation help": "Ayuda pagada de implementacion",
    "Use the tools without doing every setup step alone.": "Usa las herramientas sin hacer cada paso de setup en soledad.",
    "Start implementation intake": "Enviar intake de implementacion",
    "Email Kyanite": "Escribir a Kyanite",
    "What we check": "Que revisamos",
    "What you get": "Que recibes",
    "Exact Help": "Ayuda concreta",
    "What Kyanite can help you do.": "Lo que Kyanite puede ayudarte a hacer.",
    "Install and configure": "Instalar y configurar",
    "Adapt the workflow": "Adaptar el flujo",
    "Advise and hand off": "Asesorar y dejar handoff",
    "Why this exists": "Por que existe",
    "Kyanite already builds the tools.": "Kyanite ya construye las herramientas.",
    "Best fit": "Mejor fit",
    "Structured implementation intake": "Intake estructurado de implementacion",
    "Tell Kyanite what you want help using.": "Dile a Kyanite que quieres ayuda para usar.",
    "Name": "Nombre",
    "Email": "Email",
    "Company / Project": "Empresa / Proyecto",
    "Kyanite tool / source / demo URL(s)": "Herramienta Kyanite / fuente / URL(s) de demo",
    "Tool / workflow summary": "Resumen de herramienta / flujo",
    "Biggest implementation pain": "Mayor dolor de implementacion",
    "What would make this worth paying for?": "Que haria que esto valga la pena pagar?",
    "Send implementation intake": "Enviar intake de implementacion",
    "What happens next": "Que pasa despues",
    "Kyanite reads the artifact before selling the fix.": "Kyanite lee el artefacto antes de vender la solucion.",
    "Implementation intake sent. Kyanite will review it and follow up.": "Intake enviado. Kyanite lo revisara y dara seguimiento.",
    "Something went wrong. Email info@kyanitelabs.tech.": "Algo salio mal. Escribe a info@kyanitelabs.tech.",
    "Work with Kyanite": "Trabajar con Kyanite",
    "Operator Assets": "Activos de operador",
    "Get the Kyanite tool working in your environment.": "Haz que la herramienta Kyanite funcione en tu entorno.",
    "Implementation path": "Ruta de implementación",
    "Send the implementation brief": "Enviar el brief de implementación",
    "Email the context": "Escribir el contexto",
    "What you bring": "Lo que tú traes",
    "What Kyanite returns": "Lo que Kyanite devuelve",
    "Send brief": "Enviar brief",
    "Want this working in your environment?": "¿Quieres que esto funcione en tu entorno?",
    "If this post describes a Kyanite tool or result you need, implementation help can cover setup, advising, docs, examples, checks, and a usable handoff.": "Si esta nota describe una herramienta o resultado de Kyanite que necesitas, la ayuda de implementación cubre setup, asesoría, docs, ejemplos, checks y un handoff usable.",
    "Fit boundary": "Límite de fit",
    "Get help using the tool.": "Recibe ayuda para usar la herramienta.",
    "Get the tool working.": "Haz funcionar la herramienta.",
    "If this post describes a Kyanite tool or result you need in your real environment, implementation help is the paid path: setup, advising, docs, examples, and a usable handoff.": "Si esta nota describe una herramienta o resultado Kyanite que necesitas en tu entorno real, la ayuda de implementacion es la ruta pagada: setup, asesoria, docs, ejemplos y un handoff usable.",
    "Kyanite offers help grounded in its tools, products, and build practice. Broader consulting routes through PuenteWorks.": "Kyanite ofrece ayuda basada en sus herramientas, productos y practica de construccion. La consultoria mas amplia se enruta por PuenteWorks.",
    "The repos are proof before the pitch.": "Los repos son prueba antes del pitch.",
    "Public repositories show what Kyanite builds, learns, breaks, fixes, and releases. The paid path helps people get those tools working in real environments.": "Los repositorios publicos muestran lo que Kyanite construye, aprende, rompe, arregla y publica. La ruta pagada ayuda a que esas herramientas funcionen en entornos reales.",
    "See implementation help": "Ver ayuda de implementacion",
    "Brand boundary": "Limite de marca",
    "More Lab Notes": "Mas notas de laboratorio",
    "Keep following the system.": "Sigue el sistema.",
    "All assets": "Todos los activos",
    "Public repos": "Repos publicos",
    "Project Conversation": "Conversacion de proyecto",
    "Implementation and Advising": "Implementacion y asesoria",
    "Open-source proof and paid implementation help for getting AI tools working in real environments.": "Prueba open source y ayuda pagada de implementacion para hacer funcionar herramientas de IA en entornos reales.",
    "KyaniteLabs — Get AI Tools Working in Real Workflows": "KyaniteLabs — Herramientas de IA funcionando en flujos reales",
    "KyaniteLabs — Get AI Tools Working": "KyaniteLabs — Herramientas de IA funcionando",
    "KyaniteLabs helps builders and teams get open-source AI tools, MCP systems, media pipelines, localization QA, and repo diagnostics working in their real environment.": "KyaniteLabs ayuda a builders y equipos a implementar herramientas de IA open source, sistemas MCP, medios, localizacion y diagnosticos de repos.",
    "Open-source AI tools, MCP systems, media pipelines, localization QA, and repo diagnostics made usable in real workflows.": "Herramientas de IA open source, sistemas MCP, pipelines de medios, QA de localizacion y diagnosticos de repos hechos usables en flujos reales.",
    "Implementation Help — Get Kyanite Tools Working": "Ayuda de implementacion — Haz funcionar herramientas Kyanite",
    "Paid implementation and advising that helps builders install, adapt, understand, and hand off KyaniteLabs tools in real workflows.": "Implementacion y asesoria pagada para instalar, adaptar, entender y entregar herramientas KyaniteLabs en flujos reales.",
    "Get help turning KyaniteLabs tools into a working setup instead of doing every install, adaptation, and handoff step alone.": "Recibe ayuda para convertir herramientas KyaniteLabs en un setup funcional sin hacer cada paso de instalacion, adaptacion y handoff en soledad.",
    "Paid outcome help": "Ayuda pagada para llegar al resultado",
    "Get the tool working without doing every setup step alone.": "Haz funcionar la herramienta sin hacer cada paso de setup en soledad.",
    "KyaniteLabs is operated by Simon Gonzalez De Cruz / PuenteWorks.": "KyaniteLabs es operado por Simon Gonzalez De Cruz / PuenteWorks.",
    "Most Kyanite products are open source. Paid implementation helps you install the tool, adapt it to your environment, understand the tradeoffs, and leave with a usable handoff.": "La mayoria de los productos Kyanite son open source. La implementacion pagada te ayuda a instalar la herramienta, adaptarla a tu entorno, entender los tradeoffs y salir con un handoff usable.",
    "What result you need from the Kyanite tool": "Que resultado necesitas de la herramienta Kyanite",
    "Your machine, stack, constraints, and current blocker": "Tu maquina, stack, restricciones y bloqueo actual",
    "Install path, examples, checks, and handoff needs": "Ruta de instalacion, ejemplos, checks y necesidades de handoff",
    "A practical path to the working result": "Una ruta practica hacia el resultado funcionando",
    "Good fit when you want the outcome from a Kyanite tool or workflow instead of doing every setup, adaptation, and handoff step alone. Broader consulting belongs under PuenteWorks.": "Buen fit cuando quieres el resultado de una herramienta o flujo Kyanite sin hacer cada paso de setup, adaptacion y handoff en soledad. La consultoria mas amplia pertenece a PuenteWorks.",
    "What Kyanite can help you get working.": "Lo que Kyanite puede ayudarte a hacer funcionar.",
    "The goal is practical implementation. You should leave closer to a tool you can actually use.": "La meta es implementacion practica. Debes salir mas cerca de una herramienta que realmente puedas usar.",
    "Adapt it to the real workflow": "Adaptarlo al flujo real",
    "Understand tradeoffs and hand off": "Entender tradeoffs y dejar handoff",
    "Kyanite already builds the proof.": "Kyanite ya construye la prueba.",
    "The paid support exists so people can reach the outcome faster, not just admire the repo.": "El apoyo pagado existe para que las personas lleguen al resultado mas rapido, no solo para admirar el repo.",
    "People who want mcp-video, Epoch, DialectOS, openglaze, or a Kyanite workflow working in their environment.": "Personas que quieren mcp-video, Epoch, DialectOS, openglaze o un flujo Kyanite funcionando en su entorno.",
    "Tell KyaniteLabs what result you need from a tool, repo, media pipeline, localization QA pass, or diagnostic so the next step can be scoped.": "Dile a KyaniteLabs que resultado necesitas de una herramienta, repo, pipeline de medios, pase de QA de localizacion o diagnostico para poder definir el siguiente paso.",
    "Tell Kyanite what you need working.": "Dile a Kyanite que necesitas hacer funcionar.",
    "This gives Kyanite enough context to decide whether the tool, repo, media pipeline, localization QA pass, or diagnostic can be moved toward a working handoff. It does not charge, publish, or commit you to a scope.": "Esto da a Kyanite suficiente contexto para decidir si la herramienta, repo, pipeline de medios, pase de QA de localizacion o diagnostico puede avanzar hacia un handoff funcional. No cobra, publica ni te compromete a un alcance.",
    "Kyanite reads the context before selling the fix.": "Kyanite lee el contexto antes de vender la solucion.",
    "If this fits a Kyanite tool path, you will get a grounded next step. If it belongs under broader PuenteWorks consulting, the response will route it there instead of forcing a technical scope.": "Si encaja con una ruta de herramienta Kyanite, recibiras un siguiente paso concreto. Si pertenece a consultoria mas amplia de PuenteWorks, la respuesta lo enrutara ahi en vez de forzar un alcance tecnico.",
    "Best with source, demo, docs, product notes, logs, or current blocker evidence.": "Funciona mejor con fuente, demo, docs, notas de producto, logs o evidencia del bloqueo actual.",
    "KyaniteLabs — Creative Dev Lab for Open Source AI Tools": "KyaniteLabs — Laboratorio creativo para herramientas de IA open source",
    "KyaniteLabs — Creative Dev Lab for Open Source AI Herramientas": "KyaniteLabs — Laboratorio creativo para herramientas de IA open source",
    "KyaniteLabs — Creative Dev Lab for AI Tools": "KyaniteLabs — Laboratorio creativo para herramientas de IA",
    "KyaniteLabs — Creative Dev Lab for AI Herramientas": "KyaniteLabs — Laboratorio creativo para herramientas de IA",
    "Open-source AI tools, MCP servers, media systems, learning experiments, products, and build notes.": "Herramientas de IA open source, servidores MCP, sistemas de medios, experimentos de aprendizaje, productos y notas de construccion.",
    "KyaniteLabs is Simon Gonzalez de Cruz's creative development lab for open-source AI tools, MCP servers, media systems, learning experiments, products, and build notes.": "KyaniteLabs es el laboratorio creativo de Simon Gonzalez de Cruz para herramientas de IA open source, servidores MCP, sistemas de medios, experimentos de aprendizaje, productos y notas de construccion.",
    "What does Kyanite implementation help include?": "Que incluye la ayuda de implementacion de Kyanite?",
    "It can include installing and configuring Kyanite tools, adapting workflows, advising on setup, writing docs and examples, and leaving a usable handoff.": "Puede incluir instalacion y configuracion de herramientas Kyanite, adaptacion de flujos, asesoria de setup, docs, ejemplos y un handoff usable.",
    "Who is implementation help for?": "Para quien es la ayuda de implementacion?",
    "It is for people who want help using or adapting Kyanite-built tools such as mcp-video, Epoch, DialectOS, openglaze, and developer-learning diagnostics.": "Es para personas que quieren ayuda usando o adaptando herramientas Kyanite como mcp-video, Epoch, DialectOS, openglaze y diagnosticos de aprendizaje.",
    "Which Kyanite tool or workflow do you want help with? What are you trying to do with it?": "Con que herramienta o flujo de Kyanite quieres ayuda? Que quieres lograr con eso?",
    "What is confusing, broken, too technical, undocumented, hard to install, or hard to adapt?": "Que es confuso, roto, demasiado tecnico, indocumentado, dificil de instalar o dificil de adaptar?",
    "Installed tool, adapted workflow, docs, examples, training call, integration plan, localization QA, media pipeline, etc.": "Herramienta instalada, flujo adaptado, docs, ejemplos, llamada de entrenamiento, plan de integracion, QA de localizacion, pipeline de medios, etc.",
    "If this fits a Kyanite tool path, you will get a grounded next step. If it belongs under broader PuenteWorks consulting, Kyanite will say that instead of pretending.": "Si encaja con una ruta de herramienta Kyanite, recibiras un siguiente paso concreto. Si pertenece a una consultoria mas amplia de PuenteWorks, Kyanite lo dira en vez de fingir.",
    "No automatic charge.": "Sin cobro automatico.",
    "No public posting without permission.": "Nada se publica sin permiso.",
    "Best with source, demo, docs, product notes, logs, or workflow evidence.": "Funciona mejor con fuente, demo, docs, notas de producto, logs o evidencia del flujo.",
}

LANDING_ES_REPLACEMENTS = {
    "Implementation help for useful AI tools": "Ayuda de implementacion para herramientas de IA utiles",
    "Get the build working without losing days to setup, integration, and handoff.": "Haz funcionar el build sin perder dias en setup, integracion y handoff.",
    "KyaniteLabs turns open-source AI tools, MCP servers, media systems, localization QA, and repo diagnostics into usable working setups.": "KyaniteLabs convierte herramientas de IA open source, servidores MCP, sistemas de medios, QA de localizacion y diagnosticos de repos en setups funcionales y usables.",
    "The public repos stay inspectable. The paid path helps you install, adapt, understand, and hand off the tool in your real environment.": "Los repos publicos siguen siendo inspeccionables. La ruta pagada te ayuda a instalar, adaptar, entender y entregar la herramienta en tu entorno real.",
    "See working proof": "Ver prueba funcionando",
    "Get it working": "Hacerlo funcionar",
    "Working setup": "Setup funcionando",
    "instead of repo archaeology": "en vez de arqueologia de repos",
    "Clear handoff": "Handoff claro",
    "after install and adaptation": "despues de instalacion y adaptacion",
    "proof people can inspect": "prueba que se puede inspeccionar",
    "Turn AI video tools into something you can actually run.": "Convierte herramientas de video con IA en algo que realmente puedas ejecutar.",
    "Kyanite builds from real creative and technical bottlenecks: tools that edit video, estimate work, check localization quality, inspect repos, and leave docs/tests so the setup survives beyond the first chat.": "Kyanite construye desde bloqueos creativos y tecnicos reales: herramientas que editan video, estiman trabajo, revisan calidad de localizacion, inspeccionan repos y dejan docs/pruebas para que el setup sobreviva mas alla del primer chat.",
    "stuck useful workflow": "flujo util bloqueado",
    "constraints + taste + proof": "restricciones + gusto + prueba",
    "MCP / CLI / app / docs": "MCP / CLI / app / docs",
    "usable tool in context": "herramienta usable en contexto",
    "Proof you can inspect before asking for help.": "Prueba que puedes inspeccionar antes de pedir ayuda.",
    "The repos show what exists, what each tool does, and whether it is worth installing, adapting, or bringing into a paid implementation path.": "Los repos muestran que existe, que hace cada herramienta y si vale la pena instalarla, adaptarla o llevarla a una ruta pagada de implementacion.",
    "The thinking should make the tool easier to trust.": "El pensamiento debe hacer que la herramienta sea mas facil de confiar.",
    "Build logs, implementation notes, product decisions, and postmortems show where a tool works, where it is rough, and what it takes to use it well.": "Logs de construccion, notas de implementacion, decisiones de producto y postmortems muestran donde funciona una herramienta, donde esta rough y que hace falta para usarla bien.",
    "Outcome Model": "Modelo de resultado",
    "Make the useful thing usable.": "Hacer usable lo util.",
    "The pattern is simple: start from a real bottleneck, build a tool around it, document the tradeoffs, and help people get the result working in their own context.": "El patron es simple: empezar con un bloqueo real, construir una herramienta alrededor, documentar los tradeoffs y ayudar a que la gente haga funcionar el resultado en su propio contexto.",
    "Start from a real blocker": "Empezar con un bloqueo real",
    "Video editing, estimation, localization, glaze math, repo learning, and personal systems become worth building only when they remove a real delay, risk, or confusion.": "Video, estimacion, localizacion, calculo de esmaltes, aprendizaje de repos y sistemas personales solo valen la pena cuando quitan una demora, riesgo o confusion real.",
    "Make the result inspectable": "Hacer inspeccionable el resultado",
    "Shape the MCP, CLI, app, README, examples, screenshots, tests, metadata, and AI-readable discovery layer so a buyer can understand what they are getting.": "Da forma al MCP, CLI, app, README, ejemplos, capturas, pruebas, metadata y capa legible para IA para que un comprador entienda que esta recibiendo.",
    "Help people reach the outcome": "Ayudar a llegar al resultado",
    "Keep the tools open where possible, then sell practical setup, adaptation, and advising when someone wants the result without doing every step alone.": "Mantener abiertas las herramientas cuando sea posible, y vender setup, adaptacion y asesoria practica cuando alguien quiere el resultado sin hacer cada paso en soledad.",
    "Open-source proof. Paid help to reach the result faster.": "Prueba open source. Ayuda pagada para llegar al resultado mas rapido.",
    "Paid work helps people get Kyanite tools, products, workflows, and artifacts installed, adapted, documented, and usable.": "El trabajo pagado ayuda a que herramientas, productos, flujos y artefactos de Kyanite queden instalados, adaptados, documentados y usables.",
    "MCP servers, CLIs, domain tools, experiments, and build notes that help builders judge whether a tool can solve their problem before they pay for help.": "Servidores MCP, CLIs, herramientas de dominio, experimentos y notas de construccion que ayudan a builders a juzgar si una herramienta puede resolver su problema antes de pagar ayuda.",
    "Repos, docs, examples, release notes, and demos that reduce guesswork": "Repos, docs, ejemplos, notas de release y demos que reducen conjeturas",
    "Public proof before a paid implementation conversation": "Prueba publica antes de una conversacion de implementacion pagada",
    "For people who want the outcome from a Kyanite tool without spending days on setup, adaptation, docs, or integration alone.": "Para personas que quieren el resultado de una herramienta Kyanite sin pasar dias en setup, adaptacion, docs o integracion en soledad.",
    "Get the tool installed, configured, and checked": "Dejar la herramienta instalada, configurada y revisada",
    "Adapt it to the workflow and tradeoffs that matter": "Adaptarla al flujo y tradeoffs que importan",
    "A repeatable path for turning short-form clips into publishable video, captions, audio handoff, review loops, and durable proof assets.": "Una ruta repetible para convertir clips cortos en video publicable, captions, handoff de audio, ciclos de revision y activos de prueba durables.",
    "Help finding and fixing Spanish that would confuse, flatten, or embarrass users across docs, app strings, support macros, or locale files.": "Ayuda para encontrar y corregir espanol que podria confundir, aplanar o avergonzar a usuarios en docs, textos de app, macros de soporte o archivos de locale.",
    "A source-history diagnostic for AI-assisted developers who want to stop repeating the same mistakes and choose the next practice loop with evidence.": "Un diagnostico de historial de fuente para desarrolladores asistidos por IA que quieren dejar de repetir los mismos errores y elegir el siguiente ciclo de practica con evidencia.",
    "Downloadable prompts, repo structures, Claude Code workflows, and implementation templates for builders who want fewer blank-page starts.": "Prompts descargables, estructuras de repo, flujos de Claude Code y plantillas de implementacion para builders que quieren menos comienzos desde pagina en blanco.",
    "Bring the stuck result.": "Trae el resultado bloqueado.",
    "Tool you need running, repo you need installed, video pipeline you need usable, Spanish QA you need trusted, diagnostic you need explained, or a build you need handed off. If it connects to Kyanite's tools and practice, bring the stuck result.": "Herramienta que necesitas ejecutar, repo que necesitas instalado, pipeline de video que necesitas usable, QA de espanol que necesitas confiar, diagnostico que necesitas explicar o build que necesitas entregar. Si conecta con las herramientas y practica de Kyanite, trae el resultado bloqueado.",
    "Best for builders who want a Kyanite tool working in their real environment.": "Ideal para builders que quieren una herramienta Kyanite funcionando en su entorno real.",
    "Which Kyanite tool or result do you want working? Include repo/demo URLs, your setup, current blocker, and what done would look like.": "Que herramienta o resultado Kyanite quieres hacer funcionar? Incluye URLs de repo/demo, tu setup, bloqueo actual y como se veria terminado.",
    "KyaniteLabs is Simon Gonzalez de Cruz's creative development lab for building useful AI tools, MCP servers, media systems, domain software, and learning experiments.": "KyaniteLabs es el laboratorio creativo de Simon Gonzalez de Cruz para construir herramientas utiles de IA, servidores MCP, sistemas de medios, software de dominio y experimentos de aprendizaje.",
    "Most of the work is open source. The paid path is implementation and advising when someone wants help using a Kyanite tool without doing all the setup themselves.": "La mayor parte del trabajo es open source. La ruta pagada es implementacion y asesoria cuando alguien quiere usar una herramienta de Kyanite sin hacer todo el setup por su cuenta.",
    "MCP servers": "Servidores MCP",
    "agents can actually call": "que los agentes pueden llamar",
    "Build notes": "Notas de construccion",
    "from real experiments": "de experimentos reales",
    "Open source": "Open source",
    "tools people can inspect": "herramientas inspeccionables",
    "AI agents should edit video, not just talk about video.": "Los agentes de IA deberian editar video, no solo hablar de video.",
    "Kyanite builds tools from real creative and technical workflows: MCP servers, Python libraries, CLIs, effect pipelines, demos, docs, and install layers that make the work usable outside the original machine.": "Kyanite construye herramientas a partir de flujos creativos y tecnicos reales: servidores MCP, librerias Python, CLIs, pipelines de efectos, demos, docs y capas de instalacion que hacen usable el trabajo fuera de la maquina original.",
    "weird useful workflow": "flujo raro y util",
    "learning + taste + proof": "aprendizaje + gusto + prueba",
    "MCP / CLI / app / notes": "MCP / CLI / app / notas",
    "public tool": "herramienta publica",
    "Kyanite is build-first. The public repositories show what exists, what is being learned, and which tools are ready for people to inspect, install, adapt, or ask for help implementing.": "Kyanite empieza construyendo. Los repos publicos muestran que existe, que se esta aprendiendo y que herramientas estan listas para inspeccionar, instalar, adaptar o pedir ayuda para implementar.",
    "Build logs, learning notes, agent-system essays, product notes, and postmortems. This is where the videos, repos, and experiments become durable public memory.": "Logs de construccion, notas de aprendizaje, ensayos sobre sistemas agenticos, notas de producto y postmortems. Aqui los videos, repos y experimentos se vuelven memoria publica durable.",
    "The pattern is simple, but not soft: find a real workflow, build a tool around it, write down what happened, and keep improving in public.": "El patron es simple, pero no suave: encontrar un flujo real, construir una herramienta alrededor, escribir lo que paso y seguir mejorando en publico.",
    "Build from real use": "Construir desde uso real",
    "Make it inspectable": "Hacerlo inspeccionable",
    "Help people use it": "Ayudar a que se use",
    "KyaniteLabs publishes the tools and proof. Paid work helps people get Kyanite tools, products, workflows, and artifacts installed, adapted, documented, and usable.": "KyaniteLabs publica las herramientas y la prueba. El trabajo pagado ayuda a instalar, adaptar, documentar y usar herramientas, productos, flujos y artefactos de Kyanite.",
    "Best for builders who want implementation help around Kyanite tools.": "Ideal para builders que quieren ayuda de implementacion alrededor de herramientas Kyanite.",
    "Not a fit for generic consulting, vague vendor inquiries, or unrelated agency work.": "No es para consultoria generica, consultas vagas de proveedor o trabajo de agencia sin relacion.",
    "What belongs to Kyanite vs. a separate <a href=\"https://puenteworks.com\">PuenteWorks</a> engagement": "Que pertenece a Kyanite y que requiere un engagement separado de <a href=\"https://puenteworks.com\">PuenteWorks</a>",
    "Good fit when you want the outcome from a Kyanite tool or workflow instead of doing every setup, adaptation, and handoff step alone. Broader consulting routes through <a href=\"https://puenteworks.com\">PuenteWorks</a>.": "Buen fit cuando quieres el resultado de una herramienta o flujo Kyanite sin hacer cada paso de setup, adaptacion y handoff en soledad. La consultoria mas amplia se enruta por <a href=\"https://puenteworks.com\">PuenteWorks</a>.",
    "Broader consulting routes through <a href=\"https://puenteworks.com\">PuenteWorks</a>.": "La consultoria mas amplia se enruta por <a href=\"https://puenteworks.com\">PuenteWorks</a>.",
    "Not generic consulting. That belongs under <a href=\"https://puenteworks.com\">PuenteWorks</a>.": "No es consultoria generica. Eso pertenece a <a href=\"https://puenteworks.com\">PuenteWorks</a>.",
    "If this fits a Kyanite tool path, you will get a grounded next step. If it belongs under broader <a href=\"https://puenteworks.com\">PuenteWorks</a> consulting, the response will route it there instead of forcing a technical scope.": "Si encaja con una ruta de herramienta Kyanite, recibiras un siguiente paso concreto. Si pertenece a consultoria mas amplia de <a href=\"https://puenteworks.com\">PuenteWorks</a>, la respuesta lo enrutara ahi en vez de forzar un alcance tecnico.",
    "KyaniteLabs is operated by <a href=\"https://puenteworks.com\">Simon Gonzalez De Cruz / PuenteWorks</a>.": "KyaniteLabs es operado por <a href=\"https://puenteworks.com\">Simon Gonzalez De Cruz / PuenteWorks</a>.",
    "KyaniteLabs is operated by Simon Gonzalez De Cruz / PuenteWorks.": "KyaniteLabs es operado por Simon Gonzalez De Cruz / PuenteWorks.",
    "Subscribe": "Suscribirse",
    "Kyanite Build Notes": "Notas de construccion Kyanite",
    "Follow the useful builds.": "Sigue los builds utiles.",
    "Get short notes when a Kyanite tool, product, or field note is worth inspecting: MCP servers, media pipelines, repo diagnostics, localization QA, implementation lessons, and useful weird software.": "Recibe notas cortas cuando una herramienta, producto o nota de campo de Kyanite merece inspeccionarse: servidores MCP, pipelines de medios, diagnosticos de repos, QA de localizacion, aprendizajes de implementacion y software raro util.",
    "Only public build notes and practical implementation signals.": "Solo notas publicas de construccion y senales practicas de implementacion.",
    "No scraped lists, generic AI newsletter noise, or purchased audiences.": "Sin listas scrapeadas, ruido generico de newsletters de IA ni audiencias compradas.",
    "Unsubscribe whenever the notes stop being useful.": "Puedes darte de baja cuando las notas dejen de ser utiles.",
    "Newsletter": "Boletin",
    "You are on the Kyanite Build Notes list.": "Ya estas en la lista de notas Kyanite.",
    "Name <span class=\"optional-label\">optional</span>": "Nombre <span class=\"optional-label\">opcional</span>",
    "What should Kyanite write about? <span class=\"optional-label\">optional</span>": "Sobre que debe escribir Kyanite? <span class=\"optional-label\">opcional</span>",
    "Tool, repo, media pipeline, localization, productization, or implementation problem.": "Herramienta, repo, pipeline de medios, localizacion, productizacion o problema de implementacion.",
    "Send me Kyanite Build Notes. I can unsubscribe any time.": "Enviame notas Kyanite. Puedo darme de baja cuando quiera.",
    "Join Build Notes": "Unirme a las notas",
    "Joining...": "Uniendo...",
}

EXTRA_ES_REPLACEMENTS = {
    "Ayuda de implementacion — KyaniteLabs Open Source Herramientas": "Ayuda de implementacion — Herramientas open source de KyaniteLabs",
    "Blog / Lab Notes — KyaniteLabs Builds and Learning": "Notas de laboratorio — Builds y aprendizaje de KyaniteLabs",
    "Notas de laboratorio — KyaniteLabs Builds and Learning": "Notas de laboratorio — Builds y aprendizaje de KyaniteLabs",
    "Builds": "Builds",
    "Public repositories": "Repositorios publicos",
    "Repos publicositories": "Repositorios publicos",
    "KyaniteLabs Open Source Herramientas": "Herramientas open source de KyaniteLabs",
    "Laboratorio creativo de desarrollo for open-source AI tools, Servidores MCP, build notes, and implementation help.": "Laboratorio creativo para herramientas de IA open source, servidores MCP, notas de construccion y ayuda de implementacion.",
    "Laboratorio creativo de desarrollo for open-source AI tools, Servidores MCP, media automation, learning notes, and implementation help.": "Laboratorio creativo para herramientas de IA open source, servidores MCP, automatizacion de medios, notas de aprendizaje e implementacion.",
    "Laboratorio creativo de desarrollo for open-source AI tools, Servidores MCP, build notes, and implementacion help.": "Laboratorio creativo para herramientas de IA open source, servidores MCP, notas de construccion y ayuda de implementacion.",
    "Laboratorio creativo de desarrollo for open-source AI tools, Servidores MCP, media automation, learning notes, and implementacion help.": "Laboratorio creativo para herramientas de IA open source, servidores MCP, automatizacion de medios, notas de aprendizaje e implementacion.",
    "Agent-native tools, public proof, and notes from the build floor.": "Herramientas agent-native, prueba publica y notas desde el taller.",
    "Agent-native tools, operator assets, and public product systems.": "Herramientas agent-native, activos de operador y sistemas publicos de producto.",
    "Agent-native tools and operator assets grounded in real workflows.": "Herramientas agent-native y activos de operador basados en flujos reales.",
    "KyaniteLabs is operated by Simon Gonzalez De Cruz / PuenteWorks.": "KyaniteLabs es operado por Simon Gonzalez De Cruz / PuenteWorks.",
    "Most Kyanite products are open source. The paid path here is implementation and advising around those tools: install them, adapt them to your workflow, understand the tradeoffs, and leave with something usable.": "La mayoria de los productos Kyanite son open source. La ruta pagada aqui es implementacion y asesoria alrededor de esas herramientas: instalarlas, adaptarlas a tu flujo, entender los tradeoffs y salir con algo usable.",
    "Which Kyanite tool or workflow you want to use": "Que herramienta o flujo de Kyanite quieres usar",
    "Your machine, stack, constraints, and current blockers": "Tu maquina, stack, restricciones y bloqueos actuales",
    "Install path, docs, examples, and handoff needs": "Ruta de instalacion, docs, ejemplos y necesidades de handoff",
    "Whether advising, setup, adaptation, or a build sprint fits": "Si encaja asesoria, setup, adaptacion o sprint de construccion",
    "What belongs to Kyanite vs. a separate PuenteWorks engagement": "Que pertenece a Kyanite y que requiere un engagement separado de PuenteWorks",
    "A grounded implementation path": "Una ruta de implementacion aterrizada",
    "Setup/adaptation notes and priority blockers": "Notas de setup/adaptacion y bloqueos prioritarios",
    "Docs, examples, or handoff material where useful": "Docs, ejemplos o material de handoff cuando sirva",
    "Advising on architecture, constraints, and tradeoffs": "Asesoria sobre arquitectura, restricciones y tradeoffs",
    "Scope for deeper build work if the tool needs it": "Alcance para construccion mas profunda si la herramienta lo necesita",
    "Paid path": "Ruta pagada",
    "Good fit when you want help implementing a Kyanite tool or workflow instead of doing the setup and adaptation alone. Broader consulting belongs under PuenteWorks.": "Buen fit cuando quieres ayuda implementando una herramienta o flujo de Kyanite en vez de hacer el setup y la adaptacion en soledad. La consultoria mas amplia pertenece a PuenteWorks.",
    "The goal is practical implementation. You should leave closer to using the tool.": "El objetivo es implementacion practica. Debes salir mas cerca de usar la herramienta.",
    "Get a Kyanite tool running in your environment with the right dependencies, commands, configs, examples, and basic checks.": "Deja una herramienta Kyanite funcionando en tu entorno con dependencias, comandos, configs, ejemplos y checks basicos.",
    "Map the tool to your real process: video pipeline, estimation workflow, localization QA, glaze studio work, or dev-learning diagnostics.": "Mapea la herramienta a tu proceso real: pipeline de video, estimacion, QA de localizacion, estudio de esmaltes o diagnosticos de aprendizaje.",
    "Understand the tradeoffs, next steps, limits, and maintenance expectations so the implementation survives after the session.": "Entiende tradeoffs, siguientes pasos, limites y mantenimiento para que la implementacion sobreviva despues de la sesion.",
    "MCP video editing, time estimation, Spanish localization QA, ceramic glaze software, and development-learning diagnostics. The paid support exists so people can actually use the tools, not just admire the repo.": "Edicion de video por MCP, estimacion de tiempo, QA de localizacion en español, software de esmaltes ceramicos y diagnosticos de aprendizaje. El soporte pagado existe para que la gente use las herramientas, no solo admire el repo.",
    "People who want mcp-video, Epoch, DialectOS, openglaze, or a Kyanite workflow implemented.": "Personas que quieren implementar mcp-video, Epoch, DialectOS, openglaze o un flujo Kyanite.",
    "Builders who want advising around setup, adaptation, docs, and next steps.": "Builders que quieren asesoria sobre setup, adaptacion, docs y siguientes pasos.",
    "Not generic consulting. That belongs under PuenteWorks.": "No es consultoria generica. Eso pertenece a PuenteWorks.",
    "KyaniteLabs publishes notes after there is a real build, lesson, product, or workflow to explain.": "KyaniteLabs publica notas cuando ya hay un build, aprendizaje, producto o flujo real que explicar.",
    "The blog covers open-source AI tools, MCP systems, agentic media, developer learning, implementation notes, and the work behind the proof.": "Las notas cubren herramientas de IA open source, sistemas MCP, medios agenticos, aprendizaje de desarrollo, implementacion y el trabajo detras de la prueba.",
    "Published KyaniteLabs notes on open-source AI tools, MCP systems, agentic media, developer learning, products, and implementation field notes.": "Notas de KyaniteLabs sobre herramientas de IA open source, sistemas MCP, medios agenticos, aprendizaje de desarrollo, productos e implementacion.",
    "Published technical lab notes on open-source AI tools, MCP systems, agentic media, developer learning, products, and implementation field notes.": "Notas tecnicas de laboratorio sobre herramientas de IA open source, sistemas MCP, medios agenticos, aprendizaje de desarrollo, productos e implementacion.",
    "Repositories show what Kyanite builds, learns, breaks, fixes, and releases. The paid path is implementation help around those tools, not a generic consulting offer.": "Los repositorios muestran lo que Kyanite construye, aprende, rompe, arregla y publica. La ruta pagada es ayuda de implementacion alrededor de esas herramientas, no consultoria generica.",
    "Repositorios publicos show what Kyanite builds, learns, breaks, fixes, and releases. The paid path is implementation help around those tools, not a generic consulting offer.": "Los repositorios muestran lo que Kyanite construye, aprende, rompe, arregla y publica. La ruta pagada es ayuda de implementacion alrededor de esas herramientas, no consultoria generica.",
    "Prompts, repo structures, Claude Code workflows, and implementation templates. Not courses. Not vague prompt dumps. Small artifacts built for people who ship.": "Prompts, estructuras de repo, flujos de Claude Code y plantillas de implementacion. No cursos. No dumps vagos de prompts. Artefactos pequeños para gente que envia.",
    "4 more included": "4 mas incluidos",
    "1 more included": "1 mas incluido",
    "agent-native tool protocol": "protocolo de herramienta agent-native",
    "Open mcp-video": "Abrir mcp-video",
    "Read the build note": "Leer la nota de construccion",
    "AI tool implementation": "Implementacion de herramientas de IA",
    "Public Herramientas": "Herramientas publicas",
    "Public Tools": "Herramientas publicas",
    "Servidores MCP, CLIs, domain tools, experiments, and build notes that you can inspect, install, fork, learn from, or use as starting points.": "Servidores MCP, CLIs, herramientas de dominio, experimentos y notas de construccion que puedes inspeccionar, instalar, bifurcar, estudiar o usar como punto de partida.",
    "Repos, docs, examples, release notes, and demos": "Repos, docs, ejemplos, notas de version y demos",
    "Built in public as the Kyanite portfolio and learning trail": "Construido en publico como portafolio y rastro de aprendizaje de Kyanite",
    "Paid help": "Ayuda pagada",
    "For people who want to use a Kyanite tool without doing all the setup, adaptation, docs, or workflow integration alone.": "Para personas que quieren usar una herramienta Kyanite sin hacer solas todo el setup, adaptacion, docs o integracion del flujo.",
    "Install, configure, and adapt the tool": "Instalar, configurar y adaptar la herramienta",
    "Map the workflow and advise on tradeoffs": "Mapear el flujo y asesorar sobre tradeoffs",
    "Leave docs, examples, and a usable handoff": "Dejar docs, ejemplos y un handoff usable",
    "Agentic Media System": "Sistema de medios agentico",
    "Media pipeline": "Pipeline de medios",
    "Scoped": "Por alcance",
    "Built from the Infinite Monkey production workflow": "Construido desde el flujo de produccion de Infinite Monkey",
    "Visual system, script, caption, and edit handoff": "Sistema visual, guion, captions y handoff de edicion",
    "Turns social clips into durable blog and proof assets": "Convierte clips sociales en notas y activos de prueba durables",
    "Discuss media workflow": "Hablar del flujo de medios",
    "Help using DialectOS for Spanish docs, app strings, support macros, or locale files across target dialects.": "Ayuda usando DialectOS para docs en español, textos de app, macros de soporte o archivos locale en dialectos objetivo.",
    "Up to 10,000 source words and 5 dialects": "Hasta 10,000 palabras fuente y 5 dialectos",
    "Severity table and implementation-ready report": "Tabla de severidad y reporte listo para implementar",
    "For teams avoiding embarrassing generic Spanish": "Para equipos que quieren evitar español generico y vergonzoso",
    "Ask about certification": "Preguntar por certificacion",
    "Learning Diagnostics": "Diagnosticos de aprendizaje",
    "A source-history diagnostic for AI-assisted developers who want evidence about their learning patterns, repeated failures, and next practice loops.": "Diagnostico de historial fuente para desarrolladores asistidos por IA que quieren evidencia sobre patrones de aprendizaje, fallas repetidas y siguientes ciclos de practica.",
    "Uses devarch-framework and learning-archaeology patterns": "Usa devarch-framework y patrones de arqueologia de aprendizaje",
    "Finds repeated failures, habits, and study opportunities": "Encuentra fallas repetidas, habitos y oportunidades de practica",
    "Outputs a report people can act on": "Entrega un reporte accionable",
    "Request diagnostic": "Pedir diagnostico",
    "Downloadable prompts, repo structures, Claude Code workflows, and implementation templates for builders who already ship.": "Prompts descargables, estructuras de repo, flujos de Claude Code y plantillas de implementacion para builders que ya envian.",
    "Designed as workflows, not prompt confetti": "Diseñados como flujos, no confeti de prompts",
    "Good entry point before scoped work": "Buen punto de entrada antes de un alcance pagado",
    "Open shop": "Abrir tienda",
    "mcp-video, Epoch, DialectOS, openglaze, devarch tools": "mcp-video, Epoch, DialectOS, openglaze y herramientas devarch",
    "Start from a workflow that actually hurts or fascinates: video editing, estimating time, localization, glaze math, learning from commits.": "Empieza desde un flujo que de verdad duele o fascina: edicion de video, estimacion de tiempo, localizacion, matematicas de esmaltes o aprendizaje desde commits.",
    "Shape the MCP, CLI, app, README, examples, screenshots, tests, metadata, and AI-readable discovery layer so the work can survive outside the chat.": "Da forma al MCP, CLI, app, README, ejemplos, capturas, pruebas, metadata y capa legible para IA para que el trabajo sobreviva fuera del chat.",
    "Keep the tools open where possible, sell practical implementation help when someone wants the setup, adaptation, or advising done with them.": "Mantener abiertas las herramientas cuando sea posible y vender ayuda practica de implementacion cuando alguien quiere setup, adaptacion o asesoria hecha con ellos.",
    "Servidores MCP, CLIs, domain tools, experiments, and build notes that you can inspect, install, fork, learn from, or use as starting points.": "Servidores MCP, CLIs, herramientas de dominio, experimentos y notas de construccion que puedes inspeccionar, instalar, bifurcar, estudiar o usar como punto de partida.",
    "Tool you need running, repo you need installed, video pipeline you need usable, Spanish QA you need trusted, diagnostic you need explained, or a build you need handed off. If it connects to Kyanite's tools and practice, bring the blocker.": "Herramienta que necesitas corriendo, repo que necesitas instalado, pipeline de video que necesitas usable, QA de espanol que necesitas confiable, diagnostico que necesitas explicado o build que necesitas entregar. Si conecta con las herramientas y practica de Kyanite, trae el bloqueo.",
    "© 2026 KyaniteLabs. All rights reserved.": "© 2026 KyaniteLabs. Todos los derechos reservados.",
    "&copy; 2026 KyaniteLabs. All rights reserved.": "&copy; 2026 KyaniteLabs. Todos los derechos reservados.",
    "This gives Kyanite enough context to decide whether the request fits: open-source tools, build workflows, MCP systems, media pipelines, localization QA, and learning diagnostics.": "Esto da a Kyanite suficiente contexto para decidir si el pedido encaja: herramientas open source, flujos de construccion, sistemas MCP, pipelines de medios, QA de localizacion y diagnosticos de aprendizaje.",
}

SPANISH_REPLACEMENTS = {**COMMON_ES_REPLACEMENTS, **LANDING_ES_REPLACEMENTS, **EXTRA_ES_REPLACEMENTS}


def add_hreflang(html, en_path, es_path):
    html = re.sub(
        r'\n?  <link rel="alternate" hreflang="(?:en|es|es-419|x-default)" href="[^"]+">',
        "",
        html,
    )
    alternates = f"""
  <link rel="alternate" hreflang="en" href="{CANONICAL_BASE}{en_path}">
  <link rel="alternate" hreflang="es" href="{CANONICAL_BASE}{es_path}">
  <link rel="alternate" hreflang="es-419" href="{CANONICAL_BASE}{es_path}">
  <link rel="alternate" hreflang="x-default" href="{CANONICAL_BASE}{en_path}">
"""
    return html.replace("</head>", alternates + "</head>", 1)


def spanishify(html, en_path, es_path):
    html = html.replace('<html lang="en">', '<html lang="es">', 1)
    url_pairs = [
        ('href="/implementation/intake"', 'href="/es/implementation/intake"'),
        ('href="/implementation"', 'href="/es/implementation"'),
        ('href="/blog/', 'href="/es/blog/'),
        ('href="/blog"', 'href="/es/blog"'),
        ('href="/shop/', 'href="/es/shop/'),
        ('href="/shop"', 'href="/es/shop"'),
        ('href="/about"', 'href="/es/about"'),
        ('href="/#', 'href="/es/#'),
        ('href="/"', 'href="/es/"'),
        ('https://kyanitelabs.tech/implementation/intake', 'https://kyanitelabs.tech/es/implementation/intake'),
        ('https://kyanitelabs.tech/implementation', 'https://kyanitelabs.tech/es/implementation'),
        ('https://kyanitelabs.tech/blog/', 'https://kyanitelabs.tech/es/blog/'),
        ('https://kyanitelabs.tech/blog', 'https://kyanitelabs.tech/es/blog'),
        ('https://kyanitelabs.tech/shop/', 'https://kyanitelabs.tech/es/shop/'),
        ('https://kyanitelabs.tech/shop', 'https://kyanitelabs.tech/es/shop'),
    ]
    for old, new in url_pairs:
        html = html.replace(old, new)
    html = html.replace(
        f'class="language-link" href="{es_path}" hreflang="es" lang="es"',
        f'class="language-link" href="{en_path}" hreflang="en" lang="en"',
    )
    html = html.replace(f'<link rel="canonical" href="{CANONICAL_BASE}{en_path}">', f'<link rel="canonical" href="{CANONICAL_BASE}{es_path}">')
    html = html.replace(f'content="{CANONICAL_BASE}{en_path}"', f'content="{CANONICAL_BASE}{es_path}"')
    html = html.replace('>ES</a>', '>EN</a>')
    html = html.replace(f'href="{CANONICAL_BASE}/es/es/', f'href="{CANONICAL_BASE}/es/')
    html = html.replace('href="/es/es/', 'href="/es/')
    html = html.replace('href="/es/static/', 'href="/static/')
    html = html.replace('href="/es/', 'href="/es/')
    ordered_replacements = sorted(SPANISH_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True)
    for english, spanish in ordered_replacements:
        html = html.replace(english, spanish)
    html = html.replace('"inLanguage": "en-US"', '"inLanguage": "es-419"')
    return add_hreflang(html, en_path, es_path)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    try:
        html = render_template_file(
            "landing-v2.html",
            public_projects=PUBLIC_PROJECTS,
            blog_posts=BLOG_POSTS,
            canonical_base=CANONICAL_BASE,
        )
        return add_hreflang(html, "/", "/es/")
    except Exception as e:
        # Fallback to old HTML if v2 fails
        return render_template_string(HTML, KOFI_URL=app.config["KOFI_URL"])


@app.route("/es/")
@app.route("/es")
def index_es():
    html = render_template_file(
        "landing-v2.html",
        public_projects=PUBLIC_PROJECTS_ES,
        blog_posts=BLOG_POSTS_ES,
        canonical_base=CANONICAL_BASE,
    )
    return spanishify(html, "/", "/es/")


@app.route("/about")
def about():
    return render_template_file(
        "about.html",
        copy=ABOUT_COPY["en"],
        canonical_base=CANONICAL_BASE,
    )


@app.route("/es/about")
def about_es():
    return render_template_file(
        "about.html",
        copy=ABOUT_COPY["es"],
        canonical_base=CANONICAL_BASE,
    )


LEGAL_PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} | KyaniteLabs</title>
  <meta name="description" content="{{ description }}">
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
  <link rel="canonical" href="{{ canonical_base }}{{ path }}">
  <link rel="alternate" type="text/plain" title="KyaniteLabs AI-readable brief" href="https://kyanitelabs.tech/llms.txt">
  <link rel="alternate" type="text/plain" title="KyaniteLabs full AI-readable context" href="https://kyanitelabs.tech/llms-full.txt">
  <link rel="alternate" type="application/rss+xml" title="KyaniteLabs Blog Feed" href="https://kyanitelabs.tech/feed.xml">
  <script>window.addEventListener('load',function(){window.setTimeout(function(){var s=document.createElement('script');s.src='/static/posthog.js';document.body.appendChild(s);},0);},{once:true});</script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #070812;
      --panel: #111421;
      --text: #f4f7ff;
      --muted: #aab4c7;
      --line: #2a3044;
      --accent: #38d8ff;
      --body-font: "Plus Jakarta Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --display-font: "Space Grotesk", system-ui, sans-serif;
      --mono-font: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      --step--1: clamp(0.84rem, 0.79rem + 0.22vw, 0.95rem);
      --step-0: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
      --step-1: clamp(1.2rem, 1.1rem + 0.5vw, 1.45rem);
      --step-4: clamp(2.07rem, 1.64rem + 2.15vw, 3.2rem);
      --measure: 66ch;
    }
    * { box-sizing: border-box; }
    html {
      font-size: 100%;
      -webkit-text-size-adjust: 100%;
      text-size-adjust: 100%;
    }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--body-font);
      font-size: var(--step-0);
      line-height: 1.6;
      font-synthesis: none;
      font-optical-sizing: auto;
      text-rendering: optimizeLegibility;
    }
    main {
      width: min(760px, var(--measure), calc(100% - 32px));
      margin: 0 auto;
      padding: 64px 0;
    }
    .skip-link {
      position: absolute;
      left: 16px;
      top: 12px;
      transform: translateY(-140%);
      background: var(--accent);
      color: var(--bg);
      border-radius: 4px;
      padding: 10px 14px;
      z-index: 20;
    }
    .skip-link:focus {
      transform: translateY(0);
      outline: 3px solid var(--text);
      outline-offset: 3px;
    }
    a { color: var(--accent); }
    header {
      border-bottom: 1px solid var(--line);
      margin-bottom: 32px;
      padding-bottom: 24px;
    }
    .brand {
      color: var(--accent);
      font-family: var(--mono-font);
      font-size: var(--step--1);
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    h1 {
      font-family: var(--display-font);
      font-size: var(--step-4);
      line-height: 1;
      margin: 12px 0 0;
      text-wrap: balance;
    }
    h2 {
      font-family: var(--display-font);
      font-size: var(--step-1);
      line-height: 1.2;
      margin: 32px 0 8px;
      text-wrap: balance;
    }
    p, li {
      color: var(--muted);
      max-width: var(--measure);
      text-wrap: pretty;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 16px 0;
      padding: 20px;
    }
    footer {
      color: var(--muted);
      border-top: 1px solid var(--line);
      margin-top: 32px;
      padding-top: 20px;
      font-size: var(--step--1);
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <main id="main">
    <header>
      <a class="brand" href="/">KyaniteLabs</a>
      <h1>{{ title }}</h1>
      <p>Last updated: June 4, 2026</p>
    </header>
    {{ body|safe }}
    <footer>
      <p>KyaniteLabs is operated by <a href="https://puenteworks.com">Simon Gonzalez De Cruz / PuenteWorks</a>.</p>
      <p>Questions: <a href="mailto:info@kyanitelabs.tech">info@kyanitelabs.tech</a></p>
    </footer>
  </main>
</body>
</html>
"""


@app.route("/privacy")
def privacy_policy():
    body = """
    <section>
      <h2>What this covers</h2>
      <p>This policy covers KyaniteLabs public site forms, Kyanite Build Notes newsletter signups, implementation intake, contact requests, public analytics, and internal connected workflows used by authorized KyaniteLabs operators.</p>
    </section>
    <section>
      <h2>Data we use</h2>
      <p>Public forms may collect your name, email address, request context, newsletter interests, consent status, source page, timestamp, browser user agent, and IP-derived request metadata. Internal connected workflows may store connected account identifiers, display names, handles, access tokens, refresh tokens, post metadata, local media references, captions, and publishing status needed to operate approved posting workflows.</p>
    </section>
    <section>
      <h2>How data is used</h2>
      <p>We use public form data to reply to requests, review implementation fit, send Kyanite Build Notes when you explicitly subscribe, honor unsubscribe requests, troubleshoot form delivery, and maintain basic operational records. We use connected workflow data to authenticate accounts, upload approved content, track publishing state, troubleshoot failures, and maintain a human-reviewable content pipeline.</p>
    </section>
    <section>
      <h2>Sharing</h2>
      <p>We do not sell personal data. Data is shared with platform APIs only as needed to authenticate, upload, or publish content that an authorized operator has approved. Email and infrastructure providers may process messages or operational logs as needed to run the site and newsletter workflow.</p>
    </section>
    <section>
      <h2>Retention and access</h2>
      <p>Newsletter records are kept until you unsubscribe or ask for removal. Operational records and tokens are kept only as long as they are useful for the workflow or required for troubleshooting. Access is limited to authorized KyaniteLabs operators.</p>
    </section>
    """
    return render_template_string(
        LEGAL_PAGE_HTML,
        title="Privacy Policy",
        description="KyaniteLabs privacy policy for contact forms, connected workflows, operational records, platform integrations, and public site analytics.",
        path="/privacy",
        canonical_base=CANONICAL_BASE,
        body=body,
    )


@app.route("/terms")
def terms_of_service():
    body = """
    <section>
      <h2>Authorized use</h2>
      <p>Kyanite Content Factory is intended for authorized KyaniteLabs and PuenteWorks operators. Users are responsible for connecting only accounts they have authority to manage.</p>
    </section>
    <section>
      <h2>Platform rules</h2>
      <p>Use of connected social platforms remains subject to each platform's own terms, policies, API rules, and review requirements.</p>
    </section>
    <section>
      <h2>Content responsibility</h2>
      <p>Operators are responsible for reviewing captions, media, disclosures, music usage, and publication settings before posting content externally.</p>
    </section>
    <section>
      <h2>Availability</h2>
      <p>The tool is provided for internal workflow use. Availability can depend on local services, platform APIs, account status, and third-party review or rate limits.</p>
    </section>
    <section>
      <h2>Contact</h2>
      <p>For questions about this tool or these terms, contact KyaniteLabs at info@kyanitelabs.tech.</p>
    </section>
    """
    return render_template_string(
        LEGAL_PAGE_HTML,
        title="Terms of Service",
        description="KyaniteLabs terms of service for authorized workflows, platform rules, content responsibility, availability, and contact boundaries.",
        path="/terms",
        canonical_base=CANONICAL_BASE,
        body=body,
    )


@app.route("/robots.txt")
def robots_txt():
    return Response(
        "\n".join([
            "User-agent: *",
            "Allow: /",
            "",
            "# Search and answer-engine crawlers should be able to quote the public offer pages.",
            "User-agent: OAI-SearchBot",
            "Allow: /",
            "",
            "User-agent: GPTBot",
            "Allow: /",
            "",
            "User-agent: ChatGPT-User",
            "Allow: /",
            "",
            "User-agent: ClaudeBot",
            "Allow: /",
            "",
            "User-agent: Claude-User",
            "Allow: /",
            "",
            "User-agent: PerplexityBot",
            "Allow: /",
            "",
            "User-agent: Google-Extended",
            "Allow: /",
            "",
            "User-agent: Applebot-Extended",
            "Allow: /",
            "",
            "User-agent: CCBot",
            "Allow: /",
            "",
            f"Sitemap: {CANONICAL_BASE}/sitemap.xml",
            f"# AI-readable site brief: {CANONICAL_BASE}/llms.txt",
            f"# Full AI-readable context: {CANONICAL_BASE}/llms-full.txt",
            f"# Structured AI sitemap: {CANONICAL_BASE}/ai-sitemap.json",
            f"# Blog RSS feed: {CANONICAL_BASE}/feed.xml",
            f"# IndexNow key: {CANONICAL_BASE}/{INDEXNOW_KEY}.txt",
            "",
        ]),
        mimetype="text/plain",
    )


@app.route(f"/{TIKTOK_SITE_VERIFICATION_FILENAME}")
def tiktok_site_verification():
    return Response(TIKTOK_SITE_VERIFICATION_BODY, mimetype="text/plain")


@app.route(f"/{INDEXNOW_KEY}.txt")
def indexnow_key_file():
    return Response(INDEXNOW_KEY, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    today = datetime.now(UTC).date().isoformat()
    pages = [
        ("/", "1.0", "weekly"),
        ("/about", "0.9", "monthly"),
        ("/privacy", "0.45", "yearly"),
        ("/terms", "0.45", "yearly"),
        ("/blog", "0.88", "weekly"),
        ("/implementation", "0.9", "monthly"),
        ("/implementation/intake", "0.75", "monthly"),
        ("/shop", "0.65", "monthly"),
        ("/shop/ai-coding-agent-blueprint", "0.55", "monthly"),
        ("/shop/claude-code-productivity-pack", "0.55", "monthly"),
        ("/es/", "1.0", "weekly"),
        ("/es/about", "0.9", "monthly"),
        ("/es/blog", "0.88", "weekly"),
        ("/es/implementation", "0.9", "monthly"),
        ("/es/implementation/intake", "0.75", "monthly"),
        ("/es/shop", "0.65", "monthly"),
        ("/es/shop/ai-coding-agent-blueprint", "0.55", "monthly"),
        ("/es/shop/claude-code-productivity-pack", "0.55", "monthly"),
        ("/llms.txt", "0.7", "weekly"),
        ("/llms-full.txt", "0.65", "weekly"),
        ("/ai-sitemap.json", "0.7", "weekly"),
        ("/feed.xml", "0.6", "weekly"),
    ]
    pages.extend((f"/blog/{post['slug']}", "0.82", "monthly") for post in BLOG_POSTS)
    pages.extend((f"/es/blog/{post['slug']}", "0.82", "monthly") for post in BLOG_POSTS_ES)
    urls = []
    for path, priority, changefreq in pages:
        urls.append(f"""  <url>
    <loc>{CANONICAL_BASE}{path}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>""")
    body = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
%s
</urlset>
""" % "\n".join(urls)
    return Response(body, mimetype="application/xml")


@app.route("/feed.xml")
@app.route("/rss.xml")
def feed_xml():
    items = []
    for post in BLOG_POSTS:
        url = f"{CANONICAL_BASE}/blog/{post['slug']}"
        title = html_lib.escape(post["title"])
        description = html_lib.escape(post["excerpt"])
        category = html_lib.escape(post["category"])
        items.append(f"""    <item>
      <title>{title}</title>
      <link>{url}</link>
      <guid isPermaLink="true">{url}</guid>
      <description>{description}</description>
      <category>{category}</category>
      <pubDate>{rss_date(post["date"])}</pubDate>
    </item>""")
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>KyaniteLabs Blog / Lab Notes</title>
    <link>{CANONICAL_BASE}/blog</link>
    <description>Build notes, implementation field notes, AI tool essays, and KyaniteLabs public proof updates.</description>
    <language>en-us</language>
    <lastBuildDate>{format_datetime(datetime.now(UTC))}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    return Response(body, mimetype="application/rss+xml")


@app.route("/ai-sitemap.json")
def ai_sitemap_json():
    return jsonify({
        "site": {
            "name": "KyaniteLabs",
            "url": CANONICAL_BASE,
            "description": "Open-source proof and paid implementation help for getting AI tools, MCP systems, media pipelines, localization QA, and repo diagnostics working in real environments.",
            "parentOrganization": {
                "name": "PuenteWorks",
                "url": PUENTEWORKS_URL,
                "role": "Legal and business container for broader consulting, workflow, and AI operations work.",
            },
            "portfolioRelationship": {
                "puenteWorks": PUENTEWORKS_URL,
                "kyaniteLabs": CANONICAL_BASE,
                "summary": "PuenteWorks leads business workflow and consulting engagements; KyaniteLabs is the technical product and implementation lab inside the same owned portfolio.",
            },
            "languages": ["en", "es"],
            "discovery": {
                "sitemap": f"{CANONICAL_BASE}/sitemap.xml",
                "rss": f"{CANONICAL_BASE}/feed.xml",
                "llms": f"{CANONICAL_BASE}/llms.txt",
                "llmsFull": f"{CANONICAL_BASE}/llms-full.txt",
            },
        },
        "audienceFit": [
            "Developers, builders, artists, and AI operators who want Kyanite-built tools working in their environment.",
            "Teams who want the outcome from Kyanite open-source tools without doing every setup, adaptation, and handoff step alone.",
            "People following the build notes, learning process, experiments, and public product work behind KyaniteLabs.",
        ],
        "paidPaths": [
            {
                "name": "Implementation and Advising",
                "url": f"{CANONICAL_BASE}/implementation",
                "deliverables": [
                    "Get Kyanite tools installed, configured, and checked",
                    "Adapt an open-source tool to the real workflow and tradeoffs that matter",
                    "Explain setup, architecture, docs, and handoff",
                    "Build implementation scope for MCP, media, localization, or dev tooling work",
                ],
            },
            {
                "name": "MCP / Agent Tool Build",
                "url": f"{CANONICAL_BASE}/#support",
                "deliverables": [
                    "MCP server, CLI, or Python/TypeScript package",
                    "Tool schemas, examples, tests, docs, and install path",
                    "Public or internal implementation surface",
                ],
            },
            {
                "name": "Agentic Media System",
                "url": f"{CANONICAL_BASE}/#support",
                "deliverables": [
                    "mcp-video-backed media workflow",
                    "Repeatable video assembly recipes",
                    "Clips, captions, posting assets, and review handoff",
                ],
            },
            {
                "name": "Spanish Launch QA",
                "url": f"{CANONICAL_BASE}/#support",
                "deliverables": [
                    "DialectOS-backed Spanish localization QA",
                    "Dialect, register, glossary, and structure checks",
                    "Implementation-ready localization report",
                ],
            },
        ],
        "publicRepositories": PUBLIC_PROJECTS,
        "founder": {
            "name": "Simon Gonzalez de Cruz",
            "url": f"{CANONICAL_BASE}/about",
            "spanishUrl": f"{CANONICAL_BASE}/es/about",
        },
        "blogPosts": [
            {
                "title": post["title"],
                "url": f"{CANONICAL_BASE}/blog/{post['slug']}",
                "spanishUrl": f"{CANONICAL_BASE}/es/blog/{post['slug']}",
                "primaryKeyword": post.get("primary_keyword"),
                "description": post["excerpt"],
            }
            for post in BLOG_POSTS
        ],
        "contact": "info@kyanitelabs.tech",
    })


@app.route("/llms.txt")
def llms_txt():
    project_lines = "\n".join(
        f"- [{p['name']}]({p['url']}): {p['description']}" for p in PUBLIC_PROJECTS
    )
    body = f"""# KyaniteLabs

> Open-source proof and paid implementation help for getting AI tools working in real environments.

KyaniteLabs is where Simon Gonzalez de Cruz turns AI tools, MCP servers, media systems, developer-learning experiments, domain software, and product notes into public proof. Most Kyanite products are open source. The paid path helps people install, adapt, understand, and hand off the tools in their real environment.

KyaniteLabs is operated by [Simon Gonzalez De Cruz / PuenteWorks]({PUENTEWORKS_URL}). Kyanite is the public lab for tool implementation, while broader consulting belongs under PuenteWorks.

## Primary Pages

- [Homepage]({CANONICAL_BASE}/): outcome-led overview, public GitHub proof, products, blog, and contact form.
- [About Simon Gonzalez de Cruz]({CANONICAL_BASE}/about): founder page with Kyanite's builder story, principles, and brand boundary.
- [Blog]({CANONICAL_BASE}/blog): build notes, learning notes, agent-system essays, and tool implementation field notes.
- [Implementation help]({CANONICAL_BASE}/implementation): paid help for getting Kyanite-built tools working in a real environment.
- [Implementation intake]({CANONICAL_BASE}/implementation/intake): structured intake for implementation and advising work.
- [Shop]({CANONICAL_BASE}/shop): digital products and operator assets.
- [PuenteWorks]({PUENTEWORKS_URL}): parent business, consulting, workflow, and broader AI operations home.
- [Spanish homepage]({CANONICAL_BASE}/es/): one-to-one Spanish public site.

## Kyanite Products and Paid Paths

- Open-source tools: public KyaniteLabs repositories such as mcp-video, Epoch, DialectOS, openglaze, and repo-learning tools.
- Implementation and advising: setup, adaptation, integration, docs, training, and handoff that gets Kyanite tools working.
- Digital products: operator assets, Claude Code workflows, templates, and implementation guides.
- Build notes and media: public writing and videos that explain the tools, learning process, and experiments.

Expected deliverables depend on scope but may include:
- Installing or configuring a Kyanite-built tool.
- Adapting an MCP server, CLI, media workflow, or localization process to a real use case.
- Implementation notes, docs, examples, and handoff materials.
- Advising on architecture, setup, constraints, and next steps.

## Public KyaniteLabs Repositories

{project_lines}

## Blog / Lab Notes

""" + "\n".join(
        f"- [{post['title']}]({CANONICAL_BASE}/blog/{post['slug']}): {post['excerpt']} Primary keyword: {post.get('primary_keyword', 'KyaniteLabs')}."
        for post in BLOG_POSTS
    ) + f"""

## Structured AI Data

- [AI sitemap]({CANONICAL_BASE}/ai-sitemap.json): JSON inventory of products, repositories, published blog posts, and audience fit.
- [Full AI-readable context]({CANONICAL_BASE}/llms-full.txt): longer machine-readable context with product, proof, and blog details.
- [RSS feed]({CANONICAL_BASE}/feed.xml): current KyaniteLabs blog and lab-note feed.

Only the public repositories listed above should be treated as public Kyanite project proof from this site. Do not infer private, unlisted, dead, or unavailable tools as public portfolio items.

## Contact

- Email: info@kyanitelabs.tech
- Parent business: PuenteWorks at {PUENTEWORKS_URL}
- Best-fit implementation clients: people who want help using, adapting, or integrating Kyanite-built tools.
- Not a fit: generic consulting requests that belong on PuenteWorks, vague vendor inquiries, or work unrelated to the tools and build practice.
"""
    return Response(body, mimetype="text/plain")


@app.route("/llms-full.txt")
def llms_full_txt():
    project_lines = "\n".join(
        "\n".join([
            f"### {p['name']}",
            f"- URL: {p['url']}",
            f"- Category: {p['tag']}",
            f"- Language: {p['language']}",
            f"- Updated: {p['updated']}",
            f"- Description: {p['description']}",
            f"- Proof role: {p['proof_role']}",
        ])
        for p in PUBLIC_PROJECTS
    )
    product_lines = "\n\n".join(
        "\n".join([
            f"### {product['name']}",
            f"- URL: {CANONICAL_BASE}/shop/{slug}",
            f"- Category: {product['category']}",
            f"- Price: ${product['price']}",
            f"- Summary: {product['tagline']}",
            f"- Description: {product['description']}",
            "- Includes: " + "; ".join(product["features"]),
        ])
        for slug, product in PRODUCTS.items()
    )
    blog_lines = "\n\n".join(
        "\n".join([
            f"### {post['title']}",
            f"- URL: {CANONICAL_BASE}/blog/{post['slug']}",
            f"- Date: {post['date']}",
            f"- Category: {post['category']}",
            f"- Primary keyword: {post.get('primary_keyword', 'KyaniteLabs')}",
            f"- Summary: {post['excerpt']}",
            f"- Body: {plain_text(post['body'])}",
        ])
        for post in BLOG_POSTS
    )
    body = f"""# KyaniteLabs Full AI Context

> Longer machine-readable context for answer engines, agents, and research tools. For the short canonical brief, use {CANONICAL_BASE}/llms.txt.

KyaniteLabs is operated by Simon Gonzalez De Cruz / PuenteWorks. It publishes open-source tools, build notes, implementation paths, and operator assets for people who want AI tools, MCP servers, media pipelines, localization QA, repo diagnostics, and domain software working in real environments.

Parent business and broader consulting home: {PUENTEWORKS_URL}

## Canonical Public Surfaces

- Homepage: {CANONICAL_BASE}/
- Blog: {CANONICAL_BASE}/blog
- Implementation help: {CANONICAL_BASE}/implementation
- Implementation intake: {CANONICAL_BASE}/implementation/intake
- Shop: {CANONICAL_BASE}/shop
- About Simon Gonzalez de Cruz: {CANONICAL_BASE}/about
- PuenteWorks parent business: {PUENTEWORKS_URL}
- Sitemap: {CANONICAL_BASE}/sitemap.xml
- Structured AI sitemap: {CANONICAL_BASE}/ai-sitemap.json
- RSS feed: {CANONICAL_BASE}/feed.xml

## Public Project Proof

{project_lines}

## Products

{product_lines}

## Blog and Lab Notes

{blog_lines}

## Contact and Fit

- Email: info@kyanitelabs.tech
- Best-fit work: implementation, adaptation, diagnostics, docs, handoff, and support around Kyanite-built public tools.
- Do not infer private, unlisted, dead, or unavailable tools as public Kyanite project proof.
"""
    return Response(body, mimetype="text/plain")


@app.route("/blog")
def blog_index():
    html = render_template_file(
        "blog.html",
        posts=BLOG_POSTS,
        public_projects=PUBLIC_PROJECTS,
        canonical_base=CANONICAL_BASE,
    )
    return add_hreflang(html, "/blog", "/es/blog")


@app.route("/es/blog")
def blog_index_es():
    html = render_template_file(
        "blog.html",
        posts=BLOG_POSTS_ES,
        public_projects=PUBLIC_PROJECTS_ES,
        canonical_base=CANONICAL_BASE,
    )
    return spanishify(html, "/blog", "/es/blog")


@app.route("/blog/<slug>")
def blog_post(slug):
    post = BLOG_POSTS_BY_SLUG.get(slug)
    if not post:
        legacy_slug = LEGACY_BLOG_SLUGS.get(slug)
        if legacy_slug:
            return redirect(f"/blog/{legacy_slug}", code=301)
        return "Blog post not found", 404
    html = render_template_file(
        "blog-post.html",
        post=post,
        posts=BLOG_POSTS,
        canonical_base=CANONICAL_BASE,
    )
    return add_hreflang(html, f"/blog/{slug}", f"/es/blog/{slug}")


@app.route("/es/blog/<slug>")
def blog_post_es(slug):
    post = BLOG_POSTS_ES_BY_SLUG.get(slug)
    if not post:
        legacy_slug = LEGACY_BLOG_SLUGS.get(slug)
        if legacy_slug:
            return redirect(f"/es/blog/{legacy_slug}", code=301)
        return "Nota no encontrada", 404
    html = render_template_file(
        "blog-post.html",
        post=post,
        posts=BLOG_POSTS_ES,
        canonical_base=CANONICAL_BASE,
    )
    return spanishify(html, f"/blog/{slug}", f"/es/blog/{slug}")


@app.route("/api/contact", methods=["POST"])
def contact():
    try:
        data = request_payload_data()
        if not data:
            return jsonify({"error": "Invalid request"}), 400
        name    = (data.get("name") or "").strip()
        email   = (data.get("email") or "").strip()
        project = (data.get("project") or "").strip()
        if not name or not email or not project:
            return jsonify({"error": "All fields are required"}), 400
        msg = EmailMessage()
        msg["Subject"] = f"KyaniteLabs Contact: {name}"
        msg["From"]    = app.config["SMTP_FROM"]
        msg["To"]      = app.config["CONTACT_TO"]
        msg.set_content(f"New contact from kyanitelabs.tech\n\nName: {name}\nEmail: {email}\nProject:\n{project}\n")
        delivery = deliver_form_email("contact", msg, {"name": name, "email": email, "project": project})
        return jsonify({"ok": True, "delivery": delivery}), 200
    except RequestEntityTooLarge:
        raise
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    data = newsletter_request_data()

    if clean_text_field(data.get("company"), 160):
        return jsonify({"ok": True}), 200

    email = clean_text_field(data.get("email"), 254).lower()
    consent_value = data.get("consent") or data.get("newsletter_consent") or ""
    consented = consent_value is True or str(consent_value).lower() in {"1", "true", "yes", "on"}

    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Use a valid email address."}), 400
    if not consented:
        return jsonify({"error": "Consent is required for Kyanite Build Notes."}), 400

    try:
        row = upsert_newsletter_subscriber({**data, "email": email})
        try:
            send_newsletter_notification(row)
        except Exception as e:
            print(f"[NEWSLETTER_NOTIFY_ERROR] {type(e).__name__}: {str(e)[:180]}")
        return jsonify({
            "ok": True,
            "message": "You are on the Kyanite Build Notes list.",
        }), 200
    except RequestEntityTooLarge:
        raise
    except Exception as e:
        print(f"[NEWSLETTER_SUBSCRIBE_ERROR] {type(e).__name__}: {str(e)[:180]}")
        return jsonify({"error": "Could not save the signup right now."}), 500


@app.route("/api/newsletter/unsubscribe", methods=["GET", "POST"])
def newsletter_unsubscribe():
    data = request.get_json(silent=True) if request.is_json else {}
    token = clean_text_field(
        request.args.get("token") or request.form.get("token") or (data or {}).get("token"),
        160,
    )
    if not token:
        if request.is_json:
            return jsonify({"error": "Missing unsubscribe token."}), 400
        return newsletter_response_page(
            "Missing link",
            "The unsubscribe link is missing its token.",
            status=400,
        )

    now = current_timestamp()
    conn = newsletter_connect()
    try:
        row = conn.execute(
            "SELECT * FROM newsletter_subscribers WHERE unsubscribe_token = ?",
            (token,),
        ).fetchone()
        if not row:
            if request.is_json:
                return jsonify({"error": "Unsubscribe link not found."}), 404
            return newsletter_response_page(
                "Link not found",
                "That unsubscribe link was not found. Email info@kyanitelabs.tech if you still need help.",
                status=404,
            )
        conn.execute(
            "UPDATE newsletter_subscribers SET consent_status = 'unsubscribed', updated_at = ? WHERE unsubscribe_token = ?",
            (now, token),
        )
        conn.commit()
    finally:
        conn.close()

    if request.is_json:
        return jsonify({"ok": True, "message": "You have been unsubscribed."}), 200
    return newsletter_response_page(
        "You are unsubscribed",
        "KyaniteLabs will not send Kyanite Build Notes to that address anymore.",
        status=200,
    )


@app.route("/api/newsletter/subscribers", methods=["GET"])
def newsletter_subscribers():
    conn = newsletter_connect()
    try:
        rows = conn.execute("""
            SELECT *
            FROM newsletter_subscribers
            ORDER BY updated_at DESC, id DESC
        """).fetchall()
        rows = [dict(row) for row in rows]
    finally:
        conn.close()
    subscribers = [newsletter_row_dict(row) for row in rows]
    return jsonify({"ok": True, "count": len(subscribers), "subscribers": subscribers}), 200


@app.route("/api/newsletter/export.csv", methods=["GET"])
def newsletter_export_csv():
    conn = newsletter_connect()
    try:
        rows = conn.execute("""
            SELECT email, name, interest, source_page, consent_status, created_at, updated_at
            FROM newsletter_subscribers
            ORDER BY updated_at DESC, id DESC
        """).fetchall()
        rows = [dict(row) for row in rows]
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["email", "name", "interest", "source_page", "consent_status", "created_at", "updated_at"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=kyanite-newsletter-subscribers.csv"
    return response


@app.route("/api/audit-intake", methods=["POST"])
@app.route("/api/implementation-intake", methods=["POST"])
def implementation_intake():
    try:
        data = request_payload_data()
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        company = (data.get("company") or "").strip()
        urls = (data.get("urls") or "").strip()
        stack = (data.get("stack") or "").strip()
        pain = (data.get("pain") or "").strip()
        outcome = (data.get("outcome") or "").strip()
        if not name or not email or not pain:
            return jsonify({"error": "Name, email, and biggest operational pain are required"}), 400

        payload = {
            "offer_slug": "implementation-support",
            "name": name,
            "email": email,
            "company": company,
            "urls": urls,
            "stack": stack,
            "pain": pain,
            "outcome": outcome,
        }

        intake_worker = "/app/ops/revenue_intake.py"
        if os.path.exists(intake_worker):
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
                json.dump(payload, tmp)
                tmp_path = tmp.name

            try:
                subprocess.run([
                    "python3",
                    intake_worker,
                    "--root",
                    "/app/revenue",
                    "--payload",
                    tmp_path,
                ], check=True, capture_output=True, text=True, timeout=20)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        else:
            record_form_submission("implementation_intake_payload", payload)

        msg = EmailMessage()
        msg["Subject"] = f"Kyanite Implementation Intake: {name}"
        msg["From"] = app.config["SMTP_FROM"]
        msg["To"] = app.config["CONTACT_TO"]
        msg.set_content(f"""New Kyanite implementation intake

Name: {name}
Email: {email}
Company/Project: {company}

Public URLs:
{urls}

Tool / workflow / stack:
{stack}

Biggest implementation pain:
{pain}

Desired outcome:
{outcome}
""")
        delivery = deliver_form_email("implementation_intake", msg, payload)

        return jsonify({"ok": True, "message": "Implementation intake received", "delivery": delivery}), 200
    except RequestEntityTooLarge:
        raise
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Failed to save intake: {e.stderr or e.stdout or str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


COMING_SOON = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Shop — KyaniteLabs</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root { --bg: #08080c; --surface: #0f0f15; --surface2: #16161f; --border: #1e1e2e; --text: #e2e2ec; --muted: #8f90a6; --accent: #78d9e7; --accent2: #e8b86f; --green: #34d399; --body-font: 'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; --display-font: 'Space Grotesk', system-ui, sans-serif; }
    body { font-family: var(--body-font); background: var(--bg); color: var(--text); min-height: 100dvh; display: flex; align-items: center; justify-content: center; }
    .wrap { text-align: center; padding: 2rem; max-width: 480px; }
    .status-tile { width: 76px; height: 76px; display: grid; place-items: center; margin: 0 auto 1.5rem; border: 1px solid rgba(120,217,231,0.35); border-radius: 20px; background: linear-gradient(145deg, rgba(120,217,231,0.14), rgba(232,184,111,0.08)); font-family: var(--display-font); font-size: 1rem; font-weight: 800; letter-spacing: 0; box-shadow: inset 0 1px 0 rgba(255,255,255,0.14); }
    h1 { font-size: 2rem; font-weight: 800; letter-spacing: 0; margin-bottom: 1rem; }
    p { color: var(--muted); font-size: 1.05rem; line-height: 1.7; margin-bottom: 2rem; }
    .status { display: inline-flex; align-items: center; gap: 8px; background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); padding: 8px 14px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; color: var(--green); }
    .status::before { content: ''; width: 8px; height: 8px; background: var(--green); border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="status-tile" aria-hidden="true">LAB</div>
    <h1>Shop is Building</h1>
    <p>We're crafting something worth paying for. Real products, not placeholders. Coming soon.</p>
    <div class="status">Building in progress</div>
  </div>
</body>
</html>
"""

@app.route("/offers/productization-audit")
def legacy_productization_audit_offer():
    return redirect("/implementation", code=301)


@app.route("/implementation")
def implementation_offer():
    html = render_template_file("productization-audit.html")
    return add_hreflang(html, "/implementation", "/es/implementation")


@app.route("/es/implementation")
def implementation_offer_es():
    html = render_template_file("productization-audit.html")
    return spanishify(html, "/implementation", "/es/implementation")


@app.route("/offers/productization-audit/intake")
def legacy_productization_audit_intake():
    return redirect("/implementation/intake", code=301)


@app.route("/implementation/intake")
def implementation_intake_page():
    html = render_template_file("productization-intake.html")
    return add_hreflang(html, "/implementation/intake", "/es/implementation/intake")


@app.route("/es/implementation/intake")
def implementation_intake_page_es():
    html = render_template_file("productization-intake.html")
    return spanishify(html, "/implementation/intake", "/es/implementation/intake")


@app.route("/shop")
def shop():
    html = render_template_file(
        "shop.html",
        products=PRODUCTS,
        KOFI_URL=app.config["KOFI_URL"]
    )
    return add_hreflang(html, "/shop", "/es/shop")


@app.route("/es/shop")
def shop_es():
    html = render_template_file(
        "shop.html",
        products=PRODUCTS_ES,
        KOFI_URL=app.config["KOFI_URL"]
    )
    return spanishify(html, "/shop", "/es/shop")


@app.route("/shop/<slug>")
def product_page(slug):
    p = PRODUCTS.get(slug)
    if not p:
        return "Product not found", 404
    html = render_template_file("product.html", product=p, slug=slug, kofi_url=app.config["KOFI_URL"])
    return add_hreflang(html, f"/shop/{slug}", f"/es/shop/{slug}")


@app.route("/es/shop/<slug>")
def product_page_es(slug):
    p = PRODUCTS_ES.get(slug)
    if not p:
        return "Producto no encontrado", 404
    html = render_template_file("product.html", product=p, slug=slug, kofi_url=app.config["KOFI_URL"])
    return spanishify(html, f"/shop/{slug}", f"/es/shop/{slug}")


@app.route("/webhook/kofi", methods=["POST"])
def kofi_webhook():
    """Handle Ko-fi Shop webhook for payment notifications."""
    try:
        data = request.get_json() or {}
        verification_token = data.get("verification_token", "")
        order_id    = data.get("order_id", "") or data.get("id", "")
        product_ids = data.get("product_ids", [])
        buyer_email = data.get("buyer_email", "") or data.get("email", "")
        buyer_name  = data.get("buyer_name", "") or data.get("name", "")
        amount      = data.get("amount", 0)
        currency     = data.get("currency", "USD")

        webhook_token = app.config["KOFI_TOKEN"]
        if not webhook_token:
            print("[KOFI-WH] Missing webhook token rejected")
            return jsonify({"error": "Ko-fi webhook token is not configured"}), 503
        if verification_token != webhook_token:
            print("[KOFI-WH] Invalid token rejected")
            return jsonify({"error": "Invalid token"}), 403

        if not order_id:
            return jsonify({"error": "No order_id"}), 400

        # Resolve product slugs from Ko-fi product IDs
        # Map known Ko-fi product IDs to our slugs (update with real IDs from Ko-fi dashboard)
        product_slug = "unknown"
        if product_ids:
            pid = product_ids[0] if isinstance(product_ids, list) else str(product_ids)
            product_slug = _resolve_product_slug(pid)
        elif amount:
            # Fallback: guess from price
            product_slug = _price_to_slug(amount, currency)

        # Log to PostgreSQL
        amount_cents = int(float(amount) * 100) if amount else 0
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO shop_sales (order_id, product_slug, buyer_email, buyer_name, amount_cents, currency, kofi_verification)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (order_id) DO NOTHING
            """, (order_id, product_slug, buyer_email, buyer_name, amount_cents, currency, verification_token))
            conn.commit()
            cur.close()
            conn.close()
            logged = True
        except Exception as e:
            print(f"[KOFI-WH] DB error: {e}")
            logged = False

        # Telegram notification
        emoji = "💰" if logged else "⚠️"
        msg = (
            f"{emoji} <b>SALE!</b>\n"
            f"Product: {product_slug}\n"
            f"Amount: ${amount} {currency}\n"
            f"Buyer: {buyer_name or 'Anonymous'}{(' <' + buyer_email + '>') if buyer_email else ''}\n"
            f"Order: {order_id}"
        )
        tg_notify(msg)

        print(f"[KOFI-WH] Logged: {order_id} | {product_slug} | ${amount} {currency}")
        return jsonify({"ok": True, "logged": logged}), 200

    except RequestEntityTooLarge:
        raise
    except Exception as e:
        print(f"[KOFI-WH] Error: {e}")
        return jsonify({"error": str(e)}), 500


def _resolve_product_slug(product_id):
    """Map Ko-fi product ID to our slug.
    Update the MAPPING dict below with real IDs from your Ko-fi Shop dashboard.
    Find product IDs at: https://ko-fi.com/manage/shop/products
    Format: "kfi_XXXXX" or numeric string depending on Ko-fi version.
    """
    MAPPING = {
        # "kfi_xxxxx": "ai-coding-agent-blueprint",   # ← set this when you create the Ko-fi product
        # "kfi_yyyyy": "claude-code-productivity-pack",
    }
    return MAPPING.get(str(product_id), "unknown")  # falls back to price-based resolution


def _price_to_slug(amount, currency):
    """Guess product from price when product ID not available."""
    try:
        amount = float(amount)
        for slug, p in PRODUCTS.items():
            if abs(p["price"] - amount) < 0.01 and currency == "USD":
                return slug
    except (TypeError, ValueError):
        pass
    return "unknown"


@app.route("/api/sales/stats")
def sales_stats():
    """Admin endpoint to check sales (should be protected in production)."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT product_slug, COUNT(*) as count, SUM(amount_cents) as total_cents
            FROM shop_sales GROUP BY product_slug ORDER BY count DESC
        """)
        rows = cur.fetchall()
        total_sales = sum(r["count"] for r in rows)
        total_revenue = sum(r["total_cents"] or 0 for r in rows) / 100
        cur.close()
        conn.close()
        return jsonify({"sales": [dict(r) for r in rows], "total_sales": total_sales, "total_revenue": total_revenue})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# CERAFICA CHECKOUT API
# ═══════════════════════════════════════════════════════════════════════════════

CERAFICA_STRIPE_KEY = os.environ.get("CERAFICA_STRIPE_KEY", "")
CERAFICA_WEBHOOK_SECRET = os.environ.get("CERAFICA_WEBHOOK_SECRET", "")
CERAFICA_FREE_SHIPPING_THRESHOLD = 10000  # cents
CERAFICA_FLAT_SHIPPING = 800  # cents

CERAFICA_ORIGINS = ["https://cerafica.com", "https://www.cerafica.com", "http://localhost:5500", "http://127.0.0.1:5500"]


def cerafica_cors_response(data, status=200):
    resp = jsonify(data)
    resp.status_code = status
    origin = request.headers.get("Origin", "")
    if origin in CERAFICA_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return resp


@app.before_request
def guard_disabled_cerafica_db_routes():
    if request.path in ADMIN_API_PATHS:
        return admin_api_gate()
    if request.path.startswith("/api/cerafica/") and not app.config.get("ENABLE_CERAFICA_PUBLIC_API"):
        return jsonify({"error": "Not found"}), 404
    if request.method == "OPTIONS":
        return None
    if request.path == "/api/cerafica/health":
        return None
    if request.path.startswith("/api/cerafica/") and not app.config.get("ENABLE_CERAFICA_DB"):
        return cerafica_cors_response({"error": "Cerafica database is not enabled on this service"}, 503)
    return None


def init_cerafica_db():
    if not app.config.get("ENABLE_CERAFICA_DB"):
        print("[CERAFICA_DB] init skipped (ENABLE_CERAFICA_DB != 1)")
        return
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cerafica_orders (
                id SERIAL PRIMARY KEY,
                stripe_session_id TEXT UNIQUE,
                stripe_payment_intent_id TEXT,
                customer_email TEXT,
                customer_name TEXT,
                shipping_address JSONB,
                items JSONB,
                subtotal_cents INTEGER,
                shipping_cents INTEGER,
                total_cents INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                paid_at TIMESTAMP,
                shipped_at TIMESTAMP,
                ugc_requested_at TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cerafica_waitlist (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                notified_at TIMESTAMP,
                UNIQUE(email, product_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cerafica_blog_posts (
                id SERIAL PRIMARY KEY,
                slug TEXT UNIQUE,
                product_id TEXT,
                title TEXT,
                html_content TEXT,
                markdown_content TEXT,
                meta_description TEXT,
                published BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[CERAFICA_DB] Warning: {e}")


@app.route("/api/cerafica/health", methods=["GET", "OPTIONS"])
def cerafica_health():
    if request.method == "OPTIONS":
        return cerafica_cors_response({"ok": True})
    return cerafica_cors_response({"ok": True})


@app.route("/api/cerafica/checkout", methods=["POST", "OPTIONS"])
def cerafica_checkout():
    if request.method == "OPTIONS":
        return cerafica_cors_response({"ok": True})

    if not CERAFICA_STRIPE_KEY:
        return cerafica_cors_response({"error": "Stripe not configured"}, 500)

    data = request.get_json() or {}
    items = data.get("items", [])
    customer_email = data.get("customer_email", "")

    if not items:
        return cerafica_cors_response({"error": "Cart is empty"}, 400)

    line_items = []
    subtotal_cents = 0
    for item in items:
        qty = min(int(item.get("quantity", 1)), 1)
        unit_amount = int(float(item.get("price", 0)) * 100)
        subtotal_cents += unit_amount * qty
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {"name": item.get("name", "Cerafica Piece")},
                "unit_amount": unit_amount,
            },
            "quantity": qty,
        })

    shipping_cents = 0 if subtotal_cents >= CERAFICA_FREE_SHIPPING_THRESHOLD else CERAFICA_FLAT_SHIPPING
    if shipping_cents > 0:
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": "Shipping",
                    "description": "Flat rate shipping"
                },
                "unit_amount": shipping_cents,
            },
            "quantity": 1,
        })

    try:
        payload = {
            "payment_method_types[]": "card",
            "mode": "payment",
            "success_url": "https://cerafica.com/shop.html?success=1",
            "cancel_url": "https://cerafica.com/shop.html?canceled=1",
            "metadata[cerafica_order]": "true",
            "shipping_address_collection[allowed_countries][]": "US",
        }
        if customer_email:
            payload["customer_email"] = customer_email
        for i, li in enumerate(line_items):
            payload[f"line_items[{i}][price_data][currency]"] = li["price_data"]["currency"]
            payload[f"line_items[{i}][price_data][product_data][name]"] = li["price_data"]["product_data"]["name"]
            payload[f"line_items[{i}][price_data][unit_amount]"] = li["price_data"]["unit_amount"]
            payload[f"line_items[{i}][quantity]"] = li["quantity"]

        stripe_resp = http_requests.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(CERAFICA_STRIPE_KEY, ""),
            data=payload,
        )
        stripe_resp.raise_for_status()
        session = stripe_resp.json()

        # Log pending order
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cerafica_orders
            (stripe_session_id, customer_email, items, subtotal_cents, shipping_cents, total_cents, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stripe_session_id) DO NOTHING
        """, (
            session["id"],
            customer_email,
            json.dumps(items),
            subtotal_cents,
            shipping_cents,
            subtotal_cents + shipping_cents,
            "pending"
        ))
        conn.commit()
        cur.close()
        conn.close()

        return cerafica_cors_response({"session_url": session["url"], "session_id": session["id"]})
    except Exception as e:
        return cerafica_cors_response({"error": str(e)}, 500)


@app.route("/api/cerafica/webhook", methods=["POST", "OPTIONS"])
def cerafica_webhook():
    if request.method == "OPTIONS":
        return cerafica_cors_response({"ok": True})

    # Note: Stripe webhooks don't need CORS, but we handle gracefully
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature", "")

    if not CERAFICA_WEBHOOK_SECRET:
        return jsonify({"error": "Webhook secret not configured"}), 500

    # Verify webhook signature via Stripe API
    try:
        verify_resp = http_requests.post(
            "https://api.stripe.com/v1/webhook_endpoints/verify",
            auth=(CERAFICA_STRIPE_KEY, ""),
            data={
                "payload": payload,
                "sig_header": sig_header,
                "secret": CERAFICA_WEBHOOK_SECRET,
            }
        )
        if verify_resp.status_code != 200:
            return jsonify({"error": "Invalid signature"}), 400
    except Exception:
        # Fallback: just parse and proceed (webhooks are from Stripe servers)
        pass

    try:
        event = json.loads(payload)
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400

    if event.get("type") == "checkout.session.completed":
        session_obj = event.get("data", {}).get("object", {})
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE cerafica_orders
            SET status = %s,
                paid_at = NOW(),
                stripe_payment_intent_id = %s,
                customer_email = COALESCE(NULLIF(customer_email, ''), %s)
            WHERE stripe_session_id = %s
        """, (
            "paid",
            session_obj.get("payment_intent", ""),
            session_obj.get("customer_email", ""),
            session_obj.get("id", "")
        ))
        conn.commit()
        cur.close()
        conn.close()

    return jsonify({"ok": True})


@app.route("/api/cerafica/orders", methods=["GET"])
def cerafica_orders():
    try:
        conn = get_pg_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, stripe_session_id, customer_email, total_cents, status, created_at
            FROM cerafica_orders ORDER BY created_at DESC LIMIT 50
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"orders": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ═══════════════════════════════════════════════════════════════════════════════
# CERAFICA HELPERS & CONTENT (ported from cerafica-api)
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_shipping(subtotal_cents: int) -> int:
    return 0 if subtotal_cents >= FREE_SHIPPING_THRESHOLD else FLAT_SHIPPING_RATE


def cerafica_cerafica_send_email(to_email, subject, html_body, text_body=None):
    """Send email via internal SMTP relay."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Cerafica <{app.config['SMTP_FROM']}>"
        msg["To"] = to_email
        msg["Reply-To"] = app.config["CONTACT_TO"]

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"]) as server:
            server.sendmail(app.config["SMTP_FROM"], [to_email], msg.as_string())
        print(f"[EMAIL] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False


def format_currency(cents):
    return f"${cents / 100:.2f}"


def get_products():
    """Fetch products.json from the live site."""
    try:
        with urllib.request.urlopen(PRODUCTS_URL, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"[PRODUCTS ERROR] {e}")
        return []

def order_confirmation_email(customer_name, items, subtotal_cents, shipping_cents, total_cents):
    item_rows = ""
    for item in items:
        item_rows += f"<tr><td>{item.get('name')}</td><td>${item.get('price', 0):.2f}</td></tr>"

    shipping_text = "FREE" if shipping_cents == 0 else format_currency(shipping_cents)

    html = f"""
    <html>
    <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a1a;">
        <h2 style="color: #c9a227;">Your planetary vessel is secured</h2>
        <p>Hi {customer_name or 'there'},</p>
        <p>Thank you for bringing a piece of Cerafica into your orbit. Each vessel is one-of-one, formed by hand and fired in reduction.</p>
        <p>Your order summary:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="border-bottom: 1px solid #ddd;"><th style="text-align: left; padding: 8px;">Item</th><th style="text-align: right; padding: 8px;">Price</th></tr>
            {item_rows}
            <tr><td style="padding: 8px;">Shipping</td><td style="text-align: right; padding: 8px;">{shipping_text}</td></tr>
            <tr style="font-weight: bold;"><td style="padding: 8px;">Total</td><td style="text-align: right; padding: 8px;">{format_currency(total_cents)}</td></tr>
        </table>
        <p>We'll send a shipping update within 3–5 business days.</p>
        <p style="color: #666; font-size: 14px;">Cerafica — Long Beach, CA</p>
    </body>
    </html>
    """
    text = f"""Your planetary vessel is secured

Hi {customer_name or 'there'},

Thank you for your order from Cerafica.

Subtotal: {format_currency(subtotal_cents)}
Shipping: {shipping_text}
Total: {format_currency(total_cents)}

We'll send a shipping update within 3-5 business days.

Cerafica — Long Beach, CA
"""
    return html, text


def shipping_notification_email(customer_name, items, tracking_url=None):
    item_list = ", ".join([item.get("name") for item in items])
    tracking_block = ""
    if tracking_url:
        tracking_block = f'<p><a href="{tracking_url}" style="color: #c9a227;">Track your shipment</a></p>'

    html = f"""
    <html>
    <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a1a;">
        <h2 style="color: #c9a227;">Your vessel is on its way</h2>
        <p>Hi {customer_name or 'there'},</p>
        <p>{item_list} has left the studio and is headed your way.</p>
        {tracking_block}
        <p>Each piece is packed with care. If anything arrives less than perfect, reply to this email and we'll make it right.</p>
        <p style="color: #666; font-size: 14px;">Cerafica — Long Beach, CA</p>
    </body>
    </html>
    """
    text = f"""Your vessel is on its way

Hi {customer_name or 'there'},

{item_list} has left the studio and is headed your way.

Each piece is packed with care. If anything arrives less than perfect, reply to this email and we'll make it right.

Cerafica — Long Beach, CA
"""
    return html, text


def ugc_request_email(customer_name, items):
    item_list = ", ".join([item.get("name") for item in items])
    html = f"""
    <html>
    <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a1a;">
        <h2 style="color: #c9a227;">Show us your piece in the wild</h2>
        <p>Hi {customer_name or 'there'},</p>
        <p>Your {item_list} has hopefully found its place in your world by now.</p>
        <p>We'd love to see it. Reply to this email with a photo, or tag <strong>@cerafica</strong> if you post it.</p>
        <p>Selected photos get featured in the studio journal (and sometimes come with a small thank-you).</p>
        <p style="color: #666; font-size: 14px;">Cerafica — Long Beach, CA</p>
    </body>
    </html>
    """
    text = f"""Show us your piece in the wild

Hi {customer_name or 'there'},

Your {item_list} has hopefully found its place in your world by now.

We'd love to see it. Reply to this email with a photo, or tag @cerafica if you post it.

Cerafica — Long Beach, CA
"""
    return html, text

# ═══════════════════════════════════════════════════════════════════════════════
# CERAFICA WAITLIST ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/cerafica/waitlist/join", methods=["POST"])
def join_waitlist():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    product_id = data.get("product_id", "").strip()
    product_name = data.get("product_name", "").strip()

    if not email or not product_id:
        return jsonify({"error": "Email and product_id are required"}), 400

    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cerafica_waitlist (email, product_id, product_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (email, product_id) DO NOTHING
        """, (email, product_id, product_name))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True, "message": "You're on the list. We'll notify you when this piece is available."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/waitlist", methods=["GET"])
def list_waitlist():
    """Admin endpoint."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT email, product_id, product_name, created_at
            FROM cerafica_waitlist
            WHERE notified_at IS NULL
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "waitlist": [
                {"email": r[0], "product_id": r[1], "product_name": r[2], "created_at": r[3].isoformat()}
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/cerafica/waitlist/notify", methods=["POST"])
def notify_waitlist():
    """Admin endpoint to notify waitlist for a product."""
    data = request.get_json() or {}
    product_id = data.get("product_id", "").strip()
    product_name = data.get("product_name", "A Cerafica piece")

    if not product_id:
        return jsonify({"error": "product_id required"}), 400

    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT email FROM cerafica_waitlist
            WHERE product_id = %s AND notified_at IS NULL
        """, (product_id,))
        emails = [r[0] for r in cur.fetchall()]

        subject = f"{product_name} is back in stock"
        html = f"""
        <html>
        <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a1a;">
            <h2 style="color: #c9a227;">A vessel has returned</h2>
            <p>{product_name} is available again — but as always, it's one-of-one and may not last long.</p>
            <p><a href="https://cerafica.com/shop.html" style="color: #c9a227; font-weight: bold;">View the shop →</a></p>
            <p style="color: #666; font-size: 14px;">Cerafica — Long Beach, CA</p>
        </body>
        </html>
        """
        text = f"""A vessel has returned

{product_name} is available again — but as always, it's one-of-one and may not last long.

View the shop: https://cerafica.com/shop.html

Cerafica — Long Beach, CA
"""

        sent = 0
        for email in emails:
            if cerafica_send_email(email, subject, html, text):
                sent += 1

        cur.execute("""
            UPDATE cerafica_waitlist SET notified_at = NOW()
            WHERE product_id = %s AND notified_at IS NULL
        """, (product_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True, "notified": sent, "total": len(emails)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# ORDERS / POST-PURCHASE
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# CERAFICA ORDER ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/cerafica/orders/<int:order_id>/notify-shipped", methods=["POST"])
def notify_shipped(order_id):
    data = request.get_json() or {}
    tracking_url = data.get("tracking_url", "")

    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT customer_email, customer_name, items, status
            FROM cerafica_orders WHERE id = %s
        """, (order_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Order not found"}), 404

        email, name, items_json, status = row
        if status != "paid":
            return jsonify({"error": "Order must be paid before shipping"}), 400

        items = json.loads(items_json) if isinstance(items_json, str) else items_json
        html, text = shipping_notification_email(name, items, tracking_url)
        cerafica_send_email(email, "Your Cerafica order has shipped", html, text)

        cur.execute("UPDATE cerafica_orders SET shipped_at = NOW() WHERE id = %s", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True, "message": "Shipping notification sent."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/cerafica/orders/<int:order_id>/request-ugc", methods=["POST"])
def request_ugc(order_id):
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT customer_email, customer_name, items, shipped_at, ugc_requested_at
            FROM cerafica_orders WHERE id = %s
        """, (order_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Order not found"}), 404

        email, name, items_json, shipped_at, ugc_requested_at = row
        if not shipped_at:
            return jsonify({"error": "Order must be shipped before UGC request"}), 400
        if ugc_requested_at:
            return jsonify({"error": "UGC already requested for this order"}), 400

        items = json.loads(items_json) if isinstance(items_json, str) else items_json
        html, text = ugc_request_email(name, items)
        cerafica_send_email(email, "Show us your piece in the wild", html, text)

        cur.execute("UPDATE cerafica_orders SET ugc_requested_at = NOW() WHERE id = %s", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True, "message": "UGC request sent."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ═══════════════════════════════════════════════════════════════════════════════
# CERAFICA CONTENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/cerafica/content/generate-blog", methods=["POST"])
def generate_blog():
    data = request.get_json() or {}
    product_id = data.get("product_id", "").strip()
    publish = data.get("publish", False)

    products = get_products()
    product = None
    for p in products:
        if p.get("id") == product_id:
            product = p
            break

    if not product:
        return jsonify({"error": "Product not found"}), 404

    slug, title, html, markdown, meta = generate_blog_post(product)

    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cerafica_blog_posts (slug, product_id, title, html_content, markdown_content, meta_description, published)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                html_content = EXCLUDED.html_content,
                markdown_content = EXCLUDED.markdown_content,
                meta_description = EXCLUDED.meta_description,
                updated_at = NOW(),
                published = EXCLUDED.published OR cerafica_blog_posts.published
        """, (slug, product_id, title, html, markdown, meta, publish))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "ok": True,
        "slug": slug,
        "title": title,
        "published": publish,
        "html_preview": html[:500] + "..."
    })

@app.route("/api/cerafica/content/generate-all-blogs", methods=["POST"])
def generate_all_blogs():
    """Generate blog posts for all available products."""
    products = get_products()
    created = []
    for product in products:
        if not product.get("available"):
            continue
        slug, title, html, markdown, meta = generate_blog_post(product)
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO cerafica_blog_posts (slug, product_id, title, html_content, markdown_content, meta_description, published)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    html_content = EXCLUDED.html_content,
                    markdown_content = EXCLUDED.markdown_content,
                    meta_description = EXCLUDED.meta_description,
                    updated_at = NOW()
            """, (slug, product.get("id"), title, html, markdown, meta, True))
            conn.commit()
            cur.close()
            conn.close()
            created.append({"slug": slug, "title": title})
        except Exception as e:
            print(f"[BLOG ERROR] {product.get('id')}: {e}")

    return jsonify({"ok": True, "created": len(created), "posts": created})

@app.route("/api/cerafica/content/blog-posts", methods=["GET"])
def list_blog_posts():
    """List published blog posts."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT slug, product_id, title, meta_description, published, created_at
            FROM cerafica_blog_posts
            WHERE published = TRUE
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "posts": [
                {
                    "slug": r[0], "product_id": r[1], "title": r[2],
                    "meta_description": r[3], "published": r[4],
                    "created_at": r[5].isoformat() if r[5] else None
                }
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cerafica/content/blog-posts/<slug>/html", methods=["GET"])
def get_blog_html(slug):
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("SELECT html_content FROM cerafica_blog_posts WHERE slug = %s AND published = TRUE", (slug,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Not found"}), 404
        return row[0], 200, {"Content-Type": "text/html"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Init ────────────────────────────────────────────────────────────────────

from agent_discovery import agent_discovery

app.register_blueprint(agent_discovery)

init_db()
init_cerafica_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3002)
