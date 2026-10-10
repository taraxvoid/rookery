#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["keyring>=25"]
# ///
"""Reconcile OpenRouter keys + guardrails against nest/spend.toml.

  plan            diff OpenRouter against spend.toml (default; read-only)
  apply           create/patch keys and guardrails to match; idempotent
  report          per-key spend (day/week/month) and credit balance
  env [--sh]      print `set -gx VAR key` lines (fish) from the keychain
  rotate <id>     delete and recreate one key, storing the new secret
  publish [--dry-run]
                  push an amount-free containment summary to voidlight's
                  /ingest/spend (signed); --dry-run prints it instead

Secrets live in the OS keychain via `keyring` (macOS Keychain, Secret Service
on Linux), service "rookery-openrouter" — never in a file an agent with Bash
can read. The management key is account "management"; store it once with
`keyring set rookery-openrouter management`. OPENROUTER_MANAGEMENT_KEY in the
environment overrides it, for a one-off run.
"""

import hashlib
import hmac
import json
import os
import re
import sys
import time
import tomllib
from datetime import UTC, date, datetime, timedelta
import urllib.error
import urllib.request
from pathlib import Path

import keyring

NEST = Path(__file__).parent
API = os.environ.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")  # override only for testing
MERCURY_API = os.environ.get("MERCURY_API_BASE", "https://api.mercury.com/api/v1")  # override only for testing
SERVICE = "rookery-openrouter"
# Monthly-equivalent multipliers for Mercury card spend-limit intervals.
INTERVAL_TO_MONTH = {"daily": 30, "weekly": 52 / 12, "monthly": 1, "yearly": 1 / 12}


def strip_jsonc_comments(text: str) -> str:
    # Same rule as validate.py: line comments only.
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def kilo_models_by_env() -> dict[str, set[str]]:
    models: dict[str, set[str]] = {}
    for path in sorted((NEST / "kilo").glob("*.jsonc")):
        config = json.loads(strip_jsonc_comments(path.read_text()))
        model = config.get("model", "")
        if not model.startswith("openrouter/"):
            continue  # local ollama birds spend nothing
        for env in config.get("provider", {}).get("openrouter", {}).get("env", []):
            models.setdefault(env, set()).add(model.removeprefix("openrouter/"))
    return models


def desired() -> dict[str, dict]:
    spec = tomllib.loads((NEST / "spend.toml").read_text())
    by_env = kilo_models_by_env()
    out = {}
    for key_id, k in spec["keys"].items():
        out[key_id] = {
            "name": k["name"],
            "env": k["env"],
            "key": {"limit": k["limit_usd"], "limit_reset": k["limit_reset"]},
            "guardrail": {
                "allowed_models": sorted(by_env.get(k["env"], set()) | set(k.get("extra_models", []))),
                "limit_usd": k["guardrail"]["limit_usd"],
                "reset_interval": k["guardrail"]["reset_interval"],
            },
        }
    return out | {"_credits": spec.get("credits", {})}


