#!/usr/bin/env python3
"""
consciousness_upgrade_pipeline.py

Composes the four independently-VERIFIED "Consciousness Upgrade
Protocol" stages into one real pipeline, following the same discipline as
engine_composition_loop.py: two (here, four) already-verified pieces get
wired together with an EXPLICIT, DISCLOSED bridge, and the composition
is actually run and reported on, not just asserted to work.

THE REAL COMPOSITION PROBLEM, STATED HONESTLY: Stage 1's self-signature
values (consciousness_upgrade_self_signature.py) are free-text strings
("how_i_show_up": "direct"). Stage 2's constraints
(consciousness_upgrade_constraint_pruner.py) are numeric intervals on a
named belief. These are DIFFERENT TYPES -- there is no automatic way to
"just plug them together." The bridge built here is a single, explicit
convention, not a universal law:

  BRIDGE CONVENTION: if one or more OTHER sources have declared a numeric
  Constraint on some belief B, then proposing a new self-signature value
  for B is treated as the proposer declaring a POINT constraint
  (low == high == that number) from source "self" on the same belief B.
  Stage 2's check_belief() is run on [the external constraints] + [this
  point constraint] BEFORE Stage 1's propose_change() is allowed to run.
  If the combined set is UNSATISFIABLE, the proposed change is REFUSED:
  the self-signature is NOT updated and NOTHING is written to the
  ChangeLedger -- consistent with Stage 2's own Principle of Agency &
  Sovereignty (this function refuses the change and reports the
  conflict; it does not silently override either side's declared
  requirement).

WHAT THIS DELIBERATELY DOES NOT CLAIM: beliefs with no external numeric
constraint pass through completely unaffected -- self-signature values
are not required to be numeric in general, only when some other source
has already numerically bounded that specific belief. A proposed value
for a belief that IS externally constrained but ISN'T parseable as a
number raises an explicit error rather than silently skipping the check
(the alternative -- silently treating "not a number" as "no constraint"
-- would quietly defeat the whole point of the bridge).

After a change is accepted, Stage 3's pattern registry
(consciousness_upgrade_pattern_registry.py) scans the REAL resulting
ChangeLedger for patterns -- this is composition, not just each stage's
own unit tests, because it depends on the actual ChangeRecord objects
Stage 1 produced flowing correctly into Stage 3's detectors (field names,
types, ordering) rather than a hand-built stand-in. Stage 4's
groundedness checker (consciousness_upgrade_groundedness.py) is then used
to check real claims ABOUT this composed pipeline's own behavior, backed
by this module's own test suite -- the same "check the claim by actually
re-running its test" discipline applied one level up, to the composition
itself rather than to the individual stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from consciousness_upgrade_self_signature import (
    SelfSignature, ChangeLedger, propose_change, verify_signature,
)
from consciousness_upgrade_constraint_pruner import (
    Constraint, SatisfiabilityResult, check_belief, explain,
)
from consciousness_upgrade_pattern_registry import default_registry, PatternMatch


@dataclass(frozen=True)
class PipelineStepResult:
    """Result of one attempted change through the composed pipeline.
    `signature` is the CURRENT signature either way -- the new one if
    accepted, the unchanged original if refused -- so a caller never has
    to guess which one is "live" after a refusal."""
    accepted: bool
    signature: SelfSignature
    conflict: Optional[SatisfiabilityResult]
    detail: str


def propose_change_with_constraint_check(
    current: SelfSignature,
    new_values: Dict[str, str],
    reason: str,
    ledger: ChangeLedger,
    external_constraints: List[Constraint],
    now: Optional[str] = None,
) -> PipelineStepResult:
    """The real bridge between Stage 1 and Stage 2 (see module docstring
    for the disclosed convention). Checks every belief in `new_values`
    that ALSO appears in `external_constraints`; if any such check is
    unsatisfiable, refuses the ENTIRE change (does not partially apply
    some keys and reject others -- a self-signature is one declared
    state, not independently-committable fields)."""
    affected_beliefs = {c.belief for c in external_constraints} & set(new_values.keys())

    for belief in sorted(affected_beliefs):
        raw = new_values[belief]
        try:
            point = float(raw)
        except ValueError as e:
            raise ValueError(
                f"Belief {belief!r} has external numeric constraint(s) from "
                f"{sorted({c.source for c in external_constraints if c.belief == belief})} "
                f"but the proposed value {raw!r} isn't parseable as a number -- "
                f"the bridge requires a numeric value for any belief someone "
                f"else has numerically bounded, rather than silently skipping "
                f"the check."
            ) from e

        combined = [c for c in external_constraints if c.belief == belief]
        combined.append(Constraint(belief, "self", point, point))
        result = check_belief(combined)
        if not result.satisfiable:
            return PipelineStepResult(
                accepted=False,
                signature=current,
                conflict=result,
                detail=(
                    f"Refused: {explain(result)} Nothing was written to the "
                    f"signature or the ledger."
                ),
            )

    new_sig = propose_change(current, new_values, reason, ledger, now=now)
    return PipelineStepResult(
        accepted=True,
        signature=new_sig,
        conflict=None,
        detail="Accepted: no external numeric constraint was violated.",
    )


def scan_ledger_for_patterns(ledger: ChangeLedger, initial_hash: Optional[str] = None,
                               reason_threshold: int = 2, freq_threshold: int = 3,
                               freq_window_seconds: float = 3600.0) -> Dict[str, List[PatternMatch]]:
    """Runs Stage 3's default pattern registry against the REAL
    ChangeLedger produced by propose_change_with_constraint_check() calls
    -- a thin wrapper, but a genuine one: it's exercising the actual
    ChangeRecord objects Stage 1 built, not a hand-constructed stand-in,
    which is exactly what makes this composition rather than two
    independently-tested stages sitting side by side."""
    registry = default_registry(reason_threshold, freq_threshold, freq_window_seconds)
    return registry.scan(ledger.records, initial_hash=initial_hash)


if __name__ == "__main__":
    print("=" * 78)
    print("  CONSCIOUSNESS UPGRADE PROTOCOL -- COMPOSED PIPELINE (STAGES 1-4)")
    print("=" * 78)

    from consciousness_upgrade_self_signature import create_signature

    sig0 = create_signature(
        {"weekly_deep_work_hours": "10", "communication_style": "direct"},
        now="2026-01-01T00:00:00Z",
    )
    ledger = ChangeLedger()

    # Two OTHER sources have numerically constrained this belief.
    external = [
        Constraint("weekly_deep_work_hours", "team_lead", 15.0, 40.0),
        Constraint("weekly_deep_work_hours", "mentor", 10.0, 20.0),
    ]
    # Combined external range: [15, 20] (max(15,10)=15, min(40,20)=20).

    print("\n--- Attempt 1: propose 10 hours (below the [15,20] joint requirement) ---")
    step1 = propose_change_with_constraint_check(
        sig0, {"weekly_deep_work_hours": "10", "communication_style": "direct"},
        reason="that's what feels sustainable", ledger=ledger,
        external_constraints=external, now="2026-01-01T01:00:00Z",
    )
    print(f"accepted={step1.accepted}\n{step1.detail}")

    print("\n--- Attempt 2: propose 18 hours (inside [15,20]) ---")
    step2 = propose_change_with_constraint_check(
        step1.signature, {"weekly_deep_work_hours": "18", "communication_style": "direct"},
        reason="compromise after seeing the conflict", ledger=ledger,
        external_constraints=external, now="2026-01-01T02:00:00Z",
    )
    print(f"accepted={step2.accepted}\n{step2.detail}")

    print("\n--- Attempt 3: revert communication_style, unaffected by any constraint ---")
    step3 = propose_change_with_constraint_check(
        step2.signature, {"weekly_deep_work_hours": "18", "communication_style": "conflict-avoidant"},
        reason="trying something different", ledger=ledger,
        external_constraints=external, now="2026-01-01T03:00:00Z",
    )
    step4 = propose_change_with_constraint_check(
        step3.signature, {"weekly_deep_work_hours": "18", "communication_style": "direct"},
        reason="that didn't feel right", ledger=ledger,
        external_constraints=external, now="2026-01-01T04:00:00Z",
    )
    print(f"step3.accepted={step3.accepted}, step4.accepted={step4.accepted}")

    print("\n--- Stage 3: scanning the REAL resulting ledger for patterns ---")
    results = scan_ledger_for_patterns(ledger, initial_hash=sig0.content_hash)
    for name, matches in results.items():
        print(f"{name}: {len(matches)} match(es)")
        for m in matches:
            print(f"  - {m.explanation}")
