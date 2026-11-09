#!/usr/bin/env python3
"""
test_recursive_attractor_engine.py
Correctness verification for recursive_attractor_engine.py per
TESTING_STANDARD.md.

Ground truth used -- all independently derivable, not reverse-engineered
from the engine's own output:
  - Linear contraction map S' = a*S + E has a CLOSED-FORM fixed point
    S* = E / (1 - a), solvable directly from S* = a*S* + E without ever
    running the engine (basic geometric-series algebra).
  - The logistic map x' = r*x*(1-x) has well-documented, textbook
    bifurcation regimes: a stable nonzero fixed point at x* = (r-1)/r for
    1 < r < 3; a period-2 cycle for 3 < r < 1+sqrt(6) (~3.449); and
    chaotic (non-periodic, bounded) behavior for r > ~3.57 (the Feigenbaum
    accumulation point), confirmed at r=3.9 specifically, which has no
    known periodic window. These are standard, citable results, not
    something derived from this engine.
  - S' = 2*S is provably unbounded for any nonzero S0 (exponential growth),
    used as ground truth for the AbyssException/divergence guard.
  - Tiphareth integration's weighted-average formula is checked against an
    independently hand-computed weighted sum, not by calling the function
    twice.

VERIFIED per TESTING_STANDARD.md. Break-it checks documented inline via
the four break-it proofs run during development (see the commit message
this file ships with for the exact injected bugs and their results).
"""

import sys
import math
import unittest
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from recursive_attractor_engine import (
    iterate, classify_trajectory, tiphareth_integrate,
    AbyssException, AttractorType,
)


class TestLinearContractionFixedPoint(unittest.TestCase):
    """S' = a*S + E. Closed form: S* = E / (1 - a). Independently solvable
    by hand -- this is not reverse-engineered from the code."""

    def test_matches_closed_form_fixed_point(self):
        a, E = 0.5, 1.0
        expected_fixed_point = E / (1.0 - a)  # = 2.0, by hand
        F = lambda S, e: a * S + e
        hist = iterate(F, S0=np.array([0.0]), E=np.array([E]), n_steps=60)
        result = classify_trajectory(hist)
        self.assertEqual(result.kind, AttractorType.FIXED_POINT)
        self.assertAlmostEqual(float(result.fixed_point[0]), expected_fixed_point, places=4)

    def test_different_contraction_rate_matches_its_own_closed_form(self):
        a, E = 0.2, 5.0
        expected_fixed_point = E / (1.0 - a)  # = 6.25, by hand
        F = lambda S, e: a * S + e
        hist = iterate(F, S0=np.array([-10.0]), E=np.array([E]), n_steps=80)
        result = classify_trajectory(hist)
        self.assertEqual(result.kind, AttractorType.FIXED_POINT)
        self.assertAlmostEqual(float(result.fixed_point[0]), expected_fixed_point, places=4)

    def test_starting_already_at_the_fixed_point_stays_there(self):
        a, E = 0.5, 1.0
        fp = E / (1.0 - a)
        F = lambda S, e: a * S + e
        hist = iterate(F, S0=np.array([fp]), E=np.array([E]), n_steps=10)
        result = classify_trajectory(hist)
        self.assertEqual(result.kind, AttractorType.FIXED_POINT)

    def test_multidimensional_state_vector_converges_componentwise(self):
        a = 0.5
        E = np.array([1.0, -2.0, 0.5])
        expected = E / (1.0 - a)
        F = lambda S, e: a * S + e
        hist = iterate(F, S0=np.zeros(3), E=E, n_steps=60)
        result = classify_trajectory(hist)
        self.assertEqual(result.kind, AttractorType.FIXED_POINT)
        np.testing.assert_allclose(result.fixed_point, expected, atol=1e-3)