def management_key() -> str:
    key = os.environ.get("OPENROUTER_MANAGEMENT_KEY") or keyring.get_password(SERVICE, "management")
    if not key:
        sys.exit(f"no management key: `keyring set {SERVICE} management` (or set OPENROUTER_MANAGEMENT_KEY)")
    return key


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {management_key()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")
    return json.loads(raw) if raw else {}


def paged(path: str) -> list[dict]:
    # Page size differs per endpoint (/keys takes no limit param), so walk
    # until an empty page rather than guessing it.
    items: list[dict] = []
    sep = "&" if "?" in path else "?"
    for _ in range(50):
        page = call("GET", f"{path}{sep}offset={len(items)}").get("data", [])
        if not page:
            return items
        items += page
    sys.exit(f"GET {path}: still paging after 50 pages — offset ignored?")


def current() -> tuple[dict, dict, dict]:
    keys = {k["name"]: k for k in paged("/keys")}
    guardrails = {g["name"]: g for g in paged("/guardrails?limit=100")}
    assigned = {a["key_hash"]: a["guardrail_id"] for a in paged("/guardrails/assignments/keys?limit=100")}
    return keys, guardrails, assigned


def diff(want: dict, have: dict) -> dict:
    return {f: v for f, v in want.items() if (sorted(have.get(f) or []) if isinstance(v, list) else have.get(f)) != v}


def plan_actions() -> list[tuple[str, str, dict]]:
    want = desired()
    want.pop("_credits")
    keys, guardrails, assigned = current()
    actions = []
    for key_id, w in want.items():
        name = w["name"]
        if not w["guardrail"]["allowed_models"]:
            sys.exit(f"{key_id}: no models — no nest/kilo config uses {w['env']} and extra_models is empty")

        g = guardrails.get(name)
        if g is None:
            actions.append(("create-guardrail", name, {"name": name, **w["guardrail"]}))
        elif changes := diff(w["guardrail"], g):
            actions.append(("patch-guardrail", name, changes))

        k = keys.get(name)
        if k is None:
            actions.append(("create-key", name, {"name": name, **w["key"]}))
        else:
            if changes := diff(w["key"], k):
                actions.append(("patch-key", name, changes))
            if keyring.get_password(SERVICE, w["env"]) is None:
                print(f"warn: {name} exists but its secret isn't in the keychain — `spend.py rotate {key_id}`")

        if k is None or g is None or assigned.get(k["hash"]) != g["id"]:
            actions.append(("assign", name, {}))
    return actions


def cmd_plan() -> None:
    actions = plan_actions()
    for verb, name, body in actions:
        print(f"{verb:17} {name}  {json.dumps(body) if body else ''}")
    print("no changes" if not actions else f"{len(actions)} change(s) — `spend.py apply` to make them")


def cmd_apply() -> None:
    envs = {w["name"]: w["env"] for k, w in desired().items() if k != "_credits"}
    for verb, name, body in plan_actions():
        keys, guardrails, _ = current()
        match verb:
            case "create-guardrail":
                call("POST", "/guardrails", body)
            case "patch-guardrail":
                call("PATCH", f"/guardrails/{guardrails[name]['id']}", body)
            case "create-key":
                created = call("POST", "/keys", body)
                keyring.set_password(SERVICE, envs[name], created["key"])
            case "patch-key":
                call("PATCH", f"/keys/{keys[name]['hash']}", body)
            case "assign":
                call("POST", f"/guardrails/{guardrails[name]['id']}/assignments/keys", {"key_hashes": [keys[name]["hash"]]})
        print(f"{verb:17} {name}  done")
    cmd_plan()  # should now say "no changes"


def cmd_rotate(key_id: str) -> None:
    w = desired().get(key_id) or sys.exit(f"unknown key id {key_id!r}")
    keys, _, _ = current()
    if (k := keys.get(w["name"])) is not None:
        call("DELETE", f"/keys/{k['hash']}")
    created = call("POST", "/keys", {"name": w["name"], **w["key"]})
    keyring.set_password(SERVICE, w["env"], created["key"])
    print(f"rotated {w['name']}")
    cmd_apply()  # the new key has no guardrail until reassigned


def cmd_report() -> None:
    want = desired()
    credits = want.pop("_credits")
    keys, _, _ = current()
    print(f"{'key':16} {'today':>8} {'week':>8} {'month':>8} {'left':>8}")
    for w in want.values():
        k = keys.get(w["name"])
        if k is None:
            print(f"{w['name']:16} (not created)")
            continue
        left = "—" if k["limit_remaining"] is None else f"{k['limit_remaining']:.2f}"
        print(f"{w['name']:16} {k['usage_daily']:8.2f} {k['usage_weekly']:8.2f} {k['usage_monthly']:8.2f} {left:>8}")
    c = call("GET", "/credits")["data"]
    balance = c["total_credits"] - c["total_usage"]
    flag = "  LOW" if balance < credits.get("warn_below_usd", 0) else ""
    print(f"\ncredit balance  ${balance:.2f}{flag}")


def cmd_env(sh: bool) -> None:
    for key_id, w in desired().items():
        if key_id == "_credits":
            continue
        secret = keyring.get_password(SERVICE, w["env"])
        if secret is None:
            print(f"# {w['env']}: not in keychain", file=sys.stderr)
        elif sh:
            print(f"export {w['env']}={secret}")
        else:
            print(f"set -gx {w['env']} {secret}")


# --- publish: amount-free containment summary for voidlight -----------------
#
# Everything below the fetch layer is pure, so tests/test_spend.py checks the
# summary from fake API responses. What leaves this machine is ratios, flags
# and counts: never a dollar amount, balance, key name or card detail.
# voidlight re-validates the exact shape (its src/spend.ts) and rejects extras.


def ratio(used: float | None, limit: float | None) -> float | None:
    if used is None or not limit:
        return None
    return round(used / limit, 4)


def tier_usage(want: dict, keys: dict) -> list[dict]:
    tiers = []
    for key_id, w in want.items():
        k = keys.get(w["name"]) or {}
        tiers.append({
            "id": key_id,
            "dayUsed": ratio(k.get("usage_daily"), w["key"]["limit"]),
            "monthUsed": ratio(k.get("usage_monthly"), w["guardrail"]["limit_usd"]),
        })
    return tiers


def monthly_cap_usd(card: dict) -> float | None:
    limit = card.get("spendLimit") or {}
    cents, interval = limit.get("amountCents"), limit.get("interval")
    if cents is None or interval not in INTERVAL_TO_MONTH:
        return None
    return cents / 100 * INTERVAL_TO_MONTH[interval]


def card_summary(cards: list[dict], declines: int, merchants: list[str], guardrail_total: float) -> dict:
    """Containment counts over the active virtual cards for the given vendors.

    capCoversGuardrails compares the OpenRouter card's monthly-equivalent cap
    with the sum of monthly guardrail limits (spend.toml's rule: the card must
    not decline before a guardrail trips). None while there's no such card.
    """
    wanted = {m.lower() for m in merchants}

    def merchant(c: dict) -> str:
        return ((c.get("merchantLock") or {}).get("name") or "").lower()

    vendor = [
        c for c in cards
        if c.get("status") == "active" and c.get("type") == "virtual"
        and (merchant(c) in wanted or (c.get("nickname") or "").lower().split("-")[0] in wanted)
    ]
    openrouter = [c for c in vendor if merchant(c) == "openrouter"]
    caps = [monthly_cap_usd(c) for c in openrouter]
    covers = None if not openrouter or None in caps else sum(caps) >= guardrail_total
    return {
        "total": len(vendor),
        "merchantLocked": sum(1 for c in vendor if merchant(c) in wanted),
        "capped": sum(1 for c in vendor if monthly_cap_usd(c) is not None),
        "capCoversGuardrails": covers,
        "declines30d": declines,
    }


def build_summary(want: dict, keys: dict, in_sync: bool, credit_low: bool, cards: dict | None, now: datetime) -> dict:
    return {
        "version": 1,
        "generatedAt": now.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "tiers": tier_usage(want, keys),
        "allowlistsInSync": in_sync,
        "creditLow": credit_low,
        "cards": cards,
    }


def signature(secret: str, timestamp: str, body: str) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def mercury(path: str, token: str) -> dict:
    req = urllib.request.Request(MERCURY_API + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_cards(token: str, merchants: list[str], guardrail_total: float, today: date) -> dict:
    cards = mercury("/cards?type=virtual&status=active&limit=1000", token).get("cards", [])
    summary = card_summary(cards, 0, merchants, guardrail_total)
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
    spec = tomllib.loads((NEST / "spend.toml").read_text())
    pub = spec.get("publish", {})
    want = desired()
    credits = want.pop("_credits")
    keys, _, _ = current()
    in_sync = not plan_actions()
    c = call("GET", "/credits")["data"]
    credit_low = c["total_credits"] - c["total_usage"] < credits.get("warn_below_usd", 0)

    token = os.environ.get("MERCURY_API_TOKEN") or keyring.get_password(SERVICE, "mercury")
    guardrail_total = sum(w["guardrail"]["limit_usd"] for w in want.values())
    cards = fetch_cards(token, pub.get("card_merchants", []), guardrail_total, date.today()) if token else None

    summary = build_summary(want, keys, in_sync, credit_low, cards, datetime.now(UTC))
    body = json.dumps(summary, separators=(",", ":"))
    if dry_run:
        print(json.dumps(summary, indent=2))
        return
    secret = os.environ.get("VOIDLIGHT_INGEST_SECRET") or keyring.get_password(SERVICE, "voidlight-ingest")
    if not secret or not pub.get("url"):
        sys.exit(f"publish needs [publish].url in spend.toml and `keyring set {SERVICE} voidlight-ingest`")
    timestamp = str(int(time.time() * 1000))
    req = urllib.request.Request(
        pub["url"],
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
        case [] | ["plan"]:
            cmd_plan()
        case ["apply"]:
            cmd_apply()
        case ["report"]:
            cmd_report()
        case ["env"] | ["env", "--sh"]:
            cmd_env(sh="--sh" in argv)
        case ["rotate", key_id]:
            cmd_rotate(key_id)
        case ["publish"] | ["publish", "--dry-run"]:
            cmd_publish(dry_run="--dry-run" in argv)
        case _:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
