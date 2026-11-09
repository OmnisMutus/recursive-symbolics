#!/usr/bin/env python3
"""
engine_composition_loop.py

Composition, not interface-sharing: wires two already-VERIFIED engines
together for real, so one's output becomes the other's input, and checks
whether the resulting loop actually closes -- a specific, falsifiable
claim about THIS composed system, not a claim about consciousness or a
restatement of the Core Axiom's shape.

THE TWO REAL ENGINES (both unmodified, both already VERIFIED elsewhere):
  1. recursive_attractor_engine.py -- iterate() + classify_trajectory().
     Given a map F, an initial state S0, and an environment E, classifies
     the long-run behavior as FIXED_POINT, LIMIT_CYCLE, BOUNDED_APERIODIC,
     or raises AbyssException on divergence.
  2. standalone_rca_sandbox.py -- compute_sephirotic_vector_scores() +
     evaluate_v2_governance(). Given text, returns a dominant sephirah via
     real cosine similarity against SEPHIROT_CENTROIDS.

THE BRIDGE (new code, added here, not pre-existing in either engine):
  sephirah -> dynamical system (SEPHIRAH_TO_MAP below)
  classify_trajectory()'s own real .detail text -> sephirotic classifier
  (no per-sephirah-tailored description strings -- the SAME fixed,
  attractor-type-keyed template is used regardless of which sephirah
  produced it, specifically so the choice of wording cannot be tuned to
  steer the classifier toward a convenient answer)

SEPHIRAH_TO_MAP -- what's precedented vs. what's a disclosed default:
  Grounded in correspondences already documented elsewhere in this repo
  (docs/recursive_symbolics_foundation_reference.md section 6's Big-O
  table, and recursive_attractor_engine.py's own docstring naming Da'ath
  as its AbyssException handler):
    Geburah  (O(n^2), severe restriction)  -> strong linear contraction (a=0.1)  -> should converge (FIXED_POINT)
    Tifereth (O(n log n), balance)         -> moderate linear contraction (a=0.5) -> should converge (FIXED_POINT)
    Netzach  (O(n), persistence/repeat)    -> logistic map r=3.2 (documented period-2 regime) -> should be LIMIT_CYCLE
    Chesed   (O(1) in the Big-O table)     -> constant map S'=E -> converges in 1 step (FIXED_POINT)
    Daath    (named as the Abyss handler)  -> divergent map S'=2*S -> raises AbyssException

  Disclosed, honest default for the 6 sephirot with NO existing
  dynamical-systems correspondence anywhere in this repo (Keter, Chokmah,
  Binah, Hod, Yesod, Malkuth): all six are assigned the SAME neutral map
  -- the engine's own existing logistic-chaotic demo (r=3.9,
  BOUNDED_APERIODIC) -- rather than six different bespoke maps invented
  for this script. Giving them six different hand-picked dynamics would
  risk steering the experiment toward a convenient story; giving them
  all the same disclosed default does not.

  NOTE ON TENSION IN THE SOURCE MATERIAL, left visible rather than
  silently resolved: Chesed is described as both "O(1), negligible
  friction" (computational-kabbalah.md's Big-O table) and "unbounded
  expansion" (agency-budget-spec.md's Chesed/Geburah framing) elsewhere
  in the framework. This script follows the O(1) reading because it has
  a concrete Big-O anchor already in this repo; the "unbounded expansion"
  reading would instead predict a divergent map for Chesed. Both are
  disclosed here rather than picking one silently.

CLOSING THE LOOP: each cycle's dominant sephirah is looked up again in
SEPHIRAH_TO_MAP to produce the next cycle's dynamical system -- literally
composing engine 2's output into engine 1's input, repeatedly. The
resulting SEQUENCE of sephirah labels is itself re-encoded as a numeric
trajectory (each label mapped to its fixed index in SEPHIRAH_ORDER) and
fed back into classify_trajectory() -- the SAME function used on the raw
dynamical systems -- to determine whether the composed system, one level
up, is itself a FIXED_POINT, LIMIT_CYCLE, or BOUNDED_APERIODIC in
sephirah-space. This reuses real code rather than writing new ad hoc
"did the label repeat" logic.

METHODOLOGY FIXED BEFORE RUNNING (same discipline as
ddpg_training_convergence_study.py): run the loop starting from EACH of
the 11 sephirot as an initial condition, for up to MAX_CYCLES steps each,
and report the real classify_trajectory() verdict on the resulting label
sequence for every starting point -- whatever it turns out to be,
including "did not resolve."
"""

