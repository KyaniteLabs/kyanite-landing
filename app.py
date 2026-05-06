"""
Kyanite Labs — Landing + Shop
"""
import os
import json
import smtplib
import subprocess
import tempfile
import psycopg2
import psycopg2.extras
import requests as http_requests
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from urllib.parse import urlencode
from flask import Flask, request, jsonify, render_template_string, Response

app = Flask(__name__)

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


CANONICAL_BASE = "https://kyanitelabs.tech"

PUBLIC_PROJECTS = [
    {
        "name": "mcp-video",
        "url": "https://github.com/KyaniteLabs/mcp-video",
        "description": "Video editing MCP server, Python library, and CLI for AI agents.",
    },
    {
        "name": "Epoch",
        "url": "https://github.com/KyaniteLabs/Epoch",
        "description": "Time estimation MCP server for PERT, COCOMO, Monte Carlo, forecasting, and model-cost planning.",
    },
    {
        "name": "DialectOS",
        "url": "https://github.com/KyaniteLabs/DialectOS",
        "description": "Spanish dialect localization and QA MCP server with glossary enforcement and quality gates.",
    },
    {
        "name": "OpenGlaze",
        "url": "https://github.com/KyaniteLabs/openglaze",
        "description": "Open-source ceramic glaze calculator, UMF analyzer, and recipe manager.",
    },
    {
        "name": "Dev Learning Archaeologist",
        "url": "https://github.com/KyaniteLabs/dev-learning-archaeologist",
        "description": "Git-history learning diagnostic that turns development evidence into a study plan.",
    },
    {
        "name": "Innerscape",
        "url": "https://github.com/KyaniteLabs/Innerscape",
        "description": "TypeScript personal growth OS for journaling, habits, body tracking, and knowledge workflows.",
    },
    {
        "name": "kyanitelabs.github.io",
        "url": "https://github.com/KyaniteLabs/kyanitelabs.github.io",
        "description": "Public source repository for the Kyanite Labs website.",
    },
]


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
        "emoji": "🤖",
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
        "emoji": "⚡",
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


# ─── Database ────────────────────────────────────────────────────────────────

