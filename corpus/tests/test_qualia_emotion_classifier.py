#!/usr/bin/env python3
"""
test_qualia_emotion_classifier.py
Correctness verification for qualia_emotion_classifier.py per
TESTING_STANDARD.md.

Ground truth strategy: this module's NEW logic is the bucketing
(emotion_planet/emotion_sephirah/emotions_by_sephirah), the two distance
measures (qualia_distance, hex_lightness), and the two nearest-neighbor
selections (nearest_sephirah, nearest_emotion_in_bucket) built on top of
them. compute_sephirotic_vector_scores()/compute_qualia_vector()
themselves are pre-existing and already covered by
test_standalone_rca_sandbox.py -- this file takes their output as a
given input where it needs one, the same way
test_ddpg_dynamic_geburah_gamma.py took actor pre-activation logits as a
given input rather than re-deriving the whole network by hand.

Where this file DOES hand-verify from scratch: RGB->HSL lightness (a
standard, calculator-checkable transform) and Euclidean distance over 4
numbers (plain arithmetic).

LEARNING_ENGINE is monkeypatched to a fresh, temp-file-backed instance
(weights fixed at 1.0) for every test in this file that touches
sephirah_reference_qualia() or the classify_* pipeline, so results don't
depend on this repo's actual rca_memory.json (which drifts with real
usage) -- same isolation pattern test_standalone_rca_sandbox.py already
uses for RCALearningEngine.
"""

import sys
import math
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import standalone_rca_sandbox as rca
import qualia_emotion_classifier as qec
from glyph_emotion_codex import load_emotion_codex


