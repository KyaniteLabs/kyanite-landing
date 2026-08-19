"""Standards-based, public agent discovery surfaces for KyaniteLabs."""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser

from flask import Blueprint, Response, jsonify, request


CANONICAL_BASE = "https://kyanitelabs.tech"
VERSION = "1.0.0"
agent_discovery = Blueprint("agent_discovery", __name__)

SKILL_BODY = """---
name: kyanite-public-product-discovery
description: Discover KyaniteLabs public tools, implementation paths, and machine-readable resources without inferring private or unlisted work.
---

# KyaniteLabs public product discovery

Use this skill to find public KyaniteLabs tools, build notes, and implementation help.

## Workflow

1. Read `https://kyanitelabs.tech/ai-sitemap.json` for the current public inventory.
2. Use only repositories and products listed in that inventory as public proof.
3. Read `https://kyanitelabs.tech/implementation` for supported implementation work.
4. Send a human to `https://kyanitelabs.tech/implementation/intake` when the request needs scoping or approval.

## Boundaries

- Do not infer private, unlisted, dead, or unavailable projects.
- Do not submit forms, purchase products, or claim a delivery commitment without human approval.
- Public discovery does not grant access to administrative APIs or private systems.
"""
SKILL_DIGEST = "sha256:" + hashlib.sha256(SKILL_BODY.encode("utf-8")).hexdigest()

OPENAPI_DOCUMENT = {
    "openapi": "3.1.0",
    "info": {
        "title": "KyaniteLabs Public Website API",
        "version": VERSION,
        "description": "Public discovery, health, contact, newsletter, and implementation-intake endpoints. Administrative APIs are intentionally excluded.",
    },
    "servers": [{"url": CANONICAL_BASE}],
    "paths": {
        "/api": {"get": {"summary": "List public API discovery resources", "responses": {"200": {"description": "Public API index"}}}},
        "/api/health": {"get": {"summary": "Check public site API health", "responses": {"200": {"description": "Service is available"}}}},
        "/ai-sitemap.json": {"get": {"summary": "Read the public KyaniteLabs inventory", "responses": {"200": {"description": "Public projects, products, and pages"}}}},
        "/api/contact": {"post": {
            "summary": "Submit the public contact form",
            "description": "Human approval is required before an agent submits this form.",
            "responses": {"200": {"description": "Message accepted"}, "400": {"description": "Invalid request"}},
        }},
        "/api/newsletter/subscribe": {"post": {
            "summary": "Join Kyanite Build Notes",
            "description": "Requires the subscriber's explicit consent.",
            "responses": {"200": {"description": "Subscription accepted"}, "400": {"description": "Invalid request or missing consent"}},
        }},
        "/api/implementation-intake": {"post": {
            "summary": "Submit an implementation request",
            "description": "Human approval is required before an agent submits this form.",
            "responses": {"200": {"description": "Intake accepted"}, "400": {"description": "Invalid request"}},
        }},
    },
}

MCP_TOOLS = [
    {
        "name": "list_public_resources",
        "description": "List canonical KyaniteLabs public discovery and implementation resources.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "find_implementation_path",
        "description": "Map a stated need to KyaniteLabs public implementation guidance without submitting any form.",
        "inputSchema": {
            "type": "object",
            "properties": {"need": {"type": "string", "minLength": 1, "maxLength": 500}},
            "required": ["need"],
            "additionalProperties": False,
        },
    },
]

AGENT_CARD = {
    "name": "KyaniteLabs Public Product Guide",
    "version": VERSION,
    "description": "A read-only guide to KyaniteLabs public tools, build notes, and implementation paths.",
    "supportedInterfaces": [{
        "url": f"{CANONICAL_BASE}/a2a/v1",
        "protocolBinding": "JSONRPC",
        "protocolVersion": "1.0",
    }],
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "extendedAgentCard": False,
    },
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [
        {
            "id": "public-product-discovery",
            "name": "Public product discovery",
            "description": "Locate KyaniteLabs public tools, repositories, products, and build notes.",
        },
        {
            "id": "implementation-fit-routing",
            "name": "Implementation fit routing",
            "description": "Route a stated need to public implementation guidance without submitting a form.",
        },
    ],
}


