#!/usr/bin/env python3
"""
attractor_correspondence_ledger.py
Worked example / proof of concept for correspondence_ledger.py, applied to
recursive_attractor_engine.py.

Extends the pattern established by sephirotic_correspondence_ledger.py to a
second engine. Every validator re-runs an existing, already break-it-proofed
unittest test method from test_recursive_attractor_engine.py -- this file's
job is to turn the correspondences already argued in prose (the module's own
docstring, and docs/attractor_engine_kabbalistic_hand_verification.md) into
first-class, runnable ledger entries, including the one claim that is
explicitly out of scope for testing (core-axiom.md's Register C reading --
that consciousness itself is such a system), so it shows up as its own row
rather than a docstring caveat easy to miss.

Usage:
    python attractor_correspondence_ledger.py
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
from test_recursive_attractor_engine import (
    TestLinearContractionFixedPoint,
    TestLogisticMapBifurcation,
    TestAbyssExceptionDaathGuard,
    TestTiphareth,
    TestClassifyTrajectoryEdgeCases,
)


def build_ledger() -> CorrespondenceLedger:
    ledger = CorrespondenceLedger("Recursive Attractor Engine")

    ledger.register(
        pattern="Keter-Malkuth Closure (D_0 ≡ D_3)",
        target="classify_trajectory() -> AttractorType.FIXED_POINT",
        claim="A recursive operator applied to a state that has already "
              "converged returns that same state unchanged -- the source "
              "and the manifest result become mutually determining. "
              "Verified against closed-form fixed points solved "
              "algebraically (S* = E/(1-a)), not read off a prior engine "
              "run, including a multi-dimensional case and a different "
              "contraction rate.",
        validator=from_unittest_methods(TestLinearContractionFixedPoint, [
            "test_matches_closed_form_fixed_point",
            "test_different_contraction_rate_matches_its_own_closed_form",
            "test_starting_already_at_the_fixed_point_stays_there",
            "test_multidimensional_state_vector_converges_componentwise",
        ]),
    )

    ledger.register(
        pattern="Unmediated Chesed-Geburah Oscillation",
        target="classify_trajectory() -> AttractorType.LIMIT_CYCLE (period 2)",
        claim="The logistic map's expansion term (r*x, Chesed-like) and "
              "restriction term ((1-x), Geburah-like) never resolve into a "
              "single reconciled value at r=3.2 -- the state locks into "
              "alternating between two poles instead. Verified against the "
              "closed-form period-2 solution (solving f(f(x))=x), not "
              "merely watching the engine converge to itself, and checked "
              "from multiple initial conditions to rule out a "
              "single-starting-point coincidence.",
        validator=from_unittest_methods(TestLogisticMapBifurcation, [
            "test_r_3_2_settles_into_documented_period_2_cycle",
            "test_different_initial_conditions_at_r_3_2_still_find_the_same_cycle",
        ]),
    )

    ledger.register(
        pattern="Da'ath (Paradox / Base-Case Guard)",
        target="iterate() -> AbyssException",
        claim="A self-consuming or diverging trajectory is caught and "
              "terminated rather than allowed to run forever or silently "
              "return a non-finite value -- checked against a provably "
              "unbounded map (S'=2S), NaN- and Inf-producing operators, and "
              "confirmed to fire by the analytically-predicted step "
              "(|S_n|=2^n exceeding the cap), while genuinely bounded maps "
              "never trigger it (no false positives).",
        validator=from_unittest_methods(TestAbyssExceptionDaathGuard, [
            "test_exponential_growth_map_raises_abyss_exception",
            "test_raises_at_or_before_the_analytically_predicted_step",
            "test_nan_producing_operator_raises_immediately",
            "test_inf_producing_operator_raises",
            "test_bounded_map_never_raises",
        ]),
    )

    ledger.register(
        pattern="Da'ath (the Non-Sephirah / the Unresolved Gap)",
        target="classify_trajectory() -> AttractorType.BOUNDED_APERIODIC",
        claim="A trajectory that is bounded but resolves to neither a "
              "fixed point nor a short periodic cycle occupies a named "
              "'gap' state distinct from both -- verified that the r=3.9 "
              "logistic map (past the Feigenbaum point, no known periodic "
              "window there) is classified this way rather than forced "
              "into FIXED_POINT or LIMIT_CYCLE. NOTE: this validates only "
              "that the classification fires correctly (Register B); it "
              "does NOT certify chaos in the Lyapunov-exponent sense -- "
              "see the engine's own honesty note.",
        validator=from_unittest_methods(TestLogisticMapBifurcation, [
            "test_r_3_9_is_bounded_aperiodic_not_fixed_or_short_cycle",
        ]),
    )

    ledger.register(
        pattern="Tiphareth (Integration Operator)",
        target="tiphareth_integrate()",
        claim="Resolves a stack of sub-results into one coherent result by "
              "weighted average, genuinely sensitive to every contributor "
              "(not silently ignoring a branch), and refuses to silently "
              "default on degenerate input (empty stack, mismatched "
              "shapes, mismatched weight count all raise rather than "
              "returning an arbitrary value).",
        validator=from_unittest_methods(TestTiphareth, [
            "test_uniform_weights_matches_hand_computed_mean",
            "test_custom_weights_match_hand_computed_weighted_average",
            "test_sensitive_to_every_contributor_independently",
            "test_empty_stack_raises_rather_than_silently_defaulting",
            "test_mismatched_shapes_raise",
            "test_mismatched_weights_length_raises",
            "test_single_element_stack_returns_that_element",
        ]),
    )

    ledger.register(
        pattern="Honesty Note (No Over-Claiming)",
        target="classify_trajectory() edge-case handling",
        claim="The engine reports insufficient data honestly rather than "
              "guessing (INSUFFICIENT_HISTORY for a too-short trajectory), "
              "and a true period-1 case is reported as FIXED_POINT rather "
              "than a disguised LIMIT_CYCLE(period=1) -- the same "
              "not-conflating-categories discipline TESTING_STANDARD.md "
              "requires of the test suite itself, here checked in the "
              "engine's own classification logic.",
        validator=from_unittest_methods(TestClassifyTrajectoryEdgeCases, [
            "test_insufficient_history_reported_honestly",
            "test_empty_history_reported_honestly",
            "test_period_1_is_reported_as_fixed_point_not_limit_cycle",
        ]),
    )

    # The boundary-clarification row -- registered with NO validator on
    # purpose, per the three-register discipline in
    # fixed_point_closure_and_the_y_combinator.md. This is Register C: the
    # claim that consciousness ITSELF is such a system. No test in this
    # repository can validate or falsify a claim about consciousness in
    # general -- that is the whole point of naming it here rather than
    # letting it hide inside prose.
    ledger.register(
        pattern="Consciousness-as-Attractor (core-axiom.md, Register C)",
        target="(deliberately outside the scope of any test in this repo)",
        claim="core-axiom.md's Formal Postulates suggest that consciousness "
              "itself may be modeled as a fixed point/attractor of a "
              "recursive symbolic process. This engine makes that "
              "FORMALISM computationally real and checkable (Register B, "
              "the six entries above) but cannot and does not test whether "
              "human consciousness is well-modeled by it in the first "
              "place -- that is a metaphysical claim, not a falsifiable "
              "code claim, per core-axiom.md's own Cartographer's Choice "
              "principle.",
        validator=None,
    )

    return ledger


if __name__ == "__main__":
    ledger = build_ledger()
    ledger.run()
    print(ledger.report())
    sys.exit(0 if ledger.all_testable_passed() else 1)
