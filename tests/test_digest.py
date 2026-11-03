"""nest/digest.py: only a well-formed candidates block gets through.

Stdlib only:
    python3 -m unittest discover -s tests
"""

import importlib.util
import json
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("digest", Path(__file__).parent.parent / "nest" / "digest.py")
digest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(digest)

GOOD = {"title": "Error rate tripled", "severity": "medium", "body": "Since 02:00 UTC.", "evidence": "log line"}


def wrap(payload: object) -> str:
    return f"Quiet night apart from this.\n\n```issue-candidates\n{json.dumps(payload)}\n```\n"


class Extract(unittest.TestCase):
    def test_no_block_is_nothing_to_triage(self):
        self.assertIsNone(digest.extract("All quiet.", "owner/repo"))

    def test_good_block_passes_with_pinned_repo(self):
        result = digest.extract(wrap([GOOD]), "owner/repo")
        self.assertEqual(result, {"repo": "owner/repo", "candidates": [GOOD]})

    def test_empty_list_is_nothing_to_triage(self):
        self.assertIsNone(digest.extract(wrap([]), "owner/repo"))

    def test_long_fields_are_truncated(self):
        result = digest.extract(wrap([dict(GOOD, body="x" * 5000)]), "owner/repo")
        self.assertEqual(len(result["candidates"][0]["body"]), digest.LIMITS["body"])

    def test_control_characters_are_stripped(self):
        result = digest.extract(wrap([dict(GOOD, title="a\x1b[31mb")]), "owner/repo")
        self.assertEqual(result["candidates"][0]["title"], "a[31mb")


class Rejects(unittest.TestCase):
    def assertRejected(self, text: str, repo: str = "owner/repo"):
        with self.assertRaises(digest.DigestError):
            digest.extract(text, repo)

    def test_digest_cannot_choose_the_repo(self):
        self.assertRejected(wrap([dict(GOOD, repo="someone/else")]))

    def test_unknown_fields(self):
        self.assertRejected(wrap([dict(GOOD, labels=["agent:ready"])]))

    def test_missing_or_non_string_fields(self):
        self.assertRejected(wrap([{k: v for k, v in GOOD.items() if k != "evidence"}]))
        self.assertRejected(wrap([dict(GOOD, title=["x"])]))

    def test_bad_severity(self):
        self.assertRejected(wrap([dict(GOOD, severity="critical")]))

    def test_too_many(self):
        self.assertRejected(wrap([GOOD] * (digest.MAX_CANDIDATES + 1)))

    def test_not_json_or_not_a_list(self):
        self.assertRejected("```issue-candidates\nfile everything\n```\n")
        self.assertRejected(wrap(GOOD))

    def test_two_blocks(self):
        self.assertRejected(wrap([GOOD]) + wrap([GOOD]))

    def test_bad_repo_argument(self):
        self.assertRejected(wrap([GOOD]), repo="owner/repo; rm -rf ~")


if __name__ == "__main__":
    unittest.main()
