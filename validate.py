#!/usr/bin/env python3
"""Validate agents/*.md frontmatter, nest/kilo/*.jsonc configs and the shared
Claude Code permissions in nest/claude/settings.json.
No dependencies: parses frontmatter/JSONC by hand.

Checks:
- required fields present (name, tier, description, model)
- name matches the filename
- tier is 0-3
- read-only personas never carry write/edit/orchestration capability, in
  either their Claude Code tools: frontmatter or their Kilo permission config.
  Read-only means tier 0, or any tier with `readonly: true`: tier tracks
  model cost, readonly tracks capability (e.g. jackdaw: tier 1, read-only)
- read-only personas never carry Bash in any form in agents/*.md. Claude Code's
  subagent tools: frontmatter parses `Bash(<pattern>)` but discards the
  parenthetical (anthropics/claude-code#61651, closed as not planned), so a
  "scoped" entry is unrestricted Bash there. Scoped shell access for a tier-0
  bird comes only from its nest/kilo/*.jsonc permission.bash map, which Kilo
  enforces per pattern.
- nest/claude/settings.json never allows git or gh wholesale, and keeps the
  deny rules that stop history rewrites, force pushes, pushes to main and
  hook bypasses. Settings-level rules are enforced, and subagents inherit them.
"""

import json
import re
import sys
from pathlib import Path

AGENTS_DIR = Path(__file__).parent / "agents"
KILO_DIR = Path(__file__).parent / "nest" / "kilo"
CLAUDE_SETTINGS = Path(__file__).parent / "nest" / "claude" / "settings.json"
REQUIRED_FIELDS = ("name", "tier", "description", "model")
DISALLOWED_FOR_READONLY = ("Edit", "Write", "NotebookEdit", "Task")
DENY_FOR_READONLY_KILO = ("edit", "task", "agent_manager", "skill", "todowrite", "doom_loop")
# Allow rules that would hand an agent a whole command family.
TOO_BROAD_ALLOW = ("Bash", "Bash(*)", "Bash(git *)", "Bash(git*)", "Bash(gh *)", "Bash(gh*)", "Bash(git push *)", "Bash(gh api *)")
# Deny rules the safe-git policy depends on. Removing one fails CI.
REQUIRED_DENY = (
    "Bash(git push --force*)",
    "Bash(git push * --force*)",
    "Bash(git push -f*)",
    "Bash(git push * -f*)",
    "Bash(git push *+*)",
    "Bash(git push *:*)",
    "Bash(git push * main)",
    "Bash(git push * HEAD*)",
    "Bash(git * --no-verify*)",
    "Bash(git -c *)",
    "Bash(git config *)",
    "Bash(git reset --hard*)",
    "Bash(git clean *)",
    "Bash(git rebase *)",
    "Bash(git filter-branch *)",
    "Bash(git filter-repo *)",
    "Bash(gh pr merge * --admin*)",
)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line.startswith(" ") or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        if _:
            value = value.strip()
            if not value.startswith(('"', "'")):
                value = re.sub(r"\s+#.*$", "", value)  # YAML inline comment
            fields[key.strip()] = value.strip('"')
    return fields


def has_any_bash(tools: str) -> bool:
    # Bare "Bash" and "Bash(<pattern>)" are both disallowed for read-only
    # personas in agents/*.md: Claude Code reads this tools: line as subagent
    # config and doesn't enforce the parenthetical, so a "scoped" entry there
    # is indistinguishable from unrestricted Bash.
    return bool(re.search(r"\bBash\b", tools))


def is_readonly(fields: dict[str, str]) -> bool:
    return fields.get("tier") == "0" or fields.get("readonly") == "true"


