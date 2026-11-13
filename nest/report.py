#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["keyring>=25"]
# ///
"""Publish an amount-free spend containment summary to voidlight.

  publish [--dry-run]
                  push the summary to voidlight's /ingest/spend (signed);
                  --dry-run prints it instead

OpenRouter is gone (docs/decisions/0002), so there are no per-tier keys or
guardrails to report on: `tiers` is empty until Copilot premium-request and
Anthropic usage reporting land (taraxvoid/rookery#10). What's left is card
containment from Mercury.

Secrets live in the OS keychain via `keyring`, service "rookery-openrouter"
(the name predates 0002; kept so stored secrets keep working): account
"voidlight-ingest" (shared HMAC key) and, optionally, "mercury" (read-only API
token; without it the card section publishes as null). VOIDLIGHT_INGEST_SECRET
and MERCURY_API_TOKEN in the environment override them, for a one-off run.
"""

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta

import keyring

MERCURY_API = os.environ.get("MERCURY_API_BASE", "https://api.mercury.com/api/v1")  # override only for testing
SERVICE = "rookery-openrouter"
PUBLISH_URL = "https://status.taraxvoid.com/ingest/spend"
# Mercury merchant-lock names of the cards that pay AI and hosting vendors.
# OpenRouter stays listed so a card left active after 0002 still shows up.
CARD_MERCHANTS = ["OpenRouter", "Cloudflare"]
# Monthly-equivalent multipliers for Mercury card spend-limit intervals.
INTERVAL_TO_MONTH = {"daily": 30, "weekly": 52 / 12, "monthly": 1, "yearly": 1 / 12}


# Everything below the fetch layer is pure, so tests/test_report.py checks the
# summary from fake API responses. What leaves this machine is flags and
# counts: never a dollar amount, balance or card detail. voidlight re-validates
# the exact shape (its src/spend.ts) and rejects extras.


def monthly_cap_usd(card: dict) -> float | None:
    limit = card.get("spendLimit") or {}
    cents, interval = limit.get("amountCents"), limit.get("interval")
    if cents is None or interval not in INTERVAL_TO_MONTH:
        return None
    return cents / 100 * INTERVAL_TO_MONTH[interval]


def card_summary(cards: list[dict], declines: int, merchants: list[str]) -> dict:
    """Containment counts over the active virtual cards for the given vendors.

    capCoversGuardrails is always None: it compared the OpenRouter card's cap
    with the OpenRouter guardrails, and neither is managed here any more.
    """
    wanted = {m.lower() for m in merchants}

    def merchant(c: dict) -> str:
        return ((c.get("merchantLock") or {}).get("name") or "").lower()

    vendor = [
        c for c in cards
        if c.get("status") == "active" and c.get("type") == "virtual"
        and (merchant(c) in wanted or (c.get("nickname") or "").lower().split("-")[0] in wanted)
    ]
    return {
        "total": len(vendor),
        "merchantLocked": sum(1 for c in vendor if merchant(c) in wanted),
        "capped": sum(1 for c in vendor if monthly_cap_usd(c) is not None),
        "capCoversGuardrails": None,
        "declines30d": declines,
    }


def build_summary(cards: dict | None, now: datetime) -> dict:
    # voidlight requires every key. With no keys or guardrails left, there is
    # nothing to be out of sync or low on credit.
    return {
        "version": 1,
        "generatedAt": now.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "tiers": [],
        "allowlistsInSync": True,
        "creditLow": False,
        "cards": cards,
    }


def signature(secret: str, timestamp: str, body: str) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def mercury(path: str, token: str) -> dict:
    req = urllib.request.Request(MERCURY_API + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_cards(token: str, merchants: list[str], today: date) -> dict:
    cards = mercury("/cards?type=virtual&status=active&limit=1000", token).get("cards", [])
    summary = card_summary(cards, 0, merchants)
    vendor_ids = [
        c["id"] for c in cards
        if ((c.get("merchantLock") or {}).get("name") or "").lower() in {m.lower() for m in merchants}
    ]
    if vendor_ids:
        since = (today - timedelta(days=30)).isoformat()
        query = "&".join(
            [f"cardId={i}" for i in vendor_ids] + ["status=failed", "status=blocked", f"start={since}", "limit=1000"]
        )
        summary["declines30d"] = len(mercury(f"/transactions?{query}", token).get("transactions", []))
    return summary


def cmd_publish(dry_run: bool) -> None:
    token = os.environ.get("MERCURY_API_TOKEN") or keyring.get_password(SERVICE, "mercury")
    cards = fetch_cards(token, CARD_MERCHANTS, date.today()) if token else None

    summary = build_summary(cards, datetime.now(UTC))
    body = json.dumps(summary, separators=(",", ":"))
    if dry_run:
        print(json.dumps(summary, indent=2))
        return
    secret = os.environ.get("VOIDLIGHT_INGEST_SECRET") or keyring.get_password(SERVICE, "voidlight-ingest")
    if not secret:
        sys.exit(f"publish needs `keyring set {SERVICE} voidlight-ingest`")
    timestamp = str(int(time.time() * 1000))
    req = urllib.request.Request(
        PUBLISH_URL,
        method="POST",
        data=body.encode(),
        headers={
            "Content-Type": "application/json",
            "X-Voidlight-Timestamp": timestamp,
            "X-Voidlight-Signature": signature(secret, timestamp, body),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"published ({resp.status})")
    except urllib.error.HTTPError as e:
        sys.exit(f"publish: HTTP {e.code} {e.read().decode(errors='replace')[:200]}")


def main(argv: list[str]) -> None:
    match argv:
        case ["publish"] | ["publish", "--dry-run"]:
            cmd_publish(dry_run="--dry-run" in argv)
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
