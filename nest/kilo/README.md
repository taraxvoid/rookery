# kilo

Per-persona [Kilo CLI](https://kilo.ai) configs for the read-only birds. Kilo
is used here for two things Claude Code subagents don't give you: per-persona
model routing through OpenRouter, and a per-pattern `bash` permission map that
is actually enforced.

Each `<bird>.jsonc` turns that bird's `../../agents/<bird>.md` `tools:` line into
Kilo's permission schema (`allow`/`ask`/`deny` per tool) plus a `sandbox` block
using Kilo's OS-level sandbox (Seatbelt on macOS, Bubblewrap on Linux; no
container needed).

Every read-only config has the same shape, and `../../validate.py` holds it there:

- `edit`, `task`, `agent_manager`, `skill`, `todowrite`, `doom_loop`: `deny`
- `bash`: `deny`, or a map whose `"*"` is `deny` with specific patterns allowed
  (canary: `gitleaks*`, `grype*`)
- `read`, `glob`, `grep`, `lsp`, `todoread`: `allow`
- `external_directory`: `deny`, so the bird stays inside its worktree
- `sandbox.enabled: true`, `sandbox.writable_paths: []`, `network: "deny"`

Nothing here grants more than the persona file does. Birds with `webfetch:
allow` still have the sandbox network denied, so they reach nothing until their
hosts are listed in `allowed_hosts`. That's deliberate: open specific hosts, never
`network: "allow"`.

## Model routing

Picked from the live `openrouter.ai/api/v1/models` catalog on 2026-09-10
(jackdaw on 2026-10-06). The catalog moves fast, so re-check before reusing a pick.

| Bird | Model | Why |
|---|---|---|
| wren | `ollama/mistral` (local) | narrow, mechanical, $0 |
| shrike | `openrouter/cohere/north-mini-code:free` | code-specialized, free |
| magpie | `openrouter/google/gemma-4-31b-it:free` | general reasoning, free |
| kingfisher | `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | reasoning-tuned precision, free |
| canary | `openrouter/deepseek/deepseek-v4-flash-0731` | security triage wants reliability over $0; still under $0.20 per M tokens |
| owl | `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | 1M context for overnight logs, free |
| tern | `openrouter/qwen/qwen3.7-flash` | 1M context, a few cents per M tokens |
| jackdaw | `openrouter/openai/gpt-6.1-sol` | cross-family reviewer, must not be Claude; on the tier-1 key, see `../../skills/council/SKILL.md` |

wren uses a local `ollama` provider (`@ai-sdk/openai-compatible` pointed at
`http://localhost:11434/v1`): no key and no spend, but it needs `ollama serve`
and `ollama pull mistral`. The rest use `OPENROUTER_API_KEY_TIER0` (jackdaw:
`TIER1`), each behind a guardrail whose model allowlist `../spend.py` derives
from these files.
