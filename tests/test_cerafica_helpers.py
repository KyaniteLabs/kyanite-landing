"""Regression pins for Cerafica helpers that previously raised NameError."""

import unittest

import app


class CeraficaHelperTest(unittest.TestCase):
    def test_shipping_uses_declared_cerafica_rates(self):
        self.assertEqual(app.calculate_shipping(app.CERAFICA_FREE_SHIPPING_THRESHOLD), 0)
        self.assertEqual(
            app.calculate_shipping(app.CERAFICA_FREE_SHIPPING_THRESHOLD - 1),
            app.CERAFICA_FLAT_SHIPPING,
        )

    def test_route_helpers_are_defined(self):
        for name in ("cerafica_send_email", "generate_blog_post", "get_products"):
            self.assertTrue(callable(getattr(app, name)), name)

    def test_generate_blog_post_returns_slugged_story(self):
        # Pins the hardened helper (#37): five fields, a URL-safe slug from the
        # product, and the description carried into body and meta.
        slug, title, html, markdown, meta = app.generate_blog_post(
            {"name": "Blue Moon", "description": "A tall vase.", "food_safe": True}
        )
        self.assertEqual(slug, "blue-moon")
        self.assertEqual(title, "Blue Moon: the story behind the piece")
        self.assertIn("A tall vase.", html)
        self.assertIn("# Blue Moon: the story behind the piece", markdown)
        self.assertIn("A tall vase.", meta)

if __name__ == "__main__":
    unittest.main()
