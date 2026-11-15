"""Source-bound consolidation checks; no external requests or publication."""
import json
import re
import unittest

from app import app, BLOG_POSTS, BLOG_POSTS_BY_SLUG, PUBLIC_PROJECTS


SLUGS = ("play1-numbers", "adversarial-custody-chains", "local-image-stack-measured")


class ResearchConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_exact_research_identity_and_existing_blog_preserved(self):
        self.assertEqual(len(BLOG_POSTS), 32)
        self.assertEqual(len({p["slug"] for p in BLOG_POSTS}), len(BLOG_POSTS))
        for slug in SLUGS:
            post = BLOG_POSTS_BY_SLUG[slug]
            self.assertEqual(post["date"], "2026-09-28")
            self.assertRegex(post["research_origin_sha256"], r"^[a-f0-9]{64}$")
            response = self.client.get(f"/blog/{slug}")
            self.assertEqual(response.status_code, 200)
            body = response.get_data(as_text=True)
            self.assertIn(f'<link rel="canonical" href="https://kyanitelabs.tech/blog/{slug}">', body)
            blocks = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', body, re.S)
            article = json.loads(blocks[0])["@graph"][0]
            self.assertEqual(article["author"]["@type"], "Organization")
            self.assertEqual(article["author"]["name"], "KyaniteLabs Research")
            self.assertEqual(article["inLanguage"], "en")

    def test_every_research_route_is_in_discovery(self):
        for path in ("/blog", "/sitemap.xml", "/feed.xml", "/llms.txt", "/llms-full.txt"):
            body = self.client.get(path).get_data(as_text=True)
            for slug in SLUGS:
                with self.subTest(path=path, slug=slug):
                    self.assertIn(f"/blog/{slug}", body)

    def test_play1_measurements_and_limits_remain_distinct(self):
        body = BLOG_POSTS_BY_SLUG["play1-numbers"]["body"]
        for value in ("72.2%", "22.7%", "17.5", "25.4", "28.5", "23.9", "20.8", "9.2"):
            self.assertIn(value, body)
        self.assertIn("No external reproduction", body)
        self.assertIn("does not claim a new independent verification", body)
        self.assertIn("does not supply sample counts", body)

    def test_open_security_defects_are_not_recast_as_fixed(self):
        body = BLOG_POSTS_BY_SLUG["adversarial-custody-chains"]["body"]
        self.assertIn("Two defects remained open", body)
        self.assertIn("does not establish that either repair later passed", body)
        self.assertIn("No external red team", body)

    def test_image_measurements_do_not_become_quality_certification(self):
        body = BLOG_POSTS_BY_SLUG["local-image-stack-measured"]["body"]
        for value in ("5.84–5.88", "58.8", "191.7", "211.4", "n=10+10", "5.6%", "15.9%"):
            self.assertIn(value, body)
        self.assertIn("an estimate, not a measured adoption result", body)
        self.assertIn("One machine class", body)
        self.assertIn("single-judge observations", body)
        self.assertIn("permission to use particular weights commercially", body)

    def test_internal_publishing_instructions_are_absent(self):
        forbidden = (":4690", "/Users/", "Comms publishing pilot", "working draft v0.1",
                     "Comms: framing", "raw-file surface")
        for slug in SLUGS:
            body = self.client.get(f"/blog/{slug}").get_data(as_text=True)
            for value in forbidden:
                self.assertNotIn(value, body)

    def test_spanish_shell_does_not_claim_translated_research(self):
        for slug in SLUGS:
            body = self.client.get(f"/es/blog/{slug}").get_data(as_text=True)
            self.assertIn("Research report in English", body)
            self.assertIn('lang="en"', body)
            blocks = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', body, re.S)
            self.assertEqual(json.loads(blocks[0])["@graph"][0]["inLanguage"], "en")

    def test_existing_author_and_product_identity_are_preserved(self):
        body = self.client.get("/blog/gpt-6-sol-luna-astra-routing-guide").get_data(as_text=True)
        blocks = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', body, re.S)
        self.assertEqual(json.loads(blocks[0])["@graph"][0]["author"]["@type"], "Person")
        projects = {p["name"]: p for p in PUBLIC_PROJECTS}
        self.assertEqual(projects["DialectOS"]["url"], "https://github.com/KyaniteLabs/DialectOS")
        self.assertEqual(projects["Kinocut"]["url"], "https://kinocut.dev")
        self.assertIn("not an effectiveness guarantee", projects["tastecheck"]["description"])
        self.assertIn("do not certify production safety", projects["checkyourself"]["description"])


if __name__ == "__main__":
    unittest.main()