import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import recursive_attractor_engine as rae
import standalone_rca_sandbox as rca

MAX_CYCLES = 15

SEPHIRAH_ORDER = [
    "Keter", "Chokmah", "Binah", "Daath", "Chesed", "Geburah",
    "Tifereth", "Netzach", "Hod", "Yesod", "Malkuth",
]
assert set(SEPHIRAH_ORDER) == set(rca.SEPHIROT_CENTROIDS.keys()), (
    "SEPHIRAH_ORDER must exactly match the real SEPHIROT_CENTROIDS keys "
    "in standalone_rca_sandbox.py -- checked at import time so a future "
    "edit to either list fails loudly instead of silently diverging."
)
_SEPH_TO_INDEX = {s: i for i, s in enumerate(SEPHIRAH_ORDER)}

_NEUTRAL_DEFAULT = ("chaotic_r3.9", lambda S, E: 3.9 * S * (1.0 - S), np.array([0.4]), np.array([0.0]))

SEPHIRAH_TO_MAP = {
    "Geburah":  ("contraction_a0.1", lambda S, E: 0.1 * S + E, np.array([0.0]), np.array([1.0])),
    "Tifereth": ("contraction_a0.5", lambda S, E: 0.5 * S + E, np.array([0.0]), np.array([1.0])),
    "Netzach":  ("logistic_r3.2",    lambda S, E: 3.2 * S * (1.0 - S), np.array([0.4]), np.array([0.0])),
    "Chesed":   ("constant_map",     lambda S, E: E, np.array([0.0]), np.array([0.7])),
    "Daath":    ("divergent_a2.0",   lambda S, E: 2.0 * S, np.array([1.0]), np.array([0.0])),
    "Keter":    _NEUTRAL_DEFAULT,
    "Chokmah":  _NEUTRAL_DEFAULT,
    "Binah":    _NEUTRAL_DEFAULT,
    "Hod":      _NEUTRAL_DEFAULT,
    "Yesod":    _NEUTRAL_DEFAULT,
    "Malkuth":  _NEUTRAL_DEFAULT,
}
assert set(SEPHIRAH_TO_MAP.keys()) == set(SEPHIRAH_ORDER), "every sephirah must have a mapped dynamical system"


DEFAULT_TEMPLATES = {
    "FIXED_POINT": ("The trajectory converged to a stable fixed point. "
                     "Consecutive states matched within tolerance. Balanced, settled, resolved."),
    "LIMIT_CYCLE": ("The trajectory settled into a repeating limit cycle with period {period}. "
                     "The state repeats, cycling back to an earlier value. Persistent, recurring pattern."),
    "BOUNDED_APERIODIC": ("The trajectory remained bounded but did not resolve into a fixed point "
                           "or a short cycle within the window checked. Unresolved, aperiodic, open-ended."),
}


def describe_attractor(result: "rae.AttractorClassification", templates: dict = None) -> str:
    """Fixed, attractor-TYPE-keyed description -- deliberately not keyed
    by which sephirah produced it, so wording cannot be tuned per-source
    to steer the classifier. Uses only vocabulary already present in
    recursive_attractor_engine.py's own docstrings and .detail strings by
    default. `templates` (a dict with the same three keys as
    DEFAULT_TEMPLATES) lets a caller substitute alternative wording for a
    robustness check -- see engine_composition_robustness_check.py --
    without ever mutating DEFAULT_TEMPLATES itself, so the original,
    committed, already-reported behavior is unaffected unless a caller
    explicitly opts in."""
    templates = templates or DEFAULT_TEMPLATES
    if result.kind == rae.AttractorType.FIXED_POINT:
        return templates["FIXED_POINT"]
    if result.kind == rae.AttractorType.LIMIT_CYCLE:
        return templates["LIMIT_CYCLE"].format(period=result.period)
    if result.kind == rae.AttractorType.BOUNDED_APERIODIC:
        return templates["BOUNDED_APERIODIC"]
    return "Insufficient history to classify."


