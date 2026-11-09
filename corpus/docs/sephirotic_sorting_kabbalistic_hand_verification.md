# Hand-Verifying `sephirotic_sorting.py` (Recursive-Symbolics/tools/)

*Register note: Register B. The Sephirah names attached to each algorithm
(HOD=insertion, GEBURAH=selection, CHOKMAH=quicksort, TIFERETH=mergesort)
are Register A labeling and are not re-litigated here — what's verified
below is that each function actually sorts correctly, independent of
whatever name is attached to it.*

## 1. The independent ground truth

Every assertion compares each function's output against Python's
built-in `sorted()` — a completely different implementation (Timsort, a
different codebase and language runtime) from any of the four
hand-written linked-list sorts here, so agreement is real evidence of
correctness, not a re-run of the same logic against itself.

## 2. By hand — why length and cycle checks matter as much as value order

A sort bug that silently drops or duplicates a node would still often
"look" sorted if the surviving values happen to already be in order —
checked explicitly with `test_returned_list_length_matches_input_length`
rather than relying on value-sequence equality alone to catch it. The
list-walking helper (`to_list()`) also tracks visited node identities via
`id()` and raises if it revisits one — a cycle bug (a `.next` pointer
looping back on itself) would hang silently otherwise; this makes it
fail loudly and immediately instead.

## 3. By hand — the CHOKMAH/quicksort 3-way partition, worked on paper

`quick_sort([3, 1, 3, 2])`, pivot = 3 (head's value):
```
less    = [1, 2]      (values < 3)
equal   = [3, 3]      (values == 3)
greater = []           (values > 3)
```
Recursing: `quick_sort([1,2])` → `[1,2]` (already ordered by the same
partition logic on a 2-element list); `quick_sort([])` → `None`.
Concatenation: `less(sorted) + equal + greater(sorted)` =
`[1, 2, 3, 3]` — matches `sorted([3,1,3,2]) == [1,2,3,3]` exactly. The
duplicate-handling (`equal` as its own bucket rather than folding into
`less` or `greater`) is what keeps this correct on repeated pivots — a
real, checkable design choice, confirmed with
`test_many_duplicate_values_mixed_with_uniques`.

## 4. By hand — the TIFERETH/mergesort split-and-merge

`merge_sort([4, 2, 7, 1])`: slow/fast pointer split gives `[4, 2]` and
`[7, 1]` (checked: `slow` advances one node per iteration, `fast`
advances two, so `fast` reaches the end after 2 iterations when `slow`
is at index 1 — midpoint is index 2, splitting into two equal halves for
this even-length case). Recursing: `merge_sort([4,2])` → `merge([4],[2])`
→ `[2,4]`; `merge_sort([7,1])` → `merge([7],[1])` → `[1,7]`. Final
`merge([2,4],[1,7])`: compare 2 vs 1 → take 1; compare 2 vs 7 → take 2;
compare 4 vs 7 → take 4; remainder → take 7. Result: `[1,2,4,7]` —
matches `sorted([4,2,7,1])` exactly.

## 5. The "ethical placeholder" claims, checked rather than accepted at face value

`shell_sort`/`heap_sort` raise `NotImplementedError` with reasoning
("unsuitable for linked lists", "requires random access"). The
underlying computer-science claim is real, not just decorative framing:
heap sort's standard array-based implementation depends on O(1) indexed
access to compute a node's parent/children by arithmetic on its index,
which a singly-linked list does not provide efficiently; shell sort's
gap-sequence traversal has the same dependency. The Register A
framing around this ("violates the principle of Non-Reduction") is not
itself a technical claim and isn't evaluated here — what's checked is
only that these functions actually raise, with the stated real-world
justification present in the message, rather than silently no-op'ing or
crashing with an unrelated error (`test_shell_sort_raises_not_implemented
_with_reasoning`, `test_heap_sort_raises_not_implemented_with_reasoning`).

## 6. Break-it proof (performed, not just described)

Flipped `merge()`'s comparison from `l1.val < l2.val` to
`l1.val > l2.val` — a realistic off-by-operator bug. Since `merge_sort`
depends on `merge()` recursively at every level, this broke sortedness
across nearly every test case that touched `merge_sort` (and, because
`REAL_SORTS` iterates all four functions inside shared `subTest` loops,
the failure count multiplied across the parameterized cases). Reverted;
`diff -q` against a pre-edit backup confirmed byte-identical.

## 7. Files

- [`../../Recursive-Symbolics/tools/sephirotic_sorting.py`](../tools/sephirotic_sorting.py) — the module.
- [`../../Recursive-Symbolics/tools/test_sephirotic_sorting.py`](../tools/test_sephirotic_sorting.py) — 14 tests (each expanding across 4 sort functions and multiple sizes/seeds via `subTest`), all passing.

---

## Provenance

Third file outside `solo/` brought to VERIFIED (after `delta_operator.py`
and `agency_budget.py`), and the first of the three to verify genuine
general-purpose algorithms (sorting) rather than the recurring
directive-strength gamma formula — checked against `sorted()` as an
independent reference, following the same discipline
`real_ridge_benchmark_vs_sklearn.py` already established for comparing
this repo's own implementations against a trusted external one.
