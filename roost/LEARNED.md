# Learned

Durable, cross-run knowledge. Append a dated entry; don't rewrite history above it.
Every persona above tier 0 reads this before starting a task in a repo it covers.

## 2026-09-19: first real wiring, first end-to-end unit

**Wiring `agents/*.md` as Claude Code subagents**: symlink `~/.claude/agents` to
`<rookery checkout>/agents` (user scope, so every project on the machine gets
them). Confirmed working:
- `claude plugin validate <dir>` refuses a symlinked directory ("pass the real
  directory instead"). That's specific to `plugin validate`; validate the real
  path. The subagent loader follows the symlink fine: `claude --debug agents -p
  "list your subagents"` listed every persona, grouped by tier.
- Plain tool restriction is enforced: shrike (Read/Grep/Glob only), asked to
  write a file, reported it had no Write tool and created nothing.
- Delegation works: a parent session dispatched magpie for a scoped question
  and got the right file:line answer back.

**`Bash(<pattern>)` in subagent `tools:` frontmatter grants unrestricted Bash.**
Claude Code parses the parenthetical and discards it (anthropics/claude-code#61651,
later closed as not planned). canary's old `Bash(gitleaks*), Bash(grype*)` was
full shell access: a live hole in the tier-0 invariant everything else rests
on. Fix: no read-only persona carries Bash in any form in `agents/*.md`, and
`validate.py` rejects it. Scoped shell lives in settings-level permission rules
(`nest/claude/settings.json`), which are enforced. (Kilo's `permission.bash` map
was the other enforced option until decision 0002 removed Kilo.)
**Rule**: never trust a permission syntax without checking that the harness
enforces it. Parsing cleanly is not evidence of enforcement.

**`validate.py` silently stopped checking the Kilo configs** (since removed) after a directory
move: it still pointed at the old path, found zero files, and passed. **Rule**:
a validator that can silently check nothing is worse than none. It must fail
when the directory it's about to scan is missing or empty.

**First end-to-end unit** (repo specifics in
[`flocks/ravenflight/roost/`](../flocks/ravenflight/roost/LEARNED.md)): a real issue in a production site's repo (reject
disposable email domains at signup) went all the way to a PR: code change in the
one shared validation helper, tests added, build, type check, lint, unit and
Playwright suites all green, pre-commit and pre-push hooks clean, PR linked to
the issue and left for human review before merge.
- Strengthen shared validation at its single definition, not per call site.
- A package's npm publish can lag its maintained upstream by years. Use it as a
  baseline, and say in the PR that it's incomplete rather than shipping it as if
  it were complete.
- **Rule**: measure before treating a dependency as too big. A ~2.3MB data
  file looked like a Workers bundle-size risk; gzipped, the whole worker was
  ~1MB against a 3MB free-tier limit.
