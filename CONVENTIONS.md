# Conventions

How agent work gets picked up, claimed, reviewed and escalated in any repo that
uses rookery. [README.md](README.md) covers the tiers these sit on.

Most of this is process: it holds because the tools driving agents follow it.
Where something is enforced, this file says so.

## Labels

Source of truth: [`.github/labels.yml`](.github/labels.yml), applied to this
repo by the sync-labels workflow on every change to `main`. Repos that adopt
rookery copy the file and the workflow.

| Label | Meaning | On |
|---|---|---|
| `agent:ready` | A human decided this is scoped enough to hand to an agent. Nothing is picked up without it. | Issues |
| `agent:do-not-automate` | Never automate. Checked before `agent:ready`. | Issues |
| `agent:working` | An agent has claimed this and is on it. | Issues, PRs |
| `agent:needs-you` | Blocked on a human decision. | Issues, PRs |
| `agent:in-review` | PR open, awaiting review before merge. | PRs |
| `agent:ready-to-merge` | Reviewed, gates pass. | PRs |
| `agent-authored` | Opened by an agent, whatever credentials it ran under. | Issues, PRs |
| `source:digest` | Filed by a crow from a tier-0 digest, not by a human. Never auto-promoted to `agent:ready`. | Issues |

The four in-flight states match [Agent Orchestrator](https://github.com/OrchestratorInc/agent-orchestrator)'s
board columns, so GitHub and the orchestrator never describe one task two ways.

## What makes an issue `agent:ready`

Add the label (or file with the **Agent-ready task** issue template, which adds
it) only when all of these hold:

- **Small blast radius.** A wrong attempt is cheap to revert and doesn't touch
  billing, auth, deploy config or someone else's in-flight work.
- **A clear acceptance criterion.** "Done" can be stated without the agent
  inferring intent.
- **No architecture or product judgment left.** If the real question is
  "should we do this" or "which design", a human or a raven settles it first.
  What's left for the agent is implementation.

Example that clears the bar: "reject disposable email domains at signup, in the
shared validation helper, with tests". Example that doesn't: "make the
anonymous-submission dashboard better", which hides a product decision.

## Claiming

Before doing anything else, the agent comments with its name and branch and
swaps `agent:ready` for `agent:working`:

> crow claimed this, working in `agent/crow/123-reject-disposable-emails`

Several tools can act on one repo, and none share a lock. The claim comment is
what stops two of them taking the same issue.

## Branches

`agent/<persona>/<issue>-<slug>`, e.g. `agent/crow/10-reject-disposable-emails`.
Provenance shows in every branch list. Human branches aren't held to this.
Enforced for pushes: `nest/claude/settings.json` only lets agents push `agent/*`.

## PRs

Every PR uses the template's "How verified" and "Provenance" sections.
Agent-written PRs also get `agent-authored`, so the share of agent-written
history stays visible over time instead of being asserted.

Past roughly 300 changed lines (excluding lockfiles and generated output), stop
and split the work, or open an issue proposing the plan. Guidance for now; a CI
check is tracked separately.

## Escalation

When stuck (ambiguous requirements, a decision above its tier, repeated
failure), an agent comments saying exactly what it's stuck on, adds
`agent:needs-you` and stops. It doesn't keep retrying and doesn't guess past
its tier: a bird hands off to a crow, a crow to a raven, a raven to a human.

## Review of sensitive paths

[`.github/CODEOWNERS`](.github/CODEOWNERS) requests a human review on workflows,
CODEOWNERS itself, the enforcement configs under `nest/` and `validate.py`,
whoever opens the PR. Branch protection decides whether that review is required.

## Credentials

Agents never use a personal access token. Workflows use the job's short-lived
`GITHUB_TOKEN` today; agent PRs opened with it don't trigger further workflows
(GitHub's anti-recursion guard), which is why a dedicated GitHub App identity is
planned.
