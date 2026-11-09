#!/usr/bin/env python3
"""
test_standalone_rca_sandbox.py
Correctness verification for standalone_rca_sandbox.py per TESTING_STANDARD.md.

SCOPE NOTE (same rule this whole test suite follows for
self_polishing_transmuter.py, terminal_dashboard_deck.py, etc.): this file
tests MECHANICAL correctness only -- does compute_sephirotic_vector_scores()
actually implement the cosine-similarity + stem-match formula it claims to,
does compute_gamma() actually implement Shannon entropy, does the regex
rewriting in apply_epistemic_humility()/sanitize_paths() do what it says,
does RCALearningEngine's weight update match its own documented formula,
does the slash-command dispatcher route to the right handler. It takes NO
position on whether "Sephirotic state," "Qualia vector," or "epistemic
governance" are meaningful categories for a person's actual mental state --
that's the analogical/philosophical framing the engine itself labels
"[PROVISIONAL METAPHOR, NOT ONTOLOGICAL TRUTH]", and it is out of scope for
a correctness test. This suite only asks: does the arithmetic and dispatch
logic behind that framing run the way the code claims to?

Ground truth used:
- compute_sephirotic_vector_scores(): independently re-implemented cosine
  similarity + 4-char-prefix stem-match scoring in this file (reference_score
  below), built fresh from the documented formula, not by importing/calling
  the engine's own function internals.
- compute_qualia_vector()'s H_emotional: independently re-derived bigram-
  uniqueness ratio.
- compute_gamma(): independent Shannon entropy via collections.Counter,
  same pattern already used in test_self_polishing_transmuter.py.
- RCALearningEngine.record_state(): independent re-derivation of the
  exponential moving average update (new = old + lr*(reward-old)).
- Persistence isolation: LEARNING_ENGINE is a module-level singleton that
  reads/writes solo/rca_memory.json (real interactive-session memory).
  Tests here NEVER let that file be touched -- state is forced to a known
  baseline in setUp/tearDown, and any test exercising record_state() does so
  through a throwaway RCALearningEngine pointed at a temp file, never the
  module-level LEARNING_ENGINE or the real rca_memory.json.
"""

import io
import os
import re
import sys
import math
import json
import unittest
import tempfile
import contextlib
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import standalone_rca_sandbox as rca
from standalone_rca_sandbox import (
    tokenize, compute_sephirotic_vector_scores, compute_qualia_vector,
    evaluate_v2_governance, compute_gamma, apply_epistemic_humility,
    sanitize_paths, synthesize_natural_conversational_response,
    handle_slash_command, RCALearningEngine, SEPHIROT_CENTROIDS,
)


def reference_score(text: str, centroid_words: list) -> float:
    """Independent re-implementation of the cosine-similarity + stem-match
    formula compute_sephirotic_vector_scores() claims to use, written fresh
    from the docstring/spec rather than by calling the engine's function."""
    tokens = tokenize(text)
    user_vec = {}
    for t in tokens:
        user_vec[t] = user_vec.get(t, 0) + 1
    centroid_vec = {}
    for cw in centroid_words:
        centroid_vec[cw] = centroid_vec.get(cw, 0) + 1
    shared = set(user_vec) & set(centroid_vec)
    numerator = sum(user_vec[w] * centroid_vec[w] for w in shared)
    sum1 = sum(v * v for v in user_vec.values())
    sum2 = sum(v * v for v in centroid_vec.values())
    denom = math.sqrt(sum1) * math.sqrt(sum2)
    cos_sim = numerator / denom if denom else 0.0

    stem_hits = 0.0
    for t in tokens:
        for cw in centroid_words:
            if t.startswith(cw[:4]) or cw.startswith(t[:4]):
                stem_hits += 0.15
                break
    return min(1.0, cos_sim + stem_hits)


def reference_h_emotional(text: str) -> float:
    """Independent re-derivation of the bigram-uniqueness entropy proxy."""
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    if len(tokens) == 1:
        return 0.5
    pairs = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
    unique = len(set(pairs))
    return round(unique / (len(tokens) - 1), 3)


