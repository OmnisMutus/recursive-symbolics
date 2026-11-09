#!/usr/bin/env python3
"""
test_symbolic_debugger.py
Independent correctness test for symbolic_debugger.py: tokenize,
detect_counts, dominant_sephira, suggest_balance, calculate_entropy,
analyze.

INDEPENDENT GROUND TRUTH: calculate_entropy() uses the exact same
unique-adjacent-pair-over-total-pairs formula already hand-verified
elsewhere in this project (solo/standalone_rca_sandbox.py's H_emotional,
see docs/rca_sandbox_gamma_kabbalistic_hand_verification.md) -- this
file re-derives it independently by hand for a small, calculator-checkable
example rather than assuming the other file's derivation transfers.
keyword_map / balancing_rules ground truth is the actual symbolic_api.json,
re-parsed directly in this file, not copied.

DISCOVERED, DOCUMENTED FINDING: exactly one keyword collides across two
sephirot in symbolic_api.json -- "earth" appears in both Binah's and
Malkuth's keyword lists. Because keyword_map is built by iterating
API["sephirot"].items() in JSON order and later entries silently overwrite
earlier ones in a plain dict, Malkuth's mapping wins (Malkuth is listed
after Binah) and Binah's "earth" keyword is effectively unreachable
through detect_counts(). This is a real, checked property of the existing
code and data, not introduced or fixed by this test file.

Also note: balancing_rules maps Geburah -> Geburah (restriction balances
itself) but Chesed -> Geburah (not the reverse) -- an asymmetric mapping
that is a real, existing property of symbolic_api.json, tested here as a
fact about the data, with no claim made about whether it is esoterically
"correct" (Register A, out of scope for this test file).
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import symbolic_debugger as sd  # noqa: E402

BASE_DIR = Path(__file__).parent
API_PATH = BASE_DIR / "symbolic_api.json"


class TestTokenize(unittest.TestCase):
    def test_lowercases_and_splits_on_word_boundaries(self):
        self.assertEqual(sd.tokenize("Stuck AND Blocked!"), ["stuck", "and", "blocked"])

    def test_empty_string(self):
        self.assertEqual(sd.tokenize(""), [])


class TestKeywordMapCollision(unittest.TestCase):
    """The discovered "earth" collision, confirmed against a fresh,
    independent re-parse of symbolic_api.json (not sd's own module-level
    keyword_map, so this isn't just re-checking the same cached dict
    against itself)."""

    @classmethod
    def setUpClass(cls):
        with API_PATH.open("r", encoding="utf-8") as f:
            cls.api = json.load(f)

    def test_earth_appears_in_both_binah_and_malkuth_keyword_lists(self):
        binah_kw = [k.lower() for k in self.api["sephirot"]["Binah"]["keywords"]]
        malkuth_kw = [k.lower() for k in self.api["sephirot"]["Malkuth"]["keywords"]]
        self.assertIn("earth", binah_kw)
        self.assertIn("earth", malkuth_kw)

    def test_earth_is_the_only_collision_across_all_sephirot(self):
        seen = {}
        collisions = set()
        for seph, data in self.api["sephirot"].items():
            for kw in data["keywords"]:
                k = kw.lower()
                if k in seen and seen[k] != seph:
                    collisions.add(k)
                seen[k] = seph
        self.assertEqual(collisions, {"earth"})

    def test_malkuth_wins_the_earth_collision_in_symbolic_debugger(self):
        # Malkuth is listed after Binah in symbolic_api.json's "sephirot"
        # object, so plain dict overwrite means Malkuth's mapping wins --
        # confirmed against sd's actual module-level keyword_map.
        self.assertEqual(sd.keyword_map["earth"], "Malkuth")

    def test_binah_earth_keyword_is_therefore_unreachable_via_detect_counts(self):
        counts = sd.detect_counts(sd.tokenize("earth"))
        self.assertEqual(counts["Malkuth"], 1)
        self.assertNotIn("Binah", counts)


class TestDetectCountsAndDominantSephira(unittest.TestCase):
    def test_geburah_keywords_detected(self):
        tokens = sd.tokenize("I feel stuck and blocked")
        counts = sd.detect_counts(tokens)
        self.assertEqual(counts["Geburah"], 2)  # "stuck" and "blocked"
        self.assertEqual(sd.dominant_sephira(counts), "Geburah")

    def test_no_keywords_returns_none_dominant(self):
        counts = sd.detect_counts(sd.tokenize("the quick brown fox"))
        self.assertEqual(len(counts), 0)
        self.assertIsNone(sd.dominant_sephira(counts))

    def test_dominant_is_the_highest_count_sephirah(self):
        # "restrict" and "stuck" both Geburah; "flow" alone is Chesed --
        # Geburah should win 2-to-1.
        tokens = sd.tokenize("restrict stuck flow")
        counts = sd.detect_counts(tokens)
        self.assertEqual(sd.dominant_sephira(counts), "Geburah")


class TestSuggestBalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with API_PATH.open("r", encoding="utf-8") as f:
            cls.rules = json.load(f)["balancing_rules"]

    def test_matches_real_balancing_rules_table(self):
        for seph, expected in self.rules.items():
            self.assertEqual(sd.suggest_balance(seph), expected)

    def test_geburah_balances_to_itself(self):
        # A real, existing asymmetry in symbolic_api.json: Geburah maps
        # to itself, Chesed maps to Geburah but not the reverse. Tested
        # as a fact about the data; no claim made about whether this is
        # esoterically intended (Register A).
        self.assertEqual(sd.suggest_balance("Geburah"), "Geburah")
        self.assertEqual(sd.suggest_balance("Chesed"), "Geburah")

    def test_sephirah_with_no_rule_returns_none(self):
        self.assertIsNone(sd.suggest_balance("Daath"))
        self.assertIsNone(sd.suggest_balance("Kether"))


class TestCalculateEntropy(unittest.TestCase):
    def test_empty_text_is_zero(self):
        self.assertEqual(sd.calculate_entropy(""), 0.0)

    def test_single_token_is_zero(self):
        self.assertEqual(sd.calculate_entropy("hello"), 0.0)

    def test_hand_computed_alternating_pattern(self):
        # tokens = [a, b, a, b]; pairs = "a b", "b a", "a b";
        # unique pairs = {"a b", "b a"} = 2; total pairs = 3;
        # entropy = 2/3, exactly -- checkable by hand.
        self.assertAlmostEqual(sd.calculate_entropy("a b a b"), 2 / 3, places=9)

    def test_fully_repetitive_text_is_minimal(self):
        # "must restrict must restrict must restrict" -> tokens all
        # alternate between the same 2 words, so every pair is one of
        # only 2 distinct pairs repeated -- same shape as the alternating
        # test above, hand-checkable the same way.
        text = "must restrict must restrict must restrict"
        tokens = sd.tokenize(text)
        self.assertEqual(len(tokens), 6)
        # pairs: "must restrict","restrict must","must restrict",
        #        "restrict must","must restrict" -> unique = 2, total = 5
        self.assertAlmostEqual(sd.calculate_entropy(text), 2 / 5, places=9)

    def test_all_distinct_words_is_maximal(self):
        # 4 tokens, all distinct -> 3 pairs, all distinct -> entropy = 1.0
        self.assertAlmostEqual(sd.calculate_entropy("one two three four"), 1.0, places=9)


class TestAnalyze(unittest.TestCase):
    def test_returns_well_formed_dict_with_keywords(self):
        result = sd.analyze("I feel stuck and blocked")
        self.assertEqual(result["dominant"], "Geburah")
        self.assertEqual(result["suggestion"], "Geburah")
        self.assertIn("entropy", result)

    def test_returns_none_dominant_and_suggestion_with_no_keywords(self):
        result = sd.analyze("the quick brown fox jumps")
        self.assertIsNone(result["dominant"])
        self.assertIsNone(result["suggestion"])
        self.assertGreater(result["entropy"], 0.0)  # still computed regardless

    def test_entropy_present_even_with_no_keyword_matches(self):
        # calculate_entropy() runs independently of keyword detection --
        # confirms analyze() doesn't short-circuit entropy when counts
        # is empty.
        result = sd.analyze("zebra quokka narwhal platypus")
        self.assertAlmostEqual(result["entropy"], 1.0, places=9)


def run_unit_test_suite():
    print("=" * 72)
    print("  SYMBOLIC_DEBUGGER.PY -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("Test") and isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
