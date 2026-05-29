from __future__ import annotations

import contextlib
import io
import json
import unittest

from app import app, TIKTOK_SITE_VERIFICATION_BODY, TIKTOK_SITE_VERIFICATION_FILENAME


class LandingSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    def test_public_pages_and_static_assets_load(self) -> None:
        paths = [
            "/",
            "/privacy",
            "/terms",
            f"/{TIKTOK_SITE_VERIFICATION_FILENAME}",
            "/sitemap.xml",
            "/static/posthog.js",
            "/static/liminal-sites/liminal-sensorium.css",
            "/static/liminal-sites/liminal-sensorium.js",
            "/static/liminal-sites/liminal-sensorium-config.json",
            "/static/liminal-sites/liminal-sensorium-manifest.json",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_homepage_contains_runtime_and_conversion_contracts(self) -> None:
        html = self.client.get("/").get_data(as_text=True)

        self.assertIn("/static/posthog.js", html)
        self.assertIn("/static/liminal-sites/liminal-sensorium.js", html)
        self.assertIn("/implementation/intake", html)
        self.assertNotIn("MENU</button>", html)
        self.assertIn("&#9776;</button>", html)

    def test_policy_pages_and_discovery_files_keep_expected_content(self) -> None:
        self.assertIn("Privacy Policy", self.client.get("/privacy").get_data(as_text=True))
        self.assertIn("Terms of Service", self.client.get("/terms").get_data(as_text=True))
        self.assertEqual(
            self.client.get(f"/{TIKTOK_SITE_VERIFICATION_FILENAME}").get_data(as_text=True),
            TIKTOK_SITE_VERIFICATION_BODY,
        )

        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("https://kyanitelabs.tech/privacy", sitemap)
        self.assertIn("https://kyanitelabs.tech/terms", sitemap)

    def test_posthog_proxy_and_sensorium_config_keep_privacy_guards(self) -> None:
        posthog_js = self.client.get("/static/posthog.js").get_data(as_text=True)

        self.assertIn("_phIsBot", posthog_js)
        self.assertIn("navigator.sendBeacon", posthog_js)
        self.assertIn("keepalive:true", posthog_js)

        sensorium_css = self.client.get("/static/liminal-sites/liminal-sensorium.css").get_data(as_text=True)
        self.assertIn(":not(.skip-link)", sensorium_css)

        config = json.loads(self.client.get("/static/liminal-sites/liminal-sensorium-config.json").get_data(as_text=True))
        self.assertIs(config["guardrails"]["missionLocked"], True)
        self.assertIn("copy", config["guardrails"]["protectedSurfaces"])
        self.assertIn("layout", config["guardrails"]["protectedSurfaces"])
        self.assertEqual(config["layerConfig"]["runtimeFlags"]["pointerEvents"], "none")

    def test_kofi_webhook_rejects_bad_token_without_logging_secret(self) -> None:
        app.config["KOFI_TOKEN"] = "expected-secret"
        log = io.StringIO()

        with contextlib.redirect_stdout(log):
            response = self.client.post(
                "/webhook/kofi",
                json={"verification_token": "do-not-log-me", "order_id": "test"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("do-not-log-me", log.getvalue())


if __name__ == "__main__":
    unittest.main()
