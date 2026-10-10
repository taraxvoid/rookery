# skills

Shared skills any persona in `../agents/` can invoke. One directory per skill,
each with a `SKILL.md` in the standard Claude Code skill format (frontmatter
`name` and `description`; the body is the instructions).

Only shared, cross-repo skills belong here. Anything specific to one repo goes in
that repo's own `CLAUDE.md` or `.claude/skills/`.

- [`council/`](council/SKILL.md): cross-model-family review before a crow
  merges or a raven makes an architecture call.
