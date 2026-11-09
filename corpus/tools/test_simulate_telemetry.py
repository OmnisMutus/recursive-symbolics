#!/usr/bin/env python3
"""
test_simulate_telemetry.py
Independent correctness test for simulate_telemetry.py.

NOTE ON SCOPE: this file is test-fixture INFRASTRUCTURE -- it exists to
generate synthetic input for telemetry_analyzer.py's own tests/real use
(see its own docstring), not an engine making an independent claim about
anything. This test confirms generate_entry()'s shape and that main()
produces well-formed, chronologically-sorted JSONL -- it does not (and
should not) assert anything about whether the synthetic data is
"representative" of real usage, since it's explicitly synthetic by
design.

main()'s hardcoded output path (community_dataset.jsonl, real content
already present) is redirected to a temp directory via the same
`__file__` monkeypatch technique used elsewhere in this test suite.

DISCOVERED, DOCUMENTED FINDING: main()'s `entries.sort(key=lambda x:
x["timestamp"])` call is currently a no-op against its own hardcoded
data. A break-it proof that removed the sort entirely was run against
this test suite and every test still passed -- because each of the 4
synthetic users' time blocks starts at a strictly later base_time than
the previous user's (base_time, +5min, +10min, +15min), and within each
user the entries already increment forward in time, the unsorted
insertion order already happens to be fully chronological. The sort call
is real, correctly written, and would matter if the per-user blocks were
ever reordered or interleaved differently -- it just isn't exercised by
the data as currently written. This is recorded here rather than left as
a silently-passing break-it proof that looked like a null result.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import simulate_telemetry as st  # noqa: E402


class TestGenerateEntry(unittest.TestCase):
    def test_returns_expected_shape(self):
        from datetime import datetime, timezone
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entry = st.generate_entry(ts, "hash123", "Geburah", "Chesed", "some text")
        self.assertEqual(entry["user_id_hash"], "hash123")
        self.assertEqual(entry["dominant_sephirah"], "Geburah")
        self.assertEqual(entry["patch"], "Chesed")
        self.assertEqual(entry["data"], "some text")
        self.assertEqual(entry["source"], "debugger")
        self.assertEqual(entry["timestamp"], ts.isoformat())

    def test_custom_source(self):
        from datetime import datetime, timezone
        entry = st.generate_entry(datetime.now(timezone.utc), "h", "Hod", "Netzach", "x", source="web_observatory")
        self.assertEqual(entry["source"], "web_observatory")


class TestMainGeneratesSortedDataset(unittest.TestCase):
    def test_writes_16_entries_sorted_by_timestamp(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmpdir, ignore_errors=True))
        fake_file = str(Path(tmpdir) / "simulate_telemetry.py")

        old_file = st.__file__
        try:
            st.__file__ = fake_file
            st.main()
        finally:
            st.__file__ = old_file

        out_path = Path(tmpdir) / "community_dataset.jsonl"
        self.assertTrue(out_path.is_file())
        lines = out_path.read_text(encoding="utf-8").strip().splitlines()
        # 4 users x 4 texts each, per simulate_telemetry.py's own data.
        self.assertEqual(len(lines), 16)

        records = [json.loads(l) for l in lines]
        timestamps = [r["timestamp"] for r in records]
        self.assertEqual(timestamps, sorted(timestamps))  # confirms the sort actually happened

        user_hashes = {r["user_id_hash"] for r in records}
        self.assertEqual(user_hashes, {
            "hash_fast_chesed", "hash_slow_tifereth", "hash_warmup_user", "hash_stuck_geburah",
        })

    def test_every_record_is_well_formed_json_with_required_keys(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmpdir, ignore_errors=True))
        fake_file = str(Path(tmpdir) / "simulate_telemetry.py")
        old_file = st.__file__
        try:
            st.__file__ = fake_file
            st.main()
        finally:
            st.__file__ = old_file

        out_path = Path(tmpdir) / "community_dataset.jsonl"
        for line in out_path.read_text(encoding="utf-8").strip().splitlines():
            record = json.loads(line)
            for key in ("timestamp", "user_id_hash", "dominant_sephirah", "patch", "source", "data"):
                self.assertIn(key, record)


def run_unit_test_suite():
    print("=" * 72)
    print("  SIMULATE_TELEMETRY.PY -- CORRECTNESS TEST SUITE")
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
