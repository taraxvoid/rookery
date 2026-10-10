#!/usr/bin/env python3
"""Extract and check the issue-candidates block from a tier-0 digest.

The digest is built from logs and analytics anyone can write into, so nothing
from it reaches the triaging crow unchecked: only the fenced issue-candidates
block, parsed as JSON, at most MAX_CANDIDATES entries, known fields only, each
a string within a length limit, severity from a fixed set. The target repo
comes from the caller, never from the digest.

    nest/digest.py <owner/repo> < digest.txt    # prints checked JSON, or nothing

Exit 0 with no output when the digest has no block; exit 1 if the block is
malformed (an honest bird can't produce one, so it's worth a look).
Stdlib only.
"""

import json
import re
import sys

MAX_CANDIDATES = 10
LIMITS = {"title": 120, "body": 2000, "evidence": 1000}
SEVERITIES = ("low", "medium", "high")
_BLOCK = re.compile(r"^```issue-candidates[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
_REPO = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class DigestError(ValueError):
    pass


def check_candidate(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise DigestError("candidate is not an object")
    unknown = set(raw) - set(LIMITS) - {"severity"}
    if unknown:
        raise DigestError(f"unknown fields: {sorted(unknown)}")
    out = {}
    for field, limit in LIMITS.items():
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise DigestError(f"{field} must be a non-empty string")
        out[field] = _CONTROL.sub("", value.strip())[:limit]
    if raw.get("severity") not in SEVERITIES:
        raise DigestError(f"severity must be one of {SEVERITIES}")
    out["severity"] = raw["severity"]
    return out


def extract(digest: str, repo: str) -> dict | None:
    if not _REPO.match(repo):
        raise DigestError(f"bad repo {repo!r}")
    blocks = _BLOCK.findall(digest)
    if not blocks:
        return None
    if len(blocks) > 1:
        raise DigestError("more than one issue-candidates block")
    try:
        parsed = json.loads(blocks[0])
    except json.JSONDecodeError as e:
        raise DigestError(f"block is not JSON: {e}") from e
    if not isinstance(parsed, list):
        raise DigestError("block is not a JSON array")
    if len(parsed) > MAX_CANDIDATES:
        raise DigestError(f"more than {MAX_CANDIDATES} candidates")
    candidates = [check_candidate(c) for c in parsed]
    return {"repo": repo, "candidates": candidates} if candidates else None


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        result = extract(sys.stdin.read(), argv[0])
    except DigestError as e:
        print(f"digest rejected: {e}", file=sys.stderr)
        return 1
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
