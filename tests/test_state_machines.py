"""Tests for the explicit lifecycles in app.py (the LIFECYCLES section).

Postgres-backed routes run against an in-memory sqlite database through a
small adapter (``%s`` -> ``?``, ``NOW()`` -> ``CURRENT_TIMESTAMP``), so the
guarded UPDATE statements are actually executed, not mocked.
"""
from __future__ import annotations

import contextlib
import itertools
import json
import os
import random
import sqlite3
import tempfile
import unittest
from unittest import mock

import app as app_module
from app import (
    IllegalTransition,
    InconsistentState,
    NEWSLETTER_TRANSITIONS,
    NewsletterConsent,
    NewsletterEvent,
    ORDER_EVENT_TIMESTAMP_COLUMN,
    ORDER_STAGE_SQL,
    ORDER_TRANSITIONS,
    OrderEvent,
    OrderStage,
    OrderStatus,
    PublicationState,
    WaitlistStage,
    app,
    derive_order_stage,
    derive_publication_state,
    derive_waitlist_stage,
    next_newsletter_consent,
    next_order_stage,
    next_publication_state,
    next_waitlist_stage,
    parse_newsletter_consent,
    parse_order_status,
)

TS = "2026-01-01 00:00:00"

SCHEMA = """
CREATE TABLE cerafica_orders (
    id INTEGER PRIMARY KEY,
    stripe_session_id TEXT UNIQUE,
    stripe_payment_intent_id TEXT,
    customer_email TEXT,
    customer_name TEXT,
    shipping_address TEXT,
    items TEXT,
    subtotal_cents INTEGER,
    shipping_cents INTEGER,
    total_cents INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,
    shipped_at TIMESTAMP,
    ugc_requested_at TIMESTAMP
);
CREATE TABLE cerafica_waitlist (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified_at TIMESTAMP,
    UNIQUE(email, product_id)
);
CREATE TABLE cerafica_blog_posts (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE,
    product_id TEXT,
    title TEXT,
    html_content TEXT,
    markdown_content TEXT,
    meta_description TEXT,
    published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _pg_to_sqlite(sql: str) -> str:
    return sql.replace("%s", "?").replace("NOW()", "CURRENT_TIMESTAMP")


class _Cursor:
    def __init__(self, raw: sqlite3.Cursor):
        self._raw = raw

    def execute(self, sql, params=()):
        self._raw.execute(_pg_to_sqlite(sql), params)

    def fetchone(self):
        return self._raw.fetchone()

    def fetchall(self):
        return self._raw.fetchall()

    @property
    def rowcount(self):
        return self._raw.rowcount

    def close(self):
        pass


class _Conn:
    def __init__(self, db: sqlite3.Connection):
        self._db = db

    def cursor(self, **_kwargs):
        return _Cursor(self._db.cursor())

    def commit(self):
        self._db.commit()

    def rollback(self):
        self._db.rollback()

    def close(self):
        pass


class CeraficaDbCase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(SCHEMA)
        self.client = app.test_client()
        self.sent: list[tuple[str, str]] = []
        self.fail_emails: set[str] = set()
        self._config = {
            k: app.config.get(k) for k in ("ENABLE_CERAFICA_DB", "ENABLE_CERAFICA_PUBLIC_API", "ADMIN_API_TOKEN")
        }
        app.config["ENABLE_CERAFICA_DB"] = True
        app.config["ENABLE_CERAFICA_PUBLIC_API"] = True
        # operator routes are behind the admin gate; these tests act as the operator
        app.config["ADMIN_API_TOKEN"] = "test-admin-token"
        self.client.environ_base["HTTP_AUTHORIZATION"] = "Bearer test-admin-token"

        def fake_send(to_email, subject, html_body, text_body=None):
            if to_email in self.fail_emails:
                return False
            self.sent.append((to_email, subject))
            return True

        self._patches = [
            mock.patch.object(app_module, "get_pg_conn", lambda: _Conn(self.db)),
            mock.patch.object(app_module, "cerafica_send_email", fake_send, create=True),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in reversed(self._patches):
            p.stop()
        app.config.update(self._config)
        self.db.close()

    # helpers
    def add_order(self, status="pending", shipped_at=None, ugc_requested_at=None, session="cs_1",
                  email="buyer@example.com", paid_at=None, payment_intent=None) -> int:
        cur = self.db.execute(
            """INSERT INTO cerafica_orders (stripe_session_id, customer_email, customer_name, items,
               status, shipped_at, ugc_requested_at, paid_at, stripe_payment_intent_id)
               VALUES (?, ?, 'Buyer', ?, ?, ?, ?, ?, ?)""",
            (session, email, json.dumps([{"name": "Vase", "price": 40}]), status, shipped_at,
             ugc_requested_at, paid_at, payment_intent),
        )
        self.db.commit()
        return cur.lastrowid

    def order(self, order_id: int) -> dict:
        self.db.row_factory = sqlite3.Row
        try:
            return dict(self.db.execute("SELECT * FROM cerafica_orders WHERE id = ?", (order_id,)).fetchone())
        finally:
            self.db.row_factory = None

    def stage(self, order_id: int) -> OrderStage:
        row = self.order(order_id)
        return derive_order_stage(row["status"], row["shipped_at"], row["ugc_requested_at"])

    def deliver_webhook(self, session="cs_1", payment_intent="pi_1"):
        body = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {"id": session, "payment_intent": payment_intent,
                                "customer_email": "buyer@example.com"}},
        })
        with mock.patch.object(app_module, "CERAFICA_WEBHOOK_SECRET", "whsec_test"):
            return self.client.post("/api/cerafica/webhook", data=body,
                                    headers={"Content-Type": "application/json",
                                             "Stripe-Signature": stripe_signature(body, "whsec_test")})


def stripe_signature(body: str, secret: str, ts: int | None = None) -> str:
    import hashlib, hmac, time
    ts = int(time.time()) if ts is None else ts
    sig = hmac.new(secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


# ── Newsletter consent ───────────────────────────────────────────────────────

class NewsletterConsentMachineTests(unittest.TestCase):
    def test_transition_table_is_total_over_states_and_events(self) -> None:
        # Every real state handles every event; a missing subscriber can only subscribe.
        expected = set(itertools.product(NewsletterConsent, NewsletterEvent)) | {(None, NewsletterEvent.SUBSCRIBE)}
        self.assertEqual(set(NEWSLETTER_TRANSITIONS), expected)

    def test_every_transition_lands_on_expected_state(self) -> None:
        for source in [None, *NewsletterConsent]:
            self.assertIs(next_newsletter_consent(source, NewsletterEvent.SUBSCRIBE), NewsletterConsent.SUBSCRIBED)
        for source in NewsletterConsent:
            self.assertIs(next_newsletter_consent(source, NewsletterEvent.UNSUBSCRIBE), NewsletterConsent.UNSUBSCRIBED)

    def test_unsubscribing_a_missing_subscriber_is_illegal(self) -> None:
        with self.assertRaises(IllegalTransition):
            next_newsletter_consent(None, NewsletterEvent.UNSUBSCRIBE)

    def test_unknown_event_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            next_newsletter_consent(NewsletterConsent.SUBSCRIBED, "delete")

    def test_persisted_values_are_unchanged(self) -> None:
        self.assertEqual({c.value for c in NewsletterConsent}, {"subscribed", "unsubscribed"})

    def test_legacy_values_parse_tolerantly(self) -> None:
        self.assertIs(parse_newsletter_consent(" Subscribed "), NewsletterConsent.SUBSCRIBED)
        self.assertIs(parse_newsletter_consent("UNSUBSCRIBED"), NewsletterConsent.UNSUBSCRIBED)
        with self.assertRaises(InconsistentState):
            parse_newsletter_consent("bounced")


class NewsletterConsentRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        self._config = {k: app.config.get(k) for k in (
            "NEWSLETTER_DB_PATH", "NEWSLETTER_UNSUBSCRIBE_SECRET", "CONTACT_TO")}
        app.config.update(NEWSLETTER_DB_PATH=self.path, NEWSLETTER_UNSUBSCRIBE_SECRET="s", CONTACT_TO="")
        self.client = app.test_client()

    def tearDown(self) -> None:
        app.config.update(self._config)
        with contextlib.suppress(FileNotFoundError):
            os.remove(self.path)

    def status(self, email="r@example.com") -> str:
        db = sqlite3.connect(self.path)
        try:
            return db.execute("SELECT consent_status FROM newsletter_subscribers WHERE email = ?", (email,)).fetchone()[0]
        finally:
            db.close()

    def test_subscribe_unsubscribe_resubscribe_round_trip(self) -> None:
        token = app_module.newsletter_unsubscribe_token("r@example.com")
        self.client.post("/api/newsletter/subscribe", json={"email": "r@example.com", "consent": True})
        self.assertEqual(self.status(), "subscribed")
        self.assertEqual(self.client.get(f"/api/newsletter/unsubscribe?token={token}").status_code, 200)
        self.assertEqual(self.status(), "unsubscribed")
        # second click on the link stays a success
        self.assertEqual(self.client.get(f"/api/newsletter/unsubscribe?token={token}").status_code, 200)
        self.assertEqual(self.status(), "unsubscribed")
        self.client.post("/api/newsletter/subscribe", json={"email": "r@example.com", "consent": True})
        self.assertEqual(self.status(), "subscribed")

    def test_unsubscribe_honors_legacy_consent_value(self) -> None:
        token = app_module.newsletter_unsubscribe_token("r@example.com")
        self.client.post("/api/newsletter/subscribe", json={"email": "r@example.com", "consent": True})
        db = sqlite3.connect(self.path)
        db.execute("UPDATE newsletter_subscribers SET consent_status = 'opted-in-v1'")
        db.commit()
        db.close()
        self.assertEqual(self.client.get(f"/api/newsletter/unsubscribe?token={token}").status_code, 200)
        self.assertEqual(self.status(), "unsubscribed")


# ── Cerafica order ───────────────────────────────────────────────────────────

class OrderMachineTests(unittest.TestCase):
    STATUSES = [None, "pending", "paid", " PAID "]

    def test_derived_state_table(self) -> None:
        expected = {
            ("pending", None, None): OrderStage.PENDING,
            (None, None, None): OrderStage.PENDING,
            ("paid", None, None): OrderStage.PAID,
            ("paid", TS, None): OrderStage.SHIPPED,
            ("paid", TS, TS): OrderStage.UGC_REQUESTED,
        }
        for args, stage in expected.items():
            with self.subTest(args=args):
                self.assertIs(derive_order_stage(*args), stage)
        for args in [("pending", TS, None), ("pending", None, TS), ("pending", TS, TS), ("paid", None, TS)]:
            with self.subTest(args=args):
                with self.assertRaises(InconsistentState):
                    derive_order_stage(*args)

    def test_every_stage_is_reachable_and_has_sql_predicate(self) -> None:
        reachable = {OrderStage.PENDING} | {t for _, t in ORDER_TRANSITIONS.values()}
        self.assertEqual(reachable, set(OrderStage))
        self.assertEqual(set(ORDER_STAGE_SQL), set(OrderStage))
        self.assertEqual(set(ORDER_EVENT_TIMESTAMP_COLUMN) | {OrderEvent.PAYMENT_COMPLETED}, set(OrderEvent))

    def test_sql_predicates_agree_with_python_derivation(self) -> None:
        """For every stored combination, exactly the derived stage's predicate matches."""
        db = sqlite3.connect(":memory:")
        db.executescript(SCHEMA)
        for status, shipped, ugc in itertools.product(self.STATUSES + ["refunded"], [None, TS], [None, TS]):
            db.execute("DELETE FROM cerafica_orders")
            db.execute("INSERT INTO cerafica_orders (id, status, shipped_at, ugc_requested_at) VALUES (1, ?, ?, ?)",
                       (status.strip().lower() if status else status, shipped, ugc))
            matches = {s for s, pred in ORDER_STAGE_SQL.items()
                       if db.execute(f"SELECT 1 FROM cerafica_orders WHERE {pred}").fetchone()}
            with self.subTest(status=status, shipped=shipped, ugc=ugc):
                try:
                    stage = derive_order_stage(status, shipped, ugc)
                except InconsistentState:
                    self.assertEqual(matches, set())
                else:
                    self.assertEqual(matches, {stage})
        db.close()

    def test_every_legal_and_illegal_transition(self) -> None:
        for stage, event in itertools.product(OrderStage, OrderEvent):
            source, target = ORDER_TRANSITIONS[event]
            with self.subTest(stage=stage, event=event):
                if stage is source:
                    self.assertIs(next_order_stage(stage, event), target)
                else:
                    with self.assertRaises(IllegalTransition):
                        next_order_stage(stage, event)

    def test_persisted_status_values_unchanged_and_legacy_tolerant(self) -> None:
        self.assertEqual({s.value for s in OrderStatus}, {"pending", "paid"})
        self.assertIs(parse_order_status(None), OrderStatus.PENDING)
        self.assertIs(parse_order_status(" Paid"), OrderStatus.PAID)
        with self.assertRaises(InconsistentState):
            parse_order_status("refunded")


