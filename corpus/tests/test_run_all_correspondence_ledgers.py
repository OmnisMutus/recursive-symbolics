#!/usr/bin/env python3
"""
test_run_all_correspondence_ledgers.py
Correctness verification for run_all_correspondence_ledgers.py per
TESTING_STANDARD.md.

This tests the AGGREGATION LOGIC (run_ledgers()), not any specific
Sephirotic/engine claim -- those are each already covered by their own
ledger's worked-example tests. Ground truth here is split two ways:

1. Hand-built toy "ledger modules" (simple objects exposing a
   build_ledger() function, constructed from real CorrespondenceLedger/
   Correspondence objects with known, controlled outcomes) -- so the
   unexpected-failure and resolved-known-failure detection logic can be
   tested against known-by-construction scenarios, not by re-deriving
   anything from the real engines.
2. One integration test against the 5 REAL ledgers in this repo,
   asserting the current known-good baseline (22 total correspondences,
   15 VERIFIED, 0 FAILED, 7 UNTESTABLE, ok == True). This is a regression
   snapshot on the aggregation glue code, not a re-test of any individual
   engine -- if a ledger is legitimately extended later, this specific
   test's numbers need a deliberate, conscious update, not a silent one.

CORRECTION (dated, see LIBER_0.md): the baseline above used to be 14
VERIFIED / 1 FAILED [documented] -- ddpg_correspondence_ledger.py's
actor-critic gap was a real, deliberately-registered FAILED entry.
That gap is now fixed (see ddpg_quadcopter_rca_engine.py's dated
correction note), so the baseline moved to 15/0/7 and
KNOWN_EXPECTED_FAILURES is now empty.
test_ddpg_actor_critic_gap_is_the_one_known_failure below was updated to
match (now asserts the gap is VERIFIED, not FAILED) rather than deleted,
so the change in behavior stays visible in this file's own history.
"""

import sys
import io
import json
import unittest
import tempfile
import contextlib
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))  # for root-level run_all_correspondence_ledgers.py
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from correspondence_ledger import CorrespondenceLedger, ValidationResult
from run_all_correspondence_ledgers import main as run_all_main
from run_all_correspondence_ledgers import (
    run_ledgers, LEDGERS, KNOWN_EXPECTED_FAILURES,
)


def _toy_module(ledger_factory):
    """Wraps a zero-arg ledger-building function in an object exposing
    build_ledger(), the same shape a real ledger module has (a module
    with a module-level build_ledger() function)."""
    return SimpleNamespace(build_ledger=ledger_factory)


class TestRunLedgersAggregation(unittest.TestCase):
    """Ground truth: hand-built toy ledgers with known, controlled
    VERIFIED/FAILED/UNTESTABLE outcomes, constructed the same way
    test_correspondence_ledger.py's own fixtures are."""

    def _all_clean_ledger(self):
        ledger = CorrespondenceLedger("toy-clean")
        ledger.register("A", "t", "c", validator=lambda: ValidationResult(True))
        ledger.register("B", "t", "c", validator=None)
        return ledger

    def _one_failing_ledger(self):
        ledger = CorrespondenceLedger("toy-failing")
        ledger.register("Known Gap", "t", "c",
                         validator=lambda: ValidationResult(False, "expected to fail"))
        ledger.register("C", "t", "c", validator=lambda: ValidationResult(True))
        return ledger

    def test_aggregates_counts_across_multiple_ledgers(self):
        ledgers = [
            ("toy_clean.py", _toy_module(self._all_clean_ledger)),
            ("toy_failing.py", _toy_module(self._one_failing_ledger)),
        ]
        result = run_ledgers(ledgers, known_expected_failures=set())
        # toy-clean: 1 VERIFIED, 1 UNTESTABLE. toy-failing: 1 FAILED, 1 VERIFIED.
        self.assertEqual(result.total_verified, 2)
        self.assertEqual(result.total_failed, 1)
        self.assertEqual(result.total_untestable, 1)
        self.assertEqual(result.total, 4)
        self.assertEqual(len(result.ledger_results), 2)

    def test_failure_not_in_known_list_is_unexpected_and_not_ok(self):
        ledgers = [("toy_failing.py", _toy_module(self._one_failing_ledger))]
        result = run_ledgers(ledgers, known_expected_failures=set())
        self.assertEqual(len(result.unexpected_failures), 1)
        self.assertEqual(result.unexpected_failures[0][0], "toy_failing.py")
        self.assertEqual(result.unexpected_failures[0][1], "Known Gap")
        self.assertFalse(result.ok)

    def test_failure_in_known_list_is_not_unexpected_and_is_ok(self):
        ledgers = [("toy_failing.py", _toy_module(self._one_failing_ledger))]
        known = {("toy_failing.py", "Known Gap")}
        result = run_ledgers(ledgers, known_expected_failures=known)
        self.assertEqual(result.unexpected_failures, [])
        self.assertTrue(result.ok)

    def test_known_failure_that_does_not_actually_fail_is_flagged_as_resolved(self):
        # "Known Gap" is registered in known_expected_failures, but this
        # ledger's version of it PASSES -- simulating the gap having
        # been genuinely fixed.
        def _fixed_ledger():
            ledger = CorrespondenceLedger("toy-fixed")
            ledger.register("Known Gap", "t", "c", validator=lambda: ValidationResult(True))
            return ledger
        ledgers = [("toy_fixed.py", _toy_module(_fixed_ledger))]
        known = {("toy_fixed.py", "Known Gap")}
        result = run_ledgers(ledgers, known_expected_failures=known)
        self.assertEqual(result.unexpected_failures, [])
        self.assertEqual(result.resolved_known_failures, [("toy_fixed.py", "Known Gap")])
        # A resolved known failure is good news, not a regression --
        # must NOT flip ok to False.
        self.assertTrue(result.ok)

    def test_empty_ledger_list_yields_zero_totals_and_ok(self):
        result = run_ledgers([], known_expected_failures=set())
        self.assertEqual(result.total, 0)
        self.assertTrue(result.ok)