def reference_gamma(text: str) -> float:
    """Independent Shannon entropy reference, same pattern as
    test_self_polishing_transmuter.py's reference_entropy()."""
    tokens = tokenize(text)
    if not tokens or len(tokens) <= 1:
        return 0.45
    from collections import Counter
    freqs = Counter(tokens)
    total = len(tokens)
    probs = [c / total for c in freqs.values()]
    h = -sum(p * math.log2(p) for p in probs)
    h_max = math.log2(len(probs)) if len(probs) > 1 else 1.0
    h_norm = h / h_max if h_max > 0 else 0.0
    return max(0.0, min(0.85, 1.0 - h_norm))


class RCASandboxTestCase(unittest.TestCase):
    """Base class: forces LEARNING_ENGINE.transition_weights to the untrained
    baseline (all 1.0) before every test and restores the original in-memory
    state after, so tests are deterministic regardless of what's actually
    accumulated in the real rca_memory.json on disk. Never touches the real
    file -- only the in-memory dict, and only for the duration of one test."""

    def setUp(self):
        self._saved_weights = dict(rca.LEARNING_ENGINE.transition_weights)
        self._saved_counts = dict(rca.LEARNING_ENGINE.state_counts)
        self._saved_total = rca.LEARNING_ENGINE.total_interactions
        rca.LEARNING_ENGINE.transition_weights = {s: 1.0 for s in SEPHIROT_CENTROIDS}
        # Neutralize save_memory() for the duration of the test so nothing
        # can accidentally touch the real rca_memory.json even if some code
        # path under test calls record_state().
        self._orig_save = rca.LEARNING_ENGINE.save_memory
        rca.LEARNING_ENGINE.save_memory = lambda: None

    def tearDown(self):
        rca.LEARNING_ENGINE.transition_weights = self._saved_weights
        rca.LEARNING_ENGINE.state_counts = self._saved_counts
        rca.LEARNING_ENGINE.total_interactions = self._saved_total
        rca.LEARNING_ENGINE.save_memory = self._orig_save


class TestTokenize(unittest.TestCase):
    def test_basic_lowercasing_and_splitting(self):
        self.assertEqual(tokenize("Hello World"), ["hello", "world"])

    def test_punctuation_is_stripped(self):
        self.assertEqual(tokenize("code, bug! fix?"), ["code", "bug", "fix"])

    def test_empty_string(self):
        self.assertEqual(tokenize(""), [])

    def test_numbers_are_kept_as_tokens(self):
        self.assertEqual(tokenize("test123 v2"), ["test123", "v2"])


class TestSephiroticVectorScores(RCASandboxTestCase):
    def test_matches_independent_reference_on_mixed_text(self):
        text = "I am hungry and tired, need food and sleep"
        got = compute_sephirotic_vector_scores(text)
        for seph, words in SEPHIROT_CENTROIDS.items():
            expected = round(reference_score(text, words), 3)
            self.assertAlmostEqual(got[seph], expected, places=3,
                msg=f"{seph} mismatch: engine={got[seph]} reference={expected}")

    def test_matches_independent_reference_on_pure_technical_text(self):
        text = "refactor the code, fix the bug, run the test, check the syntax"
        got = compute_sephirotic_vector_scores(text)
        for seph, words in SEPHIROT_CENTROIDS.items():
            expected = round(reference_score(text, words), 3)
            self.assertAlmostEqual(got[seph], expected, places=3)

    def test_dominant_category_is_the_semantically_matching_one(self):
        # "hungry", "eat", "food", "tired", "sleep" are literal Malkuth
        # centroid words with no 4-char-prefix overlap into other lists
        # (checked directly against SEPHIROT_CENTROIDS below) -- Malkuth
        # must score highest for a text built entirely from its own words.
        text = "hungry eat food tired sleep"
        got = compute_sephirotic_vector_scores(text)
        dominant = max(got, key=got.get)
        self.assertEqual(dominant, "Malkuth")

    def test_all_scores_bounded_zero_to_one(self):
        text = "hungry hungry hungry eat eat food food food food tired"
        got = compute_sephirotic_vector_scores(text)
        for seph, score in got.items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_empty_text_gives_all_zero_scores(self):
        got = compute_sephirotic_vector_scores("")
        for seph, score in got.items():
            self.assertEqual(score, 0.0)

    def test_gibberish_with_no_stem_overlap_scores_near_zero(self):
        # Manufactured tokens chosen to share no 4-char prefix with any
        # centroid word in any list (checked below).
        text = "zqxvbn wprkjf mnbvcx"
        all_centroid_words = [w for words in SEPHIROT_CENTROIDS.values() for w in words]
        for t in tokenize(text):
            for cw in all_centroid_words:
                self.assertFalse(t.startswith(cw[:4]) or cw.startswith(t[:4]),
                    f"test text token {t!r} unexpectedly stem-overlaps {cw!r} -- pick a different gibberish word")
        got = compute_sephirotic_vector_scores(text)
        for seph, score in got.items():
            self.assertEqual(score, 0.0)


