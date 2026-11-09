#!/usr/bin/env python3
"""
test_self_polishing_transmuter.py
Correctness verification for self_polishing_transmuter.py per TESTING_STANDARD.md.

SCOPE NOTE (stated per PHILOSOPHICAL_AND_ENGINEERING_BOUNDARIES.md's own rule
about naming which kind of claim is being made): this file tests the
MECHANICAL correctness of two functions -- compute_entropy() (a real Shannon
entropy calculation, independently checkable) and transmute_artifact()'s
keyword-matching classification (a deterministic string-matching rule,
independently checkable). It takes NO position on whether "Sephirotic
attractor" is a meaningful category for changelog text -- that's an
analogical/naming claim, not a tested one, and is out of scope here.

Ground truth used:
- compute_entropy(): Shannon entropy computed independently via
  collections.Counter and the standard formula H = -sum(p*log2(p)),
  normalized by log2(num_unique_tokens) -- written fresh in this file,
  not calling the engine's own compute_entropy().
- transmute_artifact(): the keyword-matching rule (4-character prefix
  overlap in either direction) is deterministic, so ground truth is a
  hand-picked set of texts built from words known to be in exactly one
  CENTROIDS category (verified by inspecting CENTROIDS directly), so the
  expected dominant attractor is unambiguous.
"""

import sys
import math
import unittest
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from self_polishing_transmuter import SelfPolishingTransmuter, CENTROIDS


def reference_entropy(text: str) -> float:
    """Independent Shannon entropy reference -- Counter-based, not reusing
    the engine's re.findall/dict-comprehension implementation path."""
    import re
    tokens = re.findall(r"\b\w+\b", text.lower())
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    probs = [c / total for c in counts.values()]
    h = -sum(p * math.log2(p) for p in probs if p > 0)
    h_max = math.log2(len(probs)) if len(probs) > 1 else 1.0
    return round(h / h_max, 3) if h_max > 0 else 0.0


class TestComputeEntropy(unittest.TestCase):
    def setUp(self):
        self.t = SelfPolishingTransmuter()

    def test_empty_string_is_zero(self):
        self.assertEqual(self.t.compute_entropy(""), 0.0)

    def test_whitespace_only_is_zero(self):
        self.assertEqual(self.t.compute_entropy("   \n\t  "), 0.0)

    def test_single_repeated_token_is_zero_entropy(self):
        # No uncertainty when every token is identical.
        self.assertAlmostEqual(self.t.compute_entropy("test test test"), 0.0, places=6)

    def test_two_equally_likely_tokens_is_max_normalized_entropy(self):
        # Textbook case: 2 equally likely outcomes -> normalized entropy = 1.0
        self.assertAlmostEqual(self.t.compute_entropy("a b"), 1.0, places=6)

    def test_four_equally_likely_tokens_is_also_max_normalized_entropy(self):
        # Normalization means uniform distributions always hit 1.0 regardless
        # of how many categories there are.
        self.assertAlmostEqual(self.t.compute_entropy("a a b b c c d d"), 1.0, places=6)

    def test_matches_independent_reference_skewed_distribution(self):
        text = "fix fix fix fix bug error revert containment"
        self.assertAlmostEqual(self.t.compute_entropy(text), reference_entropy(text), places=6)

    def test_matches_independent_reference_random_prose(self):
        text = "The quick brown fox jumps over the lazy dog near the river bank"
        self.assertAlmostEqual(self.t.compute_entropy(text), reference_entropy(text), places=6)


class TestTransmuteArtifact(unittest.TestCase):
    def setUp(self):
        self.t = SelfPolishingTransmuter()

    def test_empty_artifact_returns_error(self):
        result = self.t.transmute_artifact("")
        self.assertIn("error", result)

    def test_punctuation_only_returns_error(self):
        result = self.t.transmute_artifact("!!! ... ---")
        self.assertIn("error", result)

    def test_unambiguous_geburah_text_dominant(self):
        # All 4 words are Geburah-category keywords, verified directly against
        # CENTROIDS -- ground truth is the source dict, not a guess.
        self.assertTrue(all(w in CENTROIDS["Geburah (Severity / Restriction)"]
                             for w in ["fix", "bug", "error", "revert"]))
        result = self.t.transmute_artifact("fix bug error revert")
        self.assertEqual(result["dominant_attractor"], "Geburah (Severity / Restriction)")
        self.assertEqual(result["attractor_scores"]["Geburah (Severity / Restriction)"], 1.0)
        # No other category should score above 0 for these specific words.
        for seph, score in result["attractor_scores"].items():
            if seph != "Geburah (Severity / Restriction)":
                self.assertEqual(score, 0.0)

    def test_unambiguous_chesed_text_dominant(self):
        self.assertTrue(all(w in CENTROIDS["Chesed (Expansion / Features)"]
                             for w in ["add", "feature", "new", "extend"]))
        result = self.t.transmute_artifact("add feature new extend")
        self.assertEqual(result["dominant_attractor"], "Chesed (Expansion / Features)")

    def test_no_keyword_match_falls_back_to_hod(self):
        # Gibberish tokens with no 4-char prefix overlap with any CENTROIDS
        # keyword must fall back to the documented default (Hod), per the
        # engine's own explicit fallback logic, not crash or pick randomly.
        result = self.t.transmute_artifact("xyz123 qwerty zzzzzz")
        self.assertEqual(result["dominant_attractor"], "Hod (Micro-Detail / Maintenance)")
        self.assertTrue(all(score == 0.0 for score in result["attractor_scores"].values()))

    def test_confidence_lower_bound_clamped_at_20(self):
        result = self.t.transmute_artifact("xyz123 qwerty zzzzzz")
        self.assertGreaterEqual(result["confidence_pct"], 20)

    def test_confidence_upper_bound_clamped_at_95(self):
        result = self.t.transmute_artifact("fix bug error revert containment security strict block deny restrict")
        self.assertLessEqual(result["confidence_pct"], 95)

    def test_fuzzy_prefix_matching_documented_quirk(self):
        # DOCUMENTED CHARACTERISTIC, not a bug fix: the matching rule is a
        # 4-character prefix overlap in EITHER direction
        # (t.startswith(kw[:4]) or kw.startswith(t[:4])), which means a word
        # like "address" fuzzy-matches the Chesed keyword "add" even though
        # semantically "address" (e.g. "address the bug") has nothing to do
        # with "add" (expansion/new feature). This test locks in that this
        # is the engine's actual, current behavior -- not an assertion that
        # it's correct classification, just that it's what the code does.
        result = self.t.transmute_artifact("address")
        self.assertGreater(result["attractor_scores"]["Chesed (Expansion / Features)"], 0.0,
            "This locks in the known prefix-matching quirk; if this ever fails, "
            "the matching rule changed and this comment/test should be revisited.")

    def test_invariants_contain_current_entropy_value(self):
        result = self.t.transmute_artifact("fix bug error revert")
        self.assertIn(f"H_s = {result['entropy_hs']}", result["invariants"][0])

    def test_dominant_attractor_matches_max_score(self):
        import random
        rng = random.Random(5)
        words = ["fix", "add", "bump", "merge", "api", "feature", "revert", "release", "syntax", "schema"]
        text = " ".join(rng.choice(words) for _ in range(15))
        result = self.t.transmute_artifact(text)
        max_score = max(result["attractor_scores"].values())
        self.assertEqual(result["attractor_scores"][result["dominant_attractor"]], max_score)


def run_unit_test_suite():
    print("=" * 72)
    print("  SELF-POLISHING TRANSMUTER — CORRECTNESS TEST SUITE")
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
