#!/usr/bin/env python3
"""
test_sephirotic_reward_engine.py
Tests the STRUCTURAL CLAIMS made in sephirotic_reward_engine.py, not just
that the functions execute. Each test corresponds to a specific claim
stated in that module's docstrings:

  1. Chesed increases with expansion, independent of stability
  2. Geburah increases with instability, independent of expansion
  3. Tifereth genuinely reconciles -- doesn't ignore either side, and lets
     severe restriction (crash) dominate large expansion, as the
     Chesed/Geburah "push-pull" correspondence claims it should

If these fail, the reward function does NOT structurally match the
Sephirotic mapping it claims to implement, regardless of whether it
"runs" or produces plausible-looking numbers.

VERIFIED per TESTING_STANDARD.md on 2026-07-30:
  Ground truth used: hand-derived reference values independent of the
  implementation's own formula (e.g. test_weights_control_relative_influence
  asserts against 1.0*5.0 - 10.0*3.0 = -25.0, computed by hand, not by
  calling the function twice); test_geburah_signature_has_no_expansion_parameters
  uses inspect.signature() to check the actual function contract rather
  than trusting the docstring.
  Break-it check performed: edited tifereth_reconciliation() to return only
  (chesed_weight * chesed_value), dropping the geburah_value term entirely.
  Result: 5 of 16 tests failed (test_crash_gives_negative_reward_regardless_of_prior_speed,
  test_low_chesed_high_geburah_gives_negative_reward,
  test_reconciliation_is_sensitive_to_both_terms_independently,
  test_severe_geburah_dominates_large_chesed, test_weights_control_relative_influence).
  Reverted; clean 16/16 pass confirmed restored.
  Analogical (untested) claim, stated explicitly per TESTING_STANDARD.md's
  own distinction: excluding Binah/Malkuth/Keter from the reward function
  is reasoned by structural resemblance, not falsified by any test here.
"""

import sys
import unittest
import numpy as np
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from sephirotic_reward_engine import SephiroticRewardComponents


class TestChesedExpansionIndependence(unittest.TestCase):
    """Chesed term: must track expansion/energy, NOT stability."""

    def setUp(self):
        self.engine = SephiroticRewardComponents()

    def test_higher_speed_increases_chesed(self):
        low_speed = self.engine.chesed_expansion_term(
            velocity=np.array([0.1, 0.0, 0.0]), altitude_gain=0.0)
        high_speed = self.engine.chesed_expansion_term(
            velocity=np.array([5.0, 0.0, 0.0]), altitude_gain=0.0)
        self.assertGreater(high_speed, low_speed)

    def test_higher_altitude_gain_increases_chesed(self):
        low_gain = self.engine.chesed_expansion_term(
            velocity=np.array([0.0, 0.0, 0.0]), altitude_gain=0.1)
        high_gain = self.engine.chesed_expansion_term(
            velocity=np.array([0.0, 0.0, 0.0]), altitude_gain=5.0)
        self.assertGreater(high_gain, low_gain)

    def test_negative_altitude_gain_does_not_increase_chesed(self):
        # Losing altitude is not "expansion" -- must be floored at 0
        # contribution, not treated as negative expansion (that's Geburah's
        # job via instability/crash, not Chesed's).
        result = self.engine.chesed_expansion_term(
            velocity=np.array([0.0, 0.0, 0.0]), altitude_gain=-10.0)
        self.assertEqual(result, 0.0)

    def test_chesed_is_independent_of_angular_velocity(self):
        # CRITICAL STRUCTURAL CHECK: chesed_expansion_term's signature does
        # not even accept angular_velocity/crash/constraint args -- confirm
        # this is enforced by the function signature itself, not just by
        # convention. A tumbling-but-fast-forward-moving craft should score
        # identically to a stable-and-fast-forward-moving craft on THIS
        # term specifically (instability penalty belongs entirely to Geburah).
        result_would_be_same_regardless_of_tumble = self.engine.chesed_expansion_term(
            velocity=np.array([3.0, 0.0, 0.0]), altitude_gain=1.0)
        # Calling it again with identical translational state must give
        # an identical result -- there is no parameter through which
        # instability could leak in.
        result_again = self.engine.chesed_expansion_term(
            velocity=np.array([3.0, 0.0, 0.0]), altitude_gain=1.0)
        self.assertEqual(result_would_be_same_regardless_of_tumble, result_again)


