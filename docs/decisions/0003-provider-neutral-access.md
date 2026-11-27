# 0003: Provider-neutral access plane; OpenRouter as its first backend

- Status: **proposed**
- Date: 2026-11-26
- Amends: [0002](0002-claude-copilot-gh-aw.md) (keeps its runtimes, reverses
  its "drop OpenRouter")

## Context

0002 dropped Kilo and OpenRouter together and left spend with each vendor:
Copilot premium requests, an Anthropic workspace limit, a card per vendor.
Two problems showed up within three weeks:

- **Lock-in by default.** Every limit now lives in a vendor console. Moving a
  persona from one model family to another means a new account, a new key, a
  new limit and a new card. The council's cross-family rule (#4) gets more
  expensive to keep with every vendor added.
- **One flaky vendor stops everything.** Copilot returned HTTP 429 to both
  voidlife drivers on 2026-11-24 (taraxvoid/voidlife#48, #50), and nothing
  could route around it.

Kilo was the right thing to drop: Claude Code and gh-aw now enforce tool,
shell and sandbox rules natively. OpenRouter was dropped with it but was doing
a different job: access, scope and cost per key, independent of the harness.

## Decision

- rookery declares **access** in one provider-neutral file,
  `nest/access.toml`: per tier, the allowed model families, a budget, a reset
  period, and whether prompts may be retained. Nothing in it names a gateway.
- A **backend adapter** reconciles a gateway to that file (`plan`, `apply`,
  `report`, `rotate`). The first backend is OpenRouter, restoring what
  `nest/spend.py` did before 0002: per-tier keys, each with a guardrail
  (model and provider allowlist, credit limit, zero data retention). The
  management key stays in the OS keychain.
- **Harnesses stay as 0002 has them**, and point at the gateway only where
  it pays:
  - attended Claude Code stays on the subscription, direct. A subscription
    can't be routed through a gateway, and per-token pricing plus a gateway
    fee costs more for the hours of attended work;
  - every metered, headless or unattended run (gh-aw non-Copilot engines,
    `claude -p` digests, the cross-family reviewer) uses a tier key from the
    gateway.
- `validate.py` gains a check that every persona's `model:` and every
  gh-aw `engine.model` rookery renders is allowed by its tier in
  `access.toml`, as it once derived allowlists from the Kilo configs.

## Why OpenRouter first, and the exit

| Option | For | Against |
|---|---|---|
| **OpenRouter** (managed) | Per-key guardrails already cover allowlists, budget, ZDR and regions; zero ops; `spend.py` and its tests exist in history; Claude Code supports it through `ANTHROPIC_BASE_URL` | 5.5% fee on credits; Stripe agreed to acquire it (2026-08-19), so terms may change |
| **LiteLLM** (self-hosted, MIT) | Virtual keys and budgets in the open-source build; no fee | Postgres and Redis to run; compromised PyPI releases in March and October 2026, a hard sell for a security practice |
| **Vercel AI Gateway** | Budgets per key, no token markup | Another platform account; not otherwise in the stack |
| **Cloudflare AI Gateway** | Already in the stack; caching, rate limits, logs | No per-key budgets or model allowlists in the comparisons read; logging on by default |
| Portkey, Bifrost | Strong governance | Pitched at teams; more than one operator needs |

OpenRouter wins on "works this week with code that already existed". The
neutral `access.toml` is what keeps it from becoming lock-in: the exit is a
second adapter (LiteLLM or Vercel are the likely ones, both
OpenAI-compatible), not a rewrite. Re-check this table at each research
sweep; the voidlife baseline should Watch the gateway space.

## Consequences

- `nest/spend.py`, `nest/spend.toml` and `tests/test_spend.py` come back from
  history (before 077ac01), split into `nest/access.toml` (neutral) and
  `nest/backends/openrouter.py` (adapter).
- `nest/report.py` keeps publishing the amount-free containment summary;
  `tiers` fills in from the adapter's `report` again.
- The Mercury card for OpenRouter stays as the outer bound. Don't revoke the
  `rookery-tier*` keys or the management key yet (README "Leaving
  OpenRouter" is withdrawn).
- Two bills remain (subscription and gateway) but every metered key is in one
  place with one set of limits.

## Open questions to settle before "accepted"

1. Does gh-aw's `claude` engine honour `ANTHROPIC_BASE_URL` and an
   `ANTHROPIC_AUTH_TOKEN`, or does it need a custom engine? Test on
   `research-claude` in voidlife first.
2. Which non-Claude family reviews (jackdaw), and at what tier budget?
3. Does `claude-code-action` accept a gateway key? Reports say it requires
   `anthropic_api_key` and ignores `ANTHROPIC_AUTH_TOKEN`; `agent-dispatch.yml`
   may need to pass the gateway key through that input.