class OrderRouteTests(CeraficaDbCase):
    def test_notify_shipped_sends_and_records(self) -> None:
        # Old code called the undefined name `cerafica_send_email` -> 500.
        oid = self.add_order(status="paid")
        resp = self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        self.assertEqual(len(self.sent), 1)
        self.assertIs(self.stage(oid), OrderStage.SHIPPED)

    def test_post_purchase_routes_reach_the_real_email_helper(self) -> None:
        # Old code defined `cerafica_cerafica_send_email` but called
        # `cerafica_send_email`, so every post-purchase route raised NameError.
        self._patches.pop().stop()  # use the real helper, fake only SMTP
        oid = self.add_order(status="paid")
        with mock.patch.object(app_module.smtplib, "SMTP") as smtp:
            resp = self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        smtp.return_value.__enter__.return_value.sendmail.assert_called_once()
        self.assertIs(self.stage(oid), OrderStage.SHIPPED)

    def test_notify_shipped_twice_does_not_resend(self) -> None:
        oid = self.add_order(status="paid")
        self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={})
        first_shipped_at = self.order(oid)["shipped_at"]
        resp = self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.order(oid)["shipped_at"], first_shipped_at)

    def test_failed_shipping_email_leaves_order_paid_for_retry(self) -> None:
        oid = self.add_order(status="paid", email="down@example.com")
        self.fail_emails.add("down@example.com")
        resp = self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={})
        self.assertEqual(resp.status_code, 502)
        self.assertIs(self.stage(oid), OrderStage.PAID)
        self.fail_emails.clear()
        self.assertEqual(self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={}).status_code, 200)
        self.assertIs(self.stage(oid), OrderStage.SHIPPED)

    def test_shipping_a_pending_order_is_refused(self) -> None:
        oid = self.add_order(status="pending")
        resp = self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self.sent, [])

    def test_ugc_only_once_and_only_after_shipping(self) -> None:
        oid = self.add_order(status="paid")
        self.assertEqual(self.client.post(f"/api/cerafica/orders/{oid}/request-ugc").status_code, 409)
        self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={})
        self.assertEqual(self.client.post(f"/api/cerafica/orders/{oid}/request-ugc").status_code, 200)
        self.assertEqual(self.client.post(f"/api/cerafica/orders/{oid}/request-ugc").status_code, 409)
        self.assertEqual([s for _, s in self.sent].count("Show us your piece in the wild"), 1)
        self.assertIs(self.stage(oid), OrderStage.UGC_REQUESTED)

    def test_inconsistent_stored_row_is_refused_not_advanced(self) -> None:
        oid = self.add_order(status="paid", ugc_requested_at=TS)  # UGC without shipping
        self.assertEqual(self.client.post(f"/api/cerafica/orders/{oid}/notify-shipped", json={}).status_code, 409)
        self.assertEqual(self.sent, [])

    def test_webhook_marks_pending_order_paid(self) -> None:
        oid = self.add_order(status="pending")
        self.assertEqual(self.deliver_webhook().status_code, 200)
        self.assertIs(self.stage(oid), OrderStage.PAID)
        self.assertEqual(self.order(oid)["stripe_payment_intent_id"], "pi_1")

    def test_duplicate_webhook_does_not_rewrite_paid_order(self) -> None:
        # Old UPDATE had no source-state guard: a Stripe retry rewrote paid_at.
        oid = self.add_order(status="paid", paid_at="2000-01-01 00:00:00", payment_intent="pi_1")
        self.deliver_webhook(payment_intent="pi_other")
        row = self.order(oid)
        self.assertEqual(row["paid_at"], "2000-01-01 00:00:00")
        self.assertEqual(row["stripe_payment_intent_id"], "pi_1")

    def test_late_webhook_cannot_touch_shipped_order(self) -> None:
        oid = self.add_order(status="paid", shipped_at=TS, paid_at="2000-01-01 00:00:00")
        self.deliver_webhook()
        self.assertEqual(self.order(oid)["paid_at"], "2000-01-01 00:00:00")
        self.assertIs(self.stage(oid), OrderStage.SHIPPED)

    def test_random_event_sequences_keep_db_and_model_in_step(self) -> None:
        """Model-based test: random admin/webhook events vs. a pure model."""
        actions = ["webhook", "ship", "ugc", "ship_fail", "ugc_fail"]
        for seed in range(25):
            rng = random.Random(seed)
            self.db.execute("DELETE FROM cerafica_orders")
            self.db.commit()
            self.sent.clear()
            oid = self.add_order(status="pending", email="buyer@example.com")
            model = OrderStage.PENDING
            expected_emails = 0
            for _ in range(12):
                action = rng.choice(actions)
                failing = action.endswith("_fail")
                self.fail_emails = {"buyer@example.com"} if failing else set()
                if action == "webhook":
                    self.deliver_webhook()
                    event = OrderEvent.PAYMENT_COMPLETED
                else:
                    event = OrderEvent.SHIPPED if action.startswith("ship") else OrderEvent.UGC_REQUESTED
                    path = "notify-shipped" if event is OrderEvent.SHIPPED else "request-ugc"
                    resp = self.client.post(f"/api/cerafica/orders/{oid}/{path}", json={})
                legal = ORDER_TRANSITIONS[event][0] is model
                if legal and not failing:
                    model = next_order_stage(model, event)
                    if event is not OrderEvent.PAYMENT_COMPLETED:
                        expected_emails += 1
                        self.assertEqual(resp.status_code, 200)
                elif event is not OrderEvent.PAYMENT_COMPLETED:
                    self.assertIn(resp.status_code, (409, 502))
                with self.subTest(seed=seed):
                    self.assertIs(self.stage(oid), model)
                    self.assertEqual(len(self.sent), expected_emails)