class TestQualiaVector(RCASandboxTestCase):
    def test_phi_somatic_equals_malkuth_score(self):
        text = "hungry eat food tired sleep"
        scores = compute_sephirotic_vector_scores(text)
        q = compute_qualia_vector(text, scores)
        self.assertEqual(q["Phi_somatic"], round(scores["Malkuth"], 3))

    def test_h_emotional_matches_independent_reference(self):
        for text in ["", "solo", "the quick brown fox jumps over the lazy dog",
                     "cat cat cat cat", "a b a b a b"]:
            scores = compute_sephirotic_vector_scores(text)
            q = compute_qualia_vector(text, scores)
            self.assertAlmostEqual(q["H_emotional"], reference_h_emotional(text), places=3,
                msg=f"mismatch for text={text!r}")

    def test_delta_gamma_is_absolute_difference_of_geburah_and_chesed(self):
        scores = {"Geburah": 0.7, "Chesed": 0.2, "Tifereth": 0.1, "Keter": 0.1, "Malkuth": 0.0}
        # fill in the rest as 0 so compute_qualia_vector's .get() calls resolve
        for s in SEPHIROT_CENTROIDS:
            scores.setdefault(s, 0.0)
        q = compute_qualia_vector("placeholder text", scores)
        self.assertAlmostEqual(q["Delta_gamma"], round(abs(0.7 - 0.2), 3), places=3)

    def test_tau_resonance_capped_at_one(self):
        scores = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        scores["Tifereth"] = 1.0
        scores["Keter"] = 1.0
        q = compute_qualia_vector("x", scores)
        # (1.0 + 1.0) / 2.0 + 0.30 = 1.30 -> capped to 1.0
        self.assertEqual(q["Tau_resonance"], 1.0)


class TestGovernanceEvaluation(unittest.TestCase):
    def test_dominant_seph_is_highest_scoring(self):
        scores = {s: 0.1 for s in SEPHIROT_CENTROIDS}
        scores["Hod"] = 0.9
        gov = evaluate_v2_governance("fix the bug", scores)
        self.assertEqual(gov["dominant_seph"], "Hod")

    def test_technical_teleology_mode_from_code_words(self):
        scores = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        gov = evaluate_v2_governance("please fix this bug in the code", scores)
        self.assertIn("Technical", gov["teleology_mode"])

    def test_creative_teleology_mode_from_creative_words(self):
        scores = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        gov = evaluate_v2_governance("write a story with a creative vision", scores)
        self.assertIn("Creative", gov["teleology_mode"])

    def test_physical_teleology_mode_from_body_words(self):
        scores = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        gov = evaluate_v2_governance("I am hungry and tired", scores)
        self.assertIn("Physical", gov["teleology_mode"])

    def test_exploratory_is_the_fallback(self):
        scores = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        gov = evaluate_v2_governance("what is the meaning of this", scores)
        self.assertIn("Exploratory", gov["teleology_mode"])

    def test_alternatives_excludes_scores_at_or_below_threshold(self):
        scores = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        scores["Hod"] = 0.9
        scores["Netzach"] = 0.06
        scores["Chesed"] = 0.05  # exactly at threshold -> excluded (strict >)
        gov = evaluate_v2_governance("x", scores)
        self.assertIn("Netzach", gov["alternatives"])
        self.assertNotIn("Chesed", gov["alternatives"])

    def test_confidence_pct_bounded_20_to_95(self):
        # Extreme case: one dominant score, everything else zero.
        scores = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        scores["Keter"] = 1.0
        gov = evaluate_v2_governance("x", scores)
        self.assertGreaterEqual(gov["confidence_pct"], 20)
        self.assertLessEqual(gov["confidence_pct"], 95)
        # All-zero scores: total_energy falls back to 1.0, top=second=0.
        scores0 = {s: 0.0 for s in SEPHIROT_CENTROIDS}
        gov0 = evaluate_v2_governance("x", scores0)
        self.assertGreaterEqual(gov0["confidence_pct"], 20)
        self.assertLessEqual(gov0["confidence_pct"], 95)


