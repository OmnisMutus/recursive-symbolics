"""
test_sephirotic_sorting.py

Independent ground truth: Python's built-in sorted() (Timsort, a
completely different implementation/language-runtime code path from any
of the four hand-written linked-list sorts here) is the reference every
assertion below compares against -- the same "compare against a trusted,
independent implementation" discipline real_ridge_benchmark_vs_sklearn.py
already uses for its own comparison.

Until this file existed, sephirotic_sorting.py had never been tested by
any standard in this repository -- confirmed by `find . -iname "test_*"`
returning only test_delta_operator.py and test_agency_budget.py before
this file was added.
"""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sephirotic_sorting as ss  # noqa: E402


REAL_SORTS = {
    "insertion_sort": ss.insertion_sort,
    "selection_sort": ss.selection_sort,
    "quick_sort": ss.quick_sort,
    "merge_sort": ss.merge_sort,
}


def to_list(head):
    """Walks the linked list and returns its values as a plain Python
    list -- also implicitly checks there's no cycle (a cycle would hang
    this loop, caught by the test runner's own timeout rather than
    silently passing)."""
    vals = []
    curr = head
    seen = set()
    while curr:
        if id(curr) in seen:
            raise AssertionError("Cycle detected in returned linked list -- "
                                  "a node's .next eventually points back to "
                                  "an already-visited node.")
        seen.add(id(curr))
        vals.append(curr.val)
        curr = curr.next
    return vals


class TestAllFourSortsAgainstBuiltinSorted(unittest.TestCase):
    """Every real sort function, checked against Python's sorted() --
    an independent implementation, not a re-run of any of these four
    against each other."""

    def test_random_lists_many_sizes_and_seeds(self):
        random.seed(0)
        for name, fn in REAL_SORTS.items():
            for size in [0, 1, 2, 3, 5, 10, 50, 200]:
                for trial in range(5):
                    with self.subTest(sort=name, size=size, trial=trial):
                        vals = [random.randint(-1000, 1000) for _ in range(size)]
                        head = ss.build_list(vals)
                        result = to_list(fn(head))
                        self.assertEqual(result, sorted(vals))

    def test_already_sorted_input(self):
        vals = list(range(30))
        for name, fn in REAL_SORTS.items():
            with self.subTest(sort=name):
                self.assertEqual(to_list(fn(ss.build_list(vals))), sorted(vals))

    def test_reverse_sorted_input(self):
        vals = list(range(30, 0, -1))
        for name, fn in REAL_SORTS.items():
            with self.subTest(sort=name):
                self.assertEqual(to_list(fn(ss.build_list(vals))), sorted(vals))

    def test_all_duplicate_values(self):
        vals = [7] * 20
        for name, fn in REAL_SORTS.items():
            with self.subTest(sort=name):
                self.assertEqual(to_list(fn(ss.build_list(vals))), sorted(vals))

    def test_many_duplicate_values_mixed_with_uniques(self):
        random.seed(1)
        vals = [random.choice([1, 2, 3]) for _ in range(15)] + [99, -50, 0]
        for name, fn in REAL_SORTS.items():
            with self.subTest(sort=name):
                self.assertEqual(to_list(fn(ss.build_list(vals))), sorted(vals))

    def test_empty_list_returns_none(self):
        for name, fn in REAL_SORTS.items():
            with self.subTest(sort=name):
                self.assertIsNone(fn(ss.build_list([])))

    def test_single_element_list(self):
        for name, fn in REAL_SORTS.items():
            with self.subTest(sort=name):
                result = fn(ss.build_list([42]))
                self.assertEqual(to_list(result), [42])

    def test_negative_and_zero_values(self):
        vals = [-5, 0, 3, -100, 100, 0, -1]
        for name, fn in REAL_SORTS.items():
            with self.subTest(sort=name):
                self.assertEqual(to_list(fn(ss.build_list(vals))), sorted(vals))

    def test_returned_list_length_matches_input_length(self):
        # Guards against a subtle bug where a merge/partition step drops
        # or duplicates a node -- checked explicitly, not just inferred
        # from the values happening to match by coincidence.
        random.seed(2)
        for name, fn in REAL_SORTS.items():
            for size in [5, 20, 100]:
                with self.subTest(sort=name, size=size):
                    vals = [random.randint(0, 10) for _ in range(size)]
                    result = to_list(fn(ss.build_list(vals)))
                    self.assertEqual(len(result), size)


class TestEthicalPlaceholders(unittest.TestCase):
    """shell_sort and heap_sort are deliberate refusals, not bugs --
    confirmed they actually raise, with the stated reasoning, rather than
    silently doing nothing or crashing with an unrelated error."""

    def test_shell_sort_raises_not_implemented_with_reasoning(self):
        with self.assertRaises(NotImplementedError) as ctx:
            ss.shell_sort(None)
        self.assertIn("linked lists", str(ctx.exception))

    def test_heap_sort_raises_not_implemented_with_reasoning(self):
        with self.assertRaises(NotImplementedError) as ctx:
            ss.heap_sort(None)
        self.assertIn("random access", str(ctx.exception))


class TestBuildAndUtilityFunctions(unittest.TestCase):
    def test_build_list_then_iter_linked_round_trips(self):
        vals = [3, 1, 4, 1, 5, 9, 2, 6]
        head = ss.build_list(vals)
        result = [node.val for node in ss.iter_linked(head)]
        self.assertEqual(result, vals)  # build_list preserves original order

    def test_copy_list_produces_independent_nodes(self):
        head = ss.build_list([1, 2, 3])
        copy = ss.copy_list(head)
        # Independent node objects -- mutating the copy must not affect the original.
        copy.val = 999
        self.assertEqual(head.val, 1)
        self.assertEqual(to_list(copy), [999, 2, 3])
        self.assertEqual(to_list(head), [1, 2, 3])

    def test_copy_list_of_empty_list_is_none(self):
        self.assertIsNone(ss.copy_list(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
