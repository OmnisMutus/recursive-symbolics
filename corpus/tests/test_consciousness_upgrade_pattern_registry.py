"""
test_consciousness_upgrade_pattern_registry.py

Independent ground truth: every test below hand-constructs ChangeRecord
objects directly (bypassing propose_change()/ChangeLedger entirely) with
a hand-computed expected outcome decided BEFORE running the detector, so
the check can't share a bug with the module under test. Where hashes
matter, real sha256 values are used via compute_content_hash on small,
hand-picked value dicts -- not synthetic placeholder strings -- so
"hashes matching" in the test means the same thing it means in production.
"""

import unittest

import sys
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from consciousness_upgrade_self_signature import ChangeRecord, compute_content_hash
from consciousness_upgrade_pattern_registry import (
    PatternRegistry, Pattern, PatternMatch,
    detect_exact_state_reversion, make_repeated_reason_detector,
    make_high_frequency_key_detector, default_registry,
)


def rec(ts, old_values, new_values, reason):
    """Builds a ChangeRecord the same way propose_change() would, but by
    hand -- computing changed_keys and hashes directly here rather than
    calling the module's own propose_change(), so this helper can't share
    a bug with the code under test."""
    changed = sorted(
        k for k in (set(old_values) | set(new_values))
        if old_values.get(k) != new_values.get(k)
    )
    return ChangeRecord(
        timestamp=ts,
        old_hash=compute_content_hash(old_values),
        new_hash=compute_content_hash(new_values),
        changed_keys=changed,
        reason=reason,
    )


class TestExactStateReversion(unittest.TestCase):
    def test_reverting_to_initial_state_is_detected(self):
        v0 = {"x": "a"}
        v1 = {"x": "b"}
        records = [
            rec("2026-01-01T00:00:00Z", v0, v1, "trying b"),
            rec("2026-01-01T01:00:00Z", v1, v0, "back to a"),
        ]
        matches = detect_exact_state_reversion(records, initial_hash=compute_content_hash(v0))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].record_indices, [1])

    def test_reverting_to_a_mid_history_state_is_detected(self):
        v0, v1, v2 = {"x": "a"}, {"x": "b"}, {"x": "c"}
        records = [
            rec("2026-01-01T00:00:00Z", v0, v1, "r1"),
            rec("2026-01-01T01:00:00Z", v1, v2, "r2"),
            rec("2026-01-01T02:00:00Z", v2, v1, "back to b"),  # reverts to state after record 0
        ]
        matches = detect_exact_state_reversion(records, initial_hash=compute_content_hash(v0))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].record_indices, [2])

    def test_monotonic_changes_with_no_repeats_produce_no_match(self):
        v0, v1, v2 = {"x": "a"}, {"x": "b"}, {"x": "c"}
        records = [
            rec("2026-01-01T00:00:00Z", v0, v1, "r1"),
            rec("2026-01-01T01:00:00Z", v1, v2, "r2"),
        ]
        matches = detect_exact_state_reversion(records, initial_hash=compute_content_hash(v0))
        self.assertEqual(matches, [])

    def test_without_initial_hash_still_detects_mid_history_reversion(self):
        v0, v1 = {"x": "a"}, {"x": "b"}
        records = [
            rec("2026-01-01T00:00:00Z", v0, v1, "r1"),
            rec("2026-01-01T01:00:00Z", v1, v0, "back"),
        ]
        # No initial_hash passed -- reversion to v0 must still be caught
        # because v0 is record[0].old_hash, which the detector also tracks.
        matches = detect_exact_state_reversion(records, initial_hash=None)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].record_indices, [1])

    def test_two_completely_different_value_sets_never_collide(self):
        # Sanity check that unrelated value sets don't produce equal hashes
        # (this would be a real SHA-256 collision if it happened).
        v_a = {"belief": "alpha"}
        v_b = {"belief": "beta"}
        self.assertNotEqual(compute_content_hash(v_a), compute_content_hash(v_b))


class TestRepeatedReasonDetector(unittest.TestCase):
    def test_same_reason_on_different_keys_at_threshold_is_flagged(self):
        pattern = make_repeated_reason_detector(threshold=2)
        records = [
            rec("2026-01-01T00:00:00Z", {"a": "1"}, {"a": "2"}, "cleanup"),
            rec("2026-01-01T01:00:00Z", {"b": "1"}, {"b": "2"}, "cleanup"),
        ]
        matches = pattern.detector(records, None)
        self.assertEqual(len(matches), 1)
        self.assertEqual(set(matches[0].record_indices), {0, 1})

    def test_reason_is_normalized_case_and_whitespace(self):
        pattern = make_repeated_reason_detector(threshold=2)
        records = [
            rec("2026-01-01T00:00:00Z", {"a": "1"}, {"a": "2"}, "  Cleanup  "),
            rec("2026-01-01T01:00:00Z", {"b": "1"}, {"b": "2"}, "cleanup"),
        ]
        matches = pattern.detector(records, None)
        self.assertEqual(len(matches), 1)

    def test_same_reason_on_the_SAME_key_repeatedly_is_not_flagged(self):
        # Genuinely repeated edits to one key with the same reason isn't
        # "reused across different keys" -- only >1 distinct key should count.
        pattern = make_repeated_reason_detector(threshold=2)
        records = [
            rec("2026-01-01T00:00:00Z", {"a": "1"}, {"a": "2"}, "iterating"),
            rec("2026-01-01T01:00:00Z", {"a": "2"}, {"a": "3"}, "iterating"),
        ]
        matches = pattern.detector(records, None)
        self.assertEqual(matches, [])

    def test_below_threshold_count_is_not_flagged(self):
        pattern = make_repeated_reason_detector(threshold=3)
        records = [
            rec("2026-01-01T00:00:00Z", {"a": "1"}, {"a": "2"}, "cleanup"),
            rec("2026-01-01T01:00:00Z", {"b": "1"}, {"b": "2"}, "cleanup"),
        ]
        matches = pattern.detector(records, None)  # only 2 uses, threshold is 3
        self.assertEqual(matches, [])

    def test_different_reasons_across_different_keys_not_flagged(self):
        pattern = make_repeated_reason_detector(threshold=2)
        records = [
            rec("2026-01-01T00:00:00Z", {"a": "1"}, {"a": "2"}, "reason one"),
            rec("2026-01-01T01:00:00Z", {"b": "1"}, {"b": "2"}, "reason two"),
        ]
        matches = pattern.detector(records, None)
        self.assertEqual(matches, [])


