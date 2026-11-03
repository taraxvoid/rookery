# How ravenflight runs rookery

ravenflight is the reference flock. It was previously the separate
`ravenflight/rookery` repo, which is retired in favor of this directory
([ADR 0002](../../docs/decisions/0002-claude-copilot-flocks.md)).

The repos it covers and its runner and App settings are in
[`flock.toml`](flock.toml). Its lessons are in
[`roost/LEARNED.md`](roost/LEARNED.md). Persona definitions, tiers and the
validator are shared and live at the repo root.

## Self-hosted runners

Workflows in ravenflight repos choose their runner with:

```yaml
runs-on: ${{ vars.SELF_HOSTED_RUNNERS == 'true' && 'rookery' || 'ubuntu-latest' }}
```

Unset, they fall through to GitHub-hosted runners, so a repo works before the
runner exists. The `ravenflight/flock` repo (the runner repo, not a rookery
flock) provisions the self-hosted runner.

## GitHub App: `ravenflight-aviary`

Agents act through a GitHub App, never a personal token. It is separate from
`ravenflight-releases` (which release-please uses) so a bug in an agent
workflow can't reach anything the release token can, and the reverse.

Setup needs an org owner and can't be scripted:

1. Org Settings, Developer settings, GitHub Apps, New GitHub App.
2. Name: `ravenflight-aviary`.
3. Homepage URL: any; it has no effect.
4. Webhook: disabled. The App only mints installation tokens.
5. Repository permissions: Contents, Pull requests and Issues, each Read and
   write (Metadata read-only is added automatically).
6. Installable on: only this account.
7. Create it and generate a private key (`.pem`). Keep that out of chat and
   screen shares.
8. Install it on the `ravenflight` org, all repositories.
9. Add two org-level secrets, matching the existing release bot naming:
   `AVIARY_BOT_CLIENT_ID` and `AVIARY_BOT_APP_PRIVATE_KEY`.

Then workflows mint a token with `actions/create-github-app-token` and scope
each one down with its `permission-*` inputs: a PR-only crow workflow
requests contents and pull requests and omits issues, even though the App's
ceiling includes it.
