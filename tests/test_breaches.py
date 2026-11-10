#!/usr/bin/env python3
"""
test_breaches.py
Correctness verification for symbolics/breaches.py, per docs/TESTING_STANDARD.md.

Ground truth: toy records and toy repositories built in a temporary folder, where which entries are breaches
and which guards exist is known by construction. The real LIBER_0.md gets one test at the end, and it asserts
only the property this module exists to hold: no breach in the real record is UNGUARDED or BROKEN.

What must never happen, each with a test below:
  - a breach with no guard and no reason passes
  - a guard naming a test that is not in the file counts as a guard
  - a waiver with no reason counts as a waiver
  - an entry that is not a breach is dragged in (the word "corrected" in prose is not the status CORRECTED)
  - a record the parser cannot read reports ok
  - a guard recorded for an entry that does not exist goes unnoticed
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from symbolics import breaches as b  # noqa: E402

HEAD = "# LIBER 0\n\n## Entry Format\n\n```\n### [Date] — [Short title]\n**Result:** CORRECTED\n```\n\n## Entries\n\n"


def entry(title, result, extra=""):
    return f"### 2026-01-01 — {title}\n\n**Attempted:** x.\n\n**Result:** {result}\n\n{extra}**Notes:** n.\n\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        os.makedirs(os.path.join(self.repo, "tests"))
        with open(os.path.join(self.repo, "tests", "test_x.py"), "w") as fh:
            fh.write("class T:\n    def test_real(self):\n        pass\n    def test_real_longer(self):\n        pass\n")

    def run_check(self, text, guards=()):
        return b.check(HEAD + text, {"guards": list(guards)}, self.repo)

    def statuses(self, text, guards=()):
        return [r["status"] for r in self.run_check(text, guards)["rows"]]


class TestWhatCountsAsABreach(Base):
    def test_status_words_on_the_result_line_make_a_breach(self):
        for result in ("CORRECTED.", "VERIFIED, and CORRECTED twice.", "FAILED: exact error"):
            self.assertEqual(len(self.run_check(entry("t", result))["rows"]), 1, result)

    def test_other_results_are_not_breaches(self):
        for result in ("VERIFIED.", "OPEN.", "VERIFIED, with a correction to a number", "it failed quietly"):
            self.assertEqual(self.run_check(entry("t", result))["rows"], [], result)

    def test_the_word_elsewhere_in_the_entry_does_not_make_a_breach(self):
        text = entry("t", "VERIFIED.", "This was CORRECTED later and the first run FAILED.\n\n")
        self.assertEqual(self.run_check(text)["rows"], [])

    def test_the_example_inside_the_entry_format_section_is_not_an_entry(self):
        # HEAD carries a `### ... **Result:** CORRECTED` example above `## Entries`. It must not be read.
        result = self.run_check(entry("t", "VERIFIED."))
        self.assertEqual(result["entries"], 1)
        self.assertEqual(result["rows"], [])


class TestStatuses(Base):
    def test_unguarded_breach_fails(self):
        result = self.run_check(entry("t", "CORRECTED."))
        self.assertEqual([r["status"] for r in result["rows"]], [b.UNGUARDED])
        self.assertFalse(result["ok"])

    def test_inline_guard_that_exists_is_guarded(self):
        text = entry("t", "CORRECTED.", "**Guard:** tests/test_x.py::test_real\n\n")
        result = self.run_check(text)
        self.assertEqual([r["status"] for r in result["rows"]], [b.GUARDED])
        self.assertTrue(result["ok"])

    def test_guard_may_be_a_whole_file_and_may_be_in_backticks(self):
        self.assertEqual(self.statuses(entry("t", "FAILED.", "**Guard:** `tests/test_x.py`\n\n")), [b.GUARDED])

    def test_guard_naming_an_absent_test_is_broken(self):
        result = self.run_check(entry("t", "CORRECTED.", "**Guard:** tests/test_x.py::test_gone\n\n"))
        self.assertEqual([r["status"] for r in result["rows"]], [b.BROKEN])
        self.assertIn("test_gone", result["rows"][0]["detail"])
        self.assertFalse(result["ok"])

    def test_a_test_name_must_match_whole_not_as_a_prefix(self):
        # test_rea is a prefix of test_real and is not a test.
        self.assertEqual(self.statuses(entry("t", "CORRECTED.", "**Guard:** tests/test_x.py::test_rea\n\n")),
                         [b.BROKEN])

    def test_guard_naming_an_absent_file_is_broken(self):
        self.assertEqual(self.statuses(entry("t", "CORRECTED.", "**Guard:** tests/nope.py::test_real\n\n")),
                         [b.BROKEN])

    def test_one_good_guard_does_not_hide_one_broken_guard(self):
        text = entry("t", "CORRECTED.", "**Guard:** tests/test_x.py::test_real, tests/test_x.py::test_gone\n\n")
        self.assertEqual(self.statuses(text), [b.BROKEN])

    def test_waiver_with_a_reason_is_waived_and_shown(self):
        result = self.run_check(entry("t", "CORRECTED.", "**Guard:** none: no test can check this\n\n"))
        self.assertEqual([r["status"] for r in result["rows"]], [b.WAIVED])
        self.assertEqual(result["rows"][0]["detail"], "no test can check this")
        self.assertTrue(result["ok"])
        self.assertIn("no test can check this", b.report(result))

    def test_waiver_without_a_reason_is_unguarded(self):
        for line in ("**Guard:** none:\n\n", "**Guard:** none: \n\n", "**Guard:**\n\n"):
            self.assertEqual(self.statuses(entry("t", "CORRECTED.", line)), [b.UNGUARDED], line)


class TestSidecar(Base):
    H = "2026-01-01 — old one"

    def test_sidecar_guards_an_entry_that_cannot_be_edited(self):
        rows = self.run_check(entry("old one", "CORRECTED."),
                              [{"entry": self.H, "guards": ["tests/test_x.py::test_real"]}])["rows"]
        self.assertEqual([r["status"] for r in rows], [b.GUARDED])

    def test_sidecar_waiver(self):
        self.assertEqual(self.statuses(entry("old one", "CORRECTED."), [{"entry": self.H, "waived": "why"}]),
                         [b.WAIVED])
        self.assertEqual(self.statuses(entry("old one", "CORRECTED."), [{"entry": self.H, "waived": "  "}]),
                         [b.UNGUARDED])

    def test_sidecar_broken_guard_is_broken(self):
        self.assertEqual(self.statuses(entry("old one", "CORRECTED."),
                                       [{"entry": self.H, "guards": ["tests/test_x.py::test_gone"]}]),
                         [b.BROKEN])

    def test_sidecar_naming_an_entry_that_does_not_exist_is_broken(self):
        result = self.run_check(entry("old one", "VERIFIED."),
                                [{"entry": "2026-01-01 — never written", "guards": ["tests/test_x.py"]}])
        self.assertEqual([r["status"] for r in result["rows"]], [b.BROKEN])
        self.assertFalse(result["ok"])

    def test_heading_must_match_exactly(self):
        # A near miss guards nothing: the breach stays UNGUARDED and the stray key is BROKEN.
        got = self.statuses(entry("old one", "CORRECTED."),
                            [{"entry": "2026-01-01 — Old one", "guards": ["tests/test_x.py"]}])
        self.assertEqual(sorted(got), sorted([b.UNGUARDED, b.BROKEN]))


class TestTheGuardOnTheChecker(Base):
    def test_a_record_with_no_readable_entries_is_not_ok(self):
        for text in ("", "# LIBER 0\n\nno entries heading at all\n", "# LIBER 0\n\n## Entries\n\nprose only\n"):
            result = b.check(text, {"guards": []}, self.repo)
            self.assertEqual(result["entries"], 0)
            self.assertFalse(result["ok"])
            self.assertIn("not a pass", b.report(result))

    def test_entries_with_no_breach_among_them_is_ok(self):
        result = self.run_check(entry("t", "VERIFIED."))
        self.assertTrue(result["ok"])

    def test_counts_add_up(self):
        text = (entry("a", "CORRECTED.") + entry("b", "CORRECTED.", "**Guard:** tests/test_x.py\n\n")
                + entry("c", "FAILED.", "**Guard:** none: reason\n\n") + entry("d", "VERIFIED."))
        result = self.run_check(text)
        self.assertEqual(result["entries"], 4)
        self.assertEqual(result["count"], {b.GUARDED: 1, b.WAIVED: 1, b.UNGUARDED: 1, b.BROKEN: 0})
        self.assertEqual(sum(result["count"].values()), len(result["rows"]))


class TestTheRealRecord(unittest.TestCase):
    def test_no_breach_in_the_real_record_is_unguarded_or_broken(self):
        result = b.check()
        bad = [f"{r['status']}: {r['entry']} ({r['detail']})" for r in result["rows"]
               if r["status"] in (b.UNGUARDED, b.BROKEN)]
        self.assertEqual(bad, [])
        self.assertGreater(result["entries"], 0)
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