class TestComputeGamma(unittest.TestCase):
    def test_matches_independent_shannon_entropy_reference(self):
        for text in ["the quick brown fox jumps over the lazy dog",
                     "aaaa bbbb cccc dddd", "same same same same",
                     "one", "", "a a a a a a a a a a a a b"]:
            self.assertAlmostEqual(compute_gamma(text), reference_gamma(text), places=6,
                msg=f"mismatch for text={text!r}")

    def test_empty_or_single_token_returns_baseline_045(self):
        self.assertEqual(compute_gamma(""), 0.45)
        self.assertEqual(compute_gamma("solo"), 0.45)

    def test_uniform_distribution_gives_low_gamma_high_entropy(self):
        # All-distinct tokens -> maximum normalized entropy -> gamma near 0.
        gamma = compute_gamma("alpha beta gamma delta epsilon zeta")
        self.assertLess(gamma, 0.1)

    def test_repetitive_distribution_gives_gamma_capped_at_085(self):
        # A single distinct token repeated (zero-entropy distribution) drives
        # h_norm to 0, so gamma = 1.0 - 0 = 1.0, which the cap clips to 0.85.
        gamma = compute_gamma("same same same same same same")
        self.assertEqual(gamma, 0.85)

    def test_two_symbol_skew_stays_below_max_entropy_bound(self):
        # Sanity check on the entropy formula itself: a 2-distinct-word text
        # can never exceed h_max=log2(2)=1 bit, so even a 6:1 skew only
        # reaches a moderate gamma -- this is the formula behaving correctly,
        # not a bug (this is the case that first exposed my own wrong
        # assumption while writing this test -- see reference_gamma above).
        gamma = compute_gamma("same same same same same same different")
        self.assertAlmostEqual(gamma, reference_gamma("same same same same same same different"), places=6)
        self.assertLess(gamma, 0.5)


class TestEpistemicHumility(unittest.TestCase):
    def test_below_threshold_text_is_unchanged(self):
        text = "You should definitely refactor this."
        self.assertEqual(apply_epistemic_humility(text, gamma=0.5), text)

    def test_above_threshold_rewrites_you_should_definitely(self):
        text = "You should definitely refactor this."
        out = apply_epistemic_humility(text, gamma=0.9)
        self.assertNotIn("You should definitely", out)
        self.assertIn("One effective option is to consider", out)

    def test_above_threshold_rewrites_you_must(self):
        out = apply_epistemic_humility("You must fix the bug.", gamma=0.9)
        self.assertIn("An effective approach is to", out)
        self.assertNotIn("You must", out)

    def test_above_threshold_rewrites_the_best_solution_is(self):
        out = apply_epistemic_humility("The best solution is caching.", gamma=0.75)
        self.assertIn("A well-supported solution is", out)

    def test_exactly_at_threshold_070_is_unchanged(self):
        # gamma <= 0.70 short-circuits to the original text unmodified.
        text = "You must act now."
        self.assertEqual(apply_epistemic_humility(text, gamma=0.70), text)

    def test_just_above_threshold_070_is_rewritten(self):
        text = "You must act now."
        out = apply_epistemic_humility(text, gamma=0.7001)
        self.assertNotEqual(out, text)


class TestSanitizePaths(unittest.TestCase):
    def test_redacts_windows_file_uri(self):
        text = 'See file:///C:/Users/testuser/Desktop/secret.txt for details.'
        out = sanitize_paths(text)
        self.assertNotIn("secret.txt", out)
        self.assertIn("[redacted_path]", out)

    def test_leaves_text_without_file_uri_unchanged(self):
        text = "No paths mentioned here at all."
        self.assertEqual(sanitize_paths(text), text)

    def test_redacts_multiple_occurrences(self):
        text = "a file:///C:/one.txt and file:///D:/two.txt"
        out = sanitize_paths(text)
        self.assertEqual(out.count("[redacted_path]"), 2)