# ── Cerafica waitlist ────────────────────────────────────────────────────────

class WaitlistMachineTests(unittest.TestCase):
    def test_derived_state_table(self) -> None:
        self.assertIs(derive_waitlist_stage(None), WaitlistStage.WAITING)
        self.assertIs(derive_waitlist_stage(TS), WaitlistStage.NOTIFIED)

    def test_transitions(self) -> None:
        for stage, sent in itertools.product(WaitlistStage, [True, False]):
            with self.subTest(stage=stage, sent=sent):
                if stage is WaitlistStage.WAITING and sent:
                    self.assertIs(next_waitlist_stage(stage, sent), WaitlistStage.NOTIFIED)
                else:
                    with self.assertRaises(IllegalTransition):
                        next_waitlist_stage(stage, sent)


class WaitlistRouteTests(CeraficaDbCase):
    def notified(self) -> dict:
        return dict(self.db.execute("SELECT email, notified_at IS NOT NULL FROM cerafica_waitlist").fetchall())

    def test_failed_sends_stay_waiting_and_are_retried(self) -> None:
        # Old code marked every WAITING row notified, even ones whose email failed.
        for email in ("a@example.com", "b@example.com"):
            self.db.execute("INSERT INTO cerafica_waitlist (email, product_id) VALUES (?, 'vase-1')", (email,))
        self.db.commit()
        self.fail_emails = {"b@example.com"}
        resp = self.client.post("/api/cerafica/waitlist/notify", json={"product_id": "vase-1"})
        self.assertEqual(resp.get_json()["notified"], 1)
        self.assertEqual(self.notified(), {"a@example.com": 1, "b@example.com": 0})

        self.fail_emails = set()
        resp = self.client.post("/api/cerafica/waitlist/notify", json={"product_id": "vase-1"})
        self.assertEqual(resp.get_json(), {"ok": True, "notified": 1, "total": 1})
        self.assertEqual(self.notified(), {"a@example.com": 1, "b@example.com": 1})
        self.assertEqual([e for e, _ in self.sent], ["a@example.com", "b@example.com"])


