# rookery

Tiered coding-agent personas with guardrails enforced as code.

rookery is how I run coding agents on real repos: a small set of personas,
each with a fixed level of capability and a model budget to match, plus the
config and checks that keep them inside those limits. The rules live in files a
validator and CI can check, not in prompts an agent can talk itself out of.

The personas are birds. Each name says what the bird does.

```
agents/   persona definitions (Claude Code subagent format)
skills/   shared skills personas can invoke
nest/     enforcement: Kilo configs, Claude Code permissions, spend-as-code
roost/    durable lessons that outlive a worktree
tests/    validator and spend.py tests (stdlib, mock data, no accounts needed)
```

## Design

Four rules carry the whole system:

1. **Capability and cost scale together, by tier.** Cheap or free models get
   read-only jobs. Write access, merges and architecture calls cost more and sit
   higher up.
2. **Dispatch only goes down.** A higher tier can hand work to a lower one,
   never the reverse.
3. **Enforcement beats instructions.** Every restriction in a persona's prose
   has a matching rule in a harness that actually enforces it, and
   `validate.py` fails CI when the two disagree.
4. **Nothing happens without an explicit signal.** An agent never picks up work
   nobody flagged for it.

## Tiers

### Tier 0: read and report

Narrow single-purpose personas on free or near-free models. They read code,
logs and metrics and report back to whoever dispatched them. They can't edit
files, run arbitrary shell commands or change git or GitHub state.

| Bird | Job |
|---|---|
| **shrike** | finds bugs |
| **magpie** | answers small, scoped questions about a codebase |
| **wren** | finds dead code, unused imports and small housekeeping |
| **kingfisher** | takes one log line, stack trace or incident ID and dives for root cause |
| **canary** | scans for secrets, leaked credentials and vulnerable dependencies |
| **owl** | digests overnight logs and reports anomalies by morning |
| **tern** | lightweight, recurring usage and analytics digest |

### Tier 1: crows

Reasoning models with real capability: edit code, open issues and PRs, call
APIs, and merge into `main` once CI passes and a cross-family review agrees.
Crows dispatch tier-0 birds for investigative legwork.

**jackdaw** is the one read-only tier-1 persona. It runs on a frontier model
(tier-1 cost) but only reviews (`readonly: true`, held to tier-0 rules by
`validate.py`). Its value is being a different model family from the author of
the work it reviews; see [`skills/council`](skills/council/SKILL.md).

### Tier 2: ravens

Architecture and orchestration. Ravens merge to `main` (which deploys a
protected `dev.` preview), promote to staging (`next.`) through the project's
release flow, and watch both after promoting. Architecture calls go through a
three-model council first.

### Tier 3: vixen

The goal tier, not live: CI end to end, business and market signal, and a
morning digest of what needs a human's judgment. It earns autonomy from real
lower-tier data and is reviewed before anything runs unattended.

## Enforcement

