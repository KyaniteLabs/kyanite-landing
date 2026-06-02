from __future__ import annotations

import contextlib
import io
import json
import re
import unittest

from app import (
    BLOG_POSTS,
    INDEXNOW_KEY,
    PRODUCTS,
    TIKTOK_SITE_VERIFICATION_BODY,
    TIKTOK_SITE_VERIFICATION_FILENAME,
    app,
)


class LandingSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()
        self._original_config = {
            "ADMIN_API_TOKEN": app.config.get("ADMIN_API_TOKEN", ""),
            "ENABLE_CERAFICA_DB": app.config.get("ENABLE_CERAFICA_DB", False),
            "ENABLE_CERAFICA_PUBLIC_API": app.config.get("ENABLE_CERAFICA_PUBLIC_API", False),
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
            f"/{INDEXNOW_KEY}.txt",
            "/robots.txt",
            "/sitemap.xml",
            "/llms.txt",
            "/llms-full.txt",
            "/ai-sitemap.json",
            "/feed.xml",
            "/rss.xml",
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
        self.assertIn("/static/brand/kyanite-hero-generated-blended-1672x941.png", html)
        self.assertIn("KyaniteLabs crystalline logo on a dark Voronoi technical field", html)
        self.assertIn("The projects are the proof.", html)
        self.assertIn("Choose the next move.", html)
        self.assertNotIn('id="tools"', html)
        self.assertNotIn("Flagship Proof // mcp-video", html)
        self.assertNotIn("MENU</button>", html)
        self.assertIn('aria-label="Open menu"', html)
        self.assertIn("<span></span><span></span></button>", html)

    def test_public_nav_does_not_point_to_removed_tools_section(self) -> None:
        paths = ["/", "/about", "/implementation", "/implementation/intake", "/blog", "/shop"]
        paths.extend(f"/blog/{post['slug']}" for post in BLOG_POSTS)
        paths.extend(f"/shop/{slug}" for slug in PRODUCTS)

        for path in paths:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertNotIn("#tools", html)

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
        self.assertEqual(self.client.get(f"/{INDEXNOW_KEY}.txt").get_data(as_text=True), INDEXNOW_KEY)

        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("https://kyanitelabs.tech/privacy", sitemap)
        self.assertIn("https://kyanitelabs.tech/terms", sitemap)
        self.assertIn("https://kyanitelabs.tech/llms-full.txt", sitemap)
        self.assertIn("https://kyanitelabs.tech/feed.xml", sitemap)

        robots = self.client.get("/robots.txt").get_data(as_text=True)
        self.assertIn("OAI-SearchBot", robots)
        self.assertIn("https://kyanitelabs.tech/llms-full.txt", robots)
        self.assertIn(f"https://kyanitelabs.tech/{INDEXNOW_KEY}.txt", robots)

        llms_full = self.client.get("/llms-full.txt").get_data(as_text=True)
        self.assertIn("KyaniteLabs Full AI Context", llms_full)
        self.assertIn("checkyourself", llms_full)

        feed = self.client.get("/feed.xml").get_data(as_text=True)
        self.assertIn("<rss version=\"2.0\">", feed)
        self.assertIn("<channel>", feed)

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

    def test_cerafica_api_namespace_is_not_public_by_default(self) -> None:
        app.config["ENABLE_CERAFICA_DB"] = False
        app.config["ENABLE_CERAFICA_PUBLIC_API"] = False

        for path in ["/api/cerafica/health", "/api/cerafica/checkout"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                body = response.get_data(as_text=True).lower()

                self.assertEqual(response.status_code, 404)
                self.assertNotIn("stripe", body)
                self.assertNotIn("postgres", body)
                self.assertNotIn("database is not enabled", body)

    def test_public_copy_avoids_process_leakage(self) -> None:
        paths = [
            "/",
            "/about",
            "/implementation",
            "/implementation/intake",
            "/blog",
            "/shop",
            "/llms.txt",
            "/llms-full.txt",
        ]
        paths.extend(f"/blog/{post['slug']}" for post in BLOG_POSTS)
        paths.extend(f"/shop/{slug}" for slug in PRODUCTS)
        banned_phrases = [
            "legal/payment",
            "technical/product",
            "public proof surface",
            "empty lead-gen",
            "lead-gen theater",
            "strategy theater",
            "one-off chat",
            "structured implementation request",
            "messy truth",
            "messy process",
        ]

        for path in paths:
            with self.subTest(path=path):
                body = self.client.get(path).get_data(as_text=True).lower()
                for phrase in banned_phrases:
                    self.assertNotIn(phrase, body)

    def test_spanish_routes_do_not_leak_replacement_artifacts(self) -> None:
        paths = ["/es/", "/es/about", "/es/implementation", "/es/implementation/intake", "/es/blog", "/es/shop"]

        for path in paths:
            with self.subTest(path=path):
                body = self.client.get(path).get_data(as_text=True)

                self.assertNotIn("Contactoo", body)
                self.assertNotIn("/es/es/", body)
                self.assertNotIn("Herramientas Herramientas", body)

    def test_voronoi_motion_assets_are_wired(self) -> None:
        css = self.client.get("/static/css/kyanite-system.css").get_data(as_text=True)
        homepage = self.client.get("/").get_data(as_text=True)

        self.assertIn("kyanite-voronoi-material-field-1800x1200.webp", css)
        self.assertIn("kyanite-voronoi-material-slab-1600x760.webp", css)
        self.assertIn("kyanite-voronoi-material-proof-2172x724.webp", css)
        self.assertIn("kyanite-voronoi-drift", css)
        self.assertIn("/static/js/kyanite-motion.js", homepage)
        self.assertNotIn("source-map", css)
        self.assertNotIn("source map / public build surface", css)

    def test_unrelated_client_prototypes_are_not_public_kyanite_routes(self) -> None:
        response = self.client.get("/mockup/tertulia")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(any("tertulia" in str(rule).lower() for rule in app.url_map.iter_rules()))

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
