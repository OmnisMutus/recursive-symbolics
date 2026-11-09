#!/usr/bin/env python3
"""
test_telemetry_analyzer.py
Independent correctness test for telemetry_analyzer.py: calc_symbolic_entropy,
classify_latency, classify_entropy, and main()'s file-based aggregation.

IMPORTANT, DOCUMENTED DISTINCTION: calc_symbolic_entropy() here uses a
DIFFERENT formula than symbolic_debugger.py's calculate_entropy() (see
test_symbolic_debugger.py) and standalone_rca_sandbox.py's H_emotional
(unique ADJACENT PAIRS / total pairs -- a bigram-diversity measure).
telemetry_analyzer.calc_symbolic_entropy() is unique WORDS / total WORDS
(a plain type-token ratio) -- a genuinely different, simpler statistic
that happens to share the name "H_s" / "symbolic entropy" across three
independent implementations in this project. This is worth stating
explicitly rather than assuming they're the same computation because
they share a name and a rough intent.

`main()`'s hardcoded paths (`pathlib.Path(__file__).parent / "..."`) are
redirected to a temp directory for its test by monkeypatching
`telemetry_analyzer.__file__`, the same technique used in
test_ritual_compiler.py -- this repo's real community_dataset.jsonl and
global_attractor_report.json already exist with accumulated real data
and must never be touched by this test suite.
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import telemetry_analyzer as ta  # noqa: E402


class TestCalcSymbolicEntropy(unittest.TestCase):
    def test_hand_computed_example(self):
        # "the cat sat on the mat" -> 6 words, 5 unique ("the" repeats).
        self.assertAlmostEqual(ta.calc_symbolic_entropy("the cat sat on the mat"), 5 / 6, places=9)

    def test_empty_text_is_zero(self):
        self.assertEqual(ta.calc_symbolic_entropy(""), 0.0)

    def test_all_distinct_words_is_one(self):
        self.assertEqual(ta.calc_symbolic_entropy("one two three four"), 1.0)

    def test_punctuation_is_stripped_before_counting(self):
        # "Hello, hello!" -> after stripping punctuation and lowercasing,
        # both tokens are "hello" -> 1 unique / 2 total = 0.5.
        self.assertEqual(ta.calc_symbolic_entropy("Hello, hello!"), 0.5)

    def test_is_a_different_formula_than_symbolic_debuggers_entropy(self):
        # Cross-check against symbolic_debugger.py's independent,
        # differently-defined entropy for the same text -- confirms
        # they are NOT the same computation despite the shared name.
        sys.path.insert(0, str(Path(__file__).parent))
        import symbolic_debugger as sd
        text = "the cat sat on the mat"
        self.assertNotAlmostEqual(ta.calc_symbolic_entropy(text), sd.calculate_entropy(text), places=2)


class TestClassifyLatency(unittest.TestCase):
    def test_zero_baseline_fallback(self):
        self.assertIn("Tifereth", ta.classify_latency(5.0, 0))

    def test_fast_ratio_is_chesed(self):
        self.assertIn("Chesed", ta.classify_latency(delta=1.0, baseline=10.0))  # ratio 0.1

    def test_ratio_boundary_just_under_half_is_chesed(self):
        self.assertIn("Chesed", ta.classify_latency(delta=4.99, baseline=10.0))  # ratio 0.499

    def test_ratio_exactly_half_is_tifereth_not_chesed(self):
        # ratio == 0.5 fails `< 0.5`, falls into the Tifereth branch.
        self.assertIn("Tifereth", ta.classify_latency(delta=5.0, baseline=10.0))

    def test_ratio_exactly_three_is_tifereth(self):
        self.assertIn("Tifereth", ta.classify_latency(delta=30.0, baseline=10.0))  # ratio 3.0

    def test_ratio_just_over_three_is_netzach_geburah(self):
        self.assertIn("Netzach", ta.classify_latency(delta=30.1, baseline=10.0))  # ratio 3.01


class TestClassifyEntropy(unittest.TestCase):
    def test_low_entropy_is_geburah_hod(self):
        self.assertIn("Geburah", ta.classify_entropy(0.3))

    def test_boundary_zero_point_six_is_tifereth_not_geburah(self):
        # hs == 0.6 fails `< 0.6`, falls into the Tifereth/Yesod branch.
        self.assertIn("Tifereth", ta.classify_entropy(0.6))

    def test_boundary_zero_point_eight_five_is_tifereth(self):
        self.assertIn("Tifereth", ta.classify_entropy(0.85))

    def test_just_over_zero_point_eight_five_is_chesed_netzach(self):
        self.assertIn("Chesed", ta.classify_entropy(0.8501))


class TestMainAggregation(unittest.TestCase):
    """Redirects telemetry_analyzer's hardcoded file paths to a temp
    directory (never the real community_dataset.jsonl /
    global_attractor_report.json) by monkeypatching __file__, the same
    technique test_ritual_compiler.py uses."""

    def _run_main_in_tempdir(self, entries, ritual_entries=None):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmpdir, ignore_errors=True))
        fake_file = str(Path(tmpdir) / "telemetry_analyzer.py")
        dataset_path = Path(tmpdir) / "community_dataset.jsonl"
        with dataset_path.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
            for r in (ritual_entries or []):
                f.write(json.dumps(r) + "\n")

        old_file = ta.__file__
        try:
            ta.__file__ = fake_file
            ta.main()
        finally:
            ta.__file__ = old_file

        report_path = Path(tmpdir) / "global_attractor_report.json"
        return json.loads(report_path.read_text(encoding="utf-8"))

    def test_two_events_produce_one_delta(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entries = [
            {"timestamp": base.isoformat(), "user_id_hash": "u1", "data": "hello world",
             "dominant_sephirah": "Tifereth", "patch": "Yesod"},
            {"timestamp": (base + timedelta(seconds=10)).isoformat(), "user_id_hash": "u1",
             "data": "hello again world", "dominant_sephirah": "Tifereth", "patch": "Yesod"},
        ]
        report = self._run_main_in_tempdir(entries)
        self.assertEqual(report["global_summary"]["total_users"], 1)
        user_report = report["users"]["u1"]
        self.assertEqual(len(user_report["events"]), 1)
        self.assertEqual(user_report["events"][0]["delta_sec"], 10.0)

    def test_ritual_entries_are_aggregated_separately_from_user_events(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entries = [
            {"timestamp": base.isoformat(), "user_id_hash": "u1", "data": "a",
             "dominant_sephirah": "Tifereth", "patch": "Yesod"},
            {"timestamp": (base + timedelta(seconds=5)).isoformat(), "user_id_hash": "u1",
             "data": "b", "dominant_sephirah": "Tifereth", "patch": "Yesod"},
        ]
        rituals = [
            {"event": "sephirotic_sort_ritual", "algorithm": "quicksort", "sephira": "Chokmah",
             "entropy_reduction": 0.4, "sorting_time": 0.002},
            {"event": "sephirotic_sort_ritual", "algorithm": "mergesort", "sephira": "Tifereth",
             "entropy_reduction": 0.6, "sorting_time": 0.003},
        ]
        report = self._run_main_in_tempdir(entries, rituals)
        metrics = report["global_summary"]["ritual_execution_metrics"]
        self.assertEqual(metrics["total_rituals_run"], 2)
        self.assertAlmostEqual(metrics["average_entropy_reduction"], 0.5, places=6)
        self.assertAlmostEqual(metrics["total_computational_tikun_time"], 0.005, places=6)
        self.assertEqual(metrics["algorithms_used"], {"quicksort": 1, "mergesort": 1})

    def test_single_event_user_produces_no_deltas_and_is_skipped(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entries = [{"timestamp": base.isoformat(), "user_id_hash": "lonely_user",
                    "data": "only one", "dominant_sephirah": "Hod", "patch": "Netzach"}]
        report = self._run_main_in_tempdir(entries)
        self.assertNotIn("lonely_user", report["users"])


def run_unit_test_suite():
    print("=" * 72)
    print("  TELEMETRY_ANALYZER.PY -- CORRECTNESS TEST SUITE")
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
