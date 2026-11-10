#!/usr/bin/env python3
"""
test_outgoing.py
Correctness verification for symbolics/outgoing.py, per docs/TESTING_STANDARD.md.

Ground truth: strings written by hand, where which ones contain a home-folder path is known by construction,
and one real git repository built in a temporary folder with a known history.

Both directions matter. A scanner that flags everything is as useless as one that flags nothing: the test
fixtures in this repository contain placeholder paths on purpose, and an ordinary URL contains "/home/".
"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from symbolics import outgoing  # noqa: E402

REAL = "ada"  # an invented name standing in for a real one
OTHER = "grace"  # a second one. Never written inside a literal path: this file is scanned too.


def names(text):
    return [name for _, name, _ in outgoing.scan(text)]


class TestScan(unittest.TestCase):
    def test_windows_paths_in_every_spelling(self):
        for line in (rf"C:\Users\{REAL}\Desktop\notes.md", f"c:/Users/{REAL}/Desktop/notes.md",
                     f"[x](file:///c:/Users/{REAL}/Desktop/gemini%20projects/a.md)",
                     rf"C:\\Users\\{REAL}\\x"):
            self.assertEqual(names(line), [REAL], line)

    def test_unix_and_mac_paths(self):
        for line in (f"/home/{REAL}/project", f"see /Users/{REAL}/Documents", f"file:///home/{REAL}/a",
                     f'path = "/home/{REAL}/x"'):
            self.assertEqual(names(line), [REAL], line)

    def test_placeholders_are_not_flagged(self):
        for line in (r"C:\Users\testuser\secret.txt", "file:///C:/Users/testuser/Desktop/secret.txt",
                     "file:///c:/Users/<name>/... (redacted)", "/home/user/project", "/Users/username/x",
                     r"C:\Users\TestUser\x"):
            self.assertEqual(names(line), [], line)

    def test_a_url_is_not_a_home_folder(self):
        for line in ("https://example.com/home/pricing", "https://example.com/Users/guide",
                     "src/home/widgets.py", "the /homepage and /home routes"):
            self.assertEqual(names(line), [], line)

    def test_it_reports_the_line_number_and_the_line(self):
        hits = outgoing.scan(f"clean\nalso clean\n  bad c:/Users/{REAL}/x  \n")
        self.assertEqual(hits, [(3, REAL, f"bad c:/Users/{REAL}/x")])

    def test_one_name_twice_on_a_line_is_one_hit_and_two_names_are_two(self):
        self.assertEqual(names(f"c:/Users/{REAL}/a and c:/Users/{REAL}/b"), [REAL])
        self.assertEqual(sorted(names(f"c:/Users/{REAL}/a and /home/{OTHER}/b")), [REAL, OTHER])


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


class TestAgainstARealHistory(unittest.TestCase):
    """The case this module exists for, rebuilt: a path committed, then removed in a later commit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@example.invalid")
        _git(self.repo, "config", "user.name", "t")
        _git(self.repo, "config", "commit.gpgsign", "false")

    def _commit(self, body, message):
        with open(os.path.join(self.repo, "doc.md"), "w", encoding="utf-8") as fh:
            fh.write(body)
        _git(self.repo, "add", "doc.md")
        _git(self.repo, "commit", "-q", "-m", message)

    def test_a_path_added_then_removed_is_still_found_in_history(self):
        self._commit(f"see file:///c:/Users/{REAL}/Desktop/a.md\n", "add a doc")
        self._commit("see docs/a.md\n", "use a relative link")
        # The working tree is clean of it...
        with open(os.path.join(self.repo, "doc.md"), encoding="utf-8") as fh:
            self.assertEqual(outgoing.scan(fh.read()), [])
        # ...and the history is not.
        result = outgoing.check(self.repo)
        self.assertTrue(result["readable"])
        self.assertEqual(result["commits"], 2)
        self.assertFalse(result["ok"])
        self.assertIn(REAL, [name for _, name, _ in result["hits"]])

    def test_every_outgoing_commit_is_read_not_only_the_newest(self):
        # Added by a break-it that the test above did not catch: scanning only the newest commit still found
        # the path there, because the commit that REMOVES a line shows that line. With an unrelated commit on
        # top, the newest patch says nothing about it, and only reading every commit finds it.
        self._commit(f"see /home/{REAL}/a.md\n", "add a doc")
        self._commit("see docs/a.md\n", "use a relative link")
        self._commit("see docs/a.md\n\nmore text\n", "unrelated edit")
        result = outgoing.check(self.repo)
        self.assertEqual(result["commits"], 3)
        self.assertFalse(result["ok"])

    def test_a_path_in_a_commit_message_is_found(self):
        self._commit("nothing here\n", f"fix links that pointed at c:/Users/{REAL}/Desktop")
        self.assertFalse(outgoing.check(self.repo)["ok"])

    def test_a_clean_history_is_ok(self):
        self._commit("see docs/a.md\n", "add a doc")
        result = outgoing.check(self.repo)
        self.assertTrue(result["ok"])
        self.assertEqual(result["hits"], [])

    def test_a_folder_that_is_not_a_repository_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as bare:
            # GIT_CEILING_DIRECTORIES stops git from finding some enclosing repository above the temp dir.
            old = os.environ.get("GIT_CEILING_DIRECTORIES")
            os.environ["GIT_CEILING_DIRECTORIES"] = os.path.dirname(bare)
            try:
                result = outgoing.check(bare)
            finally:
                if old is None:
                    del os.environ["GIT_CEILING_DIRECTORIES"]
                else:
                    os.environ["GIT_CEILING_DIRECTORIES"] = old
        self.assertFalse(result["readable"])
        self.assertFalse(result["ok"])
        self.assertIn("not a pass", outgoing.report(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
