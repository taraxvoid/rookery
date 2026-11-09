#!/usr/bin/env python3
"""Apply rookery's .github/labels.yml (plus any extra files) to a repo's labels.

Stdlib only: labels.yml is a flat list of {name, color, description}, simple
enough to parse without a YAML library or a third-party label-sync action.
Labels missing from the files are left alone. A label with `was:` is renamed
from its old name when the old one exists and the new one doesn't, so issues
and PRs keep it.

Extra files add a repo's own labels on top of rookery's. They can't redefine
a rookery label: a name declared twice across all files is an error, so
rookery stays the source of truth for the shared set.

    python3 sync_labels.py                     # apply (needs GH_TOKEN and GH_REPO)
    python3 sync_labels.py --check             # parse and print only
    python3 sync_labels.py extra.yml [...]     # rookery's labels plus extra.yml
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
    """Problems with label names: bad format, duplicates, or a name that is also a `was`."""
    errors = [f"{l['name']!r}: use lowercase words joined by hyphens" for l in labels if not _NAME.match(l["name"])]
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


def load(paths: list[Path]) -> tuple[list[dict[str, str]], list[str]]:
    """Every label across paths, and the problems found while reading them."""
    labels, problems = [], []
    for path in paths:
        try:
            text = path.read_text()
        except OSError as e:
            problems.append(f"{path}: {e.strerror}")
            continue
        parsed = parse_labels(text)
        declared = len(re.findall(r"^-\s", text, flags=re.MULTILINE))
        if not parsed or len(parsed) != declared:
            problems.append(f"{path}: parsed {len(parsed)} of {declared} labels; check the format")
        labels += parsed
    return labels, problems


def main(argv: list[str]) -> int:
    """Sync (or with --check, print) rookery's labels plus any extra files in argv."""
    unknown = [a for a in argv if a.startswith("--") and a != "--check"]
    if unknown:
        print(f"unknown option: {' '.join(unknown)}", file=sys.stderr)
        return 2
    paths = [LABELS_FILE, *(Path(a) for a in argv if not a.startswith("--"))]
    labels, problems = load(paths)
    if problems:
        print(*problems, sep="\n", file=sys.stderr)
        return 1

    errors = name_errors(labels)
    if errors:
        print(", ".join(map(str, paths)) + ":", *errors, sep="\n  - ", file=sys.stderr)
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
