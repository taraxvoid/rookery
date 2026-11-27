# rookery

Policy layer for coding agents: personas (`agents/`), the safe-git settings
they run under (`nest/claude/settings.json`), a validator that keeps the two
in agreement, and per-operator deployments (`flocks/`). README.md has the
design; CONVENTIONS.md has labels and the agent state machine.

## Checks

Run both before every push. They are stdlib Python, no install step:

```sh
python3 validate.py
python3 -m unittest discover -s tests
```

CI (`nest-validate.yml`) runs the same two plus gitleaks.

## Rules that bite

- `agents/` is live: `~/.claude/agents` links to the main checkout, so every
  Claude Code session on this machine sees these files. A persona edit
  changes behaviour everywhere once it lands on `main`.
- Read-only personas never carry `Bash` in any form in `tools:`. The
  `Bash(<pattern>)` form parses but is unrestricted
  (anthropics/claude-code#61651). `validate.py` rejects it; don't work around
  the check.
- Write-capable personas start `description:` with "Invoke only by name".
- Every restriction stated in a persona's prose needs a matching rule in a
  harness that enforces it. If you add a restriction, add the enforcement and
  a validator check, or don't add the restriction.
- Don't remove a rule from `REQUIRED_DENY` in `validate.py` or from
  `nest/claude/settings.json` to make something pass.
- Repo-relative paths in markdown must resolve (the validator checks), except
  in `docs/plans/` and `docs/decisions/`, which are history.
- `roost/LEARNED.md` is append-only: add a dated entry, never rewrite old ones.
- Before adding a persona, run `python3 scripts/persona-usage.py` and say in
  the PR what will run it.

## Shape of changes

- Decisions get an ADR in `docs/decisions/` (next number, `Supersedes:` when
  it does). Plans go in `docs/plans/`.
- Conventional commits; `feat!:` for anything that renames or removes a
  persona, label or settings rule, since other repos and flocks depend on
  them.