class IsolatedEngineTestCase(unittest.TestCase):
    """Swaps rca.LEARNING_ENGINE for a fresh, temp-backed instance (all
    weights default to 1.0) for the duration of each test, restoring the
    original afterward -- keeps this file's expected numbers independent
    of whatever this repo's live rca_memory.json currently contains."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._real_engine = rca.LEARNING_ENGINE
        rca.LEARNING_ENGINE = rca.RCALearningEngine(memory_path=Path(self._tmpdir) / "test_memory.json")

    def tearDown(self):
        rca.LEARNING_ENGINE = self._real_engine
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)


class TestEmotionPlanetParsing(unittest.TestCase):
    """Hand-checked against the literal Esoteric column strings in
    docs/glyph_correspondence_codex.md."""

    def test_sun_parses(self):
        self.assertEqual(qec.emotion_planet("☉ Sun – Golden Yellow \U0001F702"), "Sun")

    def test_mars_parses(self):
        self.assertEqual(qec.emotion_planet("♂ Mars – Red \U0001F702"), "Mars")

    def test_uranus_parses(self):
        self.assertEqual(qec.emotion_planet("♅ Uranus – Violet ☉"), "Uranus")

    def test_spirit_parses(self):
        self.assertEqual(qec.emotion_planet("☉ Spirit – Violet"), "Spirit")

    def test_unrecognized_returns_none(self):
        self.assertIsNone(qec.emotion_planet("no planet name in here at all"))


class TestEmotionSephirahMapping(unittest.TestCase):
    def test_sun_maps_to_tifereth(self):
        self.assertEqual(qec.emotion_sephirah("☉ Sun – Golden Yellow \U0001F702"), "Tifereth")

    def test_mars_maps_to_geburah(self):
        self.assertEqual(qec.emotion_sephirah("♂ Mars – Red \U0001F702"), "Geburah")

    def test_jupiter_maps_to_chesed_even_though_unused(self):
        # Jupiter never actually appears in the codex (see
        # TestEmotionsBySephirah below), but the PLANET_TO_SEPHIRAH
        # mapping itself is still structurally correct if given it --
        # this pins that down independently of the (separate) fact that
        # no row uses it.
        self.assertEqual(qec.emotion_sephirah("♃ Jupiter – Violet"), "Chesed")

    def test_uranus_maps_to_none(self):
        self.assertIsNone(qec.emotion_sephirah("♅ Uranus – Violet ☉"))

    def test_spirit_maps_to_none(self):
        self.assertIsNone(qec.emotion_sephirah("☉ Spirit – Violet"))


class TestEmotionsBySephirah(unittest.TestCase):
    """Ground truth: the real docs/glyph_correspondence_codex.md table,
    read directly -- not a copy."""

    @classmethod
    def setUpClass(cls):
        cls.rows = load_emotion_codex()
        cls.buckets, cls.uncovered = qec.emotions_by_sephirah(cls.rows)

    def test_all_100_rows_accounted_for(self):
        total = sum(len(v) for v in self.buckets.values()) + len(self.uncovered)
        self.assertEqual(total, 100)

    def test_chesed_bucket_is_genuinely_empty(self):
        # Confirmed by grep against the source document: "Jupiter" does
        # not appear anywhere in the Esoteric column of any of the 100
        # rows. This is a real fact about the document, not a bug.
        self.assertEqual(self.buckets["Chesed"], [])

    def test_madness_and_chaos_are_uncovered(self):
        uncovered_names = {r["name"] for r in self.uncovered}
        self.assertEqual(uncovered_names, {"Madness", "Chaos"})

    def test_uncovered_rows_are_exactly_uranus_and_spirit(self):
        for row in self.uncovered:
            planet = qec.emotion_planet(row["esoteric"])
            self.assertIn(planet, ("Uranus", "Spirit"))

    def test_geburah_bucket_contains_anger(self):
        names = {r["name"] for r in self.buckets["Geburah"]}
        self.assertIn("Anger", names)

    def test_tifereth_bucket_contains_ecstasy(self):
        names = {r["name"] for r in self.buckets["Tifereth"]}
        self.assertIn("Ecstasy", names)

    def test_every_covered_sephirah_except_chesed_is_nonempty(self):
        for seph in rca.SEPHIRAH_PLANET_COLOR:
            if seph == "Chesed":
                continue
            self.assertGreater(len(self.buckets[seph]), 0, f"{seph} unexpectedly has no emotions")


class TestHexLightness(unittest.TestCase):
    """RGB->HSL lightness is a standard, calculator-checkable transform:
    L = (max(r,g,b) + min(r,g,b)) / 2 on the [0,1]-normalized channels."""

    def test_white_is_maximally_light(self):
        self.assertAlmostEqual(qec.hex_lightness("#ffffff"), 1.0, places=6)

    def test_black_is_minimally_light(self):
        self.assertAlmostEqual(qec.hex_lightness("#000000"), 0.0, places=6)

    def test_pure_red_is_exactly_half(self):
        # r=1, g=0, b=0 -> (max+min)/2 = (1+0)/2 = 0.5, by hand.
        self.assertAlmostEqual(qec.hex_lightness("#ff0000"), 0.5, places=6)

    def test_mid_gray_hand_computed(self):
        # #808080 -> r=g=b=128/255 -> max=min so L = 128/255 exactly.
        expected = 128 / 255
        self.assertAlmostEqual(qec.hex_lightness("#808080"), expected, places=6)

    def test_ecstasy_is_lighter_than_annihilation(self):
        # Spot check against the actual codex data: row 1 (Ecstasy,
        # #ffef8a) vs row 100 (Annihilation, #000000).
        self.assertGreater(qec.hex_lightness("#ffef8a"), qec.hex_lightness("#000000"))


class TestQualiaDistance(unittest.TestCase):
    def test_identical_vectors_have_zero_distance(self):
        a = {"Phi_somatic": 0.3, "H_emotional": 0.7, "Delta_gamma": 0.1, "Tau_resonance": 0.9}
        self.assertEqual(qec.qualia_distance(a, dict(a)), 0.0)

    def test_hand_computed_distance(self):
        # a vs b differ only in Delta_gamma (1.0 vs 0.0) and Tau_resonance
        # (0.3 vs 0.875): sqrt(0^2 + 0^2 + 1.0^2 + (-0.575)^2)
        #             = sqrt(1 + 0.330625) = sqrt(1.330625) ~= 1.15353
        a = {"Phi_somatic": 0.0, "H_emotional": 1.0, "Delta_gamma": 1.0, "Tau_resonance": 0.3}
        b = {"Phi_somatic": 0.0, "H_emotional": 1.0, "Delta_gamma": 0.0, "Tau_resonance": 0.875}
        expected = math.sqrt(1.0 ** 2 + 0.575 ** 2)
        self.assertAlmostEqual(qec.qualia_distance(a, b), expected, places=6)
        self.assertAlmostEqual(qec.qualia_distance(a, b), 1.15353, places=4)


class TestSephirahReferenceQualia(IsolatedEngineTestCase):
    """With LEARNING_ENGINE weights fixed at 1.0 (see
    IsolatedEngineTestCase), these values are exactly reproducible --
    confirmed by direct computation before this test was written, and
    now locked in so a future change to compute_qualia_vector() or
    SEPHIROT_CENTROIDS surfaces here."""

    def test_tifereth_self_reference(self):
        q = qec.sephirah_reference_qualia("Tifereth")
        self.assertEqual(q["Delta_gamma"], 0.0)
        self.assertEqual(q["Tau_resonance"], 0.875)

    def test_geburah_and_chesed_self_references_collide(self):
        # A discovered, honest limitation, not hidden: Delta_gamma is
        # abs(Geburah_score - Chesed_score), so Geburah's own text
        # (Geburah=1.0, Chesed=0.0) and Chesed's own text (Geburah=0.0,
        # Chesed=1.0) produce the IDENTICAL Delta_gamma=1.0 -- the sign
        # of the imbalance is thrown away by abs(). Combined with
        # H_emotional=1.0 and Tau_resonance=0.3 also matching for both
        # (neither text touches Tifereth/Keter words), their full
        # reference vectors are exactly equal.
        geburah_ref = qec.sephirah_reference_qualia("Geburah")
        chesed_ref = qec.sephirah_reference_qualia("Chesed")
        self.assertEqual(geburah_ref, chesed_ref)
        self.assertEqual(geburah_ref["Delta_gamma"], 1.0)

    def test_all_seven_references_are_computable(self):
        refs = qec.all_sephirah_references()
        self.assertEqual(set(refs.keys()), set(rca.SEPHIRAH_PLANET_COLOR.keys()))
        for seph, q in refs.items():
            for dim in qec.QUALIA_DIMS:
                self.assertIn(dim, q)


class TestNearestSephirah(IsolatedEngineTestCase):
    def test_excludes_chesed_even_when_it_would_be_the_exact_match(self):
        # Chesed's own reference vector (see test above) is identical to
        # Geburah's -- but Chesed has zero emotions in the codex, so it
        # must never be returned, and Geburah (the only other exact
        # match, since they collide) should be returned instead.
        buckets, _ = qec.emotions_by_sephirah()
        chesed_like_qualia = {"Phi_somatic": 0.0, "H_emotional": 1.0, "Delta_gamma": 1.0, "Tau_resonance": 0.3}
        result = qec.nearest_sephirah(chesed_like_qualia, buckets)
        self.assertNotEqual(result, "Chesed")
        self.assertEqual(result, "Geburah")

    def test_tifereth_like_input_routes_to_tifereth(self):
        buckets, _ = qec.emotions_by_sephirah()
        tifereth_like = {"Phi_somatic": 0.0, "H_emotional": 1.0, "Delta_gamma": 0.0, "Tau_resonance": 0.875}
        self.assertEqual(qec.nearest_sephirah(tifereth_like, buckets), "Tifereth")

    def test_raises_if_no_candidates_have_emotions(self):
        empty_buckets = {seph: [] for seph in rca.SEPHIRAH_PLANET_COLOR}
        with self.assertRaises(ValueError):
            qec.nearest_sephirah({"Phi_somatic": 0, "H_emotional": 0, "Delta_gamma": 0, "Tau_resonance": 0}, empty_buckets)


class TestNearestEmotionInBucket(unittest.TestCase):
    def test_hand_constructed_bucket(self):
        # Two synthetic rows: one very light, one very dark. Input
        # Tau_resonance closer to the light one should win.
        bucket = [
            {"name": "Light One", "hex": "#ffffff", "index": 1, "description": ""},
            {"name": "Dark One", "hex": "#000000", "index": 2, "description": ""},
        ]
        self.assertEqual(qec.nearest_emotion_in_bucket(0.9, bucket)["name"], "Light One")
        self.assertEqual(qec.nearest_emotion_in_bucket(0.1, bucket)["name"], "Dark One")
        # Exactly at the midpoint (0.5), Python's min() keeps the FIRST
        # tie -- pins down that behavior explicitly rather than leaving
        # it implicit.
        self.assertEqual(qec.nearest_emotion_in_bucket(0.5, bucket)["name"], "Light One")

    def test_raises_on_empty_bucket(self):
        with self.assertRaises(ValueError):
            qec.nearest_emotion_in_bucket(0.5, [])


class TestClassifyPipeline(IsolatedEngineTestCase):
    def test_classify_qualia_returns_well_formed_result(self):
        qualia = {"Phi_somatic": 0.0, "H_emotional": 1.0, "Delta_gamma": 0.0, "Tau_resonance": 0.875}
        result = qec.classify_qualia(qualia)
        for key in ("sephirah", "planet", "emotion", "index", "hex", "description"):
            self.assertIn(key, result)
        self.assertNotEqual(result["sephirah"], "Chesed")
        self.assertTrue(1 <= result["index"] <= 100)

    def test_classify_text_is_deterministic(self):
        text = "balance harmony integration beauty synthesis centered heart peace"
        first = qec.classify_text(text)
        second = qec.classify_text(text)
        self.assertEqual(first["emotion"], second["emotion"])
        self.assertEqual(first["index"], second["index"])

    def test_classify_text_never_returns_madness_or_chaos(self):
        # Madness/Chaos are explicitly uncovered (Uranus/Spirit) -- no
        # classification path should ever be able to reach them.
        samples = [
            "rigid stuck restriction judgment severe harsh strict cut",
            "expansion flow abundance grace generous kindness mercy",
            "the cat sat on the mat",
            "hungry tired sleep physical body pain exhausted",
        ]
        for text in samples:
            result = qec.classify_text(text)
            self.assertNotIn(result["emotion"], ("Madness", "Chaos"))


def run_unit_test_suite():
    print("=" * 72)
    print("  QUALIA EMOTION CLASSIFIER -- CORRECTNESS TEST SUITE")
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