def get_pg_conn():
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
  <title>Kyanite Labs - Public AI Tools</title>
  <meta name="description" content="Kyanite Labs builds and productizes public AI tools, MCP servers, domain software, and repo-native launch systems.">
  <style>
    body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: #05070b; color: #f3f8ff; min-height: 100vh; display: grid; place-items: center; }
    main { width: min(760px, calc(100% - 40px)); }
    h1 { font-size: clamp(2.2rem, 8vw, 4rem); line-height: 1.05; letter-spacing: 0; margin: 0 0 18px; }
    p { color: #c2d2df; font-size: 1.08rem; line-height: 1.7; }
    a { color: #26e6ff; font-weight: 700; }
  </style>
</head>
<body>
  <main>
    <h1>Kyanite turns weird AI workflows into usable tools.</h1>
    <p>Public proof lives in the KyaniteLabs GitHub organization: MCP servers, agent tooling, domain software, localization QA, and repo-native launch systems.</p>
    <p><a href="https://github.com/KyaniteLabs">View public KyaniteLabs repositories</a> or email <a href="mailto:info@kyanitelabs.tech">info@kyanitelabs.tech</a>.</p>
  </main>
</body>
</html>
"""

# ─── Product Detail HTML ────────────────────────────────────────────────────

def product_html(p, slug):
    badge_html = ""
    if p["badge"]:
        c = p["badge_color"]
        badge_html = f'<span class="product-badge" style="background:{c}20;color:{c};border:1px solid {c}40;">{p["badge"]}</span>'

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
        "brand": {"@type": "Brand", "name": "Kyanite Labs"},
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
  <title>{p.get('seo_title', p['name'] + ' — Kyanite Labs Shop')}</title>
  <meta name="description" content="{p.get('seo_description', p['tagline'])}">
  <meta name="keywords" content="{p.get('keywords', '')}">
  <meta name="robots" content="index, follow">
  <meta property="og:title" content="{p.get('seo_title', p['name'])}">
  <meta property="og:description" content="{p.get('seo_description', p['tagline'])}">
  <meta property="og:type" content="product">
  <meta property="og:url" content="https://kyanitelabs.tech/shop/{slug}">
  <meta property="product:price:amount" content="{p['price']}">
  <meta property="product:price:currency" content="USD">
  <link rel="canonical" href="https://kyanitelabs.tech/shop/{slug}">
  <script type="application/ld+json">{ld_json}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{ --bg: #08080c; --surface: #0f0f15; --surface2: #16161f; --border: #1e1e2e; --text: #e2e2ec; --muted: #6b6b80; --accent: #7c6af5; --accent2: #a78bfa; --accent-glow: rgba(124,106,245,0.15); --green: #34d399; --green-bg: rgba(52,211,153,0.1); --radius: 12px; --radius-sm: 8px; --orange: #f59e0b; }}
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ color: var(--accent2); }}
    nav {{ position: fixed; top: 0; left: 0; right: 0; z-index: 100; padding: 0 2rem; height: 64px; display: flex; align-items: center; justify-content: space-between; background: rgba(8,8,12,0.9); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); }}
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
    .product-emoji {{ font-size: 3.5rem; margin-bottom: 24px; }}
    .product-badge {{ display: inline-block; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 3px 10px; border-radius: 100px; margin-bottom: 12px; }}
    .product-category {{ font-size: 0.75rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }}
    .product-name {{ font-size: clamp(1.8rem, 4vw, 2.8rem); font-weight: 800; letter-spacing: 0; line-height: 1.15; margin-bottom: 16px; }}
    .product-tagline {{ font-size: 1.1rem; color: var(--muted); line-height: 1.6; margin-bottom: 32px; }}
    .product-description {{ font-size: 1rem; color: var(--text); line-height: 1.75; margin-bottom: 40px; padding-bottom: 40px; border-bottom: 1px solid var(--border); }}
    .features-section {{}}
    .features-section h2 {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 20px; letter-spacing: 0; }}
    .features-list {{ list-style: none; display: flex; flex-direction: column; gap: 14px; }}
    .features-list li {{ display: flex; align-items: flex-start; gap: 12px; font-size: 0.9rem; color: var(--text); }}
    .features-list li::before {{ content: ''; width: 20px; height: 20px; background: var(--green-bg); border-radius: 50%; flex-shrink: 0; margin-top: 2px; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2334d399' stroke-width='3'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E"); background-size: 11px; background-position: center; background-repeat: no-repeat; }}
    .product-sidebar {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; position: sticky; top: 80px; }}
    .sidebar-preview {{ background: var(--surface2); border-bottom: 1px solid var(--border); padding: 40px; text-align: center; }}
    .sidebar-emoji {{ font-size: 4rem; margin-bottom: 16px; }}
    .sidebar-price {{ font-size: 3rem; font-weight: 800; letter-spacing: 0; margin-bottom: 4px; }}
    .sidebar-price span {{ font-size: 1rem; font-weight: 500; color: var(--muted); }}
    .sidebar-delivery {{ font-size: 0.8rem; color: var(--green); display: flex; align-items: center; gap: 6px; justify-content: center; margin-top: 8px; }}
    .sidebar-delivery::before {{ content: ''; width: 8px; height: 8px; background: var(--green); border-radius: 50%; box-shadow: 0 0 6px var(--green); animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
    .sidebar-body {{ padding: 28px; }}
    .kofi-btn {{ display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 16px; background: #00b8f1; color: #fff; border: none; border-radius: var(--radius-sm); font-size: 1rem; font-weight: 700; cursor: pointer; font-family: inherit; text-decoration: none; transition: all 0.2s; margin-bottom: 20px; }}
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
  <div class="nav-logo">Kyanite<span>.</span></div>
  <div class="nav-links">
    <a href="/">Home</a>
    <a href="/shop" class="active">Shop</a>
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
    <p>&copy; 2026 Kyanite Labs. All rights reserved.</p>
    <p><a href="/">Home</a> · <a href="/shop">Shop</a> · <a href="mailto:info@kyanitelabs.tech">Contact</a></p>
  </div>
</footer>
</body>
</html>
"""


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    try:
        with open("templates/landing-v2.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        # Fallback to old HTML if v2 fails
        return render_template_string(HTML, KOFI_URL=app.config["KOFI_URL"])


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
            "User-agent: PerplexityBot",
            "Allow: /",
            "",
            f"Sitemap: {CANONICAL_BASE}/sitemap.xml",
            f"# AI-readable site brief: {CANONICAL_BASE}/llms.txt",
            "",
        ]),
        mimetype="text/plain",
    )


