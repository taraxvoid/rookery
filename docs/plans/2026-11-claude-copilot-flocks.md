# Plan: drop Kilo; Claude for dev, Copilot + gh-aw for chores; flocks

Status: proposal, 2026-11-02. Nothing here is built yet. This revision replaces
the earlier version, which tried to keep Kilo + OpenRouter.

## Decision

- **Drop Kilo and OpenRouter.**
- **Claude Code** handles attended, substantial software work: crow, raven and
  their read-only subagents.
- **Copilot through gh-aw** ([GitHub Agentic Workflows](https://github.com/github/gh-aw))
  handles unattended, scheduled and chore work: digests, cruft, scans and
  cross-family review.
- rookery stays the **policy layer**: personas, tier rules, a validator that
  checks prose against enforcement, the council and the roost. Today it renders
  that policy into Kilo configs. Afterwards it renders it into Claude Code
  settings and gh-aw workflows.
- One operator's deployment is a **flock**: `flocks/<name>/`. ravenflight is the
  first, and is documented as the worked example. (`ravenflight/flock`, the
  runner repo, keeps its name. A flock is a directory here, so the two don't
  collide on disk, but say "a rookery flock" in prose wherever it's ambiguous.)

## Why dropping Kilo is worth it

Each thing Kilo was bought for now has a replacement in the two runtimes being
kept:

| Kilo gave | Replacement | Notes |
|---|---|---|
| Per-pattern `bash` permissions that are actually enforced | Claude Code **settings-level** permission rules (`nest/claude/settings.json`, already enforced). In gh-aw, the agent job has a read-only token and every write goes through safe outputs | Only subagent `tools:` frontmatter ignores patterns (anthropics/claude-code#61651); settings rules don't |
| OS sandbox (Seatbelt / Bubblewrap), network deny | gh-aw's AWF container plus firewall `network.allowed` for unattended runs. Claude Code's own sandbox for attended runs | Verify the current Claude Code sandbox settings before relying on them |
| Per-persona model routing | Claude subagent `model:` (haiku / sonnet / opus). gh-aw `engine.model` per workflow | Routing per persona was the reason for Kilo; both runtimes do it natively |
| Cross-family reviewer (jackdaw ≠ Claude) | jackdaw as a gh-aw workflow on a non-Claude Copilot model (GPT or Gemini family) | Keeps the council's core rule (#4) without OpenRouter |
| $0 / open-weight tier-0 models | **Lost.** Tier 0 becomes "cheapest vendor model" (Haiku, a Copilot base model) | No usage data showed free models earned their unreliability |
| OpenRouter guardrails as code (`spend.py`) | Copilot: premium-request budget plus gh-aw `max-ai-credits` per run. Claude: subscription for attended use, an API key with a workspace spend limit for anything headless | `spend.py` shrinks to reporting; see Phase 3 |

It also removes a whole harness from the trust model, and two items of work
nothing was blocked on:
- the orchestrator evaluation (#5);
- moving crow/raven to Kilo (#3).

It also settles ravenflight/rookery#20's concern without Kilo. That concern was
unattended runs eating the Claude subscription, and unattended work moves to
Copilot under this plan.

**What's lost, and accepted:**
- free models;
- being able to pick from all of OpenRouter's catalog;
- one spend control plane. Two vendors bill separately; the Mercury card
  remains the outer bound for whatever it pays.

## Self-review carried forward

These still hold from the first assessment's corrections:
- Issue text must not steer an agent.
- gh-aw moves fast: pin the compiler version and commit the lock files. (It
  went [GA on 2026-10-28](https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available/);
  the "preview" in the first assessment was out of date. voidchores pins
  v1.0.1.)
- taraxvoid/rookery and ravenflight/rookery have already drifted, so there
  should be one source of truth.

What changed: the custom-engine and OpenRouter risks are gone. Copilot is gh-aw's
default engine, so the documented guarantees apply as written: AWF sandbox,
firewall, threat detection and safe outputs.

## Runtime map

| Persona | Runtime | Shape |
|---|---|---|
| raven | Claude Code, attended | opus. Safe-git settings. Council via jackdaw workflows |
| crow | Claude Code, attended (`claude-code-action` only for explicitly dispatched issues) | sonnet. Safe-git settings |
| magpie, shrike, kingfisher | Claude Code subagents | haiku; `tools: Read, Grep, Glob` (no Bash in any form, as today) |
| jackdaw | gh-aw + Copilot, on `pull_request` | Non-Claude model. Safe output: a PR review or comment only |
| owl, tern | gh-aw + Copilot, `schedule` | `create-issue` with `close-older-issues`; network allowlist = their data sources |
| wren | gh-aw + Copilot, `schedule` | `create-pull-request` (`draft: true`, `allowed-files`, size caps): cruft fixes |
| canary | gh-aw `steps:` run gitleaks/grype deterministically; Copilot only triages the output | No shell for the agent; the scanners aren't agent tools |
| vixen | not live (#14 unchanged) | — |

voidchores fits gh-aw's strongest use case: scheduled, repo-scoped chores with
writes that are filtered and kept small. Treat it as the home for one flock's
unattended workflows. Every workflow there imports a persona fragment from
rookery pinned to a SHA.

## Target shape

```
agents/  skills/  roost/        unchanged: persona definitions
nest/
  claude/settings.json          unchanged: safe-git policy for attended runs
  gh-aw/shared/<bird>.md        NEW: rendered fragments (engine, model, tools, network, safe-outputs)
  render.py                     NEW: agents/*.md + tier table -> nest/gh-aw/
  report.py                     spend.py reduced to reporting (Copilot + Anthropic usage) and publish
flocks/
  README.md                     what a flock is; how to start one
  example/                      template, no real values
  ravenflight/
    flock.toml                    repos covered, labels, runners, GitHub App, budgets
    roost/                        ravenflight-specific lessons
    README.md                     "how ravenflight runs rookery"
docs/decisions/                 0001 Kilo+OpenRouter (from ravenflight#20, superseded), 0002 this decision
```

`nest/kilo/` and `nest/spend.toml` are removed. They stay in history, and ADR
0001 records why they existed and why they went, which makes a better story
than either alone.

## Phases

### Phase 0: one source of truth

1. Write `docs/decisions/0001` (the Kilo + OpenRouter rationale from
   ravenflight#20, marked superseded) and `0002` (this decision).
2. Add `flocks/ravenflight/`. `flock.toml` carries:
   - the repos covered (ravenflight.io, rvnflt, flock, rookery)
   - the labels
   - the self-hosted runner toggle (ported from ravenflight#26)
   - the `ravenflight-aviary` App name (ravenflight#14)
   - per-vendor budgets as the operator's record

   Move the ravenflight.io roost entries there.
3. `validate.py` checks each flock's schema and fails loudly if `flocks/` is
   empty.
4. Migrate ravenflight/rookery's open issues and archive it:
   - #20 and #22 close as superseded;
   - #14, #21 and #23 move over, with #21 rewritten for the new billing.

Semver: tag `v0.1.0` before this phase. Phase 0 is additive, so it's `v0.2.0`.

### Phase 1: gh-aw + Copilot, read-only first (one evening)

In voidchores, or a scratch repo:
1. owl- or tern-shaped `schedule` workflow: Copilot engine, `strict: true`,
   read permissions, `create-issue` only, `network.allowed` minimal. Check that
   it runs, the issue lands, and the per-run cost (premium requests plus
   threat detection).
2. jackdaw-shaped `pull_request` workflow on a non-Claude model. Confirm which
   model families Copilot exposes in gh-aw (`engine.model`), and that the
   review lands as a comment only.
3. wren-shaped workflow with `create-pull-request`, `draft: true` and
   `allowed-files`. A run that touches a disallowed path must be refused.
4. Issue-text exposure: the prompt contains only what the workflow body
   interpolates.

**Pass** (expected, since these are documented built-in paths): proceed.
**Fail**: record it in ADR 0002 and keep `agent-dispatch.yml`.

### Phase 2: render, validate, remove Kilo

1. `nest/render.py` emits `nest/gh-aw/shared/<bird>.md` for every gh-aw
   persona. Tier sets the ceiling on safe outputs, per the runtime map. Every
   fragment sets:
   - `strict: true`
   - a pinned engine version
   - `max-turns` from `maxTurns`
   - `max-ai-credits`
   - threat detection on
2. `validate.py`:
   - Drop the Kilo checks.
   - Add a drift check: rendered output must match what's committed.
   - Add widening checks: a flock workflow imports a persona fragment and adds
     no write `permissions`, no extra safe-output types, no
     `threat-detection: false`, and no `network` wildcard.
   - Keep the Claude settings checks and the no-Bash-in-read-only-`tools:`
     rule.
3. Replace `agent-dispatch.yml` with `agent-dispatch.md`:
   - trigger: `names: [agent:ready]`
   - `roles: [admin, maintainer, write]`
   - the author-association gate
   - engine: Claude, for a crow-shaped task with an API key in an
     environment-scoped secret; or Copilot, if the task is chore-sized

   This closes #11, and covers #8 via `safe-outputs.github-app`.
4. Delete `nest/kilo/`. Rewrite the `model:` comments in `agents/*.md`.
   Update the README's Enforcement table.
5. Close #3 and #5 as superseded. #6 becomes "network.allowed per gh-aw
   persona". #12 is mostly done by owl/tern workflows filing issues.

Semver: removing Kilo removes a supported runtime, so this is breaking. Pre-1.0
that's a **minor** bump, `v0.3.0`; say so in the release notes.

### Phase 3: spend, slimmed

`spend.py` becomes `report.py`:
- reads Copilot premium-request usage (GitHub billing API) and Anthropic usage
  (Admin API, if a key is used for headless Claude);
- maps usage to personas via workflow name or subagent;
- keeps `publish` to voidlight with the same amount-free schema.

#10 (per-persona spend) becomes easier, because each gh-aw workflow is one
persona.

### Phase 4: flocks consume rookery

- voidchores and the ravenflight repos import fragments
  `taraxvoid/rookery/nest/gh-aw/shared/<bird>.md@<sha>`. Renovate bumps the
  pins.
- Self-hosted runners for gh-aw must be Linux with Docker, disposable, carry no
  ambient credentials, and sit in a runner group separate from release jobs.
- README reframe: "a policy layer over Claude Code and gh-aw". The ADRs carry
  the narrative.

## Not changing

- The tier model, and the "dispatch only goes down" rule
- The council, including #4's rule that reviewers differ in family from the
  author
- The roost (#13)
- The label state machine
- The safe-git policy
- "Nothing happens without an explicit signal"

## Risks

- **gh-aw is newly GA (v1.x) and releases often.** Pin the
  compiler, keep lock files committed, and rely on the drift check.
- **Copilot's model list decides council diversity.** If it can't offer a
  non-Claude family at a sane price, jackdaw needs another provider (an
  OpenAI key on the Codex engine is the smallest step).
- **Headless Claude for dispatched crow work bills an API key.** Keep it
  explicit-signal-only, with an environment-scoped secret and a workspace spend
  limit.

## Sources

- [gh-aw](https://github.com/github/gh-aw)
- gh-aw reference docs:
  - [engines](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/engines.md)
  - [threat detection](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/threat-detection.md)
  - [sandbox](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/sandbox.md)
  - [self-hosted runners](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/self-hosted-runners.md)
  - [triggers](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/triggers.md)
  - [PR safe outputs](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/safe-outputs-pull-requests.md)
- [Security architecture of GitHub Agentic Workflows](https://github.blog/2026/03/09/under-the-hood-security-architecture-of-github-agentic-workflows/)
- ravenflight/rookery issues #14, #20–#23 and history through `4ae9f6a`
