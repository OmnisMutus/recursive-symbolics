"""
test_engine_composition_loop.py

engine_composition_loop.py is a measurement script (like
ddpg_training_convergence_study.py), not a TESTING_STANDARD.md
correctness claim -- "does the composed loop close" has no single right
answer to assert VERIFIED/FAILED against, and it isn't registered in
test_all_engines.py's count for that reason (same reasoning documented
in docs/ddpg_training_convergence_report.md's Limitations section).

What real bugs COULD exist, and are worth locking down here, is the
bridge wiring itself: does SEPHIRAH_TO_MAP actually cover every real
sephirah, does the Da'ath map actually diverge, do the contraction maps
actually converge, does describe_attractor() actually produce three
distinct strings, and does the meta-classification re-encoding actually
detect a fixed point when the label sequence obviously has one. These
are ordinary correctness properties of new code, independent of what the
composed experiment's results turn out to mean.
"""

import unittest

import numpy as np

import sys
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import recursive_attractor_engine as rae
import engine_composition_loop as ecl


class TestSephirahToMapCoverage(unittest.TestCase):
    def test_every_real_sephirah_is_mapped(self):
        import standalone_rca_sandbox as rca
        self.assertEqual(set(ecl.SEPHIRAH_TO_MAP.keys()), set(rca.SEPHIROT_CENTROIDS.keys()))

    def test_sephirah_order_matches_real_centroids(self):
        import standalone_rca_sandbox as rca
        self.assertEqual(set(ecl.SEPHIRAH_ORDER), set(rca.SEPHIROT_CENTROIDS.keys()))
        self.assertEqual(len(ecl.SEPHIRAH_ORDER), len(set(ecl.SEPHIRAH_ORDER)))  # no duplicates


class TestMappedDynamicalSystemsBehaveAsDocumented(unittest.TestCase):
    """Confirms each precedented mapping actually produces the regime the
    module docstring claims it does -- these are properties of
    recursive_attractor_engine.py (already VERIFIED elsewhere) applied to
    THIS script's chosen parameters, so what's being checked is that the
    parameters were chosen correctly, not re-verifying the engine itself."""

    def test_daath_map_genuinely_diverges(self):
        name, F, S0, E = ecl.SEPHIRAH_TO_MAP["Daath"]
        with self.assertRaises(rae.AbyssException):
            rae.iterate(F, S0, E, n_steps=60)

    def test_geburah_map_converges_to_fixed_point(self):
        name, F, S0, E = ecl.SEPHIRAH_TO_MAP["Geburah"]
        result = rae.classify_trajectory(rae.iterate(F, S0, E, n_steps=60))
        self.assertEqual(result.kind, rae.AttractorType.FIXED_POINT)

    def test_tifereth_map_converges_to_fixed_point(self):
        name, F, S0, E = ecl.SEPHIRAH_TO_MAP["Tifereth"]
        result = rae.classify_trajectory(rae.iterate(F, S0, E, n_steps=60))
        self.assertEqual(result.kind, rae.AttractorType.FIXED_POINT)

    def test_chesed_constant_map_converges_in_one_step(self):
        name, F, S0, E = ecl.SEPHIRAH_TO_MAP["Chesed"]
        result = rae.classify_trajectory(rae.iterate(F, S0, E, n_steps=60))
        self.assertEqual(result.kind, rae.AttractorType.FIXED_POINT)
        self.assertAlmostEqual(float(result.fixed_point[0]), float(E[0]), places=6)

    def test_netzach_logistic_map_is_genuinely_period_2(self):
        name, F, S0, E = ecl.SEPHIRAH_TO_MAP["Netzach"]
        result = rae.classify_trajectory(rae.iterate(F, S0, E, n_steps=200))
        self.assertEqual(result.kind, rae.AttractorType.LIMIT_CYCLE)
        self.assertEqual(result.period, 2)

    def test_neutral_default_map_is_shared_by_all_six_unprecedented_sephirot(self):
        unprecedented = ["Keter", "Chokmah", "Binah", "Hod", "Yesod", "Malkuth"]
        maps = [ecl.SEPHIRAH_TO_MAP[s][0] for s in unprecedented]  # the name string
        self.assertEqual(len(set(maps)), 1, "all six should share literally the same map, by design")


