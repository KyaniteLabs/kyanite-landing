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
        slug, title, html, markdown, meta = app.generate_blog_post(
            {"name": "Blue Moon", "description": "A tall vase.", "food_safe": True}
        )
        self.assertEqual(slug, "the-story-of-blue-moon")
        self.assertEqual(title, "The Story of Blue Moon")
        self.assertIn("Food-safe", html)
        self.assertIn("# The Story of Blue Moon", markdown)
        self.assertIn("A tall vase.", meta)


if __name__ == "__main__":
    unittest.main()
