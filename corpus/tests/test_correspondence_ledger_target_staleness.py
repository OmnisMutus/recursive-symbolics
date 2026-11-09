#!/usr/bin/env python3
"""
test_correspondence_ledger_target_staleness.py
Correctness verification for correspondence_ledger_target_staleness.py
per TESTING_STANDARD.md.

Ground truth: a real, temporary git repository, built fresh in each
test, with commits made at exact, hand-chosen timestamps via
GIT_AUTHOR_DATE/GIT_COMMITTER_DATE -- not mocked, not assumed. This
directly tests get_last_commit_utc() against git's own real, observable
behavior, and compute_staleness_flags()'s comparison logic against those
real, known timestamps -- not against a fake in-memory stand-in for git.
"""

import os
import sys
import unittest
import tempfile
import subprocess
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))  # for root-level run_all_correspondence_ledgers.py
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from correspondence_ledger_target_staleness import (
    get_last_commit_utc, compute_staleness_flags, format_staleness_report,
)

UTC = datetime.timezone.utc


def _init_repo(root: Path):
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)


def _commit_file(root: Path, relpath: str, content: str, commit_dt: datetime.datetime):
    """Writes relpath with content and commits it at an exact, controlled
    timestamp -- real ground truth, not a mocked git log."""
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    subprocess.run(["git", "add", relpath], cwd=root, check=True)
    env = dict(os.environ)
    date_str = commit_dt.isoformat()
    env.update({
        "GIT_AUTHOR_DATE": date_str, "GIT_COMMITTER_DATE": date_str,
        "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    })
    subprocess.run(["git", "commit", "-q", "-m", f"commit {relpath}"],
                    cwd=root, check=True, env=env)


class TestGetLastCommitUtc(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.root = Path(self._tmpdir.name)
        _init_repo(self.root)

    def test_returns_none_for_untracked_file(self):
        (self.root / "untouched.py").write_text("x = 1\n")
        self.assertIsNone(get_last_commit_utc("untouched.py", self.root))

    def test_returns_none_for_nonexistent_path(self):
        self.assertIsNone(get_last_commit_utc("does_not_exist.py", self.root))

    def test_returns_exact_commit_timestamp(self):
        commit_time = datetime.datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)
        _commit_file(self.root, "a.py", "x = 1\n", commit_time)
        got = get_last_commit_utc("a.py", self.root)
        self.assertEqual(got, commit_time)

    def test_returns_most_recent_of_multiple_commits_to_same_file(self):
        t1 = datetime.datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
        t2 = datetime.datetime(2026, 7, 15, 0, 0, 0, tzinfo=UTC)
        _commit_file(self.root, "a.py", "x = 1\n", t1)
        _commit_file(self.root, "a.py", "x = 2\n", t2)
        got = get_last_commit_utc("a.py", self.root)
        self.assertEqual(got, t2)


class TestComputeStalenessFlags(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.root = Path(self._tmpdir.name)
        _init_repo(self.root)

    def test_no_baseline_when_ledger_never_recorded(self):
        flags = compute_staleness_flags({}, target_files={"x.py": ["a.py"]}, repo_root=self.root)
        self.assertFalse(flags["x.py"]["has_baseline"])
        self.assertIsNone(flags["x.py"]["changed_since_check"])

    def test_flags_changed_when_file_committed_after_last_check(self):
        commit_time = datetime.datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC)
        _commit_file(self.root, "a.py", "x = 1\n", commit_time)
        last_run = datetime.datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC)  # before the commit
        history = {"x.py": {"last_run_utc": last_run.isoformat()}}
        flags = compute_staleness_flags(history, target_files={"x.py": ["a.py"]}, repo_root=self.root)
        self.assertTrue(flags["x.py"]["changed_since_check"])
        self.assertEqual(flags["x.py"]["most_recent_change_file"], "a.py")

    def test_not_flagged_when_check_happened_after_last_commit(self):
        commit_time = datetime.datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
        _commit_file(self.root, "a.py", "x = 1\n", commit_time)
        last_run = datetime.datetime(2026, 7, 20, 0, 0, 0, tzinfo=UTC)  # after the commit
        history = {"x.py": {"last_run_utc": last_run.isoformat()}}
        flags = compute_staleness_flags(history, target_files={"x.py": ["a.py"]}, repo_root=self.root)
        self.assertFalse(flags["x.py"]["changed_since_check"])

    def test_boundary_commit_exactly_at_last_run_is_not_flagged(self):
        # Strictly-greater-than boundary, same discipline as
        # correspondence_ledger_history.py's stale_threshold_days check.
        t = datetime.datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC)
        _commit_file(self.root, "a.py", "x = 1\n", t)
        history = {"x.py": {"last_run_utc": t.isoformat()}}
        flags = compute_staleness_flags(history, target_files={"x.py": ["a.py"]}, repo_root=self.root)
        self.assertFalse(flags["x.py"]["changed_since_check"])

    def test_picks_most_recently_changed_of_several_target_files(self):
        _commit_file(self.root, "a.py", "x = 1\n", datetime.datetime(2026, 7, 1, tzinfo=UTC))
        _commit_file(self.root, "b.py", "y = 1\n", datetime.datetime(2026, 7, 25, tzinfo=UTC))
        last_run = datetime.datetime(2026, 7, 10, tzinfo=UTC)
        history = {"x.py": {"last_run_utc": last_run.isoformat()}}
        flags = compute_staleness_flags(history, target_files={"x.py": ["a.py", "b.py"]}, repo_root=self.root)
        self.assertTrue(flags["x.py"]["changed_since_check"])
        self.assertEqual(flags["x.py"]["most_recent_change_file"], "b.py")

    def test_untracked_target_file_does_not_crash_and_reports_no_history(self):
        last_run = datetime.datetime(2026, 7, 10, tzinfo=UTC)
        history = {"x.py": {"last_run_utc": last_run.isoformat()}}
        flags = compute_staleness_flags(history, target_files={"x.py": ["never_committed.py"]}, repo_root=self.root)
        self.assertFalse(flags["x.py"]["changed_since_check"])
        self.assertIsNone(flags["x.py"]["most_recent_change_utc"])

    def test_multiple_ledgers_computed_independently(self):
        _commit_file(self.root, "a.py", "x = 1\n", datetime.datetime(2026, 7, 25, tzinfo=UTC))
        _commit_file(self.root, "b.py", "y = 1\n", datetime.datetime(2026, 7, 1, tzinfo=UTC))
        last_run = datetime.datetime(2026, 7, 10, tzinfo=UTC)
        history = {
            "x.py": {"last_run_utc": last_run.isoformat()},
            "y.py": {"last_run_utc": last_run.isoformat()},
        }
        flags = compute_staleness_flags(
            history, target_files={"x.py": ["a.py"], "y.py": ["b.py"]}, repo_root=self.root)
        self.assertTrue(flags["x.py"]["changed_since_check"])
        self.assertFalse(flags["y.py"]["changed_since_check"])


