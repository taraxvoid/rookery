"""validate.py: the repo passes, and the safe-git checks catch regressions.

Stdlib only:
    python3 -m unittest discover -s tests
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("validate", Path(__file__).parent.parent / "validate.py")
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)

SETTINGS = json.loads(validate.CLAUDE_SETTINGS.read_text())


def errors_for(settings: dict) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "settings.json"
        path.write_text(json.dumps(settings))
        return validate.check_claude_settings(path)


class RepoPasses(unittest.TestCase):
    def test_main_exits_zero(self):
        self.assertEqual(validate.main(), 0)


class SafeGitPolicy(unittest.TestCase):
    def test_shipped_settings_pass(self):
        self.assertEqual(errors_for(SETTINGS), [])

    def test_missing_required_deny_fails(self):
        for rule in validate.REQUIRED_DENY:
            with self.subTest(rule=rule):
                perms = dict(SETTINGS["permissions"], deny=[r for r in SETTINGS["permissions"]["deny"] if r != rule])
                errors = errors_for({"permissions": perms})
                self.assertTrue(any(rule in e for e in errors), errors)

    def test_broad_allow_fails(self):
        for rule in ("Bash", "Bash(git *)", "Bash(gh *)", "Bash(git push *)"):
            with self.subTest(rule=rule):
                perms = dict(SETTINGS["permissions"], allow=SETTINGS["permissions"]["allow"] + [rule])
                self.assertTrue(errors_for({"permissions": perms}))


class ReadonlyBash(unittest.TestCase):
    def test_scoped_bash_counts_as_bash(self):
        self.assertTrue(validate.has_any_bash("Read, Bash(gitleaks*)"))
        self.assertFalse(validate.has_any_bash("Read, Grep, Glob"))


if __name__ == "__main__":
    unittest.main()