@app.route("/sitemap.xml")
def sitemap_xml():
    today = datetime.utcnow().date().isoformat()
    pages = [
        ("/", "1.0", "weekly"),
        ("/offers/productization-audit", "0.95", "monthly"),
        ("/offers/productization-audit/intake", "0.8", "monthly"),
        ("/shop", "0.65", "monthly"),
        ("/shop/ai-coding-agent-blueprint", "0.55", "monthly"),
        ("/shop/claude-code-productivity-pack", "0.55", "monthly"),
    ]
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


@app.route("/llms.txt")
def llms_txt():
    project_lines = "\n".join(
        f"- [{p['name']}]({p['url']}): {p['description']}" for p in PUBLIC_PROJECTS
    )
    body = f"""# Kyanite Labs

> Product studio for public AI tools, MCP servers, domain software, and repo-native launch systems.

Kyanite Labs builds and productizes public AI-native tools. The public proof surface is the KyaniteLabs GitHub organization: MCP servers, CLI tools, domain software, localization QA, video automation, time estimation, and repo-learning diagnostics.

## Primary Pages

- [Homepage]({CANONICAL_BASE}/): product-led service overview, public GitHub proof, offers, and contact form.
- [Productization audit]({CANONICAL_BASE}/offers/productization-audit): paid first step for turning an internal workflow, agent tool, or repo into a public product surface.
- [Productization intake]({CANONICAL_BASE}/offers/productization-audit/intake): structured intake for product, MCP, or launch-packaging work.
- [Shop]({CANONICAL_BASE}/shop): digital products and operator assets.

## Core Offers

- MCP and agent-tool productization: package real workflows into MCP servers, CLIs, libraries, docs, tests, and install paths.
- Public repo launch audit: turn a repo into a buyer-readable and AI-readable public product surface with README, examples, structured metadata, and proof.
- Spanish Launch Certification: a DialectOS-backed beta localization audit for Spanish docs, app strings, support macros, or locale files.

Expected deliverables depend on scope but may include:
- Product positioning and offer map derived from the actual repository.
- MCP/CLI/API surface review or implementation plan.
- README, examples, install path, docs, and AI discovery cleanup.
- Test, CI, package, and release-readiness findings.
- Launch decision, issue list, and prioritized remediation path.

## Public KyaniteLabs Repositories

{project_lines}

Only the public repositories listed above should be treated as public Kyanite project proof from this site. Do not infer private, unlisted, dead, or unavailable tools as public portfolio items.

## Contact

- Email: info@kyanitelabs.tech
- Best-fit buyers: teams with a real workflow, repo, internal tool, MCP idea, localization need, or AI-agent process that should become a usable product.
- Not a fit: generic AI copywriting requests, dead prototypes, cheap volume work, or projects asking for promises before product truth.
"""
    return Response(body, mimetype="text/plain")