class _MarkdownExtractor(HTMLParser):
    """Small, dependency-free HTML-to-readable-Markdown converter."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.suppressed = 0
        self.link_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self.suppressed += 1
            return
        if self.suppressed:
            return
        attrs_map = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "p":
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("_")
        elif tag == "a":
            self.link_stack.append(attrs_map.get("href") or "")
            self.parts.append("[")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self.suppressed = max(0, self.suppressed - 1)
            return
        if self.suppressed:
            return
        if tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("_")
        elif tag == "a" and self.link_stack:
            href = self.link_stack.pop()
            self.parts.append(f"]({href})" if href else "]")
        elif tag in {"p", "section", "article", "header", "footer", "ul", "ol"} or re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.suppressed:
            return
        cleaned = re.sub(r"\s+", " ", data)
        if cleaned.strip():
            self.parts.append(cleaned)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


def html_to_markdown(html: str) -> str:
    parser = _MarkdownExtractor()
    parser.feed(html)
    return parser.markdown()


def _mcp_result(request_id, result):
    return jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})


def _mcp_error(request_id, code: int, message: str):
    return jsonify({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def _a2a_text(message: dict) -> str:
    parts = message.get("parts") or []
    return " ".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()


@agent_discovery.after_app_request
def add_agent_discovery_headers(response: Response):
    if request.path == "/" and 200 <= response.status_code < 400:
        links = (
            '</.well-known/api-catalog>; rel="api-catalog"; type="application/linkset+json"',
            '</openapi.json>; rel="service-desc"; type="application/openapi+json"',
            '</docs/api>; rel="service-doc"; type="text/markdown"',
            '</ai-sitemap.json>; rel="describedby"; type="application/json"',
        )
        existing = response.headers.getlist("Link")
        for link in links:
            if link not in existing:
                response.headers.add("Link", link)

    accepts_markdown = "text/markdown" in request.headers.get("Accept", "").lower()
    if request.method in {"GET", "HEAD"} and accepts_markdown and response.mimetype == "text/html" and response.status_code == 200:
        markdown = html_to_markdown(response.get_data(as_text=True))
        response.set_data("" if request.method == "HEAD" else markdown)
        response.content_type = "text/markdown; charset=utf-8"
        response.headers["x-markdown-tokens"] = str(max(1, round(len(markdown.split()) * 1.3)))
        response.headers["Vary"] = "Accept"
    return response


@agent_discovery.get("/api")
def public_api_index():
    return jsonify({
        "name": "KyaniteLabs Public Website API",
        "version": VERSION,
        "documentation": f"{CANONICAL_BASE}/docs/api",
        "openapi": f"{CANONICAL_BASE}/openapi.json",
        "health": f"{CANONICAL_BASE}/api/health",
        "authentication": "Public discovery endpoints require no authentication. Administrative APIs are not advertised for agent use.",
    })


@agent_discovery.get("/api/health")
def public_api_health():
    return jsonify({"ok": True, "service": "kyanitelabs-public-api", "version": VERSION})


@agent_discovery.get("/openapi.json")
def openapi_json():
    return Response(json.dumps(OPENAPI_DOCUMENT, separators=(",", ":")), content_type="application/openapi+json")


@agent_discovery.get("/docs/api")
def api_docs():
    body = f"""# KyaniteLabs public API

The public API supports machine-readable discovery and human-approved contact, newsletter, and implementation-intake workflows.

- API index: {CANONICAL_BASE}/api
- OpenAPI document: {CANONICAL_BASE}/openapi.json
- Health: {CANONICAL_BASE}/api/health
- Public inventory: {CANONICAL_BASE}/ai-sitemap.json

Agents may read public discovery endpoints without authentication. Do not submit contact, newsletter, intake, purchase, or other state-changing requests without the affected human's explicit approval. Administrative endpoints and private systems are outside this public API.
"""
    return Response(body, content_type="text/markdown; charset=utf-8")


@agent_discovery.get("/.well-known/api-catalog")
def api_catalog():
    catalog = {"linkset": [{
        "anchor": f"{CANONICAL_BASE}/api",
        "service-desc": [{"href": f"{CANONICAL_BASE}/openapi.json", "type": "application/openapi+json"}],
        "service-doc": [{"href": f"{CANONICAL_BASE}/docs/api", "type": "text/markdown"}],
        "status": [{"href": f"{CANONICAL_BASE}/api/health", "type": "application/json"}],
    }]}
    return Response(json.dumps(catalog, separators=(",", ":")), content_type="application/linkset+json")


@agent_discovery.get("/auth.md")
def auth_md():
    body = f"""# KyaniteLabs auth.md

## Agent audience

Agents may read KyaniteLabs public discovery resources, documentation, products, projects, and build notes without credentials.

## Registration and provisioning

KyaniteLabs does not offer self-service agent registration, OAuth client registration, or automatic public credentials. A human may request a scoped integration through the existing implementation intake; approval and any provisioning happen manually.

```yaml
agent_auth:
  skill: human-reviewed-provisioning
  register_uri: https://kyanitelabs.tech/implementation/intake
  registration_method: human-reviewed-request
  identity_types_supported:
    - verified_email
  credential_types_supported:
    - manually_provisioned
```

The affected human must review and submit that request. Agents must not submit it autonomously, and a request does not guarantee approval or credential issuance.

## Credential use

Administrative APIs and private systems are not part of the public agent interface. Do not reuse website, operator, or internal credentials. Public form submissions and purchases require explicit human approval.

