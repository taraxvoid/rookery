# 0001: Run the nest on Kilo and OpenRouter

Status: superseded by [0002](0002-claude-copilot-flocks.md). Originally
ravenflight/rookery#20, decided 2026-10-06.

## Decision

The whole nest ran on Kilo with OpenRouter keys. Claude Code stayed the
operator's own interactive harness, and nothing in the nest drew on the Claude
subscription.

## Why it was chosen

- **A subscription is the wrong footing for an always-on nest.** Headless
  `claude -p` drew on the operator's own plan limits. Anthropic had announced,
  then paused, moving headless and Agent SDK use to separate API-rate credit.
  Third-party harnesses on subscription OAuth were banned outright.
- **Kilo enforced per-pattern `bash` permissions.** Claude Code subagent
  `tools:` frontmatter did not (anthropics/claude-code#61651). Crow and raven
  have Bash, so this was a security gain as well as a billing one.
- **One harness, one bill, one control plane.** `nest/spend.py` derived
  OpenRouter guardrail allowlists from the Kilo configs.
- Rejected: Claude Code pointed at OpenRouter through `ANTHROPIC_BASE_URL`.
  Models could only be routed per process, not per persona, and OpenRouter
  itself warned it may not work with non-Anthropic models.

## Why it was superseded

Settings-level Claude Code permission rules turned out to be enforced, which
removed the main security argument. gh-aw on Copilot covers unattended work
with a sandbox, firewall and safe outputs, which removed the billing
argument. Dropping Kilo removes a whole harness from the trust model. See
0002 for the replacement and the accepted losses ($0 models, OpenRouter
guardrails as code).
