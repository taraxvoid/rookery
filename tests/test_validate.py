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


class DocLinks(unittest.TestCase):
    def check(self, text: str) -> list[str]:
        with tempfile.NamedTemporaryFile("w", suffix=".md", dir=validate.ROOT / "tests", delete=False) as f:
            f.write(text)
        path = Path(f.name)
        try:
            return validate.check_links(path)
        finally:
            path.unlink()

    def test_broken_reference_fails(self):
        self.assertTrue(self.check("see `nest/README.md` and [x](agents/nope.md)"))

    def test_real_reference_passes(self):
        self.assertEqual(self.check("see `nest/claude/settings.json` and [x](../agents/crow.md)"), [])

    def test_placeholders_globs_and_dirs_are_skipped(self):
        self.assertEqual(self.check("`nest/gh-aw/shared/<bird>.md`, `agents/*.md`, `roost/`, `skills/council/`"), [])


class LabelsFile(unittest.TestCase):
    def test_every_declared_label_parses(self):
        spec = importlib.util.spec_from_file_location("sync_labels", validate.ROOT / "sync_labels.py")
        sync_labels = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync_labels)
        self.assertEqual(sync_labels.main(["--check"]), 0)


class ReadonlyBash(unittest.TestCase):
    def test_scoped_bash_counts_as_bash(self):
        self.assertTrue(validate.has_any_bash("Read, Bash(gitleaks*)"))
        self.assertFalse(validate.has_any_bash("Read, Grep, Glob"))


class ReadonlyPersona(unittest.TestCase):
    def check(self, frontmatter: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "finch.md"
            path.write_text(f"---\n{frontmatter}\n---\n\nbody\n")
            return validate.check_file(path)

    def test_new_readonly_persona_needs_no_runtime_config(self):
        # Kilo is gone: a tier-0 bird with a tight tools: line stands on its own.
        self.assertEqual(self.check("name: finch\ntier: 0\ndescription: d\nmodel: haiku\ntools: Read, Grep, Glob"), [])

    def test_readonly_persona_must_set_tools(self):
        self.assertTrue(self.check("name: finch\ntier: 0\ndescription: d\nmodel: haiku"))

    def test_readonly_persona_rejects_write_tools(self):
        self.assertTrue(self.check("name: finch\ntier: 0\ndescription: d\nmodel: haiku\ntools: Read, Edit"))


if __name__ == "__main__":
    unittest.main()


class Flocks(unittest.TestCase):
    GOOD = 'name = "demo"\noperator = "someone"\nrepos = ["org/app"]\n'

    def check(self, toml: str, name: str = "demo", readme: bool = True) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            flock = Path(tmp) / name
            flock.mkdir()
            (flock / "flock.toml").write_text(toml)
            if readme:
                (flock / "README.md").write_text("# demo\n")
            return validate.check_flock(flock)

    def test_shipped_flocks_pass(self):
        for flock in sorted(p for p in validate.FLOCKS_DIR.iterdir() if p.is_dir()):
            with self.subTest(flock=flock.name):
                self.assertEqual(validate.check_flock(flock), [])

    def test_minimal_flock_passes(self):
        self.assertEqual(self.check(self.GOOD), [])

    def test_name_must_match_directory(self):
        self.assertTrue(any("!= directory" in e for e in self.check(self.GOOD, name="other")))

    def test_unknown_key_fails(self):
        self.assertTrue(any("unknown key 'lables'" in e for e in self.check(self.GOOD + 'lables = []\n')))

    def test_unknown_nested_key_fails(self):
        errors = self.check(self.GOOD + '[runners]\nself_hosted = true\nlable = "x"\n')
        self.assertTrue(any("runners.lable" in e for e in errors), errors)

    def test_bad_repo_slug_fails(self):
        errors = self.check('name = "demo"\noperator = "someone"\nrepos = ["not-a-slug"]\n')
        self.assertTrue(any("owner/name" in e for e in errors), errors)

    def test_empty_repos_fails(self):
        errors = self.check('name = "demo"\noperator = "someone"\nrepos = []\n')
        self.assertTrue(any("must not be empty" in e for e in errors), errors)

    def test_missing_readme_fails(self):
        self.assertTrue(any("README.md" in e for e in self.check(self.GOOD, readme=False)))

    def test_wrong_type_fails(self):
        errors = self.check(self.GOOD + '[runners]\nself_hosted = "yes"\n')
        self.assertTrue(any("must be a bool" in e for e in errors), errors)


class LabelNames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("sync_labels", validate.ROOT / "sync_labels.py")
        cls.sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.sync)

    def label(self, name: str, was: str | None = None) -> dict:
        return {"name": name, "was": was, "color": "000000", "description": ""}

    def test_shipped_labels_pass(self):
        labels = self.sync.parse_labels(self.sync.LABELS_FILE.read_text())
        self.assertEqual(self.sync.name_errors(labels), [])

    def test_was_is_parsed(self):
        text = '- name: "needs-you"\n  was: "agent:needs-you"\n  color: "D93F0B"\n  description: "x"\n'
        self.assertEqual(self.sync.parse_labels(text)[0]["was"], "agent:needs-you")

    def test_unreadable_names_fail(self):
        for name in ("agent:ready", "Needs You", "needs you", "needs_you", "-x", "x-"):
            with self.subTest(name=name):
                self.assertTrue(self.sync.name_errors([self.label(name)]))

    def test_duplicates_and_reused_old_names_fail(self):
        self.assertTrue(self.sync.name_errors([self.label("a"), self.label("a")]))
        self.assertTrue(self.sync.name_errors([self.label("a"), self.label("b", was="a")]))