For a legitimate integration request, read {CANONICAL_BASE}/implementation, then use the registration URI above or contact info@kyanitelabs.tech. A human will scope any provisioning separately.
"""
    return Response(body, content_type="text/markdown; charset=utf-8")


@agent_discovery.get("/.well-known/mcp/server-card.json")
@agent_discovery.get("/.well-known/mcp.json")
def mcp_server_card():
    return jsonify({
        "serverInfo": {"name": "KyaniteLabs Public Discovery", "version": VERSION},
        "transport": {"type": "streamable-http", "endpoint": f"{CANONICAL_BASE}/mcp"},
        "capabilities": {"tools": {"listChanged": False}, "resources": {}, "prompts": {}},
        "authentication": {"required": False},
    })


@agent_discovery.get("/.well-known/agent-card.json")
def a2a_agent_card():
    return jsonify(AGENT_CARD)


@agent_discovery.post("/a2a/v1")
def a2a_endpoint():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or "id" not in payload:
        return _mcp_error(payload.get("id") if isinstance(payload, dict) else None, -32600, "Invalid Request"), 400
    if payload.get("method") != "SendMessage":
        return _mcp_error(payload.get("id"), -32601, "Method not found")
    message = (payload.get("params") or {}).get("message")
    if not isinstance(message, dict) or not _a2a_text(message):
        return _mcp_error(payload.get("id"), -32602, "Invalid params: message text is required"), 400
    need = _a2a_text(message)[:500]
    return _mcp_result(payload["id"], {
        "message": {
            "messageId": hashlib.sha256(f"{payload['id']}:{need}".encode()).hexdigest()[:24],
            "contextId": message.get("contextId") or hashlib.sha256(need.encode()).hexdigest()[:24],
            "role": "ROLE_AGENT",
            "parts": [{
                "text": (
                    f"Review {CANONICAL_BASE}/ai-sitemap.json for public KyaniteLabs proof and "
                    f"{CANONICAL_BASE}/implementation for fit. A human must approve any submission, purchase, "
                    "credential request, or external action. No action was taken."
                ),
                "mediaType": "text/plain",
            }],
        }
    })


@agent_discovery.get("/mcp")
def mcp_descriptor():
    return jsonify({
        "name": "KyaniteLabs Public Discovery",
        "transport": "streamable-http",
        "protocolVersion": "2025-06-18",
        "methods": ["initialize", "ping", "tools/list", "tools/call"],
    })


@agent_discovery.post("/mcp")
def mcp_endpoint():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or "method" not in payload:
        return _mcp_error(payload.get("id") if isinstance(payload, dict) else None, -32600, "Invalid Request"), 400
    request_id = payload.get("id")
    method = payload["method"]
    params = payload.get("params") or {}
    if method == "initialize":
        return _mcp_result(request_id, {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "KyaniteLabs Public Discovery", "version": VERSION},
            "instructions": "Read-only public discovery. State-changing website actions require human approval.",
        })
    if method == "ping":
        return _mcp_result(request_id, {})
    if method == "tools/list":
        return _mcp_result(request_id, {"tools": MCP_TOOLS})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "list_public_resources":
            text = "\n".join([
                f"Public inventory: {CANONICAL_BASE}/ai-sitemap.json",
                f"Implementation help: {CANONICAL_BASE}/implementation",
                f"Implementation intake: {CANONICAL_BASE}/implementation/intake",
                f"Build notes: {CANONICAL_BASE}/blog",
                f"AI-readable brief: {CANONICAL_BASE}/llms.txt",
            ])
            return _mcp_result(request_id, {"content": [{"type": "text", "text": text}], "isError": False})
        if name == "find_implementation_path" and isinstance(arguments.get("need"), str) and arguments["need"].strip():
            need = arguments["need"].strip()[:500]
            text = (
                f"Need: {need}\nReview {CANONICAL_BASE}/implementation for fit, then have a human approve any submission at "
                f"{CANONICAL_BASE}/implementation/intake. No form was submitted."
            )
            return _mcp_result(request_id, {"content": [{"type": "text", "text": text}], "isError": False})
        return _mcp_error(request_id, -32602, "Invalid tool name or arguments"), 400
    return _mcp_error(request_id, -32601, "Method not found"), 404


@agent_discovery.get("/.well-known/agent-skills/index.json")
def agent_skills_index():
    return jsonify({
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [{
            "name": "kyanite-public-product-discovery",
            "type": "skill-md",
            "description": "Discover KyaniteLabs public tools, implementation paths, and machine-readable resources.",
            "url": f"{CANONICAL_BASE}/.well-known/agent-skills/kyanite-public-product-discovery/SKILL.md",
            "digest": SKILL_DIGEST,
        }],
    })


@agent_discovery.get("/.well-known/agent-skills/kyanite-public-product-discovery/SKILL.md")
def agent_skill_artifact():
    return Response(SKILL_BODY, content_type="text/markdown; charset=utf-8")