class TestLogisticMapBifurcation(unittest.TestCase):
    """Textbook logistic-map regimes, cited independently of this engine."""

    def test_r_2_5_converges_to_documented_fixed_point(self):
        # 1 < r < 3 regime: stable fixed point at x* = (r-1)/r
        r = 2.5
        expected_fp = (r - 1.0) / r  # = 0.6, by hand
        F = lambda S, E, r=r: r * S * (1.0 - S)
        hist = iterate(F, S0=np.array([0.3]), E=np.array([0.0]), n_steps=150)
        result = classify_trajectory(hist)
        self.assertEqual(result.kind, AttractorType.FIXED_POINT)
        self.assertAlmostEqual(float(result.fixed_point[0]), expected_fp, places=3)

    def test_r_3_2_settles_into_documented_period_2_cycle(self):
        # 3 < r < 1+sqrt(6) (~3.449) regime: period-2 cycle.
        r = 3.2
        F = lambda S, E, r=r: r * S * (1.0 - S)
        hist = iterate(F, S0=np.array([0.4]), E=np.array([0.0]), n_steps=200)
        result = classify_trajectory(hist)
        self.assertEqual(result.kind, AttractorType.LIMIT_CYCLE)
        self.assertEqual(result.period, 2)

    def test_r_3_9_is_bounded_aperiodic_not_fixed_or_short_cycle(self):
        # Above the Feigenbaum point (~3.57), r=3.9 is a documented chaotic
        # regime with no known periodic window.
        r = 3.9
        F = lambda S, E, r=r: r * S * (1.0 - S)
        hist = iterate(F, S0=np.array([0.4]), E=np.array([0.0]), n_steps=300)
        result = classify_trajectory(hist)
        self.assertEqual(result.kind, AttractorType.BOUNDED_APERIODIC)
        # Sanity: still bounded in the map's natural range.
        for S in hist:
            self.assertGreaterEqual(float(S[0]), -1e-6)
            self.assertLessEqual(float(S[0]), 1.0 + 1e-6)

    def test_different_initial_conditions_at_r_3_2_still_find_the_same_cycle(self):
        # Robustness check: the period-2 classification shouldn't be an
        # artifact of one specific starting point.
        r = 3.2
        F = lambda S, E, r=r: r * S * (1.0 - S)
        for s0 in [0.1, 0.4, 0.7, 0.9]:
            hist = iterate(F, S0=np.array([s0]), E=np.array([0.0]), n_steps=200)
            result = classify_trajectory(hist)
            self.assertEqual(result.kind, AttractorType.LIMIT_CYCLE, msg=f"failed for s0={s0}")
            self.assertEqual(result.period, 2, msg=f"failed for s0={s0}")


class TestAbyssExceptionDaathGuard(unittest.TestCase):
    """S' = 2*S is provably unbounded -- exact ground truth: |S_n| = |S0|*2^n,
    which exceeds any finite magnitude_cap in a computable, exact number of
    steps (no approximation needed)."""

    def test_exponential_growth_map_raises_abyss_exception(self):
        F = lambda S, E: 2.0 * S
        with self.assertRaises(AbyssException):
            iterate(F, S0=np.array([1.0]), E=np.array([0.0]), n_steps=100)

    def test_raises_at_or_before_the_analytically_predicted_step(self):
        # |S_n| = 2^n exceeds magnitude_cap=1000 once 2^n > 1000, i.e.
        # n > log2(1000) ~= 9.97, so by step 10 at the latest.
        F = lambda S, E: 2.0 * S
        try:
            iterate(F, S0=np.array([1.0]), E=np.array([0.0]), n_steps=100, magnitude_cap=1000.0)
            self.fail("Expected AbyssException before step 10")
        except AbyssException as e:
            step_num = int(str(e).split("step ")[1].split(".")[0].split(" ")[0].rstrip(":"))
            self.assertLessEqual(step_num, 10)

    def test_nan_producing_operator_raises_immediately(self):
        F = lambda S, E: S * float('nan')
        with self.assertRaises(AbyssException):
            iterate(F, S0=np.array([1.0]), E=np.array([0.0]), n_steps=5)

    def test_inf_producing_operator_raises(self):
        F = lambda S, E: S * 1e300 * 1e300  # overflows to inf
        with self.assertRaises(AbyssException):
            iterate(F, S0=np.array([1.0]), E=np.array([0.0]), n_steps=5)

    def test_bounded_map_never_raises(self):
        # Sanity: the guard shouldn't false-positive on a map that's
        # genuinely bounded (the r=3.9 logistic map, known to stay in [0,1]).
        F = lambda S, E: 3.9 * S * (1.0 - S)
        try:
            iterate(F, S0=np.array([0.4]), E=np.array([0.0]), n_steps=500)
        except AbyssException:
            self.fail("AbyssException raised on a genuinely bounded trajectory")


