# Learned: ravenflight

Lessons that only make sense for this flock's repos. Append a dated entry;
don't rewrite history above it. The general rule each one led to is in the
shared [`roost/`](../../../roost/LEARNED.md).

The flock's repos are private and this file is public: describe stack and
intent, never file paths, issue numbers or other internals. Keep those in the
repo's own `CLAUDE.md`, where only agents working in that repo read them.

## 2026-09-19: first end-to-end unit (ravenflight.io)

A crow took a real ravenflight.io issue (reject disposable email domains at
signup) all the way to a PR:
- tests were added;
- build, type check, lint, unit tests and the Playwright e2e suite passed;
- the pre-commit and pre-push hooks ran clean;
- the PR was left for review rather than merged.

- **The site's lead-capture forms share one email validator.** Strengthen it
  there, not per form.
- **`disposable-email-domains` on npm is stale** (last published 2022), though
  the upstream repo is maintained. It's a baseline that catches the common
  providers, not a complete list; the PR says so.
- **The Workers bundle-size worry was unfounded.** A ~2.3MB domain-list data
  file looked like a risk. Gzipped, the whole worker was ~1MB, against
  Cloudflare's 3MB free and 10MB paid limits.