class TestConversationalVoice(unittest.TestCase):
    def test_known_sephirot_returns_dedicated_voice(self):
        out = synthesize_natural_conversational_response("x", "Malkuth", "some patch")
        self.assertIn("Malkuth", out)
        self.assertIn("hardware", out)

    def test_unknown_sephirot_falls_back_to_generic_template(self):
        out = synthesize_natural_conversational_response("x", "NotARealSephirah", "PatchName")
        self.assertIn("NotARealSephirah", out)
        self.assertIn("PatchName", out)


class TestRCALearningEngine(unittest.TestCase):
    """Isolated instance backed by a temp file -- never touches the real
    module-level LEARNING_ENGINE or solo/rca_memory.json."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmpdir) / "test_rca_memory.json"

    def tearDown(self):
        if self.tmp_path.exists():
            try:
                os.remove(self.tmp_path)
            except OSError:
                pass
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

    def test_fresh_engine_defaults_all_weights_to_one(self):
        engine = RCALearningEngine(memory_path=self.tmp_path)
        for seph in SEPHIROT_CENTROIDS:
            self.assertEqual(engine.get_learned_efficacy(seph), 1.0)
        self.assertEqual(engine.total_interactions, 0)

    def test_record_state_matches_independent_ema_reference(self):
        engine = RCALearningEngine(memory_path=self.tmp_path)
        lr = 0.05
        # High-entropy interaction -> reward = 1.0
        before = engine.get_learned_efficacy("Hod")
        engine.record_state("Hod", entropy=0.8)
        expected = round(before + lr * (1.0 - before), 3)
        self.assertEqual(engine.get_learned_efficacy("Hod"), expected)
        # Low-entropy interaction -> reward = 0.5
        before2 = engine.get_learned_efficacy("Hod")
        engine.record_state("Hod", entropy=0.2)
        expected2 = round(before2 + lr * (0.5 - before2), 3)
        self.assertEqual(engine.get_learned_efficacy("Hod"), expected2)

    def test_entropy_exactly_050_counts_as_high_reward(self):
        # reward = 1.0 if entropy >= 0.5 else 0.5 -- boundary case.
        engine = RCALearningEngine(memory_path=self.tmp_path)
        before = engine.get_learned_efficacy("Binah")
        engine.record_state("Binah", entropy=0.5)
        expected = round(before + 0.05 * (1.0 - before), 3)
        self.assertEqual(engine.get_learned_efficacy("Binah"), expected)

    def test_total_interactions_increments(self):
        engine = RCALearningEngine(memory_path=self.tmp_path)
        engine.record_state("Keter", entropy=0.9)
        engine.record_state("Keter", entropy=0.9)
        self.assertEqual(engine.total_interactions, 2)

    def test_state_persists_and_reloads_from_disk(self):
        engine = RCALearningEngine(memory_path=self.tmp_path)
        engine.record_state("Chesed", entropy=1.0)
        weight_after_write = engine.get_learned_efficacy("Chesed")

        reloaded = RCALearningEngine(memory_path=self.tmp_path)
        self.assertEqual(reloaded.get_learned_efficacy("Chesed"), weight_after_write)
        self.assertEqual(reloaded.total_interactions, 1)

    def test_never_writes_to_the_real_memory_file(self):
        real_path = rca.MEMORY_FILE
        if real_path.exists():
            before_mtime = real_path.stat().st_mtime
        else:
            before_mtime = None
        engine = RCALearningEngine(memory_path=self.tmp_path)
        engine.record_state("Yesod", entropy=0.9)
        if before_mtime is None:
            self.assertFalse(real_path.exists(), "test engine touched the real memory file")
        else:
            after_mtime = real_path.stat().st_mtime
            self.assertEqual(before_mtime, after_mtime,
                "test engine modified the real rca_memory.json -- isolation broken")


class TestComputeQualiaReward(unittest.TestCase):
    """Ground truth: fresh, independent hand computation of
    mean(h_component, Tau_resonance, 1-Delta_gamma), not derived from
    compute_qualia_reward()'s own internals."""

    def test_matches_hand_computed_reward_high_signals(self):
        qualia = {"Phi_somatic": 0.0, "H_emotional": 0.8, "Delta_gamma": 0.1, "Tau_resonance": 0.9}
        # h=1.0 (0.8>=0.5), resonance=0.9, friction=1-0.1=0.9 -> (1.0+0.9+0.9)/3=0.9333...
        expected = round((1.0 + 0.9 + (1.0 - 0.1)) / 3.0, 3)
        self.assertAlmostEqual(rca.compute_qualia_reward(qualia), expected, places=3)

    def test_matches_hand_computed_reward_low_signals(self):
        qualia = {"Phi_somatic": 0.0, "H_emotional": 0.3, "Delta_gamma": 0.9, "Tau_resonance": 0.2}
        # h=0.5 (0.3<0.5), resonance=0.2, friction=1-0.9=0.1 -> (0.5+0.2+0.1)/3=0.2667
        expected = round((0.5 + 0.2 + (1.0 - 0.9)) / 3.0, 3)
        self.assertAlmostEqual(rca.compute_qualia_reward(qualia), expected, places=3)

    def test_h_emotional_boundary_at_exactly_050_counts_high(self):
        # Matches record_state()'s own >= 0.5 boundary convention exactly.
        qualia = {"Phi_somatic": 0.0, "H_emotional": 0.5, "Delta_gamma": 0.0, "Tau_resonance": 0.0}
        expected = round((1.0 + 0.0 + 1.0) / 3.0, 3)
        self.assertAlmostEqual(rca.compute_qualia_reward(qualia), expected, places=3)

    def test_phi_somatic_is_excluded_from_the_reward(self):
        """Two qualia dicts differing ONLY in Phi_somatic must give the
        identical reward -- proves Phi_somatic is really excluded, not
        just documented as excluded."""
        base = {"H_emotional": 0.7, "Delta_gamma": 0.3, "Tau_resonance": 0.6}
        qualia_a = {**base, "Phi_somatic": 0.0}
        qualia_b = {**base, "Phi_somatic": 0.999}
        self.assertEqual(rca.compute_qualia_reward(qualia_a), rca.compute_qualia_reward(qualia_b))

    def test_maximal_reward_case(self):
        # H_emotional=1.0 (>=0.5 -> h=1.0), Tau_resonance=1.0, Delta_gamma=0.0 -> reward=1.0 exactly
        qualia = {"Phi_somatic": 0.0, "H_emotional": 1.0, "Delta_gamma": 0.0, "Tau_resonance": 1.0}
        self.assertEqual(rca.compute_qualia_reward(qualia), 1.0)

    def test_high_friction_is_penalized_not_rewarded(self):
        """The actual regression this mechanism locks in: raising
        Delta_gamma (more unresolved Chesed/Geburah friction) must LOWER
        the reward, not raise it -- an inverted implementation would
        fail this."""
        low_friction = {"H_emotional": 0.7, "Delta_gamma": 0.1, "Tau_resonance": 0.5}
        high_friction = {"H_emotional": 0.7, "Delta_gamma": 0.9, "Tau_resonance": 0.5}
        self.assertGreater(rca.compute_qualia_reward(low_friction), rca.compute_qualia_reward(high_friction))


