# ravenflight

How [RavenFlight](https://ravenflight.io) runs rookery. This is the reference
flock: a real deployment, kept in the public repo so the shared rules always
have one concrete user to answer to.

It replaces ravenflight/rookery, the private repo rookery was split from.

## Repos

[`flock.toml`](flock.toml) lists them:

| Repo | What it is |
|---|---|
| `ravenflight/ravenflight.io` | Production site |
| `ravenflight/rvnflt` | BUSINESS.MD parser and CLI |
| `ravenflight/flock` | Self-hosted runner infrastructure. The name predates flocks; it's unrelated to this directory |
| `taraxvoid/rookery` | This repo |

Every repo carries the shared labels from
[`.github/labels.yml`](../../.github/labels.yml). Repos in the `ravenflight`
org without their own PR template fall back to the org default in
`ravenflight/.github`, which asks how the change was verified and whether an
agent wrote it.

## Where personas run

The flock is moving to [decision 0002](../../docs/decisions/0002-claude-copilot-gh-aw.md):

| Personas | Runtime | State |
|---|---|---|
| crow, raven, magpie, shrike, kingfisher | Claude Code, attended, bounded by [`nest/claude/settings.json`](../../nest/claude/settings.json) | live |
| owl, tern, wren, canary triage, jackdaw | gh-aw + Copilot | planned (0002 Phase 1 and 2) |
| read-only birds on Kilo | `nest/kilo/` | until 0002 Phase 2 removes it |
| vixen | none | not live; needs promotion criteria first (taraxvoid/rookery#14) |

vixen's goal state for this flock: wake up to clean repos, stable production, a
proposed staging merge ready to review, new issues filed for work too complex
for the birds alone, and a digest of what needs the operator's judgment.

## Environments

ravenflight.io deploys in three steps:
1. `main` deploys a protected preview at `dev.` Crows can merge there once CI
   and a jackdaw review pass.
2. Ravens promote `dev.` to `next.` (staging) through the project's release
   flow.
3. Production stays a human decision.

Ravens watch `dev.` and `next.` after promoting. The monitoring wiring (Sentry,
PostHog, logs) is still open in taraxvoid/rookery#7.

## GitHub App

`ravenflight-aviary` is planned and not created yet. It's a separate App from
`ravenflight-releases`, the App release-please mints tokens from, so the two
credentials sit in separate trust domains. Setup needs an org owner in the
GitHub UI:

1. Org Settings → Developer settings → GitHub Apps → New GitHub App, named
   `ravenflight-aviary`.
2. Webhook **off**: the App only mints installation tokens inside workflows.
3. Repository permissions: Contents, Pull requests and Issues, each read and
   write (Metadata read-only is added automatically).
4. "Only on this account"; install it on the `ravenflight` org with **All
   repositories**.
5. Generate a private key and keep it out of chat and screen shares.
6. Add org-level secrets `AVIARY_BOT_CLIENT_ID` and
   `AVIARY_BOT_APP_PRIVATE_KEY`. The names follow the existing
   `RELEASE_BOT_*` convention.

Each workflow then mints a token with `actions/create-github-app-token` and
narrows it with its `permission-*` inputs. A PR-only workflow, for example,
omits `permission-issues`. The tracking issue is taraxvoid/rookery#8.

## Runners

GitHub-hosted by default. Set the repo variable `SELF_HOSTED_RUNNERS=true` to
route CI to the `rookery`-labeled runners from `ravenflight/flock`. gh-aw jobs
on self-hosted runners need Linux and Docker, disposable hosts, no ambient
credentials, and a runner group separate from release jobs.

## Spend

The outer bound is a merchant-locked, spend-capped Mercury virtual card. Keep
the card's monthly cap at or above the sum of the per-vendor limits, or the
card declines before a vendor limit ever trips, which is harder to diagnose.
Per-vendor limits after 0002: Copilot premium requests (GitHub billing) and,
for any headless Claude use, an Anthropic workspace spend limit.

## Roost

Lessons specific to these repos live in [`roost/`](roost/LEARNED.md). The
shared [`roost/`](../../roost/LEARNED.md) holds the ones that apply anywhere.