class TestTiphareth(unittest.TestCase):
    def test_uniform_weights_matches_hand_computed_mean(self):
        stack = [np.array([1.0, 0.0]), np.array([0.0, 1.0]), np.array([2.0, 2.0])]
        expected = np.array([(1 + 0 + 2) / 3.0, (0 + 1 + 2) / 3.0])  # by hand: [1.0, 1.0]
        result = tiphareth_integrate(stack)
        np.testing.assert_allclose(result, expected)

    def test_custom_weights_match_hand_computed_weighted_average(self):
        stack = [np.array([10.0]), np.array([0.0])]
        weights = [3.0, 1.0]
        # By hand: (3*10 + 1*0) / (3+1) = 30/4 = 7.5
        expected = np.array([7.5])
        result = tiphareth_integrate(stack, weights=weights)
        np.testing.assert_allclose(result, expected)

    def test_sensitive_to_every_contributor_independently(self):
        # Changing ANY single element of the stack must change the result --
        # a broken integration that secretly ignores one branch would pass
        # naive tests but fail this one (same pattern as
        # test_sephirotic_reward_engine.py's reconciliation-sensitivity test).
        base_stack = [np.array([1.0]), np.array([2.0]), np.array([3.0])]
        base_result = tiphareth_integrate(base_stack)
        for i in range(3):
            perturbed = list(base_stack)
            perturbed[i] = perturbed[i] + 100.0
            perturbed_result = tiphareth_integrate(perturbed)
            self.assertFalse(np.allclose(perturbed_result, base_result),
                msg=f"Perturbing stack[{i}] did not change the integrated result")

    def test_empty_stack_raises_rather_than_silently_defaulting(self):
        with self.assertRaises(ValueError):
            tiphareth_integrate([])

    def test_mismatched_shapes_raise(self):
        with self.assertRaises(ValueError):
            tiphareth_integrate([np.array([1.0, 2.0]), np.array([1.0])])

    def test_mismatched_weights_length_raises(self):
        with self.assertRaises(ValueError):
            tiphareth_integrate([np.array([1.0]), np.array([2.0])], weights=[1.0])

    def test_single_element_stack_returns_that_element(self):
        stack = [np.array([42.0])]
        result = tiphareth_integrate(stack)
        np.testing.assert_allclose(result, np.array([42.0]))


class TestClassifyTrajectoryEdgeCases(unittest.TestCase):
    def test_insufficient_history_reported_honestly(self):
        result = classify_trajectory([np.array([1.0])])
        self.assertEqual(result.kind, AttractorType.INSUFFICIENT_HISTORY)

    def test_empty_history_reported_honestly(self):
        result = classify_trajectory([])
        self.assertEqual(result.kind, AttractorType.INSUFFICIENT_HISTORY)

    def test_period_1_is_reported_as_fixed_point_not_limit_cycle(self):
        # A period-1 cycle IS a fixed point; confirm it's not double-reported
        # or misclassified as LIMIT_CYCLE(period=1).
        history = [np.array([5.0]), np.array([5.0]), np.array([5.0])]
        result = classify_trajectory(history)
        self.assertEqual(result.kind, AttractorType.FIXED_POINT)


def run_unit_test_suite():
    print("=" * 72)
    print("  RECURSIVE ATTRACTOR ENGINE -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