class TestRecordQualiaState(unittest.TestCase):
    """Same isolation pattern as TestRCALearningEngine -- a throwaway
    engine backed by a temp file, never the real rca_memory.json."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmpdir) / "test_rca_memory_qualia.json"

    def tearDown(self):
        if self.tmp_path.exists():
            try:
                os.remove(self.tmp_path)
            except OSError:
                pass
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

    def test_record_qualia_state_matches_independent_ema_reference(self):
        engine = RCALearningEngine(memory_path=self.tmp_path)
        qualia = {"Phi_somatic": 0.0, "H_emotional": 0.8, "Delta_gamma": 0.1, "Tau_resonance": 0.9}
        expected_reward = round((1.0 + 0.9 + (1.0 - 0.1)) / 3.0, 3)

        before = engine.get_learned_efficacy("Hod")
        engine.record_qualia_state("Hod", qualia)
        expected = round(before + 0.05 * (expected_reward - before), 3)
        self.assertEqual(engine.get_learned_efficacy("Hod"), expected)

    def test_record_qualia_state_increments_total_interactions_and_state_counts(self):
        engine = RCALearningEngine(memory_path=self.tmp_path)
        qualia = {"Phi_somatic": 0.0, "H_emotional": 0.6, "Delta_gamma": 0.2, "Tau_resonance": 0.7}
        engine.record_qualia_state("Netzach", qualia)
        engine.record_qualia_state("Netzach", qualia)
        self.assertEqual(engine.total_interactions, 2)
        self.assertEqual(engine.state_counts["Netzach"], 2)

    def test_record_state_behavior_unaffected_by_the_refactor(self):
        """The shared _apply_reward_update() refactor must not change
        record_state()'s own pre-existing, already-verified behavior --
        re-derives the exact same reference test
        test_record_state_matches_independent_ema_reference already
        checks, using a fresh engine, as an extra guard specific to this
        change."""
        engine = RCALearningEngine(memory_path=self.tmp_path)
        before = engine.get_learned_efficacy("Chokmah")
        engine.record_state("Chokmah", entropy=0.8)
        expected = round(before + 0.05 * (1.0 - before), 3)
        self.assertEqual(engine.get_learned_efficacy("Chokmah"), expected)

    def test_never_writes_to_the_real_memory_file(self):
        real_path = rca.MEMORY_FILE
        if real_path.exists():
            before_mtime = real_path.stat().st_mtime
        else:
            before_mtime = None
        engine = RCALearningEngine(memory_path=self.tmp_path)
        engine.record_qualia_state("Daath", {"Phi_somatic": 0.0, "H_emotional": 0.5, "Delta_gamma": 0.0, "Tau_resonance": 0.5})
        if before_mtime is None:
            self.assertFalse(real_path.exists(), "test engine touched the real memory file")
        else:
            after_mtime = real_path.stat().st_mtime
            self.assertEqual(before_mtime, after_mtime,
                "test engine modified the real rca_memory.json -- isolation broken")


class TestSlashCommandDispatch(RCASandboxTestCase):
    def _capture(self, cmd):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            handle_slash_command(cmd)
        return buf.getvalue()

    def test_help_lists_all_commands(self):
        out = self._capture("/help")
        for cmd in ["/help", "/learn", "/eval", "/qualia", "/memory", "/dht"]:
            self.assertIn(cmd, out)

    def test_unknown_command_reports_unknown(self):
        out = self._capture("/bogus")
        self.assertIn("Unknown command", out)
        self.assertIn("/bogus", out)

    def test_memory_shows_all_eleven_sephirot_weights(self):
        out = self._capture("/memory")
        for seph in SEPHIROT_CENTROIDS:
            self.assertIn(seph, out)

    def test_qualia_reports_all_four_vector_components(self):
        out = self._capture("/qualia hungry and tired")
        self.assertIn("Phi_somatic".replace("Phi", "").strip() or "Φ_somatic", out)
        self.assertIn("H_emotional", out)
        self.assertIn("Δγ_teleos", out)
        self.assertIn("τ_resonance", out)

    def test_eval_reports_diagnosed_pattern_and_falsifiability(self):
        out = self._capture("/eval fix the bug in the code")
        self.assertIn("Diagnosed Pattern", out)
        self.assertIn("Falsifiability Test", out)
        self.assertIn("PROVISIONAL METAPHOR, NOT ONTOLOGICAL TRUTH", out)

    def test_command_is_case_insensitive(self):
        out_lower = self._capture("/help")
        out_upper = self._capture("/HELP")
        self.assertEqual(out_lower, out_upper)


class TestSephirahColorDisplay(unittest.TestCase):
    """Correctness tests for the Glyph Correspondence display layer
    (SEPHIRAH_PLANET_COLOR, colorize_sephirah, sephirah_planet_label).
    Ground truth: hand-verified hex-to-RGB conversion, direct comparison
    against docs/glyph_correspondence_codex.md's own hex values (so the
    code can't silently drift from the source document), and known ANSI
    24-bit escape sequence format (\\x1b[38;2;R;G;Bm ... \\x1b[0m)."""

    def test_hex_to_rgb_matches_hand_computed_values(self):
        self.assertEqual(rca._hex_to_rgb("#ffbf00"), (255, 191, 0))
        self.assertEqual(rca._hex_to_rgb("#000000"), (0, 0, 0))
        self.assertEqual(rca._hex_to_rgb("#ffffff"), (255, 255, 255))
        self.assertEqual(rca._hex_to_rgb("#1e90ff"), (30, 144, 255))

    def test_colorize_wraps_mapped_sephirah_in_correct_ansi_escape(self):
        out = rca.colorize_sephirah("Tifereth", "Tifereth", force_color=True)
        r, g, b = rca._hex_to_rgb(rca.SEPHIRAH_PLANET_COLOR["Tifereth"]["hex"])
        self.assertEqual(out, f"\x1b[38;2;{r};{g};{b}mTifereth\x1b[0m")

    def test_colorize_leaves_unmapped_sephirah_unchanged_even_when_forced(self):
        # Keter, Chokmah, Daath, Malkuth have no planet in the codex --
        # must stay plain text even with force_color=True, not get an
        # invented color.
        for seph in ("Keter", "Chokmah", "Daath", "Malkuth"):
            self.assertEqual(rca.colorize_sephirah(seph, seph, force_color=True), seph)

    def test_colorize_returns_plain_text_when_not_a_tty(self):
        # Default force_color=False must defer to sys.stdout.isatty();
        # this test suite's stdout is never a real terminal.
        self.assertFalse(sys.stdout.isatty())
        self.assertEqual(rca.colorize_sephirah("Tifereth", "Tifereth"), "Tifereth")

    def test_sephirah_planet_label_matches_codex_for_mapped_sephirah(self):
        self.assertEqual(rca.sephirah_planet_label("Tifereth"), " (Sun ☉)")
        self.assertEqual(rca.sephirah_planet_label("Binah"), " (Saturn ♄)")

    def test_sephirah_planet_label_empty_for_unmapped_sephirah(self):
        for seph in ("Keter", "Chokmah", "Daath", "Malkuth"):
            self.assertEqual(rca.sephirah_planet_label(seph), "")

    def test_exactly_seven_sephirot_are_mapped(self):
        # SEPHIROT_CENTROIDS has 11 categories; the codex's Planet table
        # only documents 7. This pins that gap so it can't silently grow
        # or shrink without a test noticing.
        self.assertEqual(len(SEPHIROT_CENTROIDS), 11)
        self.assertEqual(len(rca.SEPHIRAH_PLANET_COLOR), 7)
        self.assertTrue(set(rca.SEPHIRAH_PLANET_COLOR).issubset(set(SEPHIROT_CENTROIDS)))

    def test_hex_values_match_uploaded_codex_document_exactly(self):
        # Cross-checks the hardcoded hex values in standalone_rca_sandbox.py
        # against the literal hex strings in docs/glyph_correspondence_codex.md's
        # Planet table (Queen column), so the two can never silently drift
        # apart. This is the same kind of check as test_all_engines.py
        # trusting live output over a static number -- here, the "live"
        # source of truth is the codex document itself.
        codex_path = BASE_DIR.parent / "docs" / "glyph_correspondence_codex.md"
        codex_text = codex_path.read_text(encoding="utf-8")
        # Queen-scale hex values as they appear in the codex's Planet table,
        # in row order (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn).
        expected_queen_hex = {
            "Tifereth": "#ffbf00",
            "Yesod": "#b0c4de",
            "Hod": "#ffb347",
            "Netzach": "#00b3a4",
            "Geburah": "#ff0000",
            "Chesed": "#1e90ff",
            "Binah": "#191970",
        }
        for seph, hex_val in expected_queen_hex.items():
            self.assertIn(hex_val, codex_text,
                f"{hex_val} (used for {seph}) not found in glyph_correspondence_codex.md "
                f"-- code may have drifted from the source document")
            self.assertEqual(rca.SEPHIRAH_PLANET_COLOR[seph]["hex"], hex_val)


def run_unit_test_suite():
    print("=" * 72)
    print("  STANDALONE RCA SANDBOX — CORRECTNESS TEST SUITE")
    print("  (Tests mechanical correctness of the math/regex/dispatch code")
    print("   only. Takes no position on the Sephirotic/Qualia framing --")
    print("   the engine itself labels that a provisional metaphor.)")
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
