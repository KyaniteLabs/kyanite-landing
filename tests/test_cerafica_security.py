"""Security of the Cerafica API: the Stripe webhook fails closed and the
operator routes sit behind the admin bearer token."""
from __future__ import annotations

import json
import time
import unittest
from unittest import mock

import app as app_module
from app import app, generate_blog_post, verify_stripe_signature
from test_state_machines import CeraficaDbCase, stripe_signature

SECRET = "whsec_test"
BODY = json.dumps({"type": "checkout.session.completed",
                   "data": {"object": {"id": "cs_1", "payment_intent": "pi_1"}}})


class StripeSignatureTests(unittest.TestCase):
    def test_valid_signature_verifies(self) -> None:
        self.assertTrue(verify_stripe_signature(BODY, stripe_signature(BODY, SECRET), SECRET))
        self.assertTrue(verify_stripe_signature(BODY.encode(), stripe_signature(BODY, SECRET), SECRET))

    def test_every_bad_input_is_rejected(self) -> None:
        good = stripe_signature(BODY, SECRET)
        now = int(time.time())
        cases = {
            "no header": (BODY, "", SECRET),
            "no secret": (BODY, good, ""),
            "wrong secret": (BODY, good, "whsec_other"),
            "tampered body": (BODY + " ", good, SECRET),
            "garbage header": (BODY, "nonsense", SECRET),
            "no v1": (BODY, f"t={now}", SECRET),
            "two timestamps": (BODY, f"t={now},t={now}," + good.split(",")[1], SECRET),
            "non-numeric t": (BODY, "t=abc,v1=00", SECRET),
            "stale": (BODY, stripe_signature(BODY, SECRET, ts=now - 3600), SECRET),
            "from the future": (BODY, stripe_signature(BODY, SECRET, ts=now + 3600), SECRET),
            "binary garbage body": (b"\xff\xfe", good, SECRET),
        }
        for name, (body, header, secret) in cases.items():
            with self.subTest(name):
                self.assertFalse(verify_stripe_signature(body, header, secret))

    def test_any_matching_v1_among_several_is_accepted(self) -> None:
        ts = int(time.time())
        good = stripe_signature(BODY, SECRET, ts=ts).split(",")[1]
        self.assertTrue(verify_stripe_signature(BODY, f"t={ts},v1=deadbeef,{good}", SECRET))


class WebhookFailsClosedTests(CeraficaDbCase):
    def post(self, headers):
        with mock.patch.object(app_module, "CERAFICA_WEBHOOK_SECRET", SECRET):
            return self.client.post("/api/cerafica/webhook", data=BODY,
                                    headers={"Content-Type": "application/json", **headers})

    def test_unsigned_event_is_rejected_and_order_untouched(self) -> None:
        oid = self.add_order()
        self.assertEqual(self.post({}).status_code, 400)
        self.assertEqual(self.order(oid)["status"], "pending")

    def test_forged_signature_is_rejected(self) -> None:
        oid = self.add_order()
        resp = self.post({"Stripe-Signature": stripe_signature(BODY, "whsec_attacker")})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.order(oid)["status"], "pending")

    def test_verifier_crash_rejects_instead_of_processing(self) -> None:
        # Old code: an exception during verification fell through to processing.
        oid = self.add_order()
        header = stripe_signature(BODY, SECRET)
        with mock.patch.object(app_module.hmac, "new", side_effect=RuntimeError("boom")):
            resp = self.post({"Stripe-Signature": header})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.order(oid)["status"], "pending")

    def test_no_network_call_is_made_to_verify(self) -> None:
        oid = self.add_order()
        with mock.patch.object(app_module.http_requests, "post", side_effect=AssertionError("network")):
            resp = self.post({"Stripe-Signature": stripe_signature(BODY, SECRET)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.order(oid)["status"], "paid")


ADMIN_ROUTES = [
    ("GET", "/api/cerafica/orders"),
    ("POST", "/api/cerafica/orders/1/notify-shipped"),
    ("POST", "/api/cerafica/orders/1/request-ugc"),
    ("POST", "/api/cerafica/waitlist/notify"),
    ("POST", "/api/cerafica/content/generate-blog"),
    ("POST", "/api/cerafica/content/generate-all-blogs"),
]


class AdminGateTests(CeraficaDbCase):
    def call(self, method, path, auth=None):
        headers = {} if auth is None else {"Authorization": auth}
        self.client.environ_base.pop("HTTP_AUTHORIZATION", None)
        return self.client.open(path, method=method, json={}, headers=headers)

    def test_admin_routes_refuse_without_or_with_wrong_token(self) -> None:
        for method, path in ADMIN_ROUTES:
            with self.subTest(path=path):
                self.assertEqual(self.call(method, path).status_code, 403)
                self.assertEqual(self.call(method, path, "Bearer wrong").status_code, 403)

    def test_admin_routes_fail_closed_when_no_token_is_configured(self) -> None:
        app.config["ADMIN_API_TOKEN"] = ""
        for method, path in ADMIN_ROUTES:
            with self.subTest(path=path):
                self.assertEqual(self.call(method, path, "Bearer ").status_code, 404)

    def test_operator_with_token_gets_through(self) -> None:
        resp = self.call("GET", "/api/cerafica/orders", "Bearer test-admin-token")
        self.assertEqual(resp.status_code, 200)

    def test_customer_routes_stay_public(self) -> None:
        self.client.environ_base.pop("HTTP_AUTHORIZATION", None)
        self.assertEqual(self.client.get("/api/cerafica/content/blog-posts").status_code, 200)
        self.assertNotIn(self.client.post("/api/cerafica/waitlist/join",
                                          json={"email": "a@example.com", "product_id": "p"}).status_code,
                         (401, 403))


class BlogGeneratorTests(unittest.TestCase):
    def test_returns_the_five_parts_and_escapes_remote_fields(self) -> None:
        slug, title, html, markdown, meta = generate_blog_post(
            {"id": "Vase 1!", "name": "<script>x</script>", "description": "Line one\nLine two", "price": 40})
        self.assertEqual(slug, "vase-1")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("<p>Line two</p>", html)
        self.assertIn("$40.00", html)
        self.assertTrue(markdown.startswith("# "))
        self.assertLessEqual(len(meta), 155)

    def test_sparse_product_still_produces_a_post(self) -> None:
        slug, title, html, _md, meta = generate_blog_post({})
        self.assertEqual(slug, "a-cerafica-piece")
        self.assertTrue(title and html and meta)

    def test_unconfigured_product_source_returns_no_products(self) -> None:
        with mock.patch.object(app_module, "PRODUCTS_URL", ""):
            self.assertEqual(app_module.get_products(), [])


if __name__ == "__main__":
    unittest.main()
