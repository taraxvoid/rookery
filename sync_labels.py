#!/usr/bin/env python3
"""Apply .github/labels.yml to this repo's GitHub labels with `gh`.

Stdlib only: labels.yml is a flat list of {name, color, description}, simple
enough to parse without a YAML library or a third-party label-sync action.
Labels missing from the file are left alone. A label with `was:` is renamed
from its old name when the old one exists and the new one doesn't, so issues
and PRs keep it.

    python3 sync_labels.py            # apply (needs GH_TOKEN and GH_REPO)
    python3 sync_labels.py --check    # parse and print only
"""

import json
import re
import subprocess
import sys
from pathlib import Path

LABELS_FILE = Path(__file__).parent / ".github" / "labels.yml"
_ENTRY = re.compile(
    r'-\s*name:\s*"(?P<name>[^"]+)"\s*\n'
    r'(?:\s*was:\s*"(?P<was>[^"]+)"\s*\n)?'
    r'\s*color:\s*"(?P<color>[0-9A-Fa-f]{6})"\s*\n'
    r'\s*description:\s*"(?P<description>[^"]*)"',
)


# Lowercase words joined by hyphens: no quoting needed in shell commands or
# permission patterns like Bash(gh *ready-for-agent*).
_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_labels(text: str) -> list[dict[str, str]]:
    return [m.groupdict() for m in _ENTRY.finditer(text)]


def name_errors(labels: list[dict[str, str]]) -> list[str]:
    errors = [f"{l['name']!r}: use lowercase words joined by hyphens" for l in labels if not _NAME.match(l["name"])]
    # Old names predate the hyphen rule (e.g. "agent:ready"), but `was` is a
    # positional arg to `gh label edit`, so it must not parse as a flag.
    errors += [f"{l['was']!r}: previous name must not start with '-'" for l in labels if l.get("was", "").startswith("-")]
    names = [l["name"] for l in labels]
    errors += [f"{n!r}: declared twice" for n in sorted({n for n in names if names.count(n) > 1})]
    olds = {l["was"] for l in labels if l.get("was")}
    errors += [f"{n!r}: is both a current name and a previous one" for n in sorted(olds & set(names))]
    return errors


def existing_labels() -> set[str]:
    result = subprocess.run(
        ["gh", "label", "list", "--limit", "1000", "--json", "name"],
        capture_output=True, text=True, check=True,
    )
    return {label["name"] for label in json.loads(result.stdout)}


def main(argv: list[str]) -> int:
    text = LABELS_FILE.read_text()
    labels = parse_labels(text)
    declared = len(re.findall(r"^-\s*name:", text, flags=re.MULTILINE))
    if not labels or len(labels) != declared:
        print(f"{LABELS_FILE}: parsed {len(labels)} of {declared} labels; check the format", file=sys.stderr)
        return 1

    errors = name_errors(labels)
    if errors:
        print(f"{LABELS_FILE}:", *errors, sep="\n  - ", file=sys.stderr)
        return 1

    if "--check" in argv:
        for label in labels:
            was = f" (was {label['was']})" if label.get("was") else ""
            print(f"{label['name']}{was} #{label['color']}: {label['description']}")
        return 0

    existing = existing_labels()
    failures = []
    for label in labels:
        style = ["--color", label["color"], "--description", label["description"]]
        if label.get("was") in existing and label["name"] not in existing:
            command = ["gh", "label", "edit", label["was"], "--name", label["name"], *style]
        else:
            command = ["gh", "label", "create", label["name"], *style, "--force"]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            failures.append(f"{label['name']}: {result.stderr.strip()}")

    if failures:
        print("label sync failed:", *failures, sep="\n  - ", file=sys.stderr)
        return 1
    print(f"{len(labels)} labels synced")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