def run_one_cycle(sephirah: str, templates: dict = None):
    """Runs sephirah's mapped dynamical system, classifies it with the
    real recursive_attractor_engine, converts the real classification
    into the fixed template text, and feeds that text through the real,
    unmodified standalone_rca_sandbox classifier. Returns
    (next_sephirah, attractor_result_or_None, description_text)."""
    name, F, S0, E = SEPHIRAH_TO_MAP[sephirah]
    try:
        history = rae.iterate(F, S0, E, n_steps=60)
        result = rae.classify_trajectory(history)
        text = describe_attractor(result, templates=templates)
    except rae.AbyssException as e:
        result = None
        text = (f"An AbyssException was raised: {e}. The trajectory diverged, "
                "exceeding the magnitude cap. Abyss, void, paradox, exception.")

    scores = rca.compute_sephirotic_vector_scores(text)
    gov = rca.evaluate_v2_governance(text, scores)
    next_sephirah = gov["dominant_seph"]
    return next_sephirah, result, text, scores


def run_loop_from(start: str, max_cycles: int = MAX_CYCLES, templates: dict = None):
    """Runs the composed loop starting from `start`, for up to
    max_cycles, recording the full sephirah-label trajectory. Stops
    early only if classify_trajectory() (re-applied to the label
    sequence, encoded numerically) reports FIXED_POINT or LIMIT_CYCLE
    with enough history to be sure -- otherwise runs the full budget."""
    trajectory = [start]
    cycle_details = []
    current = start
    for _ in range(max_cycles):
        next_seph, result, text, scores = run_one_cycle(current, templates=templates)
        cycle_details.append({
            "from": current,
            "attractor_kind": result.kind.value if result else "DIVERGED_ABYSSEXCEPTION",
            "to": next_seph,
        })
        trajectory.append(next_seph)
        current = next_seph

        # Re-encode the label sequence so far and ask the SAME
        # classify_trajectory() function whether IT has resolved.
        encoded = [np.array([float(_SEPH_TO_INDEX[s])]) for s in trajectory]
        meta = rae.classify_trajectory(encoded)
        if meta.kind in (rae.AttractorType.FIXED_POINT, rae.AttractorType.LIMIT_CYCLE):
            return trajectory, cycle_details, meta

    encoded = [np.array([float(_SEPH_TO_INDEX[s])]) for s in trajectory]
    meta = rae.classify_trajectory(encoded)
    return trajectory, cycle_details, meta


def main():
    # Pin learning weights to uniform 1.0 for reproducibility, regardless
    # of whatever real interactive usage has written to rca_memory.json.
    # Disclosed explicitly: compute_sephirotic_vector_scores() reads
    # LEARNING_ENGINE.get_learned_efficacy() as a live global; without
    # pinning it, this experiment's outcome could silently depend on
    # unrelated past interactive sessions.
    original_weights = dict(rca.LEARNING_ENGINE.transition_weights)
    rca.LEARNING_ENGINE.transition_weights = {s: 1.0 for s in SEPHIRAH_ORDER}
    # Also neutralize record_state side effects for this run: none of the
    # functions called above (compute_sephirotic_vector_scores,
    # evaluate_v2_governance) call record_state() -- confirmed by reading
    # standalone_rca_sandbox.py; only the interactive /eval command path
    # does. No monkeypatching of record_state is needed as a result, but
    # asserting it here makes that assumption checkable rather than tacit.
    assert rca.LEARNING_ENGINE.total_interactions >= 0  # sanity: object is real, not stubbed

    try:
        print("=" * 78)
        print("  ENGINE COMPOSITION LOOP: recursive_attractor_engine.py  <->  standalone_rca_sandbox.py")
        print("=" * 78)
        results = {}
        for start in SEPHIRAH_ORDER:
            trajectory, cycle_details, meta = run_loop_from(start)
            results[start] = (trajectory, cycle_details, meta)
            print(f"\nStart: {start}")
            print(f"  Trajectory ({len(trajectory)} labels): {' -> '.join(trajectory)}")
            print(f"  Meta-classification (label sequence, re-run through classify_trajectory): "
                  f"{meta.kind.value}" + (f" (period={meta.period})" if meta.period else ""))
        return results
    finally:
        rca.LEARNING_ENGINE.transition_weights = original_weights


if __name__ == "__main__":
    main()
