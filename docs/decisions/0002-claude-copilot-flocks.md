# 0002: Claude Code for dev, Copilot + gh-aw for chores, flocks for operators

Status: accepted 2026-11-02. Plan and rationale:
[docs/plans/2026-11-claude-copilot-flocks.md](../plans/2026-11-claude-copilot-flocks.md).

## Decision

- Drop Kilo and OpenRouter. Claude Code runs attended work (crow, raven and
  their read-only subagents); Copilot through gh-aw runs unattended chores
  (owl, tern, wren, canary triage, jackdaw review).
- This repo is the single source of truth: the policy layer. One operator's
  deployment is a **flock** under `flocks/<name>/`. ravenflight is the first.
- `ravenflight/rookery` is retired. Its history stays there; nothing new lands
  there.

## Status of the phases

Phase 0 (one source of truth) is done by the change that added this file.
Phases 1 to 4 are still plan: Kilo is still present until Phase 2 removes it.
