"""
test_agency_budget.py

Independent correctness test for agency_budget.py -- a THIRD independent
implementation (after standalone_rca_sandbox.py's text-frequency version
and delta_operator.py's NumPy/logit version) of the same directive-
strength gamma formula: softmax, normalized Shannon entropy, 1 - h_norm
clipped to a 0.85 cap. Until this file existed, agency_budget.py had
never been tested by any standard -- confirmed by `find . -iname
"test_*"` returning only test_delta_operator.py before this file was
added.

INDEPENDENT GROUND TRUTH, TWO KINDS:
1. Cross-check against delta_operator.compute_gamma() on IDENTICAL
   logits -- a genuinely different implementation (pure Python math.exp/
   math.log2 here vs. NumPy there), written at a different time, both
   claiming to compute the same formula with the same 0.85 cap
   (confirmed both read/hardcode 0.85 -- delta_operator.py from
   sovereignty_config.json's "max_gamma_cap", agency_budget.py hardcoded
   -- checked directly, not assumed, that these are the same number).
   Agreement across many cases is real evidence both are correct, not
   just internally self-consistent.
2. A hand-derived pure-Python reference (reference_gamma below),
   independent of BOTH agency_budget.py and delta_operator.py's own
   code, for cases where a fresh, from-scratch computation is more
   convincing than cross-checking two implementations that could share
   the same bug.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import agency_budget as ab  # noqa: E402
import delta_operator as do  # noqa: E402


def reference_gamma(logits, cap=0.85):
    """From-scratch reference: softmax -> normalized Shannon entropy ->
    1 - h_norm, clipped to [0, cap]. Independent of both agency_budget.py
    and delta_operator.py's own implementations."""
    if not logits:
        return 0.0
    if len(logits) <= 1:
        return cap
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps)
    probs = [e / total for e in exps]
    h = -sum(p * math.log2(p) for p in probs if p > 0)
    h_max = math.log2(len(probs))
    h_norm = h / h_max if h_max > 0 else 0.0
    raw_gamma = 1.0 - h_norm
    return min(max(raw_gamma, 0.0), cap)


class TestComputeGammaAgainstDeltaOperator(unittest.TestCase):
    """Cross-checks agency_budget.compute_gamma() against
    delta_operator.compute_gamma() -- two independent implementations of
    the same formula -- on identical inputs."""

    CASES = [
        [2.3, 1.0, -0.5],
        [0.0, 0.0, 0.0],           # uniform -> max entropy -> gamma=0
        [100.0, -100.0, -100.0],   # extremely peaked -> gamma capped at 0.85
        [1.0, 2.0],
        [5.0],                      # single logit
        [-3.0, -3.0, -3.0, -3.0],
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [10.0, 9.99, 9.98],
        [-1.0, 1.0],
    ]

    def test_agrees_with_delta_operator_on_every_case(self):
        for logits in self.CASES:
            with self.subTest(logits=logits):
                ab_gamma = ab.compute_gamma(logits)
                do_gamma = do.compute_gamma(logits)
                self.assertAlmostEqual(ab_gamma, do_gamma, places=9)

    def test_agrees_with_from_scratch_reference_on_every_case(self):
        for logits in self.CASES:
            with self.subTest(logits=logits):
                self.assertAlmostEqual(ab.compute_gamma(logits), reference_gamma(logits), places=9)

    def test_empty_logits_returns_zero(self):
        self.assertEqual(ab.compute_gamma([]), 0.0)

    def test_single_logit_returns_max_cap(self):
        self.assertEqual(ab.compute_gamma([42.0]), 0.85)

    def test_uniform_logits_give_zero_gamma(self):
        # Maximum entropy (uniform distribution) -> norm_entropy=1 -> gamma=0
        g = ab.compute_gamma([0.0, 0.0, 0.0, 0.0])
        self.assertAlmostEqual(g, 0.0, places=9)

    def test_extremely_peaked_logits_are_capped_at_085_not_1(self):
        g = ab.compute_gamma([1000.0, -1000.0])
        self.assertEqual(g, 0.85)  # exact cap, not clipped-but-imprecise

    def test_gamma_never_exceeds_085_across_many_random_cases(self):
        import random
        random.seed(0)
        for _ in range(200):
            n = random.randint(2, 6)
            logits = [random.uniform(-50, 50) for _ in range(n)]
            self.assertLessEqual(ab.compute_gamma(logits), 0.85)
            self.assertGreaterEqual(ab.compute_gamma(logits), 0.0)


