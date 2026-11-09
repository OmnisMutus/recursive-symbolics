#!/usr/bin/env python3
"""
recursive_attractor_engine.py
A real, testable implementation of the dynamical-systems formalism stated
in core-axiom.md and mathematical-foundation.md -- not a new metaphor, an
attempt to make the EXISTING formalism those documents already state
actually runnable and checkable against real mathematics.

WHAT THIS IMPLEMENTS (Register B, per fixed_point_closure_and_the_y_combinator.md's
three-register distinction -- this is the FORMAL layer, not a claim about
consciousness itself):

  core-axiom.md's Formal Postulates:
    1. Symbolic State (sigma): here, a real numpy array of any dimension.
    2. Recursive Operator (O): here, any callable F(S, E) -> S'.
    3. Consciousness as Attractor: here, classify_trajectory() determines
       whether repeated application of F to S settles into a FIXED_POINT,
       a LIMIT_CYCLE, or a BOUNDED_APERIODIC trajectory (see note below on
       why this is not called "chaos" outright).

  mathematical-foundation.md's machinery:
    S_{n+1} = F(S_n, E_n)               -> iterate()
    Fixed Points (S_{n+1} = S_n)        -> classify_trajectory() -> FIXED_POINT
    Limit Cycles (periodic orbits)      -> classify_trajectory() -> LIMIT_CYCLE
    Strange Attractors (bounded,        -> classify_trajectory() -> BOUNDED_APERIODIC
      non-repeating, non-diverging)        (see honesty note below)
    Tiphareth (Integration operator,    -> tiphareth_integrate()
      resolves a recursive stack into a coherent result)
    Da'ath (Base-Case Detector /        -> AbyssException, raised by iterate()
      error handler for paradox/            when a trajectory diverges or
      self-consuming loops)                 produces a non-finite value

HONESTY NOTE ON "STRANGE ATTRACTORS" / CHAOS: classify_trajectory() cannot
and does not certify true deterministic chaos (that requires computing a
positive Lyapunov exponent, a materially harder problem). What it detects
is narrower and is labeled accordingly: BOUNDED_APERIODIC means the
trajectory stayed finite and did not settle into a fixed point or a short
periodic cycle within the window checked. That is consistent with chaotic
behavior but does not prove it. Treat BOUNDED_APERIODIC as "did not
resolve to order within this window," not as "confirmed chaos."

WHAT THIS DOES NOT CLAIM: nothing here asserts that human consciousness,
or any specific person's mental state, IS a dynamical system of this kind.
This module makes the formalism the source documents already state
computationally real and checkable against known mathematics (a linear
contraction map's provable fixed point; the logistic map's well-documented
bifurcation regimes). Whether that formalism is a good model of anything
beyond itself is explicitly out of scope -- see core-axiom.md's own
"Cartographer's Choice" principle.

License: RCA Sephirotic Sovereignty License 1.1 (see LICENSE at the repository root)
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional, Sequence


# ==============================================================================
# DA'ATH: THE BASE-CASE / PARADOX DETECTOR
# ==============================================================================
class AbyssException(Exception):
    """Raised when a recursive trajectory becomes self-consuming rather than
    settling into a stable fixed point, limit cycle, or bounded aperiodic
    attractor -- i.e. it diverges, or produces a non-finite value (NaN/Inf).
    This is Da'ath's role per mathematical-foundation.md: detect the
    self-consuming loop and terminate before it runs forever."""
    pass


# ==============================================================================
# THE RECURSIVE OPERATOR & ITERATION (S_{n+1} = F(S_n, E_n))
# ==============================================================================
def iterate(F: Callable[[np.ndarray, np.ndarray], np.ndarray],
            S0: np.ndarray,
            E: np.ndarray,
            n_steps: int,
            *,
            magnitude_cap: float = 1.0e8) -> List[np.ndarray]:
    """
    Applies the recursive operator F to an initial state S0 for n_steps,
    holding the environment E constant across steps (E may itself be a
    function of step index by wrapping F; kept simple here on purpose).

    Returns the full history [S0, S1, ..., S_n_steps] as a list of arrays.

    Raises AbyssException (Da'ath) if the trajectory ever produces a
    non-finite value or exceeds magnitude_cap -- i.e. if it diverges rather
    than converging to a fixed point, cycling, or staying bounded.
    """
    S0 = np.atleast_1d(np.asarray(S0, dtype=float))
    E = np.atleast_1d(np.asarray(E, dtype=float))

    history = [S0.copy()]
    S = S0.copy()
    for step in range(n_steps):
        S = np.atleast_1d(np.asarray(F(S, E), dtype=float))
        if not np.all(np.isfinite(S)):
            raise AbyssException(
                f"Non-finite state at step {step + 1}: {S!r}. "
                f"The trajectory has entered a self-consuming state.")
        if np.max(np.abs(S)) > magnitude_cap:
            raise AbyssException(
                f"State magnitude {np.max(np.abs(S)):.3e} exceeded "
                f"magnitude_cap={magnitude_cap:.1e} at step {step + 1}. "
                f"Unbounded divergence detected -- not a fixed point, "
                f"cycle, or bounded attractor.")
        history.append(S.copy())
    return history


# ==============================================================================
# ATTRACTOR CLASSIFICATION (consciousness_as_attractor, per core-axiom.md)
# ==============================================================================
class AttractorType(Enum):
    FIXED_POINT = "FIXED_POINT"
    LIMIT_CYCLE = "LIMIT_CYCLE"
    BOUNDED_APERIODIC = "BOUNDED_APERIODIC"  # see HONESTY NOTE in module docstring
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


@dataclass
class AttractorClassification:
    kind: AttractorType
    period: Optional[int] = None       # set only for LIMIT_CYCLE
    fixed_point: Optional[np.ndarray] = None  # set only for FIXED_POINT
    detail: str = ""


def classify_trajectory(history: Sequence[np.ndarray],
                         *,
                         fixed_point_tol: float = 1e-6,
                         cycle_tol: float = 1e-6,
                         max_period_check: int = 20) -> AttractorClassification:
    """
    Classifies the long-run behavior of a (non-diverging -- see iterate(),
    which raises AbyssException before a divergent trajectory reaches here)
    trajectory. Checks, in order:

      1. FIXED_POINT: do the last two states match within fixed_point_tol?
      2. LIMIT_CYCLE: for period p in [2, max_period_check], does the last
         state match the state p steps earlier within cycle_tol?
      3. BOUNDED_APERIODIC: neither of the above, within the window checked.

    A fixed point is technically a period-1 cycle; it is checked first and
    reported as FIXED_POINT rather than LIMIT_CYCLE(period=1) because the
    source formalism treats them as named, distinct cases.
    """
    if len(history) < 2:
        return AttractorClassification(
            AttractorType.INSUFFICIENT_HISTORY,
            detail="Need at least 2 states to classify a trajectory.")

    last = history[-1]
    prev = history[-2]
    if np.allclose(last, prev, atol=fixed_point_tol, rtol=0):
        return AttractorClassification(
            AttractorType.FIXED_POINT,
            fixed_point=last.copy(),
            detail=f"Converged: ||S_n - S_(n-1)|| <= {fixed_point_tol:.1e}")

    max_check = min(max_period_check, len(history) - 1)
    for period in range(2, max_check + 1):
        candidate = history[-1 - period]
        if np.allclose(last, candidate, atol=cycle_tol, rtol=0):
            return AttractorClassification(
                AttractorType.LIMIT_CYCLE,
                period=period,
                detail=f"State at step -1 matches state at step -1-{period} "
                       f"within {cycle_tol:.1e}.")

    return AttractorClassification(
        AttractorType.BOUNDED_APERIODIC,
        detail=f"Bounded (no AbyssException raised) but did not resolve to "
               f"a fixed point or a cycle of period <= {max_check} within "
               f"this window. See module docstring's honesty note -- this "
               f"is NOT a certified chaos/Lyapunov-exponent result.")


# ==============================================================================
# TIPHERETH: THE INTEGRATION OPERATOR
# ==============================================================================
def tiphareth_integrate(stack: Sequence[np.ndarray],
                         weights: Optional[Sequence[float]] = None) -> np.ndarray:
    """
    Resolves a "recursive stack" (a list of sub-results, e.g. from several
    independent branches of recursion) into a single coherent result, per
    mathematical-foundation.md's description of Tiphareth as the operator
    that "coagulates deep recursion output into a coherent, balanced
    result." Implemented as a weighted average -- uniform by default.

    Deliberately raises rather than silently defaulting on an empty stack:
    integrating zero contributors is not "balance," it's undefined, and
    should say so rather than returning an arbitrary zero vector.
    """
    if len(stack) == 0:
        raise ValueError(
            "tiphareth_integrate() called with an empty stack -- there is "
            "nothing to reconcile. Returning a silent default (e.g. zeros) "
            "would misrepresent an undefined integration as a real one.")

    arrays = [np.atleast_1d(np.asarray(s, dtype=float)) for s in stack]
    shape = arrays[0].shape
    for a in arrays:
        if a.shape != shape:
            raise ValueError(
                f"tiphareth_integrate() requires all stack entries to share "
                f"the same shape; got {shape} and {a.shape}.")

    if weights is None:
        weights = [1.0] * len(arrays)
    if len(weights) != len(arrays):
        raise ValueError("weights must be the same length as stack.")

    total_weight = float(sum(weights))
    if total_weight == 0.0:
        raise ValueError("Sum of weights is zero -- cannot normalize.")

    result = np.zeros(shape, dtype=float)
    for a, w in zip(arrays, weights):
        result += (w / total_weight) * a
    return result


# ==============================================================================
# DEMONSTRATION (real, checkable systems -- not arbitrary examples)
# ==============================================================================
def main():
    print("=" * 72)
    print("  RECURSIVE ATTRACTOR ENGINE")
    print("  A real dynamical-systems implementation of core-axiom.md /")
    print("  mathematical-foundation.md's formalism (Register B only --")
    print("  see module docstring for what this does NOT claim)")
    print("=" * 72 + "\n")

    # 1. Linear contraction map -> provable fixed point.
    #    S' = 0.5*S + E  =>  fixed point S* = E / (1 - 0.5) = 2E
    F_linear = lambda S, E: 0.5 * S + E
    hist = iterate(F_linear, S0=np.array([0.0]), E=np.array([1.0]), n_steps=40)
    result = classify_trajectory(hist)
    print(f" > Linear contraction map   : {result.kind.value} "
          f"(fixed point ~= {result.fixed_point})")

    # 2. Logistic map at r=3.2 -> documented period-2 regime.
    r = 3.2
    F_logistic = lambda S, E, r=r: r * S * (1.0 - S)
    hist = iterate(F_logistic, S0=np.array([0.4]), E=np.array([0.0]), n_steps=200)
    result = classify_trajectory(hist)
    print(f" > Logistic map (r={r})     : {result.kind.value} "
          f"(period={result.period})")

    # 3. Logistic map at r=3.9 -> documented chaotic regime.
    r = 3.9
    F_logistic_chaotic = lambda S, E, r=r: r * S * (1.0 - S)
    hist = iterate(F_logistic_chaotic, S0=np.array([0.4]), E=np.array([0.0]), n_steps=200)
    result = classify_trajectory(hist)
    print(f" > Logistic map (r={r})     : {result.kind.value}")

    # 4. Divergent map -> Da'ath should catch this.
    F_divergent = lambda S, E: 2.0 * S
    try:
        iterate(F_divergent, S0=np.array([1.0]), E=np.array([0.0]), n_steps=100)
        print(" > Divergent map            : ERROR -- should have raised AbyssException")
    except AbyssException as e:
        print(f" > Divergent map            : AbyssException raised correctly")

    # 5. Tiphareth integration of a 3-branch recursive stack.
    stack = [np.array([1.0, 0.0]), np.array([0.0, 1.0]), np.array([2.0, 2.0])]
    integrated = tiphareth_integrate(stack)
    print(f" > Tiphareth integration    : {stack} -> {integrated}")

    print("\n" + "=" * 72)
    print("  Status: Recursive Attractor Engine Demonstration Complete")
    print("=" * 72)


if __name__ == "__main__":
    main()