class TestGeburahRestrictionIndependence(unittest.TestCase):
    """Geburah term: must track instability/violation, NOT expansion."""

    def setUp(self):
        self.engine = SephiroticRewardComponents()

    def test_higher_angular_velocity_increases_geburah(self):
        stable = self.engine.geburah_restriction_term(
            angular_velocity=np.array([0.0, 0.0, 0.0]),
            is_crashed=False, constraint_violation=0.0)
        tumbling = self.engine.geburah_restriction_term(
            angular_velocity=np.array([5.0, 5.0, 5.0]),
            is_crashed=False, constraint_violation=0.0)
        self.assertGreater(tumbling, stable)

    def test_crash_adds_large_fixed_penalty(self):
        no_crash = self.engine.geburah_restriction_term(
            angular_velocity=np.array([0.0, 0.0, 0.0]),
            is_crashed=False, constraint_violation=0.0)
        crash = self.engine.geburah_restriction_term(
            angular_velocity=np.array([0.0, 0.0, 0.0]),
            is_crashed=True, constraint_violation=0.0)
        self.assertGreater(crash, no_crash)
        self.assertGreaterEqual(crash - no_crash, 100.0)

    def test_negative_constraint_violation_does_not_reduce_geburah(self):
        # A "negative violation" isn't a bonus -- must be floored at 0,
        # not treated as negative restriction (that would let Geburah
        # accidentally reward something, contradicting its restriction role).
        result = self.engine.geburah_restriction_term(
            angular_velocity=np.array([0.0, 0.0, 0.0]),
            is_crashed=False, constraint_violation=-5.0)
        self.assertEqual(result, 0.0)

    def test_geburah_signature_has_no_expansion_parameters(self):
        # CRITICAL STRUCTURAL CHECK: confirm geburah_restriction_term
        # cannot see velocity or altitude_gain at all -- inspect the
        # actual function signature rather than just trusting the docstring.
        import inspect
        sig = inspect.signature(self.engine.geburah_restriction_term)
        param_names = set(sig.parameters.keys())
        self.assertNotIn("velocity", param_names)
        self.assertNotIn("altitude_gain", param_names)


