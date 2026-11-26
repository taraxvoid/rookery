# Conventions

How agent work gets picked up, claimed, reviewed and escalated in any repo that
uses rookery. [README.md](README.md) covers the tiers these sit on.

Most of this is process: it holds because the tools driving agents follow it.
Where something is enforced, this file says so.

## Labels

Source of truth: [`.github/labels.yml`](.github/labels.yml), applied to this
repo by the sync-labels workflow on every change to `main`. Other repos don't
copy the file: they call the reusable
[`sync-labels-reusable.yml`](.github/workflows/sync-labels-reusable.yml) pinned
by commit SHA, so the shared labels update only when they bump the pin:

```yaml
on:
  push:
    branches: [main]
    paths: [.github/labels-extra.yml]
  workflow_dispatch:
permissions: {}
jobs:
  sync:
    permissions:
      contents: read
      issues: write
    uses: taraxvoid/rookery/.github/workflows/sync-labels-reusable.yml@<sha>
    with:
      extra-labels: .github/labels-extra.yml # optional, the repo's own labels
```

Extra label files use the same format as `labels.yml`. They add labels; they
can't redefine one of rookery's (a name declared twice is an error). Run it from
`main` only, never `pull_request`. Names in the shared set, such as `needs-you`
and `low-risk`, are stable: other repos depend on them, so a rename is a
breaking change.

| Label | Meaning | On |
|---|---|---|
| `ready-for-agent` | A human decided this is scoped enough to hand to an agent. Nothing is picked up without it. | Issues |
| `no-agents` | Never automate. Checked before `ready-for-agent`. | Issues |
| `agent-working` | An agent has claimed this and is on it. | Issues, PRs |
| `needs-you` | Blocked on a human decision. | Issues, PRs |
| `in-review` | PR open, awaiting review before merge. | PRs |
| `ready-to-merge` | Reviewed, gates pass. | PRs |
| `low-risk` | Judged low risk by a reviewer; merges once required checks pass. | PRs |
| `agent-authored` | Opened by an agent, whatever credentials it ran under. | Issues, PRs |
| `from-digest` | Filed by a crow from a tier-0 digest, not by a human. Never auto-promoted to `ready-for-agent`. | Issues |

Names are lowercase words joined by hyphens, so they read plainly in a label
list and never need quoting in a shell command or a permission pattern.
`needs-you`, `in-review` and `ready-to-merge` carry no `agent` prefix: they mean
the same thing whether an agent, a bot or a person is doing the work, so other
workflows (dependency review, for one) reuse them rather than adding a second
label for the same state. When a label is renamed, `labels.yml` records its
old name under `was:` and the sync renames it in place, so open issues keep it.

## What makes an issue `ready-for-agent`

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
swaps `ready-for-agent` for `agent-working`:

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
`needs-you` and stops. It doesn't keep retrying and doesn't guess past
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
