"""report.py publish: summary built from mock Mercury data.

Stdlib only (keyring is stubbed), so CI needs no accounts, cards or keys:
    python3 -m unittest discover -s tests
"""

import hashlib
import hmac
import importlib.util
import json
import sys
import types
import unittest
from datetime import UTC, datetime
from pathlib import Path

_errors = types.SimpleNamespace(KeyringError=Exception)
sys.modules.setdefault("keyring", types.SimpleNamespace(get_password=lambda *a: None, set_password=lambda *a: None, errors=_errors))
sys.modules.setdefault("keyring.errors", _errors)
_spec = importlib.util.spec_from_file_location("report", Path(__file__).parent.parent / "nest" / "report.py")
report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)


def card(merchant=None, nickname="", cents=5000, interval="monthly", status="active"):
    # Mock data, shaped like the Mercury API. Not real cards.
    return {
        "id": f"card-{merchant or nickname}",
        "status": status,
        "type": "virtual",
        "nickname": nickname,
        "merchantLock": {"name": merchant} if merchant else None,
        "spendLimit": {"amountCents": cents, "interval": interval} if cents is not None else None,
    }


MERCHANTS = ["OpenRouter", "Cloudflare"]

# voidlight's src/spend.ts accepts exactly these keys and rejects anything else.
TOP_KEYS = {"version", "generatedAt", "tiers", "allowlistsInSync", "creditLow", "cards"}
CARD_KEYS = {"total", "merchantLocked", "capped", "capCoversGuardrails", "declines30d"}


class CardSummary(unittest.TestCase):
    def test_counts_locked_and_capped_vendor_cards(self):
        cards = [
            card("Cloudflare", "cloudflare-dev", 1000, "monthly"),
            card("Cloudflare", "cloudflare-prod", 5000, "weekly"),
            card("OpenRouter", "openrouter", 6000, "monthly"),
            card(None, "taxi", 2500, "daily"),  # not a vendor card
            card("Cloudflare", "old", status="cancelled"),
        ]
        s = report.card_summary(cards, 1, MERCHANTS)
        self.assertEqual(s, {
            "total": 3, "merchantLocked": 3, "capped": 3, "capCoversGuardrails": None, "declines30d": 1,
        })

    def test_weekly_and_daily_caps_are_normalised_to_monthly(self):
        self.assertAlmostEqual(report.monthly_cap_usd(card(cents=1000, interval="weekly")), 10 * 52 / 12)
        self.assertEqual(report.monthly_cap_usd(card(cents=100, interval="daily")), 30)
        self.assertIsNone(report.monthly_cap_usd(card(cents=None)))

    def test_uncapped_card_counts_but_not_as_capped(self):
        s = report.card_summary([card("Cloudflare", cents=None)], 0, MERCHANTS)
        self.assertEqual((s["total"], s["capped"]), (1, 0))

    def test_vendor_card_without_merchant_lock_counts_but_not_as_locked(self):
        s = report.card_summary([card(None, "openrouter-backup")], 0, MERCHANTS)
        self.assertEqual((s["total"], s["merchantLocked"]), (1, 0))

    def test_declines_are_queried_for_every_counted_card(self):
        # A nickname-only vendor card is counted, so its declines must be too.
        cards = [card(None, "openrouter-backup"), card(None, "taxi")]
        calls = []

        def fake_mercury(path, token):
            calls.append(path)
            return {"cards": cards} if path.startswith("/cards") else {"transactions": [{}, {}]}

        original, report.mercury = report.mercury, fake_mercury
        try:
            s = report.fetch_cards("t", MERCHANTS, report.date(2026, 11, 13))
        finally:
            report.mercury = original
        self.assertEqual(s["declines30d"], 2)
        self.assertIn("cardId=card-openrouter-backup", calls[1])
        self.assertNotIn("card-taxi", calls[1])


class MercuryRedirects(unittest.TestCase):
    def test_redirects_are_refused(self):
        # None tells urllib not to follow, so the token never reaches a Location target.
        handler = report._NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "http://evil.example/"))


class Summary(unittest.TestCase):
    def summary(self, cards):
        return report.build_summary(cards, datetime(2026, 10, 6, 12, 0, tzinfo=UTC))

    def test_shape_is_exactly_what_voidlight_accepts(self):
        s = self.summary(report.card_summary([card("OpenRouter")], 0, MERCHANTS))
        self.assertEqual(set(s), TOP_KEYS)
        self.assertEqual(s["generatedAt"], "2026-10-06T12:00:00.000Z")
        self.assertEqual(s["tiers"], [])
        self.assertIs(s["allowlistsInSync"], True)
        self.assertIs(s["creditLow"], False)
        self.assertEqual(set(s["cards"]), CARD_KEYS)

    def test_no_amounts_or_identifiers_leave_the_machine(self):
        body = json.dumps(self.summary(report.card_summary([card("OpenRouter", "openrouter", 6000)], 0, MERCHANTS)))
        for secret_ish in ["card-", "amountCents", "6000", "60.0", "openrouter"]:
            self.assertNotIn(secret_ish, body)

    def test_cards_may_be_null(self):
        self.assertIsNone(self.summary(None)["cards"])


class Signature(unittest.TestCase):
    def test_matches_voidlight_scheme(self):
        # HMAC-SHA256 over "timestamp.body", hex, prefixed (voidlight src/spend.ts sign()).
        expected = hmac.new(b"s", b"1791300000000.{}", hashlib.sha256).hexdigest()
        self.assertEqual(report.signature("s", "1791300000000", "{}"), f"sha256={expected}")


if __name__ == "__main__":
    unittest.main()
