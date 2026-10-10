#!/usr/bin/env python3
"""Apply .github/labels.yml to this repo's GitHub labels with `gh`.

Stdlib only: labels.yml is a flat list of {name, color, description}, simple
enough to parse without a YAML library or a third-party label-sync action.
Labels missing from the file are left alone.

    python3 sync_labels.py            # apply (needs GH_TOKEN and GH_REPO)
    python3 sync_labels.py --check    # parse and print only
"""

import re
import subprocess
import sys
from pathlib import Path

LABELS_FILE = Path(__file__).parent / ".github" / "labels.yml"
_ENTRY = re.compile(
    r'-\s*name:\s*"(?P<name>[^"]+)"\s*\n'
    r'\s*color:\s*"(?P<color>[0-9A-Fa-f]{6})"\s*\n'
    r'\s*description:\s*"(?P<description>[^"]*)"',
)


def parse_labels(text: str) -> list[dict[str, str]]:
    return [m.groupdict() for m in _ENTRY.finditer(text)]


def main(argv: list[str]) -> int:
    text = LABELS_FILE.read_text()
    labels = parse_labels(text)
    declared = len(re.findall(r"^-\s*name:", text, flags=re.MULTILINE))
    if not labels or len(labels) != declared:
        print(f"{LABELS_FILE}: parsed {len(labels)} of {declared} labels; check the format", file=sys.stderr)
        return 1

    if "--check" in argv:
        for label in labels:
            print(f"{label['name']} #{label['color']}: {label['description']}")
        return 0

    failures = []
    for label in labels:
        result = subprocess.run(
            ["gh", "label", "create", label["name"], "--color", label["color"],
             "--description", label["description"], "--force"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            failures.append(f"{label['name']}: {result.stderr.strip()}")

    if failures:
        print("label sync failed:", *failures, sep="\n  - ", file=sys.stderr)
        return 1
    print(f"{len(labels)} labels synced")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
