#!/usr/bin/env python3
"""
test_debugger.py
Independent correctness test for debugger.py: the `logged` decorator,
its two sanity-check functions (_check_unique_letters,
_check_value_ranges), and its own built-in run_self_tests() suite
(re-run as ground truth, matching this project's from_script_exit_code()
convention for script-style tools -- debugger.py's own self-test already
covers the lookup/delta_operator/feedback_ingester integration it wires
together, so this file adds independent coverage of the NEW logic --
the logging wrapper and the two validators -- rather than duplicating
what debugger.py already checks of itself).

IMPORTANT SIDE-EFFECT NOTE: merely `import debugger` truncates and
rewrites tools/trace-log.txt (its logging.basicConfig() runs at import
time with mode="w"). The real trace-log.txt already contains real
content from prior sessions. This test file does NOT attempt to prevent
that truncation (it happens before any test code can run) -- the
surrounding test invocation backs up trace-log.txt before running this
file and restores it afterward (plain file copy, done outside this
file, not by any code here).

A NOTE ON A FALSE ALARM (not a bug in debugger.py, documented for
honesty): the first run of this suite saw every test that calls
run_self_tests() fail with a PermissionError from `tmp_log.unlink()`
inside debugger.py's own cleanup step -- but this turned out to be a
transient restriction of the test session's own sandboxed filesystem
mount (confirmed directly: even a file freshly created in the same
process, in the same directory, in the same run, could not be unlinked
or rm'd, though same-directory renames worked fine), not anything wrong
with debugger.py's code. Once that sandbox-level restriction was lifted
for this folder, every test here passed without any change to
debugger.py itself. Recorded here so a future reader who sees this
exact failure mode again knows to check the environment first, not
assume the code regressed.
"""

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import debugger as dbg  # noqa: E402

BASE_DIR = Path(__file__).parent


class TestCheckUniqueLetters(unittest.TestCase):
    def test_real_json_has_no_duplicate_letters(self):
        # Should not raise against the real hermetic_qabalah.json.
        dbg._check_unique_letters()


class TestCheckValueRanges(unittest.TestCase):
    def test_real_json_values_are_in_range(self):
        # cipher_value in [1, 400], path_key_scale in [11, 32] -- should
        # not raise against the real hermetic_qabalah.json (note: the
        # Kaf gematria discrepancy documented in test_lookup.py, 21
        # instead of the standard 20, is still well within [1, 400], so
        # it doesn't trip this particular range check).
        dbg._check_value_ranges()


class TestLoggedDecorator(unittest.TestCase):
    def test_wrapped_function_returns_the_real_result(self):
        def add(a, b):
            return a + b
        wrapped = dbg.logged(add)
        self.assertEqual(wrapped(2, 3), 5)

    def test_preserves_name_and_docstring(self):
        def my_func(x):
            """My docstring."""
            return x
        wrapped = dbg.logged(my_func)
        self.assertEqual(wrapped.__name__, "my_func")
        self.assertEqual(wrapped.__doc__, "My docstring.")

    def test_reraises_exceptions_after_logging(self):
        def boom():
            raise ValueError("intentional test failure")
        wrapped = dbg.logged(boom)
        with self.assertRaises(ValueError):
            wrapped()

    def test_wraps_keyword_arguments_too(self):
        def greet(name, greeting="hello"):
            return f"{greeting}, {name}"
        wrapped = dbg.logged(greet)
        self.assertEqual(wrapped("world", greeting="hi"), "hi, world")


class TestRunSelfTestsDirectly(unittest.TestCase):
    def test_run_self_tests_passes_against_the_real_files(self):
        # Re-runs debugger.py's OWN built-in integration check (lookup +
        # delta_operator + feedback_ingester wiring) as ground truth --
        # this is what the module itself claims to guarantee.
        self.assertTrue(dbg.run_self_tests())

    def test_run_self_tests_cleans_up_its_own_temp_file(self):
        dbg.run_self_tests()
        leftover = BASE_DIR / "temp_feedback_log.jsonl"
        self.assertFalse(leftover.exists(), "run_self_tests() should self-clean its temp feedback log")


class TestCLISelfTestMode(unittest.TestCase):
    """Re-runs the real 'python debugger.py test' CLI path as a
    subprocess and checks its real exit code -- from_script_exit_code()
    style, since debugger.py is a script-level tool, not a unittest
    TestCase."""

    def test_cli_test_mode_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "debugger.py"), "test"],
            capture_output=True, text=True, cwd=str(BASE_DIR), timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def run_unit_test_suite():
    print("=" * 72)
    print("  DEBUGGER.PY -- CORRECTNESS TEST SUITE")
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