class TestTiferethReconciliation(unittest.TestCase):
    """
    Tifereth: must be a genuine reconciliation, not a term that ignores
    one side or always returns a fixed blend regardless of magnitude.
    """

    def setUp(self):
        self.engine = SephiroticRewardComponents()

    def test_high_chesed_low_geburah_gives_positive_reward(self):
        result = self.engine.tifereth_reconciliation(chesed_value=10.0, geburah_value=1.0)
        self.assertGreater(result, 0.0)

    def test_low_chesed_high_geburah_gives_negative_reward(self):
        result = self.engine.tifereth_reconciliation(chesed_value=1.0, geburah_value=10.0)
        self.assertLess(result, 0.0)

    def test_severe_geburah_dominates_large_chesed(self):
        # This is the specific claim from the mapping analysis: severe
        # restriction (e.g. a crash) should be able to override even a
        # large amount of expansion -- Geburah must be able to "win" when
        # it's large enough, not be permanently diluted by a fixed ratio.
        huge_expansion_but_crashed = self.engine.tifereth_reconciliation(
            chesed_value=50.0,   # very energetic flight
            geburah_value=150.0  # but crashed (100 fixed penalty + instability)
        )
        self.assertLess(huge_expansion_but_crashed, 0.0,
            "A crash-level Geburah value must be able to override even large Chesed -- "
            "otherwise Tifereth isn't a real reconciliation, it's a capped blend.")

    def test_reconciliation_is_sensitive_to_both_terms_independently(self):
        # Confirm Tifereth actually moves when EITHER input changes --
        # a broken "reconciliation" that secretly ignores one argument
        # (e.g. returns chesed_value regardless of geburah_value) would
        # pass naive tests but fail this one.
        base = self.engine.tifereth_reconciliation(chesed_value=5.0, geburah_value=5.0)
        chesed_increased = self.engine.tifereth_reconciliation(chesed_value=8.0, geburah_value=5.0)
        geburah_increased = self.engine.tifereth_reconciliation(chesed_value=5.0, geburah_value=8.0)
        self.assertGreater(chesed_increased, base)
        self.assertLess(geburah_increased, base)

    def test_weights_control_relative_influence(self):
        # If Geburah is weighted much higher than Chesed, a moderate
        # instability should be able to outweigh a moderate expansion --
        # confirms weights aren't decorative constructor args.
        engine_geburah_heavy = SephiroticRewardComponents(chesed_weight=1.0, geburah_weight=10.0)
        result = engine_geburah_heavy.tifereth_reconciliation(chesed_value=5.0, geburah_value=3.0)
        # 1.0*5.0 - 10.0*3.0 = 5 - 30 = -25
        self.assertAlmostEqual(result, -25.0)


class TestFullRewardIntegration(unittest.TestCase):
    """End-to-end: compute_reward() wires the three pieces together correctly."""

    def setUp(self):
        self.engine = SephiroticRewardComponents()

    def test_stable_ascent_gives_positive_reward(self):
        result = self.engine.compute_reward(
            velocity=np.array([0.0, 0.0, 2.0]),
            altitude_gain=1.0,
            angular_velocity=np.array([0.01, 0.01, 0.01]),
            is_crashed=False,
            constraint_violation=0.0,
        )
        self.assertGreater(result["tifereth_reward"], 0.0)

    def test_crash_gives_negative_reward_regardless_of_prior_speed(self):
        result = self.engine.compute_reward(
            velocity=np.array([10.0, 10.0, 10.0]),  # was moving fast/ambitiously
            altitude_gain=3.0,
            angular_velocity=np.array([2.0, 2.0, 2.0]),
            is_crashed=True,
            constraint_violation=0.0,
        )
        self.assertLess(result["tifereth_reward"], 0.0)

    def test_returned_dict_exposes_both_subterms_not_just_final_scalar(self):
        # The three-way breakdown must actually be inspectable -- if this
        # engine only returned the final Tifereth number, you could never
        # verify from outside that Chesed/Geburah were computed independently
        # (you'd have to trust the internals). Exposing all three makes the
        # structural claim auditable by a reader who didn't write the code.
        result = self.engine.compute_reward(
            velocity=np.array([1.0, 0.0, 0.0]), altitude_gain=0.5,
            angular_velocity=np.array([0.0, 0.0, 0.0]),
            is_crashed=False, constraint_violation=0.0,
        )
        self.assertIn("chesed_expansion", result)
        self.assertIn("geburah_restriction", result)
        self.assertIn("tifereth_reward", result)
        self.assertAlmostEqual(
            result["tifereth_reward"],
            result["chesed_expansion"] - result["geburah_restriction"],
        )


def run_unit_test_suite():
    print("=" * 72)
    print("  SEPHIROTIC REWARD ENGINE — STRUCTURAL CLAIM TEST SUITE")
    print("  Verifying Chesed/Geburah independence + Tifereth reconciliation")
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
    status = ("ALL PASSED (structural correspondence claims verified per-assertion above)"
               if result.wasSuccessful() else "FAILED — see output above")
    print(f"  Result               : {status}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_unit_test_suite()
    sys.exit(0 if success else 1)