class TestRealLedgerIntegration(unittest.TestCase):
    """Integration test against the 5 REAL ledgers in this repo. This is
    a regression snapshot on the aggregation glue code (does it still
    correctly count and classify what the real ledgers currently
    report), not a re-derivation of any individual engine's own
    correctness -- see each ledger's own worked-example tests for that."""

    def test_real_ledgers_match_current_known_baseline(self):
        result = run_ledgers(LEDGERS, KNOWN_EXPECTED_FAILURES)
        self.assertEqual(len(result.ledger_results), 5)
        self.assertEqual(result.total, 22)
        self.assertEqual(result.total_verified, 15)
        self.assertEqual(result.total_failed, 0)
        self.assertEqual(result.total_untestable, 7)
        self.assertEqual(result.unexpected_failures, [])
        self.assertEqual(result.resolved_known_failures, [])
        self.assertTrue(result.ok)

    def test_ddpg_actor_critic_gap_is_the_one_known_failure(self):
        """CORRECTION (dated, see LIBER_0.md): this test's name is now a
        misnomer kept for history -- the DDPG actor-critic gap it used to
        assert as FAILED is fixed. Now asserts the opposite: that specific
        correspondence is VERIFIED, and the ledger has zero FAILED entries."""
        result = run_ledgers(LEDGERS, KNOWN_EXPECTED_FAILURES)
        ddpg_result = next(lr for lr in result.ledger_results
                            if lr.filename == "ddpg_correspondence_ledger.py")
        self.assertEqual(ddpg_result.failed, 0)
        self.assertEqual(ddpg_result.verified, 2)


class TestMainFreshnessWiring(unittest.TestCase):
    """Integration test for main()'s freshness-tracking wiring, using a
    temp history_path so it never touches the real repo's
    correspondence_ledger_run_history.json. Ground truth: the real 5
    ledgers' actual current results (same baseline as
    TestRealLedgerIntegration above), checked against what main() writes
    to the history file rather than re-derived independently."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.history_path = Path(self._tmpdir.name) / "history.json"

    def test_first_call_writes_history_with_no_previous_records(self):
        exit_code = run_all_main(history_path=self.history_path)
        self.assertEqual(exit_code, 0)  # 1 known FAILED, 0 unexpected -> ok
        self.assertTrue(self.history_path.exists())
        history = json.loads(self.history_path.read_text())
        self.assertEqual(len(history), 5)
        for fname, record in history.items():
            self.assertIn("last_run_utc", record)
            self.assertIn("verified", record)

    def test_second_call_updates_existing_history_not_overwrite_wholesale(self):
        run_all_main(history_path=self.history_path)
        first_snapshot = json.loads(self.history_path.read_text())

        exit_code = run_all_main(history_path=self.history_path)
        second_snapshot = json.loads(self.history_path.read_text())

        self.assertEqual(exit_code, 0)
        self.assertEqual(set(first_snapshot.keys()), set(second_snapshot.keys()))
        # Timestamps should have moved forward (or stayed equal on a very
        # fast machine), never backward or missing.
        for fname in first_snapshot:
            self.assertGreaterEqual(
                second_snapshot[fname]["last_run_utc"],
                first_snapshot[fname]["last_run_utc"],
            )


class TestMainTargetStalenessWiring(unittest.TestCase):
    """Integration test confirming main() actually calls into
    correspondence_ledger_target_staleness and prints its section -- the
    unit-level correctness of that module's own comparison logic is
    covered by test_correspondence_ledger_target_staleness.py; this only
    confirms the wiring itself fires, against the real repo's own git
    history (using a temp history_path so it never touches the real
    correspondence_ledger_run_history.json)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.history_path = Path(self._tmpdir.name) / "history.json"

    def test_target_change_section_appears_in_output(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = run_all_main(history_path=self.history_path)
        output = buf.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("TARGET-CHANGE CHECK", output)

    def test_first_call_reports_no_baseline_for_every_ledger(self):
        # First call ever against this temp history file -- there's no
        # prior recorded check yet, so every ledger should say so rather
        # than crash trying to compare against a timestamp that isn't there.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_all_main(history_path=self.history_path)
        output = buf.getvalue()
        self.assertIn("no prior recorded check to compare against", output)


def run_unit_test_suite():
    print("=" * 72)
    print("  MASTER CORRESPONDENCE LEDGER RUNNER -- CORRECTNESS TEST SUITE")
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
