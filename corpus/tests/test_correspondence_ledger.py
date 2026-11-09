#!/usr/bin/env python3
"""
test_correspondence_ledger.py
Correctness verification for correspondence_ledger.py per TESTING_STANDARD.md.

This tests the FRAMEWORK itself (registration, run(), the honesty guard,
from_unittest_methods' aggregation), not any specific Sephirotic claim --
see test_sephirotic_reward_engine.py for the underlying engine checks that
sephirotic_correspondence_ledger.py's validators reuse.

Ground truth used: hand-constructed toy unittest.TestCase classes with
known, deliberately-controlled pass/fail outcomes, so the expected ledger
status for each entry is unambiguous by construction (not by re-deriving
anything from a real engine).
"""

import sys
import unittest
import tempfile
import textwrap
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from correspondence_ledger import (
    CorrespondenceLedger, Correspondence, ValidationResult,
    from_unittest_methods, from_script_exit_code,
    STATUS_VERIFIED, STATUS_FAILED, STATUS_UNTESTABLE, STATUS_UNCHECKED,
)


class _AlwaysPasses(unittest.TestCase):
    def test_a(self):
        self.assertEqual(1, 1)

    def test_b(self):
        self.assertTrue(True)


class _OneFailsOnePasses(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(1, 1)

    def test_fail(self):
        self.assertEqual(1, 2)  # deliberately false


class _RaisesNonAssertionError(unittest.TestCase):
    def test_raises(self):
        raise RuntimeError("boom")


class TestCorrespondenceRegistration(unittest.TestCase):
    def test_register_returns_correspondence_with_unchecked_status(self):
        ledger = CorrespondenceLedger("test")
        c = ledger.register("Pattern", "target", "claim text")
        self.assertEqual(c.status, STATUS_UNCHECKED)
        self.assertIn(c, ledger.entries)

    def test_register_accumulates_multiple_entries(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t1", "c1")
        ledger.register("B", "t2", "c2")
        self.assertEqual(len(ledger.entries), 2)


class TestValidatorExecution(unittest.TestCase):
    def test_passing_validator_marks_verified(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t", "c", validator=lambda: ValidationResult(True, "ok"))
        ledger.run()
        self.assertEqual(ledger.entries[0].status, STATUS_VERIFIED)
        self.assertEqual(ledger.entries[0].detail, "ok")

    def test_failing_validator_marks_failed(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t", "c", validator=lambda: ValidationResult(False, "why it broke"))
        ledger.run()
        self.assertEqual(ledger.entries[0].status, STATUS_FAILED)
        self.assertEqual(ledger.entries[0].detail, "why it broke")

    def test_validator_that_raises_marks_failed_not_crashes(self):
        # A broken validator (e.g. a typo referencing a removed function)
        # must not crash the whole ledger run -- it should be caught and
        # reported as FAILED, same principle as the rest of this repo's
        # exit-code discipline: never let an internal error masquerade as
        # either a silent pass or a hard crash of the reporting tool itself.
        def exploding_validator():
            raise ValueError("simulated bug in the validator itself")
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t", "c", validator=exploding_validator)
        ledger.run()  # must not raise
        self.assertEqual(ledger.entries[0].status, STATUS_FAILED)
        self.assertIn("ValueError", ledger.entries[0].detail)

    def test_no_validator_marks_untestable(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t", "c", validator=None)
        ledger.run()
        self.assertEqual(ledger.entries[0].status, STATUS_UNTESTABLE)


class TestHonestyGuard(unittest.TestCase):
    """The core claim of this whole framework: an all-UNTESTABLE ledger
    must never report overall success -- mirrors the all-skipped guard in
    test_reconstructed_frameworks_comparison.py."""

    def test_all_untestable_ledger_does_not_report_success(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t1", "c1", validator=None)
        ledger.register("B", "t2", "c2", validator=None)
        ledger.run()
        self.assertFalse(ledger.all_testable_passed(),
            "A ledger with zero testable entries reported success -- "
            "this is exactly the false-positive this framework exists to prevent.")

    def test_empty_ledger_does_not_report_success(self):
        ledger = CorrespondenceLedger("test")
        ledger.run()
        self.assertFalse(ledger.all_testable_passed())

    def test_mixed_verified_and_untestable_reports_success_if_no_failures(self):
        # UNTESTABLE entries must not drag down an otherwise-clean result --
        # only actual FAILED entries should.
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t1", "c1", validator=lambda: ValidationResult(True))
        ledger.register("B", "t2", "c2", validator=None)
        ledger.run()
        self.assertTrue(ledger.all_testable_passed())

    def test_one_failure_among_verified_fails_the_whole_ledger(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t1", "c1", validator=lambda: ValidationResult(True))
        ledger.register("B", "t2", "c2", validator=lambda: ValidationResult(False, "broke"))
        ledger.run()
        self.assertFalse(ledger.all_testable_passed())


class TestFromUnittestMethods(unittest.TestCase):
    def test_all_passing_methods_yields_passed_true(self):
        validator = from_unittest_methods(_AlwaysPasses, ["test_a", "test_b"])
        result = validator()
        self.assertTrue(result.passed)
        self.assertIn("2/2", result.detail)

    def test_one_failing_method_yields_passed_false_and_names_it(self):
        validator = from_unittest_methods(_OneFailsOnePasses, ["test_pass", "test_fail"])
        result = validator()
        self.assertFalse(result.passed)
        self.assertIn("test_fail", result.detail)
        self.assertNotIn("test_pass", result.detail)  # only the failing one is named

    def test_non_assertion_exception_inside_test_method_still_fails_cleanly(self):
        validator = from_unittest_methods(_RaisesNonAssertionError, ["test_raises"])
        result = validator()
        self.assertFalse(result.passed)
        self.assertIn("test_raises", result.detail)

    def test_wired_into_a_full_ledger_run(self):
        ledger = CorrespondenceLedger("integration")
        ledger.register("A", "t", "c",
            validator=from_unittest_methods(_AlwaysPasses, ["test_a", "test_b"]))
        ledger.register("B", "t", "c",
            validator=from_unittest_methods(_OneFailsOnePasses, ["test_pass", "test_fail"]))
        ledger.run()
        self.assertEqual(ledger.entries[0].status, STATUS_VERIFIED)
        self.assertEqual(ledger.entries[1].status, STATUS_FAILED)
        self.assertFalse(ledger.all_testable_passed())


class TestFromScriptExitCode(unittest.TestCase):
    """Ground truth: two hand-written throwaway .py scripts with a known,
    controlled exit code (0 and 1), written fresh to a temp file for each
    test -- not reusing any real repo script, so the expected outcome is
    unambiguous by construction, same style as the toy TestCase fixtures
    above."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _write_script(self, body: str) -> Path:
        path = Path(self._tmpdir.name) / "toy_script.py"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path

    def test_passing_script_yields_passed_true(self):
        script = self._write_script("""
            print("PASS: everything")
            import sys; sys.exit(0)
        """)
        result = from_script_exit_code(script)()
        self.assertTrue(result.passed)
        self.assertIn("exited 0", result.detail)

    def test_failing_script_yields_passed_false_with_tail_output(self):
        script = self._write_script("""
            print("PASS: first check")
            print("FAIL: second check  something broke")
            import sys; sys.exit(1)
        """)
        result = from_script_exit_code(script)()
        self.assertFalse(result.passed)
        self.assertIn("exited 1", result.detail)
        self.assertIn("something broke", result.detail)

    def test_script_receiving_args(self):
        script = self._write_script("""
            import sys
            sys.exit(0 if sys.argv[1:] == ["expected-arg"] else 1)
        """)
        self.assertTrue(from_script_exit_code(script, args=["expected-arg"])().passed)
        self.assertFalse(from_script_exit_code(script, args=["wrong-arg"])().passed)

    def test_wired_into_a_full_ledger_run(self):
        # _write_script() always writes to the same fixed filename, so
        # build each ledger entry against its own separately-named file.
        pass_path = Path(self._tmpdir.name) / "pass_script.py"
        pass_path.write_text("import sys; sys.exit(0)", encoding="utf-8")
        fail_path = Path(self._tmpdir.name) / "fail_script.py"
        fail_path.write_text("import sys; sys.exit(1)", encoding="utf-8")

        ledger = CorrespondenceLedger("integration")
        ledger.register("A", "t", "c", validator=from_script_exit_code(pass_path))
        ledger.register("B", "t", "c", validator=from_script_exit_code(fail_path))
        ledger.run()
        self.assertEqual(ledger.entries[0].status, STATUS_VERIFIED)
        self.assertEqual(ledger.entries[1].status, STATUS_FAILED)
        self.assertFalse(ledger.all_testable_passed())


class TestReportFormatting(unittest.TestCase):
    def test_report_mentions_every_entry_pattern_name(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("UniquePatternName", "t", "c", validator=lambda: ValidationResult(True))
        ledger.run()
        self.assertIn("UniquePatternName", ledger.report())

    def test_report_includes_summary_counts(self):
        ledger = CorrespondenceLedger("test")
        ledger.register("A", "t", "c", validator=lambda: ValidationResult(True))
        ledger.register("B", "t", "c", validator=None)
        ledger.run()
        report = ledger.report()
        self.assertIn("VERIFIED               : 1 / 2", report)
        self.assertIn("UNTESTABLE (by design)  : 1 / 2", report)


def run_unit_test_suite():
    print("=" * 72)
    print("  CORRESPONDENCE LEDGER FRAMEWORK -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    # NOTE: loadTestsFromModule would also auto-discover _AlwaysPasses,
    # _OneFailsOnePasses, and _RaisesNonAssertionError above -- those are
    # inert fixtures for from_unittest_methods to exercise (two of them
    # deliberately fail/raise), not real tests of this file. Build the
    # suite explicitly from Test*-named classes only so the fixtures'
    # intentional failures don't get counted as this suite's own failures.
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