| Restriction | Where it's enforced |
|---|---|
| Tier-0 birds can't edit, run shell, dispatch or write anywhere | `nest/kilo/<bird>.jsonc`: Kilo `permission` map plus its OS sandbox (Seatbelt on macOS, Bubblewrap on Linux), no writable paths, network denied |
| Scoped shell for a tier-0 bird (canary's `gitleaks`, `grype`) | Kilo's per-pattern `permission.bash` map, default `deny` |
| Agents only run safe git commands | [`nest/claude/settings.json`](nest/claude/settings.json): an allowlist of git and `gh` commands plus deny rules for history rewrites, force pushes, pushes to `main`, hook bypasses and config changes. Run headless with `--permission-mode dontAsk` and anything off the list is refused |
| Model choice and spend per tier | [`nest/spend.toml`](nest/spend.toml): OpenRouter keys with daily limits, and guardrails whose model allowlists are derived from the Kilo configs |
| Persona prose and enforcement agree | [`validate.py`](validate.py), run in CI |
| `main` | Branch protection on the target repo, independent of anything here |

One thing I learned the hard way: Claude Code subagent `tools:` frontmatter
accepts `Bash(<pattern>)` but discards the pattern and grants unrestricted Bash
(reported as anthropics/claude-code#61651, closed as not planned). Syntax that
parses cleanly is not evidence it's enforced. So no read-only persona carries
`Bash` in any form in `agents/*.md`, `validate.py` rejects it, and scoped shell
access lives only where it's enforced: Kilo's `permission.bash`, or Claude
Code's settings-level permission rules.

## Spend

OpenRouter keys and guardrails are code, not web-UI state. `nest/spend.toml`
declares them and `nest/spend.py` reconciles OpenRouter to match. Each key's
guardrail model allowlist is derived from the `nest/kilo/*.jsonc` configs that
use it, so a bird can't be pointed at a model its key will refuse: `plan` fails
first. The outer bound is a merchant-locked, spend-capped virtual card on the
OpenRouter account.

```sh
uvx keyring set rookery-openrouter management  # management key: keychain only, never a file
uv run nest/spend.py plan                      # diff OpenRouter against spend.toml
uv run nest/spend.py apply                     # create/patch keys; secrets go to the keychain
uv run nest/spend.py report                    # per-key spend and credit balance
uv run nest/spend.py rotate tier1              # replace a leaked or lost key
```

`spend.py env` prints the tier keys as fish `set -gx` lines (`--sh` for `export` lines).

The management key can mint unlimited keys and drop every guardrail, so it
stays in the OS keychain, out of reach of any agent with file access.

`spend.py publish` pushes an amount-free containment summary (each tier's share
of its limits, whether allowlists are in sync, card containment flags) to a
[voidlight](https://github.com/taraxvoid/voidlight) status endpoint. It never
sends amounts, balances, key names or card details; `--dry-run` prints exactly
what would leave the machine.

## Working with GitHub

Work enters through labels and is tracked through labels.

| Label | Meaning |
|---|---|
| `agent:ready` | A human decided this is scoped enough to hand off. Nothing is picked up without it. |
| `agent:do-not-automate` | Explicit opt-out, checked first. |
| `agent:working` | Claimed and in progress. |
| `agent:needs-you` | Blocked on a human decision. |
| `agent:in-review` | PR open, awaiting cross-review. |
| `agent:ready-to-merge` | Reviewed, gates pass. |
| `agent-authored` | Opened by an agent, whatever credentials it ran under. |

The in-flight states match [Agent Orchestrator](https://github.com/OrchestratorInc/agent-orchestrator)'s
board columns, so GitHub and the orchestrator never disagree about a task.

- **Branches**: `agent/<bird>/<issue>-<slug>`, so provenance shows in every branch list.
- **Claiming**: the agent comments with its name and branch and flips the label to
  `agent:working`. With several tools acting on one repo, that comment is what
  stops two of them taking the same issue.
- **PRs**: the template asks how the change was verified and whether an agent wrote it.

### Dispatch workflow

[`agent-dispatch.yml`](.github/workflows/agent-dispatch.yml) runs when
`agent:ready` is added. Today it's a smoke test (claim comment plus a draft PR)
that proves the trigger end to end. It's built so issue text can't steer the agent:

- It only runs when the person adding the label has write access **and** the
  issue's author is a repo owner, member or collaborator.
- The prompt contains the issue number and nothing else. No title or body is
  interpolated, and the smoke test never reads them.
- The agent runs in `dontAsk` mode with Read and Edit on one file. It has no
  shell, git, `gh` or network tools.
- The side effects (claim comment, commit, push, draft PR) are fixed workflow
  steps. They run only after a check that the agent's diff is exactly the
  one-line change it was asked for, so nothing else it saw can leave in the PR.
- Every action is pinned to a commit SHA, and the checkout keeps no credentials.

## Roost

Worktrees are disposable; the roost isn't. Any persona above tier 0 that learns
something durable (a convention, a gotcha, a decision and why) appends it to
`roost/` before its worktree goes away, and agents read the relevant entries
before starting.

## Using it

- **Claude Code**: symlink `~/.claude/agents` to `agents/` (user scope, so every
  project sees the personas). Merge `nest/claude/settings.json` into the target
  repo's `.claude/settings.json` or pass it with `--settings`.
- **Kilo**: point a run at `nest/kilo/<bird>.jsonc`; see [`nest/kilo/README.md`](nest/kilo/README.md).
- **Checks**: `python3 validate.py` and `python3 -m unittest discover -s tests`.
  Both are stdlib only.

Repo-specific behavior belongs in each target repo's own `CLAUDE.md`; this repo
only holds what's shared across repos.

Planned work is tracked in [issues](https://github.com/taraxvoid/rookery/issues).

## License

[MIT](LICENSE)
