# 0002: Claude Code for development, Copilot + gh-aw for chores

- Status: **accepted**
- Date: 2026-11-02
- Supersedes: [0001](0001-kilo-openrouter.md)
- Plan: [docs/plans/2026-11-claude-copilot-flocks.md](../plans/2026-11-claude-copilot-flocks.md)

## Context

GitHub Agentic Workflows ([gh-aw](https://github.com/github/gh-aw)) went GA on
2026-10-28. It runs an agent in Actions:
- the agent job is read-only, inside a sandboxed container behind a firewall
  allowlist;
- writes are held until the agent exits, then filtered and threat-checked
  ("safe outputs") before a separate job applies them;
- comments from outsiders are filtered on public repos.

That is the split rookery's hand-built `agent-dispatch.yml` makes, enforced by
the platform instead of by a diff check that only works for one known change.

0001 chose Kilo to get enforced shell rules, an OS sandbox and per-persona
model routing. The two runtimes the operator was already settling on now
provide each of those.

## Decision

- **Drop Kilo and OpenRouter.**
- **Claude Code** runs attended, substantial software work: crow, raven, and
  read-only subagents on cheap models.
- **Copilot through gh-aw** runs unattended work: scheduled digests, cruft
  fixes, scanner triage and cross-family review.
- rookery stays the policy layer. It renders the tier rules into Claude Code
  settings and gh-aw workflow fragments, and `validate.py` checks they agree.
- One operator's deployment is a **flock** (`flocks/<name>/`).

## What each Kilo feature maps to

| Kilo gave | Now |
|---|---|
| Per-pattern `bash` rules, enforced | Claude Code settings-level permission rules (`nest/claude/settings.json`). In gh-aw: a read-only token, with writes only through safe outputs |
| OS sandbox, network denied | gh-aw's container and firewall allowlist (unattended). Claude Code's sandbox (attended) |
| Per-persona model | Claude subagent `model:`; gh-aw `engine.model` per workflow |
| Non-Claude reviewer (jackdaw) | A gh-aw review workflow on a non-Claude Copilot model |

## Consequences

- **Lost:** free and open-weight models; picking from all of OpenRouter's
  catalog; guardrails as code with one spend control plane. Two vendors now
  bill separately. Nothing measured showed the free models earned their
  unreliability.
- **0001's billing concern is resolved without Kilo:** unattended work runs
  on Copilot, not the Claude subscription. Headless Claude, for crow work
  dispatched from an issue, needs an API key with a workspace spend limit.
- **gh-aw is new and releases often.** Pin the compiler and commit the
  compiled lock files.
- **Open risk:** whether Copilot offers a non-Claude model family at a sane
  price decides how jackdaw runs. Fallback: an OpenAI key on gh-aw's Codex
  engine.
- **Closes as superseded:** taraxvoid/rookery#3 (move crow/raven to Kilo) and
  #5 (the Agent Orchestrator eval).

## Evidence so far

taraxvoid/voidchores#1 runs a weekly research workflow on gh-aw with the
Copilot engine. It compiles under `--strict`, filters comments with
`min-integrity: approved`, and limits writes to one directory.

One lesson came out of it: a scheduled agent that maintains a rolling PR must
not merge `main` into that PR's branch. The merge pulls in files outside the
allowed paths, and the safe output refuses the patch.
