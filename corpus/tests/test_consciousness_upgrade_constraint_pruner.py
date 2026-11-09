"""
test_consciousness_upgrade_constraint_pruner.py

Independent ground truth: for interval constraints, satisfiability of a
set is exactly `max(lows) <= min(highs)` -- a fact checkable by brute-
force sampling (try many candidate values across a wide range and see if
any satisfies every constraint) as a genuinely different computational
method from the closed-form check in check_belief(), not just a re-run
of the same formula against itself.
"""

import unittest

import sys
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from consciousness_upgrade_constraint_pruner import (
    Constraint, SatisfiabilityResult, check_belief,
    find_unsatisfiable_beliefs, prune, explain,
)


def brute_force_satisfiable(constraints, lo=-1000.0, hi=1000.0, step=0.001):
    """Independent ground truth: scan a fine-grained grid and check
    whether ANY value satisfies every constraint simultaneously. Slow,
    deliberately not using max()/min() at all, so it can't share a bug
    with check_belief()'s closed-form implementation."""
    x = lo
    while x <= hi:
        if all(c.low <= x <= c.high for c in constraints):
            return True
        x += step
    return False


class TestConstraintConstruction(unittest.TestCase):
    def test_malformed_constraint_low_greater_than_high_raises(self):
        with self.assertRaises(ValueError):
            Constraint("x", "src", 10.0, 5.0)

    def test_degenerate_point_constraint_is_allowed(self):
        c = Constraint("x", "src", 5.0, 5.0)
        self.assertEqual(c.low, c.high)


class TestSatisfiabilityAgainstBruteForce(unittest.TestCase):
    def test_two_overlapping_ranges_satisfiable(self):
        cs = [Constraint("x", "a", 0.0, 10.0), Constraint("x", "b", 5.0, 15.0)]
        result = check_belief(cs)
        self.assertTrue(result.satisfiable)
        self.assertTrue(brute_force_satisfiable(cs, 0, 15, 0.01))

    def test_two_disjoint_ranges_unsatisfiable(self):
        cs = [Constraint("x", "a", 0.0, 2.0), Constraint("x", "b", 5.0, 10.0)]
        result = check_belief(cs)
        self.assertFalse(result.satisfiable)
        self.assertFalse(brute_force_satisfiable(cs, 0, 10, 0.01))

    def test_exactly_touching_bounds_are_satisfiable_closed_intervals(self):
        # [0,5] and [5,10] share exactly the point 5.0 -- closed intervals
        # make this satisfiable, a real boundary case worth pinning down.
        cs = [Constraint("x", "a", 0.0, 5.0), Constraint("x", "b", 5.0, 10.0)]
        result = check_belief(cs)
        self.assertTrue(result.satisfiable)
        self.assertEqual(result.intersection_low, 5.0)
        self.assertEqual(result.intersection_high, 5.0)

    def test_the_documents_own_please_everyone_example_is_unsatisfiable(self):
        cs = [
            Constraint("how_i_show_up", "please_my_family", 5.0, 10.0),
            Constraint("how_i_show_up", "protect_my_own_time", 0.0, 2.0),
        ]
        result = check_belief(cs)
        self.assertFalse(result.satisfiable)
        self.assertEqual(result.conflicting_lower_bound.source, "please_my_family")
        self.assertEqual(result.conflicting_upper_bound.source, "protect_my_own_time")
        self.assertFalse(brute_force_satisfiable(cs, 0, 10, 0.001))

    def test_negative_ranges(self):
        cs = [Constraint("x", "a", -10.0, -5.0), Constraint("x", "b", -8.0, -1.0)]
        result = check_belief(cs)
        self.assertTrue(result.satisfiable)
        self.assertEqual(result.intersection_low, -8.0)
        self.assertEqual(result.intersection_high, -5.0)

    def test_redundant_constraint_does_not_change_satisfiability(self):
        # A constraint strictly wider than the others should have no
        # effect on the outcome -- it's never the argmax-low or argmin-high.
        cs = [
            Constraint("x", "tight1", 4.0, 6.0),
            Constraint("x", "tight2", 5.0, 5.5),
            Constraint("x", "wide", -100.0, 100.0),
        ]
        result = check_belief(cs)
        self.assertTrue(result.satisfiable)
        self.assertNotEqual(result.intersection_low, -100.0)
        self.assertNotEqual(result.intersection_high, 100.0)

    def test_single_constraint_is_always_satisfiable(self):
        result = check_belief([Constraint("x", "only", 3.0, 3.0)])
        self.assertTrue(result.satisfiable)

    def test_empty_list_raises_rather_than_vacuously_returning_true(self):
        with self.assertRaises(ValueError):
            check_belief([])

    def test_mismatched_beliefs_raises(self):
        cs = [Constraint("x", "a", 0.0, 1.0), Constraint("y", "b", 0.0, 1.0)]
        with self.assertRaises(ValueError):
            check_belief(cs)


