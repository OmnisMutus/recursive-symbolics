"""
test_delta_operator.py

Independent correctness test for delta_operator.py's compute_gamma() --
the directive-strength (gamma) operator central to the Agency Budget spec
(foundation/agency-budget-spec.md) and to Recursive Symbolics' own claim
that gamma <= 0.85 preserves user agency.

Until this file existed, delta_operator.py had never been tested by any
standard -- confirmed by `find . -iname "test_*"` returning nothing
anywhere in this repository before this file was added. The 104/104
cross_validate.cjs suite (omarg-ui/scripts/cross_validate.cjs) checks
that the Python and JS symbolic-debugger engines *agree* with each other;
it does not check that either is *correct* against an independent
mathematical reference. This file does that, for compute_gamma()
specifically, following the same discipline the sibling `solo/` repo
applies to its own engines (TESTING_STANDARD.md there): an independent
ground-truth reference, exhaustive boundary cases, and a documented
adversarial break-it proof (see LIBER_0.md in solo/ for the run log).

INDEPENDENT GROUND TRUTH: `reference_gamma()` below re-derives the exact
same mathematical quantity -- softmax, then normalized Shannon entropy,
then 1 - h_norm clipped to [0, cap] -- using plain Python `math.exp` /
`math.log2` and no NumPy. It is a separate implementation of the same
formula, not a re-run of compute_gamma() against itself. Every assertion
below compares delta_operator.compute_gamma()'s real output against this
independent derivation, hand-checked against the formula in
foundation/agency-budget-spec.md and mathematical-foundation.md's
Shannon-entropy definition.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import delta_operator as do  # noqa: E402


def reference_gamma(logits, cap=0.85):
    """Independent re-derivation of compute_gamma()'s formula in plain
    Python (no NumPy), mirroring delta_operator.py's own special cases
    for empty and single-element input so the boundary behavior itself
    is part of what gets checked, not assumed."""
    if not logits:
        return 0.0
    if len(logits) <= 1:
        return cap
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    s = sum(exps)
    probs = [e / s for e in exps]
    h = -sum(p * math.log2(p + 1e-12) for p in probs)
    h_max = math.log2(len(probs))
    h_norm = h / h_max if h_max > 0 else 0.0
    raw = 1.0 - h_norm
    return max(0.0, min(cap, raw))


class TestComputeGammaAgainstIndependentReference(unittest.TestCase):
    """Every case here was computed by reference_gamma() first, printed,
    and hand-checked against the softmax + Shannon-entropy formula before
    being written down as an assertion -- see
    docs/delta_operator_kabbalistic_hand_verification.md in solo/ for the
    by-hand arithmetic on two of these cases."""

    def assertGammaMatches(self, logits, places=9):
        expected = reference_gamma(logits)
        actual = do.compute_gamma(list(logits))
        self.assertAlmostEqual(actual, expected, places=places,
                                msg=f"logits={logits}: expected {expected}, got {actual}")
        return actual

    def test_uniform_logits_give_near_zero_gamma(self):
        # Maximum entropy distribution (all equal) => h_norm ~= 1 => gamma ~= 0.
        g = self.assertGammaMatches([1.0, 1.0, 1.0, 1.0])
        self.assertLess(g, 1e-9)

    def test_uniform_two_logits_also_near_zero(self):
        g = self.assertGammaMatches([5.0, 5.0])
        self.assertLess(g, 1e-9)

    def test_moderately_skewed_logits_uncapped_value(self):
        # Hand-derived: softmax([1,0]) = [0.7310586, 0.2689414],
        # H ~= 0.8399452 bits, h_max = 1.0, gamma ~= 0.1600585.
        g = self.assertGammaMatches([1.0, 0.0])
        self.assertAlmostEqual(g, 0.16005846, places=6)

    def test_three_way_moderate_skew(self):
        self.assertGammaMatches([2.0, 2.0, 0.0])

    def test_highly_skewed_logits_hit_the_cap(self):
        # softmax([10,0,0]) puts ~99.99% mass on the first logit; entropy
        # collapses near 0, so raw_gamma ~= 1.0, clipped to MAX_GAMMA_CAP.
        g = self.assertGammaMatches([10.0, 0.0, 0.0])
        self.assertEqual(g, do.MAX_GAMMA_CAP)
        self.assertEqual(g, 0.85)

    def test_extreme_skew_still_capped_not_exceeded(self):
        g = self.assertGammaMatches([500.0, 0.0])
        self.assertEqual(g, 0.85)
        self.assertLessEqual(g, 0.85)

    def test_large_magnitude_logits_numerically_stable(self):
        # Tests the np.max-subtraction stability trick: without it,
        # exp(1000) overflows. This must not raise, and must match a
        # shifted-equivalent small-magnitude case (see shift-invariance
        # test below for the formal version of this property).
        g = self.assertGammaMatches([1000.0, 1.0, 1.0])
        self.assertEqual(g, 0.85)

    def test_softmax_shift_invariance(self):
        # Softmax (and therefore gamma) is invariant to adding a constant
        # to every logit -- a real mathematical property of softmax, not
        # an implementation detail. [1,0] and [101,100] must give the
        # exact same gamma.
        g1 = do.compute_gamma([1.0, 0.0])
        g2 = do.compute_gamma([101.0, 100.0])
        g3 = do.compute_gamma([-99.0, -100.0])
        self.assertAlmostEqual(g1, g2, places=9)
        self.assertAlmostEqual(g1, g3, places=9)

    def test_negative_logits(self):
        self.assertGammaMatches([-5.0, -1.0, -10.0])

    def test_empty_logits_returns_zero(self):
        self.assertEqual(do.compute_gamma([]), 0.0)

    def test_single_logit_returns_cap_not_zero_or_uniform_result(self):
        # Explicit special case in the source (len(arr) <= 1): a single
        # logit carries no distributional information to compute entropy
        # over, so the implementation defines this as maximum directivity
        # (the cap) rather than 0.0 or raising. Documented here as
        # intentional behavior, not an oversight -- see the hand-
        # verification doc for the case this reads as surprising at first.
        self.assertEqual(do.compute_gamma([7.0]), do.MAX_GAMMA_CAP)
        self.assertEqual(do.compute_gamma([-3.0]), 0.85)

    def test_two_identical_single_valued_lists_still_hit_special_case(self):
        self.assertEqual(do.compute_gamma([0.0]), 0.85)

    def test_gamma_never_exceeds_configured_cap_across_many_random_cases(self):
        import random
        random.seed(20260801)
        for _ in range(200):
            n = random.randint(2, 8)
            logits = [random.uniform(-50, 50) for _ in range(n)]
            g = do.compute_gamma(logits)
            self.assertGreaterEqual(g, 0.0)
            self.assertLessEqual(g, do.MAX_GAMMA_CAP)
            # And must still match the independent reference every time.
            self.assertAlmostEqual(g, reference_gamma(logits), places=9)

    def test_max_gamma_cap_is_the_documented_0_85(self):
        # Ground truth for this one is the spec document itself, not code:
        # foundation/agency-budget-spec.md states the hard ceiling is 0.85.
        self.assertEqual(do.MAX_GAMMA_CAP, 0.85)


class TestEnrichResponsePayload(unittest.TestCase):
    """enrich_response() wraps compute_gamma() into the sovereignty_metadata
    payload documented in agency-budget-spec.md section 2. These checks
    confirm the wrapping is faithful, not just that gamma itself is right."""

    def test_payload_shape_and_gamma_passthrough(self):
        result = do.enrich_response("Demo content", [1.0, 0.0], alternatives=2)
        meta = result["sovereignty_metadata"]
        self.assertEqual(result["content"], "Demo content")
        expected_gamma = reference_gamma([1.0, 0.0])
        self.assertAlmostEqual(meta["directive_strength"], expected_gamma, places=9)
        # drift_coefficient is documented as tracking gamma directly.
        self.assertAlmostEqual(meta["drift_coefficient"], meta["directive_strength"], places=9)
        self.assertEqual(meta["max_gamma_cap"], 0.85)
        self.assertEqual(meta["alternatives_presented"], 2)
        self.assertEqual(meta["sovereignty_guarantee"], "ALLOWABLE_AGENCY_BUDGET_RESPECTED")

    def test_payload_with_capped_gamma(self):
        result = do.enrich_response("Directive content", [50.0, 0.0])
        self.assertEqual(result["sovereignty_metadata"]["directive_strength"], 0.85)


if __name__ == "__main__":
    unittest.main(verbosity=2)