class TestHighFrequencyKeyDetector(unittest.TestCase):
    def test_three_changes_within_window_is_flagged(self):
        pattern = make_high_frequency_key_detector(threshold=3, window_seconds=3600)
        records = [
            rec("2026-01-01T00:00:00Z", {"k": "1"}, {"k": "2"}, "r1"),
            rec("2026-01-01T00:20:00Z", {"k": "2"}, {"k": "3"}, "r2"),
            rec("2026-01-01T00:40:00Z", {"k": "3"}, {"k": "4"}, "r3"),
        ]
        matches = pattern.detector(records, None)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].record_indices, [0, 1, 2])

    def test_three_changes_spread_beyond_window_is_not_flagged(self):
        pattern = make_high_frequency_key_detector(threshold=3, window_seconds=3600)
        records = [
            rec("2026-01-01T00:00:00Z", {"k": "1"}, {"k": "2"}, "r1"),
            rec("2026-01-01T02:00:00Z", {"k": "2"}, {"k": "3"}, "r2"),
            rec("2026-01-01T04:00:00Z", {"k": "3"}, {"k": "4"}, "r3"),
        ]
        matches = pattern.detector(records, None)
        self.assertEqual(matches, [])

    def test_changes_to_different_keys_do_not_combine(self):
        pattern = make_high_frequency_key_detector(threshold=2, window_seconds=3600)
        records = [
            rec("2026-01-01T00:00:00Z", {"a": "1", "b": "1"}, {"a": "2", "b": "1"}, "r1"),
            rec("2026-01-01T00:10:00Z", {"a": "2", "b": "1"}, {"a": "2", "b": "2"}, "r2"),
        ]
        # 'a' changed once, 'b' changed once -- neither key alone reaches
        # threshold=2, even though 2 records happened total.
        matches = pattern.detector(records, None)
        self.assertEqual(matches, [])

    def test_exactly_at_window_boundary_counts_as_within(self):
        pattern = make_high_frequency_key_detector(threshold=2, window_seconds=3600)
        records = [
            rec("2026-01-01T00:00:00Z", {"k": "1"}, {"k": "2"}, "r1"),
            rec("2026-01-01T01:00:00Z", {"k": "2"}, {"k": "3"}, "r2"),  # exactly 3600s later
        ]
        matches = pattern.detector(records, None)
        self.assertEqual(len(matches), 1)


class TestPatternRegistry(unittest.TestCase):
    def test_registering_duplicate_name_raises(self):
        registry = PatternRegistry()
        p = Pattern("dup", "desc", lambda records, ih: [])
        registry.register(p)
        with self.assertRaises(ValueError):
            registry.register(p)

    def test_scan_reports_every_registered_pattern_even_with_zero_matches(self):
        registry = default_registry()
        v0 = {"x": "a"}
        records = [rec("2026-01-01T00:00:00Z", v0, {"x": "b"}, "unique reason")]
        results = registry.scan(records, initial_hash=compute_content_hash(v0))
        self.assertEqual(
            set(results.keys()),
            {"exact_state_reversion", "repeated_reason_across_different_keys",
             "high_frequency_change_on_same_key"},
        )
        # All three should be empty lists (checked-and-clean), not absent keys.
        for name, matches in results.items():
            self.assertEqual(matches, [], f"{name} unexpectedly matched: {matches}")

    def test_scan_across_all_three_patterns_on_a_combined_scenario(self):
        registry = default_registry(reason_threshold=2, freq_threshold=2, freq_window_seconds=7200)
        v0 = {"mood": "calm", "focus": "work"}
        v1 = {"mood": "anxious", "focus": "work"}
        v2 = {"mood": "calm", "focus": "work"}  # reverts mood -> exact state reversion to v0
        records = [
            rec("2026-01-01T00:00:00Z", v0, v1, "stress spike"),
            rec("2026-01-01T00:30:00Z", v1, v2, "stress spike"),  # same reason, but same key 'mood' both times
        ]
        results = registry.scan(records, initial_hash=compute_content_hash(v0))
        self.assertEqual(len(results["exact_state_reversion"]), 1)
        self.assertEqual(results["exact_state_reversion"][0].record_indices, [1])
        # Same reason used twice but both times on the same key ('mood') --
        # should NOT trigger repeated_reason_across_different_keys.
        self.assertEqual(results["repeated_reason_across_different_keys"], [])
        # 'mood' changed twice within 7200s window, threshold=2 -- should fire.
        self.assertEqual(len(results["high_frequency_change_on_same_key"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
