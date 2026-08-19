from __future__ import annotations

import hashlib
import unittest

from agent_discovery import SKILL_BODY
from app import PUBLIC_PAGE_CACHE, app


class AgentDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        PUBLIC_PAGE_CACHE.clear()
        self.client = app.test_client()

    def test_homepage_advertises_machine_readable_resources(self) -> None:
        links = self.client.get("/").headers.getlist("Link")
        for relation in ("api-catalog", "service-desc", "service-doc", "describedby"):
            self.assertTrue(any(f'rel="{relation}"' in link for link in links), relation)

    def test_markdown_content_negotiation_preserves_html_default(self) -> None:
        html = self.client.get("/")
        markdown = self.client.get("/", headers={"Accept": "text/markdown"})
        self.assertIn("text/html", html.content_type)
        self.assertIn("text/markdown", markdown.content_type)
        self.assertEqual(markdown.headers["Vary"], "Accept")
        self.assertGreater(int(markdown.headers["x-markdown-tokens"]), 0)
        self.assertIn("# KyaniteLabs", markdown.get_data(as_text=True))

    def test_api_catalog_points_to_real_documents(self) -> None:
        response = self.client.get("/.well-known/api-catalog")
        self.assertIn("application/linkset+json", response.content_type)
        self.assertEqual(response.get_json()["linkset"][0]["anchor"], "https://kyanitelabs.tech/api")
        for path in ("/api", "/openapi.json", "/docs/api", "/api/health"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_auth_md_is_truthful_and_does_not_fabricate_oauth(self) -> None:
        auth = self.client.get("/auth.md")
        self.assertIn("# KyaniteLabs auth.md", auth.get_data(as_text=True))
        self.assertIn("does not offer self-service agent registration", auth.get_data(as_text=True))
        self.assertIn("register_uri: https://kyanitelabs.tech/implementation/intake", auth.get_data(as_text=True))
        self.assertEqual(self.client.get("/.well-known/oauth-authorization-server").status_code, 404)
        self.assertEqual(self.client.get("/.well-known/oauth-protected-resource").status_code, 404)

    def test_mcp_card_describes_working_read_only_server(self) -> None:
        card = self.client.get("/.well-known/mcp/server-card.json").get_json()
        self.assertEqual(card["transport"]["endpoint"], "https://kyanitelabs.tech/mcp")
        initialize = self.client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(initialize.get_json()["result"]["serverInfo"]["name"], "KyaniteLabs Public Discovery")
        tools = self.client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(tools.get_json()["result"]["tools"]), 2)

    def test_a2a_card_describes_working_read_only_endpoint(self) -> None:
        card = self.client.get("/.well-known/agent-card.json").get_json()
        self.assertEqual(card["supportedInterfaces"][0]["url"], "https://kyanitelabs.tech/a2a/v1")
        response = self.client.post("/a2a/v1", json={
            "jsonrpc": "2.0",
            "id": "fit-1",
            "method": "SendMessage",
            "params": {"message": {"parts": [{"text": "I need help with an MCP tool."}]}},
        })
        self.assertEqual(response.status_code, 200)
        text = response.get_json()["result"]["message"]["parts"][0]["text"]
        self.assertIn("human must approve", text)
        self.assertIn("No action was taken", text)

    def test_agent_skill_digest_matches_served_artifact(self) -> None:
        index = self.client.get("/.well-known/agent-skills/index.json").get_json()
        artifact = self.client.get("/.well-known/agent-skills/kyanite-public-product-discovery/SKILL.md")
        self.assertEqual(index["skills"][0]["digest"], "sha256:" + hashlib.sha256(artifact.data).hexdigest())
        self.assertEqual(artifact.get_data(as_text=True), SKILL_BODY)

    def test_homepage_registers_webmcp_tools(self) -> None:
        self.assertIn("/static/js/kyanite-webmcp.js", self.client.get("/").get_data(as_text=True))
        response = self.client.get("/static/js/kyanite-webmcp.js")
        script = response.get_data(as_text=True)
        response.close()
        self.assertIn("navigator.modelContext.registerTool", script)
        self.assertIn("AbortController", script)


if __name__ == "__main__":
    unittest.main()
