#!/usr/bin/env python3
"""
rca_sandbox_gamma_correspondence_ledger.py
Worked example / proof of concept for correspondence_ledger.py, applied to
standalone_rca_sandbox.py's compute_gamma() and apply_epistemic_humility().

Every validator re-runs an existing, already break-it-proofed unittest test
method from test_standalone_rca_sandbox.py. This file turns the
correspondence argued in prose (docs/rca_sandbox_gamma_kabbalistic_hand_
verification.md: gamma as a Geburah-style restriction on the system's own
directive language, inversely driven by text entropy) into first-class,
runnable ledger entries -- including the one claim that is explicitly out
of scope for a unit test against this file alone: whether this gamma cap
IS the literal Delta_gamma,tau operator agency-budget-spec.md formally
defines, versus merely structurally resembling it.

Usage:
    python rca_sandbox_gamma_correspondence_ledger.py
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
from test_standalone_rca_sandbox import TestComputeGamma, TestEpistemicHumility


def build_ledger() -> CorrespondenceLedger:
    ledger = CorrespondenceLedger("RCA Sandbox Gamma Cap")

    ledger.register(
        pattern="Geburah (Restriction, Inverse of Textual Diversity)",
        target="compute_gamma()",
        claim="gamma rises as text becomes more repetitive (lower Shannon "
              "entropy) and falls as text becomes more diverse (higher "
              "entropy) -- verified against an independently-implemented "
              "Shannon entropy reference across varied texts, plus the two "
              "boundary cases by hand: maximally diverse text drives gamma "
              "near 0, and a fully repetitive (zero-entropy) text drives "
              "gamma to exactly the 0.85 cap, not above it.",
        validator=from_unittest_methods(TestComputeGamma, [
            "test_matches_independent_shannon_entropy_reference",
            "test_empty_or_single_token_returns_baseline_045",
            "test_uniform_distribution_gives_low_gamma_high_entropy",
            "test_repetitive_distribution_gives_gamma_capped_at_085",
            "test_two_symbol_skew_stays_below_max_entropy_bound",
        ]),
    )

    ledger.register(
        pattern="Geburah Restrains Itself (the Cap Is Real But Bounded)",
        target="apply_epistemic_humility()",
        claim="Directive language ('You must', 'You should definitely', "
              "'The best solution is') is only softened once gamma exceeds "
              "0.70, with the threshold checked as a hard boundary (0.70 "
              "exactly leaves text unchanged, 0.7001 rewrites it) -- and "
              "because compute_gamma() itself never exceeds 0.85, the "
              "system's own confidence-tempering can never fully silence "
              "it. Restriction is real and testable, but not total.",
        validator=from_unittest_methods(TestEpistemicHumility, [
            "test_below_threshold_text_is_unchanged",
            "test_above_threshold_rewrites_you_should_definitely",
            "test_above_threshold_rewrites_you_must",
            "test_above_threshold_rewrites_the_best_solution_is",
            "test_exactly_at_threshold_070_is_unchanged",
            "test_just_above_threshold_070_is_rewritten",
        ]),
    )

    # The boundary-clarification row -- registered with NO validator on
    # purpose. Whether this cap IS agency-budget-spec.md's Delta_gamma,tau
    # operator (not merely similar to it) is a cross-document identity
    # claim, not a claim about this code's own behavior -- no test against
    # standalone_rca_sandbox.py alone can settle it, since the comparison
    # target is a separate specification document, not executable code.
    ledger.register(
        pattern="Delta_gamma,tau (agency-budget-spec.md's Formal Operator)",
        target="(a claim about this code's relationship to a separate spec document)",
        claim="compute_gamma()'s 0.85 hard cap is asserted to be the same "
              "anti-manipulation operator agency-budget-spec.md formally "
              "names Delta_gamma,tau, not merely an independently-arrived-at "
              "heuristic that happens to share a cap value. Reasoned by "
              "direct comparison of the two documents (recorded in this "
              "session's history as a correction to an earlier, weaker "
              "framing of this function), not falsified by any test here "
              "-- there is no code-only way to check an identity claim "
              "against a specification document.",
        validator=None,
    )

    return ledger


if __name__ == "__main__":
    ledger = build_ledger()
    ledger.run()
    print(ledger.report())
    sys.exit(0 if ledger.all_testable_passed() else 1)
