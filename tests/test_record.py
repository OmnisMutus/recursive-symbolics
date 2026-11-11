"""symbolics/record.py: the record is only added to. Ground truth: git repositories built here, whose histories
are known in advance, and the real history of LIBER_0.md, where commit fc60f51 is known (read by hand on
2026-11-10) to have reworded six lines of earlier entries. The exception for that edit is named in
architecture/guards.json, never inside LIBER_0.md, which is never edited."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from symbolics import record

ENTRY = "# LIBER 0\n\n## Entries\n\n### 2026-01-01 — first\n\n**Result:** VERIFIED\n"


class Repo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.git("config", "commit.gpgsign", "false")
        self.commit(ENTRY, "start")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def git(self, *a):
        return subprocess.run(["git", "-C", self.root] + list(a), check=True, capture_output=True,
                              text=True).stdout.strip()

    def write(self, text):
        with open(os.path.join(self.root, "LIBER_0.md"), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    def guards(self, *shas):
        """Name commits as accepted edits in architecture/guards.json, the way the real repo does."""
        d = os.path.join(self.root, "architecture")
        os.makedirs(d, exist_ok=True)
        payload = {"record_edits": {"accepted": [{"commit": s} for s in shas]}}
        with open(os.path.join(d, "guards.json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def commit(self, text, msg):
        self.write(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def check(self):
        return record.check(self.root)


class TestOnlyAdded(Repo):
    def test_entries_added_above_and_below_pass(self):
        new = ENTRY.replace("## Entries\n\n", "## Entries\n\n### 2026-01-02 — newer\n\n**Result:** OPEN\n\n")
        self.commit(new + "\nmore at the end\n", "add")
        self.assertTrue(self.check()["ok"])

    def test_a_reworded_line_fails_and_names_the_commit(self):
        sha = self.commit(ENTRY.replace("VERIFIED", "FAILED"), "reword")
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertEqual([e["commit"] for e in result["edits"]], [sha[:7]])
        self.assertEqual(result["edits"][0]["lines"], ["**Result:** VERIFIED"])

    def test_a_deleted_line_fails(self):
        self.commit(ENTRY.replace("**Result:** VERIFIED\n", ""), "delete")
        self.assertFalse(self.check()["ok"])

    def test_an_older_edit_is_found_under_newer_clean_commits(self):
        self.commit(ENTRY.replace("first", "First"), "edit")
        self.commit(ENTRY.replace("first", "First") + "\nadded\n", "clean on top")
        self.assertFalse(self.check()["ok"])

    def test_an_uncommitted_edit_fails(self):
        self.write(ENTRY.replace("first", "changed"))
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertTrue(result["uncommitted"])

    def test_line_endings_and_trailing_spaces_are_not_edits(self):
        self.commit(ENTRY.replace("\n", "\r\n").replace("first", "first   "), "crlf")
        self.assertTrue(self.check()["ok"])


class TestAFileCreatedLater(unittest.TestCase):
    def test_the_commit_that_creates_the_record_only_adds(self):
        root = tempfile.mkdtemp()
        try:
            run = lambda *a: subprocess.run(["git", "-C", root] + list(a), check=True, capture_output=True)
            run("init", "-q"); run("config", "user.email", "t@example.invalid"); run("config", "user.name", "t")
            run("config", "commit.gpgsign", "false")
            open(os.path.join(root, "other.txt"), "w").write("x\n")
            run("add", "-A"); run("commit", "-q", "-m", "before the record existed")
            open(os.path.join(root, "LIBER_0.md"), "w").write(ENTRY)
            run("add", "-A"); run("commit", "-q", "-m", "record created")
            result = record.check(root)
            self.assertTrue(result["ok"], record.report(result))
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestAcceptedEdits(Repo):
    def test_an_edit_named_in_guards_passes(self):
        sha = self.commit(ENTRY.replace("first", "First"), "edit")
        self.guards(sha[:7])
        result = self.check()
        self.assertTrue(result["ok"], record.report(result))
        self.assertTrue(result["edits"][0]["recorded"])

    def test_naming_a_different_commit_does_not_cover_it(self):
        self.commit(ENTRY.replace("first", "First"), "edit")
        self.guards("abcdef1")
        self.assertFalse(self.check()["ok"])

    def test_a_short_prefix_covers_nothing(self):
        sha = self.commit(ENTRY.replace("first", "First"), "edit")
        self.guards(sha[:6])
        self.assertFalse(self.check()["ok"])

    def test_no_guards_file_means_nothing_is_covered(self):
        self.commit(ENTRY.replace("first", "First"), "edit")
        self.assertFalse(self.check()["ok"])


class TestFailsClosed(Repo):
    def test_history_that_cannot_be_read_is_an_error_not_a_pass(self):
        """Found 2026-11-10: on a mounted drive git show failed, every read came back empty, and the real
        record reported ok while holding a known edit. A read failure must never compare as no change."""
        self.commit(ENTRY.replace("first", "First"), "edit")
        real = record._git
        record._git = lambda args, cwd: (128, "") if args[:1] == ["cat-file"] else real(args, cwd)
        try:
            result = self.check()
        finally:
            record._git = real
        self.assertFalse(result["ok"])
        self.assertIn("could not read", result["error"])


class TestPure(unittest.TestCase):
    def test_erased_is_empty_for_pure_insertions(self):
        self.assertEqual(record.erased("a\nb\n", "x\na\ny\nb\nz\n"), [])

    def test_erased_lists_what_was_lost(self):
        self.assertEqual(record.erased("a\nb\nc\n", "a\nB\nc\n"), ["b"])

    def test_accepted_reads_from_guards_json(self):
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, "architecture"))
            with open(os.path.join(root, "architecture", "guards.json"), "w", encoding="utf-8") as fh:
                json.dump({"record_edits": {"accepted": [{"commit": "fc60f51"}, {"commit": "0123abc"}]}}, fh)
            self.assertEqual(record.accepted(root), {"fc60f51", "0123abc"})
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_accepted_is_empty_without_the_key(self):
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, "architecture"))
            with open(os.path.join(root, "architecture", "guards.json"), "w", encoding="utf-8") as fh:
                json.dump({"guards": []}, fh)
            self.assertEqual(record.accepted(root), set())
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestTheRealRecord(unittest.TestCase):
    def test_the_known_edit_of_2026_11_08_is_found_and_is_accepted(self):
        result = record.check()
        found = {e["commit"]: e for e in result["edits"]}
        self.assertIn("fc60f51", found)
        self.assertEqual(len(found["fc60f51"]["lines"]), 6)
        self.assertTrue(found["fc60f51"]["recorded"])

    def test_the_real_record_is_ok(self):
        result = record.check()
        self.assertTrue(result["ok"], record.report(result))


if __name__ == "__main__":
    unittest.main()