class TestFormatStalenessReport(unittest.TestCase):
    def test_no_baseline_message(self):
        flags = {"a.py": {"has_baseline": False, "changed_since_check": None,
                            "most_recent_change_file": None, "most_recent_change_utc": None}}
        report = format_staleness_report(flags)
        self.assertIn("no prior recorded check", report)

    def test_changed_message_names_the_file(self):
        flags = {"a.py": {"has_baseline": True, "changed_since_check": True,
                            "most_recent_change_file": "b.py",
                            "most_recent_change_utc": "2026-07-25T00:00:00+00:00"}}
        report = format_staleness_report(flags)
        self.assertIn("REVIEW SUGGESTED", report)
        self.assertIn("b.py", report)

    def test_unchanged_message(self):
        flags = {"a.py": {"has_baseline": True, "changed_since_check": False,
                            "most_recent_change_file": "b.py",
                            "most_recent_change_utc": "2026-06-01T00:00:00+00:00"}}
        report = format_staleness_report(flags)
        self.assertIn("no target-file changes", report)

    def test_no_git_history_message(self):
        flags = {"a.py": {"has_baseline": True, "changed_since_check": False,
                            "most_recent_change_file": None, "most_recent_change_utc": None}}
        report = format_staleness_report(flags)
        self.assertIn("can't compare", report)


class TestRealTargetFilesMapping(unittest.TestCase):
    """Sanity check against the REAL repo (not a temp one): every path
    named in TARGET_FILES must actually exist on disk. This is what would
    have caught a typo'd filename in the mapping itself."""

    def test_every_target_file_path_exists_on_disk(self):
        from correspondence_ledger_target_staleness import TARGET_FILES, REPO_ROOT
        missing = []
        for ledger_name, files in TARGET_FILES.items():
            for relpath in files:
                if not (REPO_ROOT / relpath).exists():
                    missing.append((ledger_name, relpath))
        self.assertEqual(missing, [], f"TARGET_FILES names paths that don't exist: {missing}")

    def test_every_ledger_in_target_files_matches_a_real_ledger(self):
        from correspondence_ledger_target_staleness import TARGET_FILES
        from run_all_correspondence_ledgers import LEDGERS
        real_ledger_names = {fname for fname, _ in LEDGERS}
        self.assertEqual(set(TARGET_FILES.keys()), real_ledger_names)


def run_unit_test_suite():
    print("=" * 72)
    print("  CORRESPONDENCE LEDGER TARGET STALENESS -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("Test") and isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
