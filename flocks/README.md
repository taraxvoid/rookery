# flocks

A **flock** is one operator's deployment of rookery:
- which repos it covers;
- its runners;
- its GitHub App;
- its own roost entries;
- how it actually uses the shared personas.

The personas, rules and validator at the root of this repo are the same for
every flock. Anything that names a real org, repo, domain or card lives in a
flock.

```
flocks/
  example/       copy this to start a flock
  ravenflight/   the reference flock: how RavenFlight runs rookery
```

## Starting one

1. Copy `example/` to `flocks/<name>/`. The directory name must match `name`
   in `flock.toml`.
2. Fill in [`flock.toml`](example/flock.toml). `validate.py` holds it to the
   schema, so an unknown key fails rather than being ignored.
3. Write `README.md` for anything someone else would need in order to run your
   setup: which personas you use, where they run, what's still manual.
4. Put lessons that only make sense for your repos in `roost/` inside the
   flock. Lessons that hold anywhere go in the shared [`roost/`](../roost/LEARNED.md).

A flock can also live in its own repo if it holds values you'd rather not
publish. Keep the same layout so the validator can check it.

## `flock.toml`

| Key | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | Must match the directory name |
| `operator` | string | yes | GitHub login of the human who answers `needs-you` |
| `repos` | list of `owner/name` | yes | Repos the flock's agents may work in |
| `runners.self_hosted` | bool | no | Run jobs on self-hosted runners instead of GitHub-hosted ones |
| `runners.label` | string | no | Runner label used when `self_hosted` is true |
| `github_app.name` | string | no | The App agent PRs and issues are opened as |
| `github_app.client_id_secret` | string | no | Name of the Actions secret holding the App's client ID |
| `github_app.private_key_secret` | string | no | Name of the Actions secret holding its private key |
| `github_app.status` | string | no | `planned` or `live` |

Labels aren't per flock. Every flock uses the shared set in
[`.github/labels.yml`](../.github/labels.yml), so the label state machine in
[`CONVENTIONS.md`](../CONVENTIONS.md) means the same thing everywhere.