class TestDescribeAttractorProducesDistinctText(unittest.TestCase):
    def _make(self, kind, period=None):
        return type("R", (), {"kind": kind, "period": period})()

    def test_three_attractor_types_produce_three_distinct_descriptions(self):
        texts = {
            ecl.describe_attractor(self._make(rae.AttractorType.FIXED_POINT)),
            ecl.describe_attractor(self._make(rae.AttractorType.LIMIT_CYCLE, period=2)),
            ecl.describe_attractor(self._make(rae.AttractorType.BOUNDED_APERIODIC)),
        }
        self.assertEqual(len(texts), 3)

    def test_limit_cycle_description_mentions_the_real_period(self):
        text5 = ecl.describe_attractor(self._make(rae.AttractorType.LIMIT_CYCLE, period=5))
        self.assertIn("period 5", text5)


class TestMetaClassificationDetectsObviousPatterns(unittest.TestCase):
    """The label-sequence re-encoding is just classify_trajectory() again,
    already VERIFIED elsewhere -- this only checks the encoding step
    (sephirah name -> fixed integer index) is wired correctly."""

    def test_repeated_label_is_detected_as_fixed_point(self):
        encoded = [np.array([float(ecl._SEPH_TO_INDEX[s])]) for s in ["Geburah", "Geburah", "Geburah"]]
        result = rae.classify_trajectory(encoded)
        self.assertEqual(result.kind, rae.AttractorType.FIXED_POINT)

    def test_alternating_labels_detected_as_period_2_cycle(self):
        encoded = [np.array([float(ecl._SEPH_TO_INDEX[s])]) for s in ["Chesed", "Binah", "Chesed", "Binah"]]
        result = rae.classify_trajectory(encoded)
        self.assertEqual(result.kind, rae.AttractorType.LIMIT_CYCLE)
        self.assertEqual(result.period, 2)


class TestCustomTemplatesParameter(unittest.TestCase):
    """The `templates` override on describe_attractor()/run_one_cycle()/
    run_loop_from() was added specifically so
    engine_composition_robustness_check.py could test alternative wording
    without ever mutating DEFAULT_TEMPLATES. These checks confirm the
    override actually takes effect and that omitting it reproduces the
    original, already-reported default behavior exactly."""

    def test_custom_fixed_point_template_is_actually_used(self):
        result = type("R", (), {"kind": type(rae.AttractorType.FIXED_POINT), "period": None})()
        result.kind = rae.AttractorType.FIXED_POINT
        custom = {**ecl.DEFAULT_TEMPLATES, "FIXED_POINT": "CUSTOM MARKER TEXT"}
        self.assertEqual(ecl.describe_attractor(result, templates=custom), "CUSTOM MARKER TEXT")

    def test_omitting_templates_reproduces_default_exactly(self):
        result = type("R", (), {"kind": rae.AttractorType.FIXED_POINT, "period": None})()
        self.assertEqual(ecl.describe_attractor(result), ecl.DEFAULT_TEMPLATES["FIXED_POINT"])

    def test_limit_cycle_template_still_formats_the_real_period(self):
        result = type("R", (), {"kind": rae.AttractorType.LIMIT_CYCLE, "period": 7})()
        custom = {**ecl.DEFAULT_TEMPLATES, "LIMIT_CYCLE": "period is {period} exactly"}
        self.assertEqual(ecl.describe_attractor(result, templates=custom), "period is 7 exactly")

    def test_default_templates_dict_is_never_mutated_by_a_custom_run(self):
        before = dict(ecl.DEFAULT_TEMPLATES)
        result = type("R", (), {"kind": rae.AttractorType.FIXED_POINT, "period": None})()
        custom = {**ecl.DEFAULT_TEMPLATES, "FIXED_POINT": "something else entirely"}
        ecl.describe_attractor(result, templates=custom)
        self.assertEqual(ecl.DEFAULT_TEMPLATES, before)


class TestLearningWeightsPinnedAndRestored(unittest.TestCase):
    def test_main_restores_original_transition_weights(self):
        import standalone_rca_sandbox as rca
        before = dict(rca.LEARNING_ENGINE.transition_weights)
        ecl.main()
        after = dict(rca.LEARNING_ENGINE.transition_weights)
        self.assertEqual(before, after, "main() must restore weights even though it pins them during the run")


if __name__ == "__main__":
    unittest.main(verbosity=2)
