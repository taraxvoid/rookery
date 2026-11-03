# 0001: Run every persona on Kilo + OpenRouter

- Status: **superseded** by [0002](0002-claude-copilot-gh-aw.md)
- Date: 2026-10-06
- Originally: ravenflight/rookery#20 (the private repo this one was split from)

## Context

crow and raven ran on Claude Code, and the tier-0 birds on Kilo with free
OpenRouter models. The question was whether to move the whole nest onto one
harness, and if so, which one.

## Decision

Move every persona to Kilo + OpenRouter. Claude Code stays the operator's
interactive harness; nothing automated draws on a Claude subscription.

## Why

- **A subscription is the wrong footing for an always-on nest.** Headless
  `claude -p` drew on the operator's own plan limits. Anthropic had announced
  moving headless and Agent SDK use to separate credit, then paused that.
  Third-party harnesses on subscription OAuth were banned outright.
- **Kilo enforces per-pattern `bash` permissions.** Claude Code subagent
  `tools:` frontmatter doesn't (anthropics/claude-code#61651). crow and raven
  need a shell, so this was a real security gain, not only a billing one.
- **One harness, one bill, one control plane.** `nest/spend.py`'s guardrail
  allowlists would cover crow and raven automatically once they had Kilo
  configs.

Rejected alternative: point Claude Code at OpenRouter with
`ANTHROPIC_BASE_URL`. Models could only be routed per process, not per
persona. A cached login could override the setting without a separate
`CLAUDE_CONFIG_DIR`. And OpenRouter itself warned that Claude Code "may not work
correctly" with non-Anthropic models.

## What happened

The work was planned in taraxvoid/rookery#3 (move crow/raven to Kilo) and #5
(does Agent Orchestrator apply Kilo configs as written?). Neither started
before [0002](0002-claude-copilot-gh-aw.md) replaced the plan. The read-only
birds' Kilo configs in `nest/kilo/` stay until 0002's Phase 2 removes them.