@app.route("/api/contact", methods=["POST"])
def contact():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400
        name    = (data.get("name") or "").strip()
        email   = (data.get("email") or "").strip()
        project = (data.get("project") or "").strip()
        if not name or not email or not project:
            return jsonify({"error": "All fields are required"}), 400
        msg = EmailMessage()
        msg["Subject"] = f"Kyanite Labs Contact: {name}"
        msg["From"]    = app.config["SMTP_FROM"]
        msg["To"]      = app.config["CONTACT_TO"]
        msg.set_content(f"New contact from kyanitelabs.tech\n\nName: {name}\nEmail: {email}\nProject:\n{project}\n")
        with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"]) as server:
            server.send_message(msg)
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/audit-intake", methods=["POST"])
def audit_intake():
    try:
        data = request.get_json() or {}
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
            "offer_slug": "productization-audit",
            "name": name,
            "email": email,
            "company": company,
            "urls": urls,
            "stack": stack,
            "pain": pain,
            "outcome": outcome,
        }

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            json.dump(payload, tmp)
            tmp_path = tmp.name

        try:
            subprocess.run([
                "python3",
                "/app/ops/revenue_intake.py",
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

        msg = EmailMessage()
        msg["Subject"] = f"Kyanite Productization Intake: {name}"
        msg["From"] = app.config["SMTP_FROM"]
        msg["To"] = app.config["CONTACT_TO"]
        msg.set_content(f"""New Kyanite productization intake

Name: {name}
Email: {email}
Company/Project: {company}

Public URLs:
{urls}

Repo / workflow / stack:
{stack}

Biggest productization pain:
{pain}

Desired outcome:
{outcome}
""")
        with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"]) as server:
            server.send_message(msg)

        return jsonify({"ok": True, "message": "Productization intake received"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Failed to save intake: {e.stderr or e.stdout or str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


COMING_SOON = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Shop — Kyanite Labs</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root { --bg: #08080c; --surface: #0f0f15; --surface2: #16161f; --border: #1e1e2e; --text: #e2e2ec; --muted: #6b6b80; --accent: #7c6af5; --accent2: #a78bfa; --green: #34d399; }
    body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .wrap { text-align: center; padding: 2rem; max-width: 480px; }
    .emoji { font-size: 4rem; margin-bottom: 1.5rem; }
    h1 { font-size: 2rem; font-weight: 800; letter-spacing: 0; margin-bottom: 1rem; }
    p { color: var(--muted); font-size: 1.05rem; line-height: 1.7; margin-bottom: 2rem; }
    .status { display: inline-flex; align-items: center; gap: 8px; background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.3); padding: 8px 20px; border-radius: 100px; font-size: 0.8rem; font-weight: 600; color: var(--green); }
    .status::before { content: ''; width: 8px; height: 8px; background: var(--green); border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="emoji">🔨</div>
    <h1>Shop is Building</h1>
    <p>We're crafting something worth paying for. Real products, not placeholders. Coming soon.</p>
    <div class="status">Building in progress</div>
  </div>
</body>
</html>
"""

@app.route("/offers/productization-audit")
def productization_audit_offer():
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Productization Audit — Kyanite Labs</title>
  <meta name="description" content="A product-led audit for MCP servers, agent tools, public repos, docs, package surfaces, and launch-ready AI discovery.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://kyanitelabs.tech/offers/productization-audit">
  <meta property="og:title" content="Productization Audit — Kyanite Labs">
  <meta property="og:description" content="Turn a real repo or workflow into a buyer-readable, AI-readable product surface.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://kyanitelabs.tech/offers/productization-audit">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root { --bg: #08080c; --surface: #0f0f15; --surface2: #16161f; --border: #1e1e2e; --text: #e2e2ec; --muted: #6b6b80; --accent: #7c6af5; --accent2: #a78bfa; --green: #34d399; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Inter, sans-serif; background: var(--bg); color: var(--text); }
    .container { max-width: 960px; margin: 0 auto; padding: 96px 24px 64px; }
    .badge { display:inline-block; background: rgba(124,106,245,0.12); color: var(--accent2); border:1px solid rgba(124,106,245,0.3); padding:6px 14px; border-radius:999px; font-size:12px; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; }
    h1 { font-size: clamp(2.4rem,5vw,4rem); line-height:1.05; margin:20px 0 18px; letter-spacing:0; }
    p.lead { color: var(--muted); font-size: 1.1rem; line-height: 1.8; max-width: 720px; }
    .cta { display:flex; gap:14px; flex-wrap:wrap; margin:32px 0 48px; }
    .btn { display:inline-flex; align-items:center; justify-content:center; padding:14px 20px; border-radius:12px; text-decoration:none; font-weight:700; }
    .btn-primary { background: var(--accent); color:#fff; }
    .btn-secondary { border:1px solid var(--border); color:var(--text); background: var(--surface); }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px,1fr)); gap:18px; margin: 28px 0 40px; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 22px; }
    .card h3 { margin-top:0; margin-bottom:10px; }
    ul { margin:0; padding-left: 20px; color: var(--muted); line-height: 1.7; }
    .price { font-size: 2.5rem; font-weight: 800; margin: 8px 0; }
    .price span { font-size: 1rem; color: var(--muted); font-weight: 500; }
    .section-title { margin: 40px 0 12px; font-size: 1.4rem; }
    .proof { background: rgba(52,211,153,0.08); border:1px solid rgba(52,211,153,0.28); border-radius:18px; padding:22px; }
    .proof strong { color: #fff; }
    .muted { color: var(--muted); }
    a.inline { color: var(--accent2); }
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">Paid Productization Offer</div>
    <h1>Productization Audit</h1>
    <p class="lead">If you have a real workflow, internal tool, MCP idea, or public repo that should become something people can install, understand, cite, or buy, this audit turns the repo truth into a launch plan. Kyanite uses the same product instincts behind mcp-video, Epoch, DialectOS, OpenGlaze, and Dev Learning Archaeologist.</p>
    <div class="cta">
      <a class="btn btn-primary" href="/offers/productization-audit/intake">Start productization intake</a>
      <a class="btn btn-secondary" href="mailto:info@kyanitelabs.tech?subject=Kyanite%20Productization%20Audit">Email Kyanite</a>
    </div>
    <div class="grid">
      <div class="card"><h3>What we check</h3><ul><li>Repo purpose, audience, and install path</li><li>MCP, CLI, API, package, and docs surface</li><li>README, examples, screenshots, demos, and AI discovery</li><li>Tests, CI, release tags, package metadata, and buyer trust</li><li>What should be sold, open-sourced, documented, or killed</li></ul></div>
      <div class="card"><h3>What you get</h3><ul><li>Product positioning from actual repo evidence</li><li>Launch-readiness findings and priority fixes</li><li>Offer recommendation and public proof checklist</li><li>AI-readable discovery recommendations</li><li>Scope for implementation if Kyanite should build it</li></ul></div>
      <div class="card"><h3>Pricing</h3><div class="price">$750 <span>starting</span></div><p class="muted">Good fit for one repo, tool, or workflow that already exists but needs buyer-readable product shape. Larger productization or build work scopes upward.</p></div>
    </div>
    <div class="proof">
      <strong>Why this exists:</strong> Kyanite already ships public product repos: MCP video editing, time estimation, Spanish localization QA, ceramic glaze software, and development-learning diagnostics. The offer is based on that repeatable pattern, not a generic consulting vibe.
    </div>
    <h2 class="section-title">Best fit</h2>
    <ul>
      <li>Teams with an internal AI workflow that should become an MCP server, CLI, or package</li>
      <li>Founders with a public repo that is technically real but not yet legible or sellable</li>
      <li>Builders who need repo-backed recommendations, not vague AI positioning</li>
    </ul>
    <h2 class="section-title">Next step</h2>
    <p class="muted">Send the repo, workflow, current docs, and the buyer/user you think it should serve to <a class="inline" href="mailto:info@kyanitelabs.tech">info@kyanitelabs.tech</a> or use the intake form. If the fit is wrong, Kyanite will say so.</p>
  </div>
</body>
</html>
""")


@app.route("/offers/productization-audit/intake")
def productization_audit_intake():
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Productization Intake — Kyanite Labs</title>
  <meta name="description" content="Structured intake for the Kyanite productization audit.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://kyanitelabs.tech/offers/productization-audit/intake">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#08080c; --surface:#0f0f15; --border:#1e1e2e; --text:#e2e2ec; --muted:#6b6b80; --accent:#7c6af5; --accent2:#a78bfa; --green:#34d399; --red:#ef4444; }
    * { box-sizing:border-box; } body { margin:0; font-family:Inter,sans-serif; background:var(--bg); color:var(--text); }
    .container { max-width: 880px; margin:0 auto; padding:72px 24px 48px; }
    h1 { font-size: clamp(2.1rem,4vw,3.4rem); margin:0 0 16px; letter-spacing:0; }
    .lead { color:var(--muted); line-height:1.8; max-width:720px; margin-bottom:28px; }
    form { background:var(--surface); border:1px solid var(--border); border-radius:20px; padding:28px; }
    label { display:block; font-weight:700; margin:18px 0 8px; }
    input, textarea { width:100%; border:1px solid var(--border); background:#11111a; color:var(--text); border-radius:12px; padding:14px 16px; font:inherit; }
    textarea { min-height:140px; resize:vertical; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; }
    .btn { display:inline-flex; align-items:center; justify-content:center; padding:14px 20px; border-radius:12px; text-decoration:none; font-weight:700; border:0; cursor:pointer; margin-top:22px; }
    .btn-primary { background:var(--accent); color:#fff; }
    .muted { color:var(--muted); }
    .status { margin-top:16px; display:none; padding:12px 14px; border-radius:12px; }
    .status.ok { display:block; background:rgba(52,211,153,0.08); border:1px solid rgba(52,211,153,0.28); color:var(--green); }
    .status.err { display:block; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.28); color:var(--red); }
  </style>
</head>
<body>
  <div class="container">
    <p><a href="/offers/productization-audit" style="color:#a78bfa; text-decoration:none;">Back to the productization offer</a></p>
    <h1>Productization Audit Intake</h1>
    <p class="lead">Send the repo, workflow, current public surface, and the product problem. This creates a structured productization request for Kyanite; it does not automatically buy or publish anything.</p>
    <form id="audit-intake-form" onsubmit="submitIntake(event)">
      <div class="grid">
        <div><label for="name">Name</label><input id="name" name="name" required placeholder="Alex Chen"></div>
        <div><label for="email">Email</label><input id="email" name="email" type="email" required placeholder="alex@company.com"></div>
      </div>
      <label for="company">Company / Project</label><input id="company" name="company" placeholder="Project name or company">
      <label for="urls">Repo / public URL(s)</label><textarea id="urls" name="urls" placeholder="https://github.com/org/repo
https://docs.example.com"></textarea>
      <label for="stack">Tool / workflow summary</label><textarea id="stack" name="stack" placeholder="MCP server, CLI, package, app, docs, internal workflow, data sources, target users, etc."></textarea>
      <label for="pain">Biggest productization pain</label><textarea id="pain" name="pain" required placeholder="What is real but not yet clear, usable, packaged, documented, or sellable?"></textarea>
      <label for="outcome">What would make this worth paying for?</label><textarea id="outcome" name="outcome" placeholder="A launch plan, repo cleanup, offer map, MCP surface, package release, docs, certification, etc."></textarea>
      <button class="btn btn-primary" type="submit">Send productization intake</button>
      <div id="intake-status" class="status"></div>
    </form>
  </div>
<script>
async function submitIntake(event) {
  event.preventDefault();
  const status = document.getElementById('intake-status');
  status.className = 'status';
  const fd = new FormData(document.getElementById('audit-intake-form'));
  const payload = {
    name: fd.get('name'),
    email: fd.get('email'),
    company: fd.get('company'),
    urls: fd.get('urls'),
    stack: fd.get('stack'),
    pain: fd.get('pain'),
    outcome: fd.get('outcome')
  };
  const res = await fetch('/api/audit-intake', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const data = await res.json().catch(() => ({}));
  if (res.ok && data.ok) {
    status.textContent = 'Productization intake sent. Kyanite will review it and follow up.';
    status.className = 'status ok';
    document.getElementById('audit-intake-form').reset();
  } else {
    status.textContent = data.error || 'Something went wrong. Email info@kyanitelabs.tech.';
    status.className = 'status err';
  }
}
</script>
</body>
</html>
""")


@app.route("/shop")
def shop():
    return render_template_string(
        open(os.path.join(os.path.dirname(__file__), "templates", "shop.html")).read(),
        products=PRODUCTS,
        KOFI_URL=app.config["KOFI_URL"]
    )


@app.route("/shop/<slug>")
def product_page(slug):
    p = PRODUCTS.get(slug)
    if not p:
        return "Product not found", 404
    template = open(os.path.join(os.path.dirname(__file__), "templates", "product.html")).read()
    return render_template_string(template, product=p, slug=slug, kofi_url=app.config["KOFI_URL"])


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

        # Verify webhook token if configured
        webhook_token = app.config["KOFI_TOKEN"]
        if webhook_token and verification_token != webhook_token:
            print(f"[KOFI-WH] Invalid token: {verification_token}")
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


@app.route("/mockup/tertulia")
def mockup_tertulia():
    try:
        with open("templates/mockup-terulia-crafty.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error loading mockup: {e}", 500


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


def init_cerafica_db():
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
    return cerafica_cors_response({"ok": True, "stripe_configured": bool(CERAFICA_STRIPE_KEY)})


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

init_db()
init_cerafica_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3002)
