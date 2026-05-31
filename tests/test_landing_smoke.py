from __future__ import annotations

import contextlib
import io
import json
import re
import unittest

from app import app, TIKTOK_SITE_VERIFICATION_BODY, TIKTOK_SITE_VERIFICATION_FILENAME


class LandingSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()
        self._original_config = {
            "ADMIN_API_TOKEN": app.config.get("ADMIN_API_TOKEN", ""),
            "KOFI_TOKEN": app.config.get("KOFI_TOKEN", ""),
        }

    def tearDown(self) -> None:
        app.config.update(self._original_config)

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
        self.assertIn('aria-label="Open menu"', html)
        self.assertIn("<span></span><span></span></button>", html)

    def test_homepage_images_have_accessible_alt_text(self) -> None:
        html = self.client.get("/").get_data(as_text=True)
        image_tags = re.findall(r"<img\b[^>]*>", html)

        self.assertGreater(len(image_tags), 0)
        for tag in image_tags:
            with self.subTest(tag=tag):
                if 'aria-hidden="true"' in tag:
                    self.assertIn('alt=""', tag)
                else:
                    self.assertRegex(tag, r'\salt="[^"]+"')

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

    def test_public_typography_uses_zoom_safe_scale_and_brand_fonts(self) -> None:
        css = self.client.get("/static/css/kyanite-system.css").get_data(as_text=True)

        self.assertIn("--measure: 66ch", css)
        self.assertIn("font-size: var(--step-0)", css)
        self.assertIn("text-wrap: balance", css)
        self.assertNotRegex(css, re.compile(r"font-size:\s*clamp\([^,]+,\s*[0-9.]+vw"))

        for path in ["/", "/privacy", "/terms"]:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn("Plus+Jakarta+Sans", html)
                self.assertNotIn("font-family: Inter", html)

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

    def test_security_headers_are_sent_on_public_pages(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertIn("https://puenteworks.com", response.headers["Content-Security-Policy"])
        self.assertIn("geolocation=()", response.headers["Permissions-Policy"])

    def test_public_admin_endpoints_fail_closed_without_leaking_runtime_details(self) -> None:
        for path in ["/api/sales/stats", "/api/waitlist"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                body = response.get_data(as_text=True)

                self.assertEqual(response.status_code, 404)
                self.assertNotIn("postgres", body.lower())
                self.assertNotIn("psycopg2", body.lower())
                self.assertNotIn("infra-postgres", body)

        app.config["ADMIN_API_TOKEN"] = "expected-admin-token"
        response = self.client.get("/api/sales/stats")
        self.assertEqual(response.status_code, 403)

    def test_kofi_webhook_requires_configured_secret(self) -> None:
        app.config["KOFI_TOKEN"] = ""

        response = self.client.post(
            "/webhook/kofi",
            json={"verification_token": "", "order_id": "test-order", "amount": "29.00"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("not configured", response.get_json()["error"])

    def test_public_post_payload_size_is_bounded(self) -> None:
        response = self.client.post(
            "/api/contact",
            json={
                "name": "Load Test",
                "email": "load@example.com",
                "project": "x" * 70000,
            },
        )

        self.assertEqual(response.status_code, 413)

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

    def test_docker_runtime_uses_locked_python_requirements(self) -> None:
        with open("Dockerfile", encoding="utf-8") as f:
            dockerfile = f.read()
        with open("requirements.txt", encoding="utf-8") as f:
            requirements = f.read()

        self.assertIn("pip install --no-cache-dir -r requirements.txt", dockerfile)
        for package in ["Flask", "gunicorn", "psycopg2-binary", "requests", "PyYAML"]:
            self.assertRegex(requirements, rf"(?im)^{re.escape(package)}[<>=]")


if __name__ == "__main__":
    unittest.main()
