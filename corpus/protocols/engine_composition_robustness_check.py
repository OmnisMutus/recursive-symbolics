#!/usr/bin/env python3
"""
engine_composition_robustness_check.py

Follow-up to engine_composition_loop_report.md's "What would make this a
stronger result" section: is the reported "9/11 starting points converge
to the same Chesed<->Binah cycle" finding robust, or an artifact of one
specific wording choice and one specific dict-ordering tie-break?

Two checks, both run for real rather than reasoned about in the abstract:

1. TIE-BREAK RULE CHECK: does switching from "first in SEPHIROT_CENTROIDS'
   dict order" to "first alphabetically" change which sephirah wins the
   real FIXED_POINT-description 3-way tie (Binah/Tifereth/Hod, all at
   0.3)? This does not touch standalone_rca_sandbox.py at all -- it reads
   the real, unmodified scores dict and applies a second, disclosed
   tie-break rule to it directly.

2. WORDING ROBUSTNESS CHECK: three alternative, independently-chosen
   FIXED_POINT descriptions (NOT reverse-engineered to favor any
   particular sephirah -- chosen as ordinary synonyms for "reached a
   stationary value," decided before any of them were scored) are
   substituted via engine_composition_loop.describe_attractor()'s
   `templates` parameter (added specifically so this check doesn't
   require mutating the original, already-reported DEFAULT_TEMPLATES),
   and the full 11-starting-point composition is rerun under each,
   exactly as in the original report.

Reports whatever actually happens under each variant -- including if the
convergence pattern breaks down entirely -- per the same discipline
named in the original report rather than adjusting anything after
seeing a result.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import standalone_rca_sandbox as rca
import engine_composition_loop as ecl

ORIGINAL_FIXED_POINT_TEXT = ecl.DEFAULT_TEMPLATES["FIXED_POINT"]

# Chosen independently, before scoring any of them -- ordinary synonyms
# for "the trajectory reached and stayed at one value," deliberately NOT
# picked by checking which sephirah they'd favor first.
ALTERNATIVE_FIXED_POINT_TEXTS = {
    "mathematical_plain": (
        "The trajectory reached a stationary point. The value stopped "
        "changing between iterations. Constant, unchanging, static."
    ),
    "everyday_plain": (
        "The system arrived at a single value and stayed there. No "
        "further change occurred. Steady-state, equilibrium, motionless."
    ),
    "minimal": (
        "The output stopped changing. It is now constant."
    ),
}


def check_tie_break_rule():
    print("=" * 78)
    print("  CHECK 1: does an alphabetical tie-break change the ORIGINAL winner?")
    print("=" * 78)
    rca.LEARNING_ENGINE.transition_weights = {s: 1.0 for s in rca.SEPHIROT_CENTROIDS}
    scores = rca.compute_sephirotic_vector_scores(ORIGINAL_FIXED_POINT_TEXT)
    maxscore = max(scores.values())
    tied_dict_order = [s for s in rca.SEPHIROT_CENTROIDS if scores[s] == maxscore]
    tied_alpha_order = sorted(tied_dict_order)
    print(f"  Tied sephirot at max score {maxscore}: {tied_dict_order} (dict order)")
    print(f"  Same set, alphabetical:                 {tied_alpha_order}")
    print(f"  Dict-order winner:      {tied_dict_order[0]}")
    print(f"  Alphabetical winner:    {tied_alpha_order[0]}")
    if tied_dict_order[0] == tied_alpha_order[0]:
        print("  RESULT: SAME winner either way -- this particular tie-break rule")
        print("  change would NOT have altered the reported result. The dict-order")
        print("  explanation is real, but alphabetical order was never a genuinely")
        print("  different alternative for THIS specific tie.")
    else:
        print("  RESULT: DIFFERENT winner -- the tie-break rule genuinely matters here.")
    print()


def check_wording_robustness():
    print("=" * 78)
    print("  CHECK 2: do independently-chosen alternative FIXED_POINT wordings")
    print("  change which sephirah wins, and does the 9/11 convergence hold?")
    print("=" * 78)

    variants = {"original": ORIGINAL_FIXED_POINT_TEXT, **ALTERNATIVE_FIXED_POINT_TEXTS}
    summary = {}
    for name, text in variants.items():
        rca.LEARNING_ENGINE.transition_weights = {s: 1.0 for s in rca.SEPHIROT_CENTROIDS}
        scores = rca.compute_sephirotic_vector_scores(text)
        winner = max(scores, key=lambda s: scores[s])
        print(f"\n--- Variant: {name!r} ---")
        print(f"  Text: {text}")
        top = sorted(scores.items(), key=lambda kv: -kv[1])[:3]
        print(f"  Top 3 scores: {top}")
        print(f"  Winner (as evaluate_v2_governance would pick it): {winner}")

        templates = dict(ecl.DEFAULT_TEMPLATES)
        templates["FIXED_POINT"] = text
        original_weights = dict(rca.LEARNING_ENGINE.transition_weights)
        rca.LEARNING_ENGINE.transition_weights = {s: 1.0 for s in ecl.SEPHIRAH_ORDER}
        cycle_outcomes = {}
        try:
            for start in ecl.SEPHIRAH_ORDER:
                trajectory, cycle_details, meta = ecl.run_loop_from(start, templates=templates)
                cycle_outcomes[start] = tuple(trajectory)
        finally:
            rca.LEARNING_ENGINE.transition_weights = original_weights

        distinct_final_cycles = {}
        for start, traj in cycle_outcomes.items():
            key = tuple(sorted(set(traj[-2:])))  # the 2-cycle (or singleton) it settled into
            distinct_final_cycles.setdefault(key, []).append(start)
        print(f"  Distinct final cycles across all 11 starting points: {len(distinct_final_cycles)}")
        for cyc, starts in distinct_final_cycles.items():
            print(f"    {cyc}: reached by {len(starts)}/11 starting points {starts}")
        summary[name] = distinct_final_cycles

    print("\n" + "=" * 78)
    print("  CROSS-VARIANT SUMMARY")
    print("=" * 78)
    original_dominant = max(summary["original"].items(), key=lambda kv: len(kv[1]))
    print(f"  Original wording's dominant cycle: {original_dominant[0]} "
          f"({len(original_dominant[1])}/11 starting points)")
    all_same = True
    for name, cycles in summary.items():
        if name == "original":
            continue
        dominant = max(cycles.items(), key=lambda kv: len(kv[1]))
        matches = "MATCHES original" if set(dominant[0]) == set(original_dominant[0]) else "DIFFERENT from original"
        print(f"  {name!r} dominant cycle: {dominant[0]} ({len(dominant[1])}/11) -- {matches}")
        if set(dominant[0]) != set(original_dominant[0]):
            all_same = False

    print()
    if all_same:
        print("  HONEST CONCLUSION: the dominant Chesed<->Binah cycle held across every")
        print("  independently-worded FIXED_POINT description tried. This is stronger")
        print("  evidence that the convergence is not purely a one-wording artifact --")
        print("  though it does not rule out that ALL four wordings tried happen to")
        print("  share some other stem/keyword overlap with Binah or Chesed not yet")
        print("  identified. Not claimed as proof; reported as what was actually found.")
    else:
        print("  HONEST CONCLUSION: the dominant cycle CHANGED under at least one")
        print("  independently-worded alternative. This confirms the original report's")
        print("  caution was warranted -- the 9/11 convergence was sensitive to the")
        print("  specific wording chosen, not a robust property of the composed system.")


if __name__ == "__main__":
    check_tie_break_rule()
    check_wording_robustness()
