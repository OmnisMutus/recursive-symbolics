# Hand-Verifying `consciousness_upgrade_constraint_pruner.py`

*Register note: Register B. The pasted "Consciousness Upgrade Protocol"
document's GHC-compiler framing (Stage 2, "Pruning Insoluble
Constraints") is Register A/metaphor and is not re-litigated here — see
the chat discussion checking its specific GHC-version claims against the
real GHC 9.2 release notes. What's verified below is the actual math this
module implements, independent of whether the compiler analogy is apt.*

## 1. The Formula

```
satisfiable  = max(all constraints' low) <= min(all constraints' high)
intersection = [max(lows), min(highs)]        (if satisfiable)
```

## 2. By Hand — Two Overlapping Ranges

Constraints: `[0, 10]` and `[5, 15]`.
```
max(lows)  = max(0, 5)   = 5
min(highs) = min(10, 15) = 10
5 <= 10  ->  SATISFIABLE, intersection = [5, 10]
```
Checkable by inspection: any value from 5 to 10 lies in both ranges.

## 3. By Hand — The Document's Own "Please Everyone" Example

Constraints: `please_my_family` requires `[5, 10]`, `protect_my_own_time`
requires `[0, 2]`.
```
max(lows)  = max(5, 0)  = 5   (from please_my_family)
min(highs) = min(10, 2) = 2   (from protect_my_own_time)
5 <= 2  is FALSE  ->  UNSATISFIABLE
```
No number is simultaneously `>= 5` and `<= 2` — checkable without a
calculator. The two constraints identified as the cause
(`please_my_family`, `protect_my_own_time`) are exactly the ones supplying
the `5` and the `2`, which is also hand-checkable: neither number came
from anywhere else.

## 4. By Hand — Why the Reported Pair Is *Not* Claimed to Be the Only One

Add a third constraint to the example above: `be_reliable_at_work`
requires `[3, 8]`.
```
Pairwise checks (all by hand):
  please_my_family [5,10]  vs  be_reliable_at_work [3,8]:
    max(5,3)=5, min(10,8)=8, 5<=8  ->  satisfiable
  be_reliable_at_work [3,8]  vs  protect_my_own_time [0,2]:
    max(3,0)=3, min(8,2)=2, 3<=2 is FALSE  ->  ALSO unsatisfiable
```
So with three constraints, there are two genuinely different
unsatisfiable pairs: the one the module reports
(`please_my_family`/`protect_my_own_time`, derived from the *global*
max-low and min-high) and a second, different one
(`be_reliable_at_work`/`protect_my_own_time`) that the module does not
single out. Both are real; the module's docstring says so explicitly
(`test_finds_a_real_conflict_not_the_only_possible_one` checks this
directly) rather than letting the single reported pair imply it's the
whole story.

## 5. By Hand — The Touching-Bounds Boundary Case, and What Breaking It Looks Like

Constraints: `[0, 5]` and `[5, 10]` — closed intervals sharing exactly the
point `5`.
```
max(lows)=5, min(highs)=5, 5<=5 is TRUE -> SATISFIABLE, intersection=[5,5]
```
This is the exact case the break-it proof targeted: changing the
comparison from `<=` to `<` makes `5 < 5` evaluate `False`, silently
reclassifying this case (and, as a direct consequence, every
single-constraint case, since a constraint's own `low == high` reduces
to the identical comparison) as unsatisfiable. Two tests caught this
immediately when it was actually run
(`test_exactly_touching_bounds_are_satisfiable_closed_intervals`,
`test_single_constraint_is_always_satisfiable`); the file was reverted
and confirmed byte-identical via `diff -q`.

## 6. The Guard Worth Noticing

`prune()` never chooses which constraint to discard — it requires the
caller to name one, and raises rather than silently no-op'ing if the
named source doesn't exist. This is a direct implementation of the
Principle of Agency & Sovereignty ("options, never commands") —
see `recursive_symbolics_foundation_reference.md` section 13 (same
`docs/` directory)
(`foundation/core-ethics.md` itself, cited there, was uploaded separately
and is not present in this repo; section 13 is this repo's real,
in-repo summary of it, which is what this citation actually points at)
— hand-checkable by reading the function: there is no heuristic,
priority score, or ranking anywhere in it that could make the choice for
you.

---

## Provenance

Grounds Stage 2 of the pasted "Consciousness Upgrade Protocol" document
in real interval-arithmetic satisfiability, following the same
discipline as `delta_operator_kabbalistic_hand_verification.md` — an
external, plausible-sounding framing (there, GHC version history; here,
a GHC-compiler-upgrade analogy) checked and separated from the real,
checkable computation underneath it.
