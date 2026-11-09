#!/usr/bin/env python3
"""
consciousness_upgrade_constraint_pruner.py

Grounds Stage 2 ("Pruning Insoluble Constraints") of the pasted
"Consciousness Upgrade Protocol" document in real, checkable math,
following the same discipline as delta_operator.py and
recursive_attractor_engine.py: the GHC analogy (rejecting code that
relies on an unsatisfiable constraint) is Register A/metaphor; what's
built here is Register B -- a genuine constraint-satisfiability checker,
not a poetic restatement of one.

THE REAL PROBLEM CHOSEN, AND WHY: general multi-variable constraint
satisfaction is a hard problem in general (SAT-complete). This module
deliberately restricts to ONE-DIMENSIONAL INTERVAL CONSTRAINTS: each
constraint says a single named "belief" must lie within [low, high], as
required by some named source. This is the exact shape of the document's
own example ("trying to please everyone": belief=X requires X>=5 from
one source and X<=2 from another) and it has a genuine, closed-form,
provably-correct answer -- no heuristic, no approximation:

  A set of interval constraints on the same belief is satisfiable if and
  only if max(all the lows) <= min(all the highs). If unsatisfiable, the
  pair contributing that max-low and that min-high is GUARANTEED to be,
  by itself, an unsatisfiable subset -- a genuine minimal unsatisfiable
  core, since any single constraint alone is always satisfiable (its own
  low <= high is enforced at construction). This is a real mathematical
  fact about interval intersection, not a design choice, and it is
  hand-verifiable (see
  docs/consciousness_upgrade_constraint_pruner_hand_verification.md).

  PRECISION, STATED EXPLICITLY RATHER THAN IMPLIED: this pair is *a*
  minimal unsatisfiable core, not asserted to be the *only* one. With
  three or more constraints on the same belief, other pairs can ALSO be
  independently unsatisfiable without being the global max-low/min-high
  pair (see test_finds_a_real_conflict_not_the_only_possible_one in the
  test suite, which demonstrates this directly rather than glossing over
  it) -- check_belief() reports one genuine, correct certificate that
  proves unsatisfiability; it is not an exhaustive search for every
  conflicting pair, and does not claim to be.

WHAT THIS DELIBERATELY DOES NOT DO: it does not decide WHICH of the two
conflicting constraints to discard. Per the framework's own Principle of
Agency & Sovereignty ("options, never commands" -- see
docs/recursive_symbolics_foundation_reference.md section 13, this repo's
normalized summary of `foundation/core-ethics.md`, a source document
uploaded separately and not itself present in this repo; citing the real
in-repo location rather than a file path that doesn't resolve here),
automatically guessing which belief-constraint is "outdated" or "should
win" would require a value judgment this module has no basis for making.
find_unsatisfiable_beliefs() reports the exact conflict; prune() requires
the CALLER to name which source's constraint to discard, the same way
GHC reports an unsatisfiable-constraint error and requires the programmer
to fix the code -- it does not silently pick a resolution for you.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Constraint:
    """A single bound on a named belief, attributed to a named source.
    `low`/`high` are inclusive (a closed interval [low, high])."""
    belief: str
    source: str
    low: float
    high: float

    def __post_init__(self):
        if self.low > self.high:
            raise ValueError(
                f"Constraint({self.belief!r}, {self.source!r}): low={self.low} "
                f"> high={self.high} -- a single constraint's own interval must "
                f"be non-empty; this is a malformed constraint, not an "
                f"unsatisfiable SET of constraints (that's a different, real "
                f"case this module handles -- see find_unsatisfiable_beliefs).")


@dataclass(frozen=True)
class SatisfiabilityResult:
    belief: str
    satisfiable: bool
    intersection_low: float
    intersection_high: float
    # Only set when satisfiable is False -- the exact minimal conflicting pair.
    conflicting_lower_bound: Optional[Constraint] = None
    conflicting_upper_bound: Optional[Constraint] = None


def check_belief(constraints: List[Constraint]) -> SatisfiabilityResult:
    """All `constraints` must share the same `.belief` (checked). Returns
    whether their intersection is non-empty, and if not, the exact two
    constraints responsible -- the one with the tightest (maximum) lower
    bound and the one with the tightest (minimum) upper bound."""
    if not constraints:
        raise ValueError("check_belief() called with an empty constraint list -- "
                          "there is nothing to check satisfiability of.")
    belief = constraints[0].belief
    for c in constraints:
        if c.belief != belief:
            raise ValueError(f"All constraints passed to check_belief() must share "
                              f"one belief; got {belief!r} and {c.belief!r}.")

    tightest_lower = max(constraints, key=lambda c: c.low)
    tightest_upper = min(constraints, key=lambda c: c.high)

    sat = tightest_lower.low <= tightest_upper.high
    return SatisfiabilityResult(
        belief=belief,
        satisfiable=sat,
        intersection_low=tightest_lower.low,
        intersection_high=tightest_upper.high,
        conflicting_lower_bound=None if sat else tightest_lower,
        conflicting_upper_bound=None if sat else tightest_upper,
    )


def find_unsatisfiable_beliefs(constraints: List[Constraint]) -> Dict[str, SatisfiabilityResult]:
    """Groups `constraints` by belief and checks each group. Returns a
    dict of belief -> SatisfiabilityResult for EVERY belief checked
    (both satisfiable and unsatisfiable), so a caller can distinguish
    "checked and fine" from "never mentioned" -- an all-satisfiable
    return is a real, informative result, not silently absent, the same
    anti-vacuous-truth discipline correspondence_ledger.py already uses."""
    by_belief: Dict[str, List[Constraint]] = {}
    for c in constraints:
        by_belief.setdefault(c.belief, []).append(c)
    return {belief: check_belief(group) for belief, group in by_belief.items()}


def prune(constraints: List[Constraint], belief: str, discard_source: str) -> List[Constraint]:
    """Returns a NEW list with the named source's constraint on `belief`
    removed. Requires the caller to name which constraint to discard --
    this function does not choose for you (see module docstring). Raises
    if no matching constraint exists, rather than silently no-op'ing."""
    match = [c for c in constraints if c.belief == belief and c.source == discard_source]
    if not match:
        raise ValueError(f"No constraint on belief={belief!r} from source={discard_source!r} "
                          f"found to prune -- refusing to silently no-op.")
    return [c for c in constraints if not (c.belief == belief and c.source == discard_source)]


