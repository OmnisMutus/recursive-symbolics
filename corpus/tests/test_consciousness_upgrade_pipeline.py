"""
test_consciousness_upgrade_pipeline.py

Tests the actual composition (Stage 1 <-> Stage 2 bridge, then real
ChangeLedger objects flowing into Stage 3, then real pipeline behavior
checked via Stage 4) rather than re-testing each stage in isolation --
each stage already has its own independent-ground-truth suite. Expected
outcomes below are hand-derived from the same max(lows)<=min(highs) rule
documented in Stage 2's hand-verification doc, applied to this module's
own external-constraint scenarios.
"""

import unittest

import sys
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from consciousness_upgrade_self_signature import (
    create_signature, ChangeLedger, verify_signature,
)
from consciousness_upgrade_constraint_pruner import Constraint
from consciousness_upgrade_pipeline import (
    propose_change_with_constraint_check, scan_ledger_for_patterns,
)
from consciousness_upgrade_groundedness import Claim, check_claim, GROUNDED


class TestConflictIsActuallyRefused(unittest.TestCase):
    """The core composition claim: a self-signature change that conflicts
    with OTHER sources' numeric constraints must be refused end-to-end --
    not just reported, but actually prevented from reaching the ledger
    or the signature."""

    def setUp(self):
        self.sig0 = create_signature({"hours": "10"}, now="2026-01-01T00:00:00Z")
        self.ledger = ChangeLedger()
        # max(lows)=max(15,10)=15, min(highs)=min(40,20)=20 -> joint range [15,20]
        self.external = [
            Constraint("hours", "team_lead", 15.0, 40.0),
            Constraint("hours", "mentor", 10.0, 20.0),
        ]

    def test_a_value_below_the_joint_range_is_refused(self):
        step = propose_change_with_constraint_check(
            self.sig0, {"hours": "10"}, "test", self.ledger, self.external,
            now="2026-01-01T01:00:00Z",
        )
        self.assertFalse(step.accepted)
        self.assertIsNotNone(step.conflict)
        self.assertEqual(step.conflict.conflicting_lower_bound.source, "team_lead")

    def test_refused_change_does_not_touch_the_ledger(self):
        propose_change_with_constraint_check(
            self.sig0, {"hours": "10"}, "test", self.ledger, self.external,
            now="2026-01-01T01:00:00Z",
        )
        self.assertEqual(len(self.ledger.records), 0)

    def test_refused_change_returns_the_original_unchanged_signature(self):
        step = propose_change_with_constraint_check(
            self.sig0, {"hours": "10"}, "test", self.ledger, self.external,
            now="2026-01-01T01:00:00Z",
        )
        self.assertEqual(step.signature.content_hash, self.sig0.content_hash)
        self.assertTrue(verify_signature(step.signature))

    def test_a_value_inside_the_joint_range_is_accepted_and_ledger_updated(self):
        step = propose_change_with_constraint_check(
            self.sig0, {"hours": "18"}, "test", self.ledger, self.external,
            now="2026-01-01T01:00:00Z",
        )
        self.assertTrue(step.accepted)
        self.assertEqual(len(self.ledger.records), 1)
        self.assertNotEqual(step.signature.content_hash, self.sig0.content_hash)

    def test_value_exactly_at_the_joint_boundary_is_accepted(self):
        # Joint range is [15,20] (closed interval) -- 15 and 20 should both work.
        step_low = propose_change_with_constraint_check(
            self.sig0, {"hours": "15"}, "test", self.ledger, self.external,
            now="2026-01-01T01:00:00Z",
        )
        self.assertTrue(step_low.accepted)
        step_high = propose_change_with_constraint_check(
            step_low.signature, {"hours": "20"}, "test", self.ledger, self.external,
            now="2026-01-01T02:00:00Z",
        )
        self.assertTrue(step_high.accepted)

    def test_non_numeric_value_on_a_constrained_belief_raises(self):
        with self.assertRaises(ValueError):
            propose_change_with_constraint_check(
                self.sig0, {"hours": "a lot"}, "test", self.ledger, self.external,
                now="2026-01-01T01:00:00Z",
            )

    def test_unconstrained_belief_passes_through_untouched(self):
        sig0 = create_signature({"hours": "10", "style": "direct"}, now="2026-01-01T00:00:00Z")
        step = propose_change_with_constraint_check(
            sig0, {"hours": "10", "style": "warm"}, "test", ChangeLedger(),
            external_constraints=[],  # no external constraints at all
            now="2026-01-01T01:00:00Z",
        )
        self.assertTrue(step.accepted)

    def test_all_or_nothing_a_valid_key_does_not_get_applied_if_another_key_conflicts(self):
        sig0 = create_signature({"hours": "10", "style": "direct"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        step = propose_change_with_constraint_check(
            sig0, {"hours": "10", "style": "warm"},  # hours=10 conflicts, style change is fine
            "test", ledger, self.external, now="2026-01-01T01:00:00Z",
        )
        self.assertFalse(step.accepted)
        # style must NOT have been silently applied even though it alone was fine.
        self.assertEqual(step.signature.values["style"], "direct")
        self.assertEqual(len(ledger.records), 0)


class TestPatternScanOnRealComposedLedger(unittest.TestCase):
    """Confirms Stage 3 correctly operates on the REAL ChangeRecord
    objects Stage 1/the bridge produced -- not a hand-built stand-in.
    This is the part that would break if field names, ordering, or types
    drifted between the modules."""

    def test_full_state_reversion_detected_across_two_composed_changes(self):
        sig0 = create_signature({"hours": "18", "style": "direct"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        external = []  # no constraints needed for this scenario
        step1 = propose_change_with_constraint_check(
            sig0, {"hours": "18", "style": "avoidant"}, "r1", ledger, external,
            now="2026-01-01T01:00:00Z",
        )
        step2 = propose_change_with_constraint_check(
            step1.signature, {"hours": "18", "style": "direct"}, "r2", ledger, external,
            now="2026-01-01T02:00:00Z",
        )
        results = scan_ledger_for_patterns(ledger, initial_hash=sig0.content_hash)
        self.assertEqual(len(results["exact_state_reversion"]), 1)
        self.assertEqual(results["exact_state_reversion"][0].record_indices, [1])

    def test_no_reversion_reported_when_only_a_partial_key_changes_back(self):
        # hours changes 18 -> 20 -> 18 (reverts), but style ALSO changes
        # along the way, so the FULL state at record 2 never matches any
        # earlier full state -- must NOT be flagged, since Stage 3 only
        # detects whole-state reversion (documented scope limit).
        sig0 = create_signature({"hours": "18", "style": "direct"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        step1 = propose_change_with_constraint_check(
            sig0, {"hours": "20", "style": "direct"}, "r1", ledger, [],
            now="2026-01-01T01:00:00Z",
        )
        step2 = propose_change_with_constraint_check(
            step1.signature, {"hours": "18", "style": "warm"}, "r2", ledger, [],
            now="2026-01-01T02:00:00Z",
        )
        results = scan_ledger_for_patterns(ledger, initial_hash=sig0.content_hash)
        self.assertEqual(results["exact_state_reversion"], [])


class TestGroundednessOfPipelinesOwnClaims(unittest.TestCase):
    """Uses Stage 4 to check real claims about THIS module's behavior,
    by actually re-running the tests above -- the same discipline applied
    one level up, to the composition rather than to individual stages."""

    def test_the_refusal_claim_is_grounded_by_a_real_passing_test(self):
        claim = Claim(
            "The pipeline refuses a self-signature change that conflicts "
            "with other sources' numeric constraints.",
            "test_consciousness_upgrade_pipeline.TestConflictIsActuallyRefused."
            "test_a_value_below_the_joint_range_is_refused",
        )
        result = check_claim(claim, cwd=str(_REPO_ROOT / "tests"))
        self.assertEqual(result.status, GROUNDED)

    def test_a_fabricated_claim_about_the_pipeline_is_not_grounded(self):
        claim = Claim(
            "The pipeline silently accepts any conflicting change (false).",
            "test_consciousness_upgrade_pipeline.TestConflictIsActuallyRefused."
            "test_this_does_not_exist_and_never_will",
        )
        result = check_claim(claim, cwd=str(_REPO_ROOT / "tests"))
        self.assertNotEqual(result.status, GROUNDED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
