#!/usr/bin/env python3
"""How often each subagent type actually ran, from local Claude Code transcripts.

A persona that never runs is a name, not a tool. This reads the session
transcripts Claude Code keeps under ~/.claude/projects/ and reports, per
subagent type: how many times it was dispatched, in how many projects and
when it last ran. Personas in agents/ with no runs in
the window are listed at the end, so dead ones are easy to spot.

Stdlib only, reads local files, sends nothing anywhere:
    python3 scripts/persona-usage.py            # last 30 days
    python3 scripts/persona-usage.py --days 90
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_TOOLS = {"Agent", "Task"}


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def scan(projects: Path, since: datetime) -> dict[str, dict]:
    stats: dict[str, dict] = defaultdict(lambda: {"calls": 0, "projects": set(), "last": None})
    for path in projects.rglob("*.jsonl"):
        project = path.relative_to(projects).parts[0]
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if '"subagent_type"' not in line:
                continue  # cheap prefilter; most lines are not agent calls
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = parse_ts(entry.get("timestamp"))
            if ts is None or ts < since:
                continue
            content = (entry.get("message") or {}).get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in AGENT_TOOLS:
                        kind = (block.get("input") or {}).get("subagent_type") or "general-purpose"
                        s = stats[kind]
                        s["calls"] += 1
                        s["projects"].add(project)
                        s["last"] = max(filter(None, (s["last"], ts)))
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--projects", type=Path, default=Path.home() / ".claude" / "projects")
    args = parser.parse_args()

    if not args.projects.is_dir():
        # A report that silently checks nothing is worse than none.
        print(f"no transcripts at {args.projects}", file=sys.stderr)
        return 1

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    stats = scan(args.projects, since)

    print(f"subagent runs in the last {args.days} days")
    print(f"{'type':<20} {'calls':>6} {'projects':>9}  last")
    for kind, s in sorted(stats.items(), key=lambda kv: -kv[1]["calls"]):
        last = s["last"].date().isoformat() if s["last"] else "-"
        print(f"{kind:<20} {s['calls']:>6} {len(s['projects']):>9}  {last}")

    personas = sorted(p.stem for p in (ROOT / "agents").glob("*.md"))
    unused = [name for name in personas if stats.get(name, {}).get("calls", 0) == 0]
    if unused:
        print(f"\nrookery personas with no runs in the window: {', '.join(unused)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
