# Flocks

A **flock** is one operator's deployment of rookery: which repos it covers,
which labels and runners it uses, which GitHub App it acts as, and the lessons
it has learned. Everything generic lives at the repo root; everything specific
to an operator lives in `flocks/<name>/`.

Each flock has:

- `flock.toml`: the machine-checked config (schema below)
- `README.md`: how this operator runs rookery
- `roost/LEARNED.md`: lessons specific to that operator's repos

`flocks/example/` is a template with no real values. `python3 validate.py`
checks every flock and fails if `flocks/` has none.

## `flock.toml`

```toml
name = "example"            # must match the directory name
repos = ["example/app"]     # owner/name, at least one

[runners]
self_hosted = false         # true: jobs target the self-hosted runner label
label = "rookery"           # used only when self_hosted = true

[github_app]
name = "example-aviary"     # the App agents act as; never a personal token
```

Budgets and other operator records go in the flock's `README.md`, not in
`flock.toml`, until something reads them.

Do not put credentials in a flock. Secret names are fine; values are not.