class TestEvaluateSovereigntyMetadata(unittest.TestCase):
    """evaluate_sovereignty_metadata() recomputes probs/entropy
    independently of compute_gamma() internally (confirmed by reading
    the code -- it doesn't call compute_gamma()'s internals, it
    duplicates the softmax+entropy computation). This means
    confidence_entropy (hc) and directive_strength (gamma) are only
    related by hc + gamma == 1 when gamma is NOT at the 0.85 cap --
    they diverge when it is, since hc is never capped. Checked directly
    rather than assumed."""

    def test_aai_formula_matches_1_minus_half_gamma(self):
        logits = [2.3, 1.0, -0.5]
        meta = ab.evaluate_sovereignty_metadata(logits, alternatives_count=2)
        expected_aai = round(1.0 - (meta["directive_strength"] * 0.5), 2)
        self.assertEqual(meta["agency_attribution_index"], expected_aai)

    def test_hc_plus_gamma_equals_one_when_uncapped(self):
        logits = [2.3, 1.0, -0.5]  # gamma well below 0.85 -- uncapped case
        meta = ab.evaluate_sovereignty_metadata(logits)
        self.assertLess(meta["directive_strength"], 0.85)
        self.assertAlmostEqual(meta["confidence_entropy"] + meta["directive_strength"], 1.0, places=3)

    def test_hc_plus_gamma_diverge_when_gamma_is_capped(self):
        # Extremely peaked -> raw_gamma far above 0.85, gamma capped at
        # 0.85, but hc (never capped) reflects the true near-zero entropy
        # -- hc + gamma should NOT be ~1 here, a real, checkable
        # divergence, not a bug.
        logits = [1000.0, -1000.0, -1000.0]
        meta = ab.evaluate_sovereignty_metadata(logits)
        self.assertEqual(meta["directive_strength"], 0.85)
        self.assertLess(meta["confidence_entropy"], 0.05)  # entropy is genuinely ~0
        self.assertNotAlmostEqual(meta["confidence_entropy"] + meta["directive_strength"], 1.0, places=2)

    def test_max_gamma_cap_field_is_085(self):
        meta = ab.evaluate_sovereignty_metadata([1.0, 2.0, 3.0])
        self.assertEqual(meta["max_gamma_cap"], 0.85)

    def test_sovereignty_guarantee_field_present(self):
        meta = ab.evaluate_sovereignty_metadata([1.0, 2.0])
        self.assertEqual(meta["sovereignty_guarantee"], "ALLOWABLE_AGENCY_BUDGET_RESPECTED")

    def test_alternatives_presented_passed_through_unchanged(self):
        meta = ab.evaluate_sovereignty_metadata([1.0, 2.0], alternatives_count=5)
        self.assertEqual(meta["alternatives_presented"], 5)


class TestApplyStyleFilter(unittest.TestCase):
    """Hand-derived truth table for apply_style_filter's branching logic."""

    NOTE = " (Note: Alternative paths and interpretations may also apply.)"

    def test_low_alternatives_high_gamma_appends_note(self):
        result = ab.apply_style_filter("Do X.", gamma=0.6, alternatives_count=1)
        self.assertEqual(result, "Do X." + self.NOTE)

    def test_low_alternatives_low_gamma_no_note(self):
        result = ab.apply_style_filter("Consider X.", gamma=0.2, alternatives_count=1)
        self.assertEqual(result, "Consider X.")

    def test_enough_alternatives_no_note_even_with_high_gamma(self):
        result = ab.apply_style_filter("Do X.", gamma=0.9, alternatives_count=2)
        self.assertEqual(result, "Do X.")

    def test_boundary_gamma_exactly_04_does_not_trigger_note(self):
        # Condition is `gamma > 0.4`, strictly greater -- exactly 0.4 must NOT trigger.
        result = ab.apply_style_filter("Do X.", gamma=0.4, alternatives_count=1)
        self.assertEqual(result, "Do X.")

    def test_boundary_gamma_just_above_04_triggers_note(self):
        result = ab.apply_style_filter("Do X.", gamma=0.4000001, alternatives_count=1)
        self.assertEqual(result, "Do X." + self.NOTE)

    def test_gamma_above_085_is_capped_internally_but_has_no_observable_effect(self):
        # Real, checkable fact: the `if gamma > 0.85: gamma = 0.85` cap
        # inside this function can never change its output, because the
        # only comparison that uses the (possibly-capped) gamma is
        # `gamma > 0.4`, and every value that would trigger the cap
        # (> 0.85) already satisfies `> 0.4` before capping too. Confirmed
        # by testing a gamma far above 0.85 produces the identical result
        # to one already at 0.85.
        result_uncapped_input = ab.apply_style_filter("Do X.", gamma=5.0, alternatives_count=1)
        result_at_cap = ab.apply_style_filter("Do X.", gamma=0.85, alternatives_count=1)
        self.assertEqual(result_uncapped_input, result_at_cap)


if __name__ == "__main__":
    unittest.main(verbosity=2)
