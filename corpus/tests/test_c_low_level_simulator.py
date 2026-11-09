#!/usr/bin/env python3
"""
test_c_low_level_simulator.py
Runnable unit test suite for c_low_level_simulator.py.
Contains the user-provided test cases (verbatim logic) plus two additional
boundary cases flagged as still-missing during review.
"""

import sys
import unittest
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import c_low_level_simulator


class TestCLowLevelSuite(unittest.TestCase):

    def test_islower_edge_cases(self):
        # Normal lower cases
        self.assertEqual(c_low_level_simulator._islower('a'), 1)
        self.assertEqual(c_low_level_simulator._islower('z'), 1)
        self.assertEqual(c_low_level_simulator._islower(ord('b')), 1)
        # Edge cases: Upper, digits, whitespace, empty string, multichar, None
        self.assertEqual(c_low_level_simulator._islower('A'), 0)
        self.assertEqual(c_low_level_simulator._islower('Z'), 0)
        self.assertEqual(c_low_level_simulator._islower('9'), 0)
        self.assertEqual(c_low_level_simulator._islower(' '), 0)
        self.assertEqual(c_low_level_simulator._islower(''), 0)
        self.assertEqual(c_low_level_simulator._islower('ab'), 0)
        self.assertEqual(c_low_level_simulator._islower(None), 0)

    def test_isalpha_edge_cases(self):
        # Normal alpha cases
        self.assertEqual(c_low_level_simulator._isalpha('a'), 1)
        self.assertEqual(c_low_level_simulator._isalpha('Z'), 1)
        # Edge cases: Digits, whitespace, empty string, multichar, None
        self.assertEqual(c_low_level_simulator._isalpha('0'), 0)
        self.assertEqual(c_low_level_simulator._isalpha(' '), 0)
        self.assertEqual(c_low_level_simulator._isalpha(''), 0)
        self.assertEqual(c_low_level_simulator._isalpha('az'), 0)
        self.assertEqual(c_low_level_simulator._isalpha(None), 0)

    def test_abs_edge_cases_and_int32_overflow(self):
        # Normal cases
        self.assertEqual(c_low_level_simulator._abs(-98), 98)
        self.assertEqual(c_low_level_simulator._abs(98), 98)
        self.assertEqual(c_low_level_simulator._abs(0), 0)
        # C Stdlib abs(INT_MIN) gotcha: -(-2147483648) overflows 32-bit signed int
        with self.assertRaises(OverflowError):
            c_low_level_simulator._abs(-2147483648)

    def test_add_edge_cases_and_int32_overflow(self):
        # Normal cases
        self.assertEqual(c_low_level_simulator.add(38, 60), 98)
        self.assertEqual(c_low_level_simulator.add(-10, 5), -5)
        # 32-bit signed integer addition overflow boundaries
        with self.assertRaises(OverflowError):
            c_low_level_simulator.add(2147483647, 1)
        with self.assertRaises(OverflowError):
            c_low_level_simulator.add(-2147483648, -1)

    # --- Additional cases not in the original submission ---

    def test_abs_at_exact_int32_max_boundary(self):
        # INT32_MAX itself must be valid input and output (boundary, not overflow)
        self.assertEqual(c_low_level_simulator._abs(2147483647), 2147483647)

    def test_add_at_exact_boundaries_should_not_raise(self):
        # Results landing exactly ON the boundary are valid, not overflow.
        # Only exceeding the boundary should raise.
        self.assertEqual(
            c_low_level_simulator.add(2147483646, 1), 2147483647
        )
        self.assertEqual(
            c_low_level_simulator.add(-2147483647, -1), -2147483648
        )

    def test_islower_rejects_non_ascii_and_type_confusion(self):
        # Non-ASCII letter (e.g. 'é') should not be classified as lowercase
        # under this C-style ASCII-only definition.
        self.assertEqual(c_low_level_simulator._islower('é'), 0)
        # Bool is a subclass of int in Python; must not be silently accepted
        # as a valid ordinal input in a way that produces a misleading result.
        self.assertEqual(c_low_level_simulator._islower(True), 0)


def run_unit_test_suite():
    print("=" * 72)
    print("  C LOW-LEVEL SIMULATOR — UNIT TEST SUITE")
    print("  Executing Boundary & Overflow Assertions")
    print("=" * 72 + "\n")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 72)
    print("  UNIT TEST SUITE SUMMARY")
    print("=" * 72)
    print(f"  Total Tests Executed : {result.testsRun}")
    print(f"  Total Failures       : {len(result.failures)}")
    print(f"  Total Errors         : {len(result.errors)}")
    status = "ALL PASSED (correctness verified per-assertion above)" if result.wasSuccessful() else "FAILED — see output above"
    print(f"  Result               : {status}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_unit_test_suite()
    sys.exit(0 if success else 1)
