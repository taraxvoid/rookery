---
name: council
description: Get an independent, cross-model-family second opinion before a consequential call — a crow's pre-merge cross-review, or a raven's architecture decision. Use instead of asking another Claude-backed bird to "take a look".
---

# council

A trimmed-down version of Karpathy's `llm-council`: several models answer
independently, then one synthesizes. What makes it worth the spend is
**model-family diversity** — crow and raven are both Claude, and a second
Claude reviewing Claude's work shares its blind spots and agrees with it for
the wrong reasons. Agreement between two Claude birds is not independent
confirmation; agreement across families is closer to it.

Dropped from the original on purpose: the stage where every member ranks every
other member. With 2–3 members it adds spend, not signal.

## When

| Who | Trigger | Members |
|---|---|---|
| crow | before merging any PR into `main` (replaces "get a second crow") | 1 — `jackdaw` on its default model |
| raven | a decision you'd describe as an architecture call, or one that's expensive to reverse | 3 — `jackdaw` on each of the council models below |

Not for tier 0, not for routine implementation, not for anything a gate or
test can settle on its own. If CI can answer it, ask CI.

## Council models

One per family, none of them Claude. These used to route through OpenRouter.
Since [decision 0002](../../docs/decisions/0002-claude-copilot-gh-aw.md),
jackdaw runs as a gh-aw review workflow on a non-Claude Copilot model
(`engine.model`). Which families Copilot exposes is still open (0002's Phase 1
pilot), so until then these are families to fill, not wired routes:

| Family | Role |
|---|---|
| OpenAI | jackdaw's default |
| Google | raven council |
| DeepSeek, or another non-Claude family on offer | raven council |

If Copilot offers no non-Claude family at a sane price, the fallback is an
OpenAI key on gh-aw's Codex engine.

## How

1. **Package the question, stripped of authorship.** The diff (or design
   options) plus the issue it answers. No persona names, model names, "another
   agent wrote this", or your own opinion of it — a reviewer that knows who
   wrote something grades the author instead of the work. Branch names leak
   `agent/crow/...`; leave them out.
2. **Commit to your own position first.** Raven: write your own answer down
   before reading any member's. Otherwise you're anchoring on whoever you read
   first, not chairing.
3. **Dispatch `jackdaw`** with the package (one dispatch per member for a
   raven council). Members never see each other's answers.
4. **Synthesize, as chair.** Every concrete defect a member raises gets either
   a fix or a stated reason it's wrong — "the other two didn't mention it" is
   not a reason. Where members disagree on a judgment call, that disagreement
   is the finding: record it, don't average it away.
5. **Record it.** A short "Council" section in the PR description or the
   architecture issue: which models, what each flagged, what you did about it.
   That's the data a vixen gets trained up on later.

## Escalation

- crow: jackdaw raises a blocking concern you can't resolve → don't merge;
  escalate to a raven with the review attached.
- raven: members split on something that's really a business or product call
  → that's vixen's or the operator's, per `agents/raven.md`. Hand it over with
  the council record instead of breaking the tie yourself.

## Cost

Every raven council is ~3 extra frontier-model reviews. Keep it to real
architecture calls, and check Copilot premium-request usage before making it
routine.
