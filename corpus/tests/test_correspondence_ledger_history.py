#!/usr/bin/env python3
"""
test_correspondence_ledger_history.py
Correctness verification for correspondence_ledger_history.py per
TESTING_STANDARD.md.

Ground truth: hand-controlled `now` and `last_run_utc` timestamps (exact,
known elapsed-day differences computed by hand, e.g. exactly 5.0 days
apart), plus temp JSON files for the load/save round-trip -- not
anything derived from the real correspondence ledgers.
"""

import sys
import json
import unittest
import tempfile
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from correspondence_ledger_history import (
    load_history, save_history, record_run, days_since, format_freshness_report,
)

UTC = datetime.timezone.utc


class TestLoadSaveRoundTrip(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.path = Path(self._tmpdir.name) / "history.json"

    def test_load_missing_file_returns_empty_dict(self):
        self.assertEqual(load_history(self.path), {})

    def test_save_then_load_round_trips_exactly(self):
        history = {"a.py": {"last_run_utc": "2026-07-01T00:00:00+00:00",
                             "verified": 3, "failed": 0, "untestable": 1, "total": 4}}
        save_history(history, self.path)
        self.assertEqual(load_history(self.path), history)

    def test_saved_file_is_valid_json_readable_by_stdlib_json(self):
        history = {"b.py": {"last_run_utc": "2026-07-01T00:00:00+00:00",
                             "verified": 1, "failed": 0, "untestable": 0, "total": 1}}
        save_history(history, self.path)
        with open(self.path) as f:
            reloaded = json.load(f)
        self.assertEqual(reloaded, history)


class TestRecordRun(unittest.TestCase):
    def test_first_run_ever_has_no_previous_record(self):
        now = datetime.datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)
        new_history, previous = record_run({}, [("a.py", 4, 0, 1, 5)], now=now)
        self.assertIsNone(previous["a.py"])
        self.assertEqual(new_history["a.py"]["verified"], 4)
        self.assertEqual(new_history["a.py"]["failed"], 0)
        self.assertEqual(new_history["a.py"]["untestable"], 1)
        self.assertEqual(new_history["a.py"]["total"], 5)
        self.assertEqual(new_history["a.py"]["last_run_utc"], now.isoformat())

    def test_second_run_returns_the_actual_prior_record(self):
        first_time = datetime.datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
        history, _ = record_run({}, [("a.py", 4, 0, 1, 5)], now=first_time)

        second_time = datetime.datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC)
        new_history, previous = record_run(history, [("a.py", 5, 0, 0, 5)], now=second_time)

        self.assertIsNotNone(previous["a.py"])
        self.assertEqual(previous["a.py"]["last_run_utc"], first_time.isoformat())
        self.assertEqual(previous["a.py"]["verified"], 4)  # the OLD count, not overwritten yet
        self.assertEqual(new_history["a.py"]["verified"], 5)  # the NEW count

    def test_multiple_ledgers_recorded_independently(self):
        now = datetime.datetime(2026, 7, 31, 0, 0, 0, tzinfo=UTC)
        new_history, previous = record_run(
            {}, [("a.py", 1, 0, 0, 1), ("b.py", 2, 1, 0, 3)], now=now)
        self.assertEqual(set(new_history.keys()), {"a.py", "b.py"})
        self.assertIsNone(previous["a.py"])
        self.assertIsNone(previous["b.py"])
        self.assertEqual(new_history["b.py"]["failed"], 1)


class TestDaysSince(unittest.TestCase):
    def test_none_record_yields_none(self):
        self.assertIsNone(days_since(None))

    def test_exact_five_day_gap_computes_to_five(self):
        record = {"last_run_utc": datetime.datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC).isoformat()}
        now = datetime.datetime(2026, 7, 6, 0, 0, 0, tzinfo=UTC)
        self.assertAlmostEqual(days_since(record, now=now), 5.0, places=6)

    def test_zero_gap_when_now_equals_last_run(self):
        ts = datetime.datetime(2026, 7, 31, 8, 0, 0, tzinfo=UTC)
        record = {"last_run_utc": ts.isoformat()}
        self.assertAlmostEqual(days_since(record, now=ts), 0.0, places=6)

    def test_fractional_day_gap(self):
        record = {"last_run_utc": datetime.datetime(2026, 7, 31, 0, 0, 0, tzinfo=UTC).isoformat()}
        now = datetime.datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)  # 12 hours later
        self.assertAlmostEqual(days_since(record, now=now), 0.5, places=6)


class TestFormatFreshnessReport(unittest.TestCase):
    def test_never_run_reported_as_first_recorded(self):
        report = format_freshness_report({"a.py": None})
        self.assertIn("a.py", report)
        self.assertIn("first recorded run", report)

    def test_fresh_check_under_threshold_not_flagged_stale(self):
        now = datetime.datetime(2026, 7, 31, 0, 0, 0, tzinfo=UTC)
        record = {"last_run_utc": datetime.datetime(2026, 7, 30, 0, 0, 0, tzinfo=UTC).isoformat()}
        report = format_freshness_report({"a.py": record}, stale_threshold_days=30.0, now=now)
        self.assertNotIn("STALE", report)
        self.assertIn("1.00 day(s) ago", report)

    def test_old_check_over_threshold_flagged_stale(self):
        now = datetime.datetime(2026, 7, 31, 0, 0, 0, tzinfo=UTC)
        record = {"last_run_utc": datetime.datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC).isoformat()}
        report = format_freshness_report({"a.py": record}, stale_threshold_days=30.0, now=now)
        self.assertIn("STALE", report)

    def test_exactly_at_threshold_is_not_flagged(self):
        # Boundary case: exactly `stale_threshold_days` should NOT count
        # as stale (the check is strictly-greater-than, not >=).
        now = datetime.datetime(2026, 7, 31, 0, 0, 0, tzinfo=UTC)
        record = {"last_run_utc": datetime.datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC).isoformat()}
        report = format_freshness_report({"a.py": record}, stale_threshold_days=30.0, now=now)
        self.assertNotIn("STALE", report)


def run_unit_test_suite():
    print("=" * 72)
    print("  CORRESPONDENCE LEDGER HISTORY -- CORRECTNESS TEST SUITE")
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