def explain(result: SatisfiabilityResult) -> str:
    """Human-readable explanation of a single belief's satisfiability
    result, naming the exact conflicting sources when unsatisfiable --
    mirrors GHC reporting which two things actually conflict, rather
    than just 'type error somewhere in this expression.'"""
    if result.satisfiable:
        return (f"'{result.belief}': SATISFIABLE. All constraints agree on "
                f"[{result.intersection_low}, {result.intersection_high}].")
    lb, ub = result.conflicting_lower_bound, result.conflicting_upper_bound
    return (f"'{result.belief}': UNSATISFIABLE. "
            f"'{lb.source}' requires >= {lb.low}, but '{ub.source}' requires <= {ub.high}. "
            f"{lb.low} > {ub.high} -- no value can satisfy both. "
            f"These two constraints are the exact minimal conflicting pair; "
            f"call prune() naming which one to discard.")


if __name__ == "__main__":
    print("=" * 78)
    print("  CONSCIOUSNESS UPGRADE PROTOCOL -- STAGE 2: CONSTRAINT PRUNER")
    print("=" * 78)

    # The document's own example: trying to please everyone.
    constraints = [
        Constraint("how_i_show_up", "please_my_family", 5.0, 10.0),
        Constraint("how_i_show_up", "protect_my_own_time", 0.0, 2.0),
        Constraint("how_i_show_up", "be_reliable_at_work", 3.0, 8.0),
    ]
    results = find_unsatisfiable_beliefs(constraints)
    for belief, result in results.items():
        print(f"\n{explain(result)}")

    print("\n" + "-" * 78)
    print("Pruning 'protect_my_own_time' (an explicit, disclosed choice, not guessed):")
    pruned = prune(constraints, "how_i_show_up", "protect_my_own_time")
    result2 = check_belief([c for c in pruned if c.belief == "how_i_show_up"])
    print(explain(result2))
