#!/usr/bin/env python3
"""
test_layers.py
Correctness verification for symbolics/layers.py, per docs/TESTING_STANDARD.md.

Ground truth: toy repositories built in a temporary folder, where which files exist is known by construction.
Nothing here trusts the real index to say what the checker should report; the real index gets its own two
tests at the end, and those only assert what a reader can confirm by listing the folder.

What must never happen, each with a test below:
  - a listed file that is not there is reported as anything other than MISSING
  - a component whose evidence file is gone still counts as PRESENT
  - a run that could check nothing reports ok
  - a sibling repository that is not on the machine is reported as missing work (it is NOT_HERE: unknown)
  - a draft intent is reported as ratified
  - a quotation that has been changed, or whose source has changed, still passes
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from symbolics import layers  # noqa: E402


def _toy(files):
    """Build parent/recursive-symbolics/<files> in a temp dir; return (tempdir object, repo path)."""
    tmp = tempfile.TemporaryDirectory()
    repo = os.path.join(tmp.name, layers.THIS_REPO)
    for rel, body in files.items():
        full = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body)
    os.makedirs(repo, exist_ok=True)
    return tmp, repo


def _c(path, evidence=None, repo=layers.THIS_REPO):
    c = {"repo": repo, "path": path, "what": "toy"}
    if evidence:
        c["evidence"] = evidence
    return c


class TestComponent(unittest.TestCase):
    def setUp(self):
        self.tmp, self.repo = _toy({"a.py": "", "tests/test_a.py": ""})
        self.addCleanup(self.tmp.cleanup)

    def test_present_file_is_present(self):
        self.assertEqual(layers.check_component(_c("a.py"), self.repo)["status"], layers.PRESENT)

    def test_absent_file_is_missing_and_named(self):
        row = layers.check_component(_c("gone.py"), self.repo)
        self.assertEqual(row["status"], layers.MISSING)
        self.assertIn("gone.py", row["detail"])

    def test_present_file_with_absent_evidence_is_missing(self):
        row = layers.check_component(_c("a.py", evidence="tests/test_gone.py"), self.repo)
        self.assertEqual(row["status"], layers.MISSING)
        self.assertIn("tests/test_gone.py", row["detail"])
        self.assertNotIn("a.py,", row["detail"])  # only the absent one is named

    def test_present_file_with_present_evidence_is_present(self):
        row = layers.check_component(_c("a.py", evidence="tests/test_a.py"), self.repo)
        self.assertEqual(row["status"], layers.PRESENT)

    def test_sibling_repository_not_on_disk_is_not_here_not_missing(self):
        row = layers.check_component(_c("x.py", repo="some-sibling"), self.repo)
        self.assertEqual(row["status"], layers.NOT_HERE)

    def test_sibling_repository_on_disk_is_actually_checked(self):
        sibling = os.path.join(os.path.dirname(self.repo), "some-sibling")
        os.makedirs(sibling)
        open(os.path.join(sibling, "x.py"), "w").close()
        self.assertEqual(layers.check_component(_c("x.py", repo="some-sibling"), self.repo)["status"],
                         layers.PRESENT)
        self.assertEqual(layers.check_component(_c("y.py", repo="some-sibling"), self.repo)["status"],
                         layers.MISSING)


class TestLayerAndIndex(unittest.TestCase):
    def setUp(self):
        self.tmp, self.repo = _toy({"a.py": "", "b.py": ""})
        self.addCleanup(self.tmp.cleanup)

    def _index(self, *layer_components):
        return {"layers": [{"layer": f"L{i}", "components": comps} for i, comps in enumerate(layer_components)]}

    def test_layer_statuses(self):
        result = layers.check(self._index([_c("a.py")], [_c("a.py"), _c("gone.py")], [],
                                          [_c("x.py", repo="some-sibling")]), self.repo)
        self.assertEqual([layer["status"] for layer in result["layers"]],
                         [layers.COVERED, layers.BROKEN, layers.GAP, layers.UNCHECKED])

    def test_one_missing_file_breaks_the_whole_index(self):
        result = layers.check(self._index([_c("a.py")], [_c("b.py"), _c("gone.py")]), self.repo)
        self.assertFalse(result["ok"])
        self.assertEqual(result["broken"], ["L1"])

    def test_all_present_is_ok_and_counts_what_it_looked_for(self):
        result = layers.check(self._index([_c("a.py")], [_c("b.py")]), self.repo)
        self.assertTrue(result["ok"])
        self.assertEqual(result["checked"], 2)

    def test_declared_gap_is_not_a_failure(self):
        result = layers.check(self._index([_c("a.py")], []), self.repo)
        self.assertTrue(result["ok"])

    def test_nothing_checkable_is_not_ok(self):
        # The honesty guard. No BROKEN layer anywhere, and still not a pass.
        for index in (self._index(), self._index([]), self._index([_c("x.py", repo="some-sibling")])):
            result = layers.check(index, self.repo)
            self.assertEqual(result["broken"], [])
            self.assertEqual(result["checked"], 0)
            self.assertFalse(result["ok"])


class TestIntent(unittest.TestCase):
    def setUp(self):
        self.tmp, self.repo = _toy({"README.md": "The engine reads the person\nasking, and no one else.\n"})
        self.addCleanup(self.tmp.cleanup)

    def _intent(self, text, **extra):
        intent = {"purpose": {"text": text, "source": "README.md"}, "principles": []}
        intent.update(extra)
        return intent

    def test_exact_quotation_passes_even_across_a_line_break(self):
        result = layers.check_intent(self._intent("reads the person asking, and no one else."), self.repo)
        self.assertTrue(result["ok"])
        self.assertEqual(result["statements"], 1)

    def test_altered_quotation_is_drift(self):
        result = layers.check_intent(self._intent("reads the person asking, and everyone else."), self.repo)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["drifted"]), 1)

    def test_missing_source_is_drift(self):
        intent = {"purpose": {"text": "anything", "source": "NOPE.md"}, "principles": []}
        self.assertFalse(layers.check_intent(intent, self.repo)["ok"])

    def test_empty_quotation_is_drift_not_a_free_pass(self):
        # "" is a substring of everything; it must not pass on that technicality.
        self.assertFalse(layers.check_intent(self._intent(""), self.repo)["ok"])

    def test_intent_with_no_statements_is_not_ok(self):
        self.assertFalse(layers.check_intent({"principles": []}, self.repo)["ok"])

    def test_draft_is_never_reported_as_ratified(self):
        good = "reads the person asking, and no one else."
        for extra in ({}, {"ratified": False, "ratified_by": "x", "ratified_on": "2026-01-01"},
                      {"ratified": True}, {"ratified": True, "ratified_by": "x"},
                      {"ratified": "true", "ratified_by": "x", "ratified_on": "2026-01-01"}):
            self.assertEqual(layers.check_intent(self._intent(good, **extra), self.repo)["state"], "DRAFT", extra)

    def test_ratified_needs_all_three_fields(self):
        intent = self._intent("reads the person asking, and no one else.",
                              ratified=True, ratified_by="the Maintainer", ratified_on="2026-01-01")
        self.assertEqual(layers.check_intent(intent, self.repo)["state"], "RATIFIED")


class TestTheRealFiles(unittest.TestCase):
    """Only what a reader can confirm by listing the folder. No snapshot of statuses: the index is meant to
    change, and this must not have to be edited every time it does."""

    def test_real_index_has_no_missing_file_in_this_repository(self):
        result = layers.check()
        own_missing = [f"{layer['layer']}: {r['path']} ({r['detail']})"
                       for layer in result["layers"] for r in layer["components"]
                       if r["repo"] == layers.THIS_REPO and r["status"] == layers.MISSING]
        self.assertEqual(own_missing, [])
        self.assertGreater(result["checked"], 0)

    def test_real_intent_quotes_its_sources_exactly_and_is_parseable(self):
        intent = layers.load(layers.INTENT)
        result = layers.check_intent(intent)
        self.assertEqual(result["drifted"], [])
        self.assertTrue(result["ok"])
        # Whatever state it is in, the state must agree with the file's own three fields.
        expect = "RATIFIED" if (intent.get("ratified") is True and intent.get("ratified_by")
                                and intent.get("ratified_on")) else "DRAFT"
        self.assertEqual(result["state"], expect)

    def test_report_renders_and_says_draft_when_draft(self):
        text = layers.report(layers.check(), layers.check_intent({"purpose": {"text": "", "source": "x"}}))
        self.assertIn("ARCHITECTURE INDEX", text)
        self.assertIn("INTENT: DRAFT", text)
        json.dumps(layers.check())  # the result is plain data


if __name__ == "__main__":
    unittest.main(verbosity=2)
