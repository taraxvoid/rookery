# Learned: ravenflight

Lessons specific to ravenflight's repos. Generic lessons live in the root
[roost/LEARNED.md](../../../roost/LEARNED.md). Append dated entries; don't
rewrite history above them.

## 2026-09-19: first end-to-end unit

The first real unit was ravenflight.io#10 (reject disposable email domains on
submit), shipped as ravenflight/ravenflight.io#168. Facts about that repo:

- Lead-capture email validation lives in one place: `isValidEmail` in
  `src/utils.ts`, called by both `src/pages/api/contact.ts` and
  `src/pages/api/audits/notify.ts`. Strengthen it there, not per call site.
- The change used `disposable-email-domains` and its `wildcard.json`. The
  package's npm publish was last updated in 2022 although the upstream repo is
  maintained, so it is a baseline for the persistent common providers, not a
  complete list. The PR said so.
- The ~2.3MB data file looked like a Cloudflare Workers bundle-size risk.
  Measured, the whole worker was ~1MB gzipped against 3MB (free) and 10MB
  (paid) limits.
- The PR ran `bun run build`, `check`, `lint` and `test:unit`, plus the
  pre-commit and pre-push hooks including the full Playwright e2e suite, and
  was left for human review before merge.