# ── Cerafica blog publication ────────────────────────────────────────────────

class PublicationMachineTests(unittest.TestCase):
    def test_derived_state_table(self) -> None:
        self.assertIs(derive_publication_state(True), PublicationState.PUBLISHED)
        self.assertIs(derive_publication_state(1), PublicationState.PUBLISHED)
        self.assertIs(derive_publication_state(False), PublicationState.DRAFT)
        self.assertIs(derive_publication_state(None), PublicationState.DRAFT)

    def test_transitions_never_unpublish(self) -> None:
        for current, publish in itertools.product([None, *PublicationState], [True, False]):
            with self.subTest(current=current, publish=publish):
                expected = (PublicationState.PUBLISHED
                            if publish or current is PublicationState.PUBLISHED
                            else PublicationState.DRAFT)
                self.assertIs(next_publication_state(current, publish), expected)


class BlogRouteTests(CeraficaDbCase):
    PRODUCT = {"id": "vase-1", "available": True}

    def setUp(self) -> None:
        super().setUp()
        for p in (
            mock.patch.object(app_module, "get_products", lambda: [self.PRODUCT]),
            mock.patch.object(app_module, "generate_blog_post", create=True,
                              new=lambda product: ("vase-1", "Vase", "<p>v</p>", "v", "meta")),
        ):
            p.start()
            self._patches.append(p)

    def published(self):
        return self.db.execute("SELECT published FROM cerafica_blog_posts WHERE slug = 'vase-1'").fetchone()[0]

    def test_generate_all_publishes_an_existing_draft(self) -> None:
        # Old generate-all upsert ignored `published` on conflict, leaving drafts hidden.
        self.client.post("/api/cerafica/content/generate-blog", json={"product_id": "vase-1", "publish": False})
        self.assertEqual(self.published(), 0)
        self.client.post("/api/cerafica/content/generate-all-blogs")
        self.assertEqual(self.published(), 1)

    def test_regenerating_as_draft_keeps_post_published_and_reports_it(self) -> None:
        self.client.post("/api/cerafica/content/generate-blog", json={"product_id": "vase-1", "publish": True})
        resp = self.client.post("/api/cerafica/content/generate-blog", json={"product_id": "vase-1", "publish": False})
        self.assertEqual(self.published(), 1)
        self.assertIs(resp.get_json()["published"], True)


if __name__ == "__main__":
    unittest.main()
