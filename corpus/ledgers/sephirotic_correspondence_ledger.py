#!/usr/bin/env python3
"""
sephirotic_correspondence_ledger.py
Worked example / proof of concept for correspondence_ledger.py, applied to
sephirotic_reward_engine.py.

Nothing here re-implements a check. Every validator re-runs an existing,
already break-it-proofed unittest test method from
test_sephirotic_reward_engine.py -- this file's only job is to extract the
correspondence claims already stated in that engine's docstrings and that
test file's own "STRUCTURAL CLAIMS" comments into first-class, runnable
ledger entries, including the one claim that was ALWAYS explicitly marked
untested (Binah/Malkuth/Keter's exclusion), so it shows up as its own row
instead of a docstring aside easy to miss.

Usage:
    python sephirotic_correspondence_ledger.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from correspondence_ledger import CorrespondenceLedger, from_unittest_methods
from test_sephirotic_reward_engine import (
    TestChesedExpansionIndependence,
    TestGeburahRestrictionIndependence,
    TestTiferethReconciliation,
    TestFullRewardIntegration,
)


def build_ledger() -> CorrespondenceLedger:
    ledger = CorrespondenceLedger("Sephirotic Reward Engine")

    ledger.register(
        pattern="Chesed",
        target="SephiroticRewardComponents.chesed_expansion_term()",
        claim="Increases monotonically with speed and altitude gain; "
              "structurally cannot see instability/crash/violation at all "
              "(no such parameters exist in its signature).",
        validator=from_unittest_methods(TestChesedExpansionIndependence, [
            "test_higher_speed_increases_chesed",
            "test_higher_altitude_gain_increases_chesed",
            "test_negative_altitude_gain_does_not_increase_chesed",
            "test_chesed_is_independent_of_angular_velocity",
        ]),
    )

    ledger.register(
        pattern="Geburah",
        target="SephiroticRewardComponents.geburah_restriction_term()",
        claim="Increases with instability, crashes, and constraint "
              "violations; structurally cannot see velocity/altitude_gain "
              "at all (checked via inspect.signature, not just docstring).",
        validator=from_unittest_methods(TestGeburahRestrictionIndependence, [
            "test_higher_angular_velocity_increases_geburah",
            "test_crash_adds_large_fixed_penalty",
            "test_negative_constraint_violation_does_not_reduce_geburah",
            "test_geburah_signature_has_no_expansion_parameters",
        ]),
    )

    ledger.register(
        pattern="Tifereth",
        target="SephiroticRewardComponents.tifereth_reconciliation()",
        claim="Genuine reconciliation: moves when EITHER input changes, "
              "lets severe Geburah override large Chesed (a crash-level "
              "restriction beats even energetic flight), and weights are "
              "load-bearing, not decorative.",
        validator=from_unittest_methods(TestTiferethReconciliation, [
            "test_high_chesed_low_geburah_gives_positive_reward",
            "test_low_chesed_high_geburah_gives_negative_reward",
            "test_severe_geburah_dominates_large_chesed",
            "test_reconciliation_is_sensitive_to_both_terms_independently",
            "test_weights_control_relative_influence",
        ]),
    )

    ledger.register(
        pattern="Chesed + Geburah -> Tifereth (integration)",
        target="SephiroticRewardComponents.compute_reward()",
        claim="The three pieces actually wire together end-to-end: a "
              "stable ascent nets positive reward, a crash nets negative "
              "reward regardless of prior speed, and the breakdown is "
              "genuinely auditable (chesed - geburah == tifereth exactly).",
        validator=from_unittest_methods(TestFullRewardIntegration, [
            "test_stable_ascent_gives_positive_reward",
            "test_crash_gives_negative_reward_regardless_of_prior_speed",
            "test_returned_dict_exposes_both_subterms_not_just_final_scalar",
        ]),
    )

    # The boundary-clarification row -- registered with NO validator on
    # purpose. This is the fourth step of the pattern (distinguishing
    # tested vs untested correspondences) made into a first-class ledger
    # entry instead of a docstring note someone could miss.
    ledger.register(
        pattern="Binah / Malkuth / Keter",
        target="(deliberately absent from SephiroticRewardComponents)",
        claim="Excluded from the reward function by design: Binah (the "
              "action-space clip) and Malkuth (the executed physical "
              "action) belong to the policy/environment, not the reward "
              "function; Keter was dropped during the mapping analysis as "
              "too weak a structural match to force into a reward term. "
              "Reasoned by structural resemblance, not falsified by any "
              "test here -- there is no code to check this claim against.",
        validator=None,
    )

    return ledger


if __name__ == "__main__":
    ledger = build_ledger()
    ledger.run()
    print(ledger.report())
    sys.exit(0 if ledger.all_testable_passed() else 1)
