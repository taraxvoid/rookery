# Plan: gh-aw as the CI runtime, ravenflight as a first-class colony

Status: proposal, 2026-11-02. Nothing here is built yet.

## Summary

- gh-aw ([GitHub Agentic Workflows](https://github.com/github/gh-aw)) is a
  credible **CI runtime** for rookery personas. It replaces the hand-rolled
  `agent-dispatch.yml`. It does not replace these, which are rookery's own:
  - the persona and tier model
  - spend-as-code
  - the validator that checks persona prose against enforcement
  - local Kilo runs
  - the council and the roost
- rookery becomes the **policy layer** that renders per-persona gh-aw workflow
  fragments and checks them, as it already does for Kilo and Claude Code
  settings.
- The ravenflight setup moves into this repo as `colonies/ravenflight/`: the
  reference deployment, validated in CI. Then ravenflight/rookery stops being a
  diverging fork.
- One blocking unknown: whether gh-aw can run on the Kilo + OpenRouter footing
  that ravenflight/rookery#20 committed to. Phase 1 is a time-boxed spike to
  answer that before anything is migrated.

## Self-review of the first assessment

The first pass was made without reading ravenflight/rookery or the gh-aw docs.
These corrections change the plan.

1. **It missed the harness decision.** ravenflight/rookery#20 (2026-10-06)
   settled that the whole nest runs on Kilo + OpenRouter. Claude Code stays the
   operator's interactive harness, and nothing automated draws on the Claude
   subscription. "Swap `claude-code-action` for gh-aw's Claude engine" breaks
   that decision. gh-aw only fits if one of these works:
   - **Kilo as a custom engine.** gh-aw supports imported engine definitions
     (`engine.id` plus `imports:`) and ships an unsupported OpenCode sample.
     Kilo is OpenCode-derived, so this is plausible. Unverified.
   - **A built-in engine pointed at OpenRouter.**
     - Codex engine: `OPENAI_BASE_URL` set through `engine.env`, with
       `openrouter.ai` in `network.allowed`.
     - Claude engine: `ANTHROPIC_BASE_URL`, which #20 rejected for local use.

     One of #20's reasons for rejecting option B was "models only routable per
     process, not per persona". It doesn't apply in gh-aw, where one workflow
     runs one persona. OpenRouter's warning that Claude Code may misbehave with
     non-Anthropic models still applies.
2. **The gh-aw security story is weaker for custom engines.** The docs say:
   - the AWF sandbox and firewall are documented only for built-in engines;
   - "gh-aw does not guarantee native-agent restrictions just because a
     definition compiles";
   - threat detection runs on **Copilot** by default when the main engine is
     custom, though it can be set to `claude` or `codex`, or turned off;
   - model routing rejects BYOK and custom base URLs.

   Running on custom engines or OpenRouter therefore gives up some of what makes
   gh-aw attractive. The spike has to measure how much.
3. **"Copilot premium requests" was the wrong cost frame.** That applies only
   to the Copilot engine. With BYOK, inference bills to OpenRouter, so
   `spend.py` guardrails still bound it. Threat detection has its own credit
   budget (default 400 per run) on whatever engine it uses.
4. **gh-aw belongs in the existing orchestrator evaluation.** taraxvoid#5 /
   ravenflight#22 already evaluate Agent Orchestrator against a thin dispatch
   daemon. gh-aw is a third candidate, and it answers most of #11's checklist
   directly:

   | #11 item | gh-aw feature |
   |---|---|
   | Persona selection from a maintainer-set label | `on.issues.names`, `on.roles` |
   | Side effects as fixed steps after an output check | safe outputs: `create-pull-request` with `allowed-files`, `max-patch-files`, `max-patch-size`, protected files, `draft` as policy |
   | App identity | `safe-outputs.github-app` (#8) |

   gh-aw runs on Linux only (Actions or self-hosted Linux with Docker). The
   Mac/Seatbelt path stays, so gh-aw complements the local dispatch path and
   doesn't replace it.
5. **The "trim tier-0 personas" advice was unfounded.** Drop it. Per-persona
   spend data (#10) should decide that, not a guess.
6. **taraxvoid/rookery is not a strict superset of ravenflight/rookery.** It's
   a squashed, genericized rewrite (`init`, 2026-10-09).
   - Added only in taraxvoid:
     - `nest/claude/settings.json` (the safe-git policy) and the validator
       rules for it
     - `agent-dispatch.yml`, `tests/test_validate.py`, the PR template and
       `LICENSE`
     - a safe-git paragraph in crow/raven
   - Still only in ravenflight:
     - the ravenflight-specific README (repos covered, Mercury card, vixen
       framed around the operator)
     - the ravenflight.io roost specifics, which taraxvoid anonymized
     - `SELF_HOSTED_RUNNERS` runner selection (ravenflight#26, after the split)
     - issue history: #14 (the `ravenflight-aviary` App setup steps), #20's
       rationale (taraxvoid#3 carries the work but not the *why*), #21 (first
       live `spend.py` run)
   - The two have already drifted in ten days. That alone argues for one source
     of truth.

## Target shape

```
agents/  skills/  roost/        unchanged: shared persona definitions
nest/
  kilo/                         unchanged: local runtime configs
  claude/                       unchanged: interactive harness policy
  gh-aw/                        NEW: rendered gh-aw shared fragments, one per persona
    shared/engine-*.md            engine definition(s) chosen by the Phase 1 spike
    shared/<bird>.md              engine.model, network.allowed, tools, safe-outputs
  render.py                     NEW: agents/*.md + kilo/*.jsonc + tier table -> nest/gh-aw/
  spend.py                      takes --colony; derives allowlists from kilo/ AND gh-aw/
colonies/
  README.md                     what a colony is and how to start one
  example/                      minimal template, no real values
  ravenflight/                  the reference deployment
    colony.toml                   repos covered, labels, runner choice, GitHub App name
    spend.toml                    moved from nest/spend.toml (limits, publish URL, card merchants)
    roost/                        ravenflight-specific lessons (ravenflight.io entries)
    workflows/                    the gh-aw workflows each target repo imports
    README.md                     "how ravenflight runs rookery", decisions linked
docs/
  decisions/                    ADRs: 0001 Kilo+OpenRouter (from ravenflight#20), 0002 gh-aw
  plans/                        this file
```

A **colony** is one operator's deployment of the shared rookery: which repos it
covers, its money limits, its model picks if they override the defaults, its
GitHub App, its runners and its local lessons. It's rookery's word for an
instance. "flock" is already a ravenflight repo name, so it's avoided here, and
the name is open. ravenflight is the first colony and is documented as the
worked example. Anyone adopting rookery copies `colonies/example/` (or forks it
into their own repo), so "how ravenflight does it" is first-class without being
hard-coded into the framework.

What happens to **ravenflight/rookery**: once Phase 0 lands, archive it and
point its README at `colonies/ravenflight/`. Before archiving, close or
transfer its open issues: #14, #16, #20, #21, #22, #23. If anything genuinely
can't be public (none of the current files look that way, since `spend.toml`
amounts are already public in taraxvoid), keep a private repo holding only
those values, consumed as an overlay on top of the public colony.

## Phases

Each phase is a separate PR series.

### Phase 0: one source of truth (no gh-aw yet)

1. Add `colonies/ravenflight/`.
   - Move `nest/spend.toml` there; `spend.py --colony ravenflight` (default:
     the only colony present).
   - Move the voidlight publish URL and card merchants into the colony.
2. Port ravenflight-only material:
   - `docs/decisions/0001-kilo-openrouter.md` from #20's rationale
   - the ravenflight.io roost entries, into `colonies/ravenflight/roost/`
   - the self-hosted runner toggle, as a colony setting
3. Add `colony.toml` to hold:
   - the repos covered (ravenflight.io, rvnflt, flock, rookery)
   - the label set (today it's in the README only)
   - the GitHub App name (`ravenflight-aviary`)
4. Validator changes:
   - `validate.py` checks each colony: schema, every model in its `spend.toml`
     resolvable from `nest/`, labels match the README table.
   - It fails loudly if `colonies/` is empty (per the roost rule).
5. Migrate ravenflight/rookery's open issues, then archive it.

Semver: tag `v0.1.0` before this phase as the baseline. The colony layout
changes `spend.py`'s CLI, so it's a **minor** bump (`v0.2.0`; pre-1.0).

### Phase 1: gh-aw spike (time-boxed, one evening)

Done in a scratch repo, same format as #5: pass/fail per item, results posted
on the issue.

1. Kilo as a custom engine, adapted from the OpenCode sample. Run shrike
   read-only and check:
   - does AWF wrap it (egress blocked except `openrouter.ai`)?
   - does `permission` from `shrike.jsonc` still apply?
   - is the model the one in `shrike.jsonc`, confirmed in OpenRouter activity?
2. Codex engine with `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and a
   non-OpenAI model. Does it run at all?
3. Threat detection: works with `engine: codex` on the OpenRouter key, so no
   Copilot dependency? Note the per-run cost.
4. Issue-text exposure: confirm the prompt contains only what the workflow
   body interpolates, and how gh-aw sanitizes `${{ github.event.issue.* }}` if
   used. Required to keep the "issue text can't steer the agent" property.
5. `create-pull-request` with `allowed-files` and `draft: true` from a run that
   tries to touch a disallowed path. It must be refused.

**Pass** (1 or 2, plus 3, 4 and 5): proceed to Phase 2 with that engine. Record
the result as `docs/decisions/0002-gh-aw.md`.

**Fail**: gh-aw needs Copilot or Anthropic billing to be safe. Record that as
the 0002 decision ("not adopted, because…"), which is still useful material for
the README. Fall back to #5's daemon. `agent-dispatch.yml` stays as is.

### Phase 2: render gh-aw from personas (if Phase 1 passes)

1. `nest/render.py` emits `nest/gh-aw/shared/<bird>.md` for each persona that
   runs in CI. Tier sets the ceiling:

   | Persona | safe-outputs | permissions |
   |---|---|---|
   | tier 0 (shrike, magpie, wren, kingfisher, canary) | `add-comment` max 1 | read |
   | owl, tern | `create-issue` (`close-older-issues`, label `agent-authored`), `add-comment` | read |
   | jackdaw | PR review comment only | read |
   | crow | `create-pull-request` (`draft: true`, `allowed-files` per colony, size caps), `add-labels` (allowed: `agent:*`), `add-comment` | read |
   | raven | crow's outputs plus `push-to-pull-request-branch` (`required-labels: [agent-authored]`) | read |
   | any | no merge output; merges stay with branch protection and a human | — |

   Every fragment sets these, and `network.allowed` equals the persona's Kilo
   `allowed_hosts` plus the inference host, so #6 gets one source:
   - `strict: true`
   - a pinned engine version
   - `max-turns` from `maxTurns`
   - threat detection on
2. `validate.py` additions:
   - rendered output must equal what's committed (drift check);
   - every gh-aw workflow in a colony imports a persona fragment and doesn't
     widen it: no write `permissions`, no extra safe-output types, no
     `threat-detection: false`, no `network` wildcard.
3. `spend.py` derives guardrail allowlists from `nest/gh-aw/` as well as
   `nest/kilo/`, so a CI persona can't be pointed at a model its key refuses.
   Store keys as Actions secrets in an environment limited to the default
   branch (as `agent-dispatch` does today).
4. Replace `agent-dispatch.yml` with `agent-dispatch.md` and its lock file:
   - trigger: `issues: labeled`, `names: [agent:ready]`
   - `roles: [admin, maintainer, write]`
   - keep the author-association gate (via `if:` or a pre-activation step; the
     spike confirms which)
   - the crow fragment
   - closes #11
5. Owl/tern scheduled digests through gh-aw (`schedule` plus `create-issue`),
   which is most of #12.
6. #8: `safe-outputs.github-app` with the colony's App. #9: `max-patch-files`
   and `max-patch-size` cover the coarse ceiling; a line-count ceiling is still
   a custom check if wanted.

Semver: **minor** (`v0.3.0`). New capability; the old workflow is removed but
it was a smoke test, not a public interface.

### Phase 3: target repos consume the colony

1. Each covered repo gets thin workflows that import
   `taraxvoid/rookery/nest/gh-aw/shared/<bird>.md@<sha>` plus the colony
   settings. They are compiled in that repo, and Renovate bumps the pins.
2. Pin the gh-aw compiler version. gh-aw is pre-1.0 and has retired releases
   for a security advisory (GHSA-8h78-hpm7-29gg), so upgrade deliberately.
3. If the colony uses self-hosted runners, the requirements are: Linux, Docker,
   disposable VMs, no ambient credentials, and a runner group separate from
   release jobs.

### Phase 4: README and positioning

- Reframe the README as "a policy and spend layer over agent runtimes: Kilo
  locally, gh-aw in CI, Claude Code interactively."
- Add an Enforcement table row per runtime.
- Link `colonies/ravenflight/README.md` as the worked example, and link the
  ADRs. The ADRs carry the narrative (the problem, what was tried, what failed
  and why), and that is the part worth showing.

## Not changing

- The tier model, and the "dispatch only goes down" rule
- The council, including #4's author-family rule
- The roost; #13 decides format and location, and colony-scoped entries fit it
- Local Kilo configs and the Mac sandbox path
- The `nest/claude/settings.json` safe-git policy, for interactive and Claude
  Code runs

## Risks

- **gh-aw churn.** It's in preview at about v0.9x, with frequent releases and
  some breaking. Mitigation: pin the compiler, keep lock files committed, and
  let the drift check catch surprises.
- **Custom-engine isolation is unproven.** If the spike can't show AWF and
  Kilo permissions both apply, don't ship write-capable personas on it.
- **Two runtimes to keep in sync.** `render.py` plus the drift check is the
  answer, and it's the same pattern `spend.py` already uses for Kilo.
- **Scope creep from the vixen tier.** Unchanged: #14 gates it.

## Sources

- [gh-aw README](https://github.com/github/gh-aw)
- gh-aw reference docs, read from the repository's `docs/` tree:
  - [engines](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/engines.md)
  - [third-party agents](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/third-party-agent.md)
  - [model routing](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/model-routing.md)
  - [threat detection](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/threat-detection.md)
  - [sandbox](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/sandbox.md)
  - [self-hosted runners](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/self-hosted-runners.md)
  - [triggers](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/triggers.md)
  - [PR safe outputs](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/safe-outputs-pull-requests.md)
- [Security architecture of GitHub Agentic Workflows](https://github.blog/2026/03/09/under-the-hood-security-architecture-of-github-agentic-workflows/)
- ravenflight/rookery issues #14, #20, #21, #22, #23 and commit history through
  `4ae9f6a`