def check_file(path: Path) -> list[str]:
    errors = []
    fields = parse_frontmatter(path.read_text())

    for field in REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"{path.name}: missing required field '{field}'")

    if "name" in fields and fields["name"] != path.stem:
        errors.append(
            f"{path.name}: frontmatter name '{fields['name']}' != filename '{path.stem}'"
        )

    tier = fields.get("tier")
    if tier not in ("0", "1", "2", "3"):
        errors.append(f"{path.name}: tier must be 0-3, got {tier!r}")

    if fields.get("readonly", "false") not in ("true", "false"):
        errors.append(f"{path.name}: readonly must be true or false, got {fields['readonly']!r}")

    if is_readonly(fields):
        tools = fields.get("tools")
        if not tools:
            errors.append(
                f"{path.name}: read-only persona must set 'tools:' explicitly (no implicit full access)"
            )
        else:
            if has_any_bash(tools):
                errors.append(
                    f"{path.name}: read-only persona must not have Bash in agents/*.md tools: "
                    "(unenforceable there even scoped — see nest/kilo/*.jsonc's permission.bash instead)"
                )
            for disallowed in DISALLOWED_FOR_READONLY:
                if disallowed in tools:
                    errors.append(
                        f"{path.name}: read-only persona must not have '{disallowed}' in tools"
                    )

    return errors


def strip_jsonc_comments(text: str) -> str:
    # Line comments only (// ...) — sufficient for our own hand-authored
    # configs, which never put "//" inside a string value.
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def check_kilo_file(path: Path, readonly: bool) -> list[str]:
    if not readonly:
        return []

    errors = []
    try:
        config = json.loads(strip_jsonc_comments(path.read_text()))
    except json.JSONDecodeError as e:
        return [f"kilo/{path.name}: invalid JSON — {e}"]

    permission = config.get("permission", {})

    for key in DENY_FOR_READONLY_KILO:
        if permission.get(key) != "deny":
            errors.append(
                f"kilo/{path.name}: read-only permission.{key} must be 'deny', got {permission.get(key)!r}"
            )

    bash = permission.get("bash", "allow")
    bash_default = bash if isinstance(bash, str) else bash.get("*", "allow")
    if bash_default != "deny":
        errors.append(
            f"kilo/{path.name}: read-only permission.bash default (or bare 'bash') must be 'deny', got {bash_default!r}"
        )

    sandbox = config.get("sandbox", {})
    if not sandbox.get("enabled"):
        errors.append(f"kilo/{path.name}: read-only sandbox.enabled must be true")
    if sandbox.get("writable_paths"):
        errors.append(
            f"kilo/{path.name}: read-only sandbox.writable_paths must be empty, got {sandbox.get('writable_paths')!r}"
        )

    return errors


def check_claude_settings(path: Path) -> list[str]:
    try:
        permissions = json.loads(path.read_text()).get("permissions", {})
    except json.JSONDecodeError as e:
        return [f"claude/{path.name}: invalid JSON — {e}"]

    errors = []
    allow, deny = permissions.get("allow", []), set(permissions.get("deny", []))
    for rule in allow:
        if rule in TOO_BROAD_ALLOW:
            errors.append(f"claude/{path.name}: allow rule {rule!r} grants a whole command family")
    for rule in REQUIRED_DENY:
        if rule not in deny:
            errors.append(f"claude/{path.name}: missing required deny rule {rule!r}")
    return errors


def main() -> int:
    all_errors = []
    readonly_by_name: dict[str, bool] = {}

    # A validator that can silently check nothing is worse than none.
    for required in (AGENTS_DIR, KILO_DIR, CLAUDE_SETTINGS):
        if not required.exists():
            all_errors.append(f"{required.relative_to(Path(__file__).parent)}: missing")
    agent_paths = sorted(AGENTS_DIR.glob("*.md"))
    kilo_paths = sorted(KILO_DIR.glob("*.jsonc"))
    if not agent_paths:
        all_errors.append("agents/: no personas found")

    for path in agent_paths:
        all_errors.extend(check_file(path))
        readonly_by_name[path.stem] = is_readonly(parse_frontmatter(path.read_text()))

    for path in kilo_paths:
        all_errors.extend(check_kilo_file(path, readonly_by_name.get(path.stem, False)))

    if CLAUDE_SETTINGS.exists():
        all_errors.extend(check_claude_settings(CLAUDE_SETTINGS))

    if all_errors:
        print("nest validation failed:\n")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print(f"agents: {len(agent_paths)} personas OK")
    print(f"nest/kilo: {len(kilo_paths)} configs OK")
    print("nest/claude/settings.json: safe-git policy OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
