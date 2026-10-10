"""spend.py publish: summary built from mock OpenRouter and Mercury data.

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

sys.modules.setdefault("keyring", types.SimpleNamespace(get_password=lambda *a: None, set_password=lambda *a: None))
_spec = importlib.util.spec_from_file_location("spend", Path(__file__).parent.parent / "nest" / "spend.py")
spend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(spend)

# Mock data, shaped like the real APIs. Not real cards or keys.
WANT = {
    "tier0": {"name": "rookery-tier0", "key": {"limit": 0.5}, "guardrail": {"limit_usd": 5}},
    "tier1": {"name": "rookery-tier1", "key": {"limit": 5}, "guardrail": {"limit_usd": 40}},
}
KEYS = {
    "rookery-tier0": {"usage_daily": 0.02, "usage_monthly": 0.55},
    "rookery-tier1": {"usage_daily": 1.5, "usage_monthly": 16.8},
}


def card(merchant=None, nickname="", cents=5000, interval="monthly", status="active"):
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
TIER_KEYS = {"id", "dayUsed", "monthUsed"}
CARD_KEYS = {"total", "merchantLocked", "capped", "capCoversGuardrails", "declines30d"}


class TierUsage(unittest.TestCase):
    def test_ratios_of_key_and_guardrail_limits(self):
        tiers = spend.tier_usage(WANT, KEYS)
        self.assertEqual(tiers[0], {"id": "tier0", "dayUsed": 0.04, "monthUsed": 0.11})
        self.assertEqual(tiers[1], {"id": "tier1", "dayUsed": 0.3, "monthUsed": 0.42})

    def test_missing_key_is_null_not_zero(self):
        tiers = spend.tier_usage(WANT, {})
        self.assertEqual(tiers[0], {"id": "tier0", "dayUsed": None, "monthUsed": None})


class CardSummary(unittest.TestCase):
    def test_counts_locked_and_capped_vendor_cards(self):
        cards = [
            card("Cloudflare", "cloudflare-dev", 1000, "monthly"),
            card("Cloudflare", "cloudflare-prod", 5000, "weekly"),
            card("OpenRouter", "openrouter", 6000, "monthly"),
            card(None, "taxi", 2500, "daily"),  # not a vendor card
            card("Cloudflare", "old", status="cancelled"),
        ]
        s = spend.card_summary(cards, 1, MERCHANTS, guardrail_total=45)
        self.assertEqual(s, {
            "total": 3, "merchantLocked": 3, "capped": 3, "capCoversGuardrails": True, "declines30d": 1,
        })

    def test_cap_below_guardrail_total_is_flagged(self):
        s = spend.card_summary([card("OpenRouter", cents=2000)], 0, MERCHANTS, guardrail_total=45)
        self.assertIs(s["capCoversGuardrails"], False)

    def test_weekly_and_daily_caps_are_normalised_to_monthly(self):
        self.assertAlmostEqual(spend.monthly_cap_usd(card(cents=1000, interval="weekly")), 10 * 52 / 12)
        self.assertEqual(spend.monthly_cap_usd(card(cents=100, interval="daily")), 30)
        self.assertIsNone(spend.monthly_cap_usd(card(cents=None)))

    def test_no_openrouter_card_yet_is_unknown_not_false(self):
        s = spend.card_summary([card("Cloudflare", "cloudflare-prod")], 0, MERCHANTS, guardrail_total=45)
        self.assertIsNone(s["capCoversGuardrails"])
        self.assertEqual(s["total"], 1)

    def test_vendor_card_without_merchant_lock_counts_but_not_as_locked(self):
        s = spend.card_summary([card(None, "openrouter-backup")], 0, MERCHANTS, guardrail_total=45)
        self.assertEqual((s["total"], s["merchantLocked"]), (1, 0))


class Summary(unittest.TestCase):
    def summary(self, cards):
        now = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
        return spend.build_summary(WANT, KEYS, True, False, cards, now)

    def test_shape_is_exactly_what_voidlight_accepts(self):
        s = self.summary(spend.card_summary([card("OpenRouter")], 0, MERCHANTS, 45))
        self.assertEqual(set(s), TOP_KEYS)
        self.assertEqual(s["generatedAt"], "2026-10-06T12:00:00.000Z")
        for t in s["tiers"]:
            self.assertEqual(set(t), TIER_KEYS)
        self.assertEqual(set(s["cards"]), CARD_KEYS)

    def test_no_amounts_or_identifiers_leave_the_machine(self):
        body = json.dumps(self.summary(spend.card_summary([card("OpenRouter", "openrouter")], 0, MERCHANTS, 45)))
        for secret_ish in ["rookery-tier", "card-", "amountCents", "16.8", "6000", "usage_"]:
            self.assertNotIn(secret_ish, body)

    def test_cards_may_be_null(self):
        self.assertIsNone(self.summary(None)["cards"])


class Signature(unittest.TestCase):
    def test_matches_voidlight_scheme(self):
        # HMAC-SHA256 over "timestamp.body", hex, prefixed (voidlight src/spend.ts sign()).
        expected = hmac.new(b"s", b"1791300000000.{}", hashlib.sha256).hexdigest()
        self.assertEqual(spend.signature("s", "1791300000000", "{}"), f"sha256={expected}")


if __name__ == "__main__":
    unittest.main()