class TestMinimalConflictPrecision(unittest.TestCase):
    """The module docstring is explicit that the reported pair is *a*
    minimal unsatisfiable core, not asserted to be the only one. This
    test demonstrates that directly with a real 3-constraint example,
    rather than leaving the claim untested."""

    def test_finds_a_real_conflict_not_the_only_possible_one(self):
        cs = [
            Constraint("how_i_show_up", "please_my_family", 5.0, 10.0),
            Constraint("how_i_show_up", "protect_my_own_time", 0.0, 2.0),
            Constraint("how_i_show_up", "be_reliable_at_work", 3.0, 8.0),
        ]
        result = check_belief(cs)
        self.assertFalse(result.satisfiable)
        # The reported certificate pair: max(lows)=5 (family), min(highs)=2 (own_time).
        self.assertEqual(result.conflicting_lower_bound.source, "please_my_family")
        self.assertEqual(result.conflicting_upper_bound.source, "protect_my_own_time")

        # But a DIFFERENT pair (work vs. own_time: 3 > 2) is ALSO
        # independently unsatisfiable -- confirmed directly, not assumed.
        other_pair = [
            Constraint("how_i_show_up", "be_reliable_at_work", 3.0, 8.0),
            Constraint("how_i_show_up", "protect_my_own_time", 0.0, 2.0),
        ]
        other_result = check_belief(other_pair)
        self.assertFalse(other_result.satisfiable)
        # And a third pair (family vs. work) is, in fact, satisfiable --
        # not every pair conflicts, only some.
        third_pair = [
            Constraint("how_i_show_up", "please_my_family", 5.0, 10.0),
            Constraint("how_i_show_up", "be_reliable_at_work", 3.0, 8.0),
        ]
        self.assertTrue(check_belief(third_pair).satisfiable)


class TestFindUnsatisfiableBeliefs(unittest.TestCase):
    def test_groups_by_belief_and_reports_every_group(self):
        cs = [
            Constraint("x", "a", 0.0, 1.0),
            Constraint("x", "b", 2.0, 3.0),   # x: unsatisfiable
            Constraint("y", "c", 0.0, 10.0),  # y: satisfiable, alone
        ]
        results = find_unsatisfiable_beliefs(cs)
        self.assertEqual(set(results.keys()), {"x", "y"})
        self.assertFalse(results["x"].satisfiable)
        self.assertTrue(results["y"].satisfiable)  # not silently omitted


class TestPrune(unittest.TestCase):
    def test_prune_removes_named_constraint_and_restores_satisfiability(self):
        cs = [
            Constraint("x", "a", 5.0, 10.0),
            Constraint("x", "b", 0.0, 2.0),
        ]
        self.assertFalse(check_belief(cs).satisfiable)
        pruned = prune(cs, "x", "b")
        self.assertEqual(len(pruned), 1)
        self.assertTrue(check_belief(pruned).satisfiable)

    def test_prune_on_nonexistent_source_raises_rather_than_silent_noop(self):
        cs = [Constraint("x", "a", 0.0, 1.0)]
        with self.assertRaises(ValueError):
            prune(cs, "x", "nonexistent_source")

    def test_prune_does_not_mutate_the_original_list(self):
        cs = [Constraint("x", "a", 5.0, 10.0), Constraint("x", "b", 0.0, 2.0)]
        original_len = len(cs)
        prune(cs, "x", "b")
        self.assertEqual(len(cs), original_len)


class TestExplain(unittest.TestCase):
    def test_explain_satisfiable_mentions_the_word_satisfiable(self):
        result = check_belief([Constraint("x", "a", 0.0, 5.0)])
        self.assertIn("SATISFIABLE", explain(result))

    def test_explain_unsatisfiable_names_both_real_sources(self):
        cs = [Constraint("x", "alpha", 5.0, 10.0), Constraint("x", "beta", 0.0, 2.0)]
        text = explain(check_belief(cs))
        self.assertIn("alpha", text)
        self.assertIn("beta", text)
        self.assertIn("UNSATISFIABLE", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
