#!/usr/bin/env python3
"""
consciousness_upgrade_groundedness.py

Grounds Stage 4 ("Groundedness / Levity") of the pasted "Consciousness
Upgrade Protocol" document in real, checkable mechanics -- and explicitly
NOT in the document's own `levity_sync.py` proposal, which was checked and
found internally inconsistent: its prose claims to read
`/sys/class/thermal/thermal_zone*/temp` (a real Linux path), but the
`compute_gamma()` code shown only calls `os.getloadavg()` and an undefined
`read_symbolic_entropy()` -- description and code don't match each other,
and neither has any connection to the two REAL, already-VERIFIED gamma
implementations elsewhere in this project (both are text/logit-entropy
based, not hardware telemetry). Reusing the name "gamma" for a third,
unrelated, unverified quantity would imply a false equivalence with
already-tested code. Nothing here computes a "gamma"; the vocabulary is
deliberately different.

WHAT "GROUNDEDNESS" HONESTLY MEANS HERE: this project's entire discipline
(the Register A / Register B split, the correspondence-ledger VERIFIED /
UNTESTABLE / FAILED taxonomy, "checked and reverted, not just described")
already IS a groundedness practice; Stage 4 just makes one piece of it a
runnable check rather than leaving it as a norm to remember to follow. A
Claim here isn't just a labelled belief -- it's a statement paired with
the name of an EXISTING unittest test that's supposed to back it. Running
`check_claims()` does not trust whatever status was last recorded; it
actually re-executes each cited test, right now, as a fresh subprocess
(the same subprocess-isolation approach `correspondence_ledger.py`'s
`from_script_exit_code()` already uses for exit-code-only test scripts),
and classifies the claim from what really happens:

  GROUNDED         -- the cited test exists and passes right now.
  UNGROUNDED       -- the cited test exists, ran, and genuinely failed
                      (a real AssertionError or similar), not a reference
                      problem.
  BROKEN_REFERENCE -- the cited test/module doesn't exist or can't be
                      imported (unittest's loader reports this via a
                      distinct, checkable marker,
                      `unittest.loader._FailedTest`, in its own output --
                      confirmed empirically, not assumed, before this
                      distinction was built: see hand-verification doc).
  UNTESTABLE       -- no test was cited for this claim at all.

BROKEN_REFERENCE is kept distinct from UNGROUNDED on purpose: "the test
exists and really fails" and "the claim points at something that isn't
there" are different failure modes with different fixes, and conflating
them (as an exit-code-only check would) would lose real information --
the same anti-conflation discipline as constraint_pruner.py distinguishing
a malformed single constraint from a genuinely unsatisfiable set.

groundedness_ratio() is deliberately `Optional[float]`: if there are zero
GROUNDED-or-UNGROUNDED claims (everything is UNTESTABLE or
BROKEN_REFERENCE), the ratio is `None`, not silently 0.0 or vacuously 1.0
-- the same anti-vacuous-truth convention `find_unsatisfiable_beliefs()`
and `correspondence_ledger.py`'s all-UNTESTABLE guard already use.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

GROUNDED = "GROUNDED"
UNGROUNDED = "UNGROUNDED"
BROKEN_REFERENCE = "BROKEN_REFERENCE"
UNTESTABLE = "UNTESTABLE"

_LOADER_FAILURE_MARKER = "unittest.loader._FailedTest"


@dataclass(frozen=True)
class Claim:
    """A statement paired with the dotted name of the unittest test that
    is supposed to back it, e.g. 'test_consciousness_upgrade_pattern_registry.TestExactStateReversion.test_reverting_to_initial_state_is_detected'.
    `dotted_test_name=None` means the claim is explicitly untestable
    (a design choice, a value judgment, a Register A statement) rather
    than an oversight -- stated, not implied."""
    text: str
    dotted_test_name: Optional[str] = None


@dataclass(frozen=True)
class ClaimResult:
    claim: Claim
    status: str
    detail: str


def check_claim(claim: Claim, cwd: Optional[str] = None, timeout: float = 30.0) -> ClaimResult:
    """Actually runs the claim's cited test, right now, as a fresh
    subprocess -- does not trust any previously-recorded status. Returns
    which of the four real outcomes actually happened."""
    if claim.dotted_test_name is None:
        return ClaimResult(claim, UNTESTABLE, "No test cited for this claim.")

    proc = subprocess.run(
        [sys.executable, "-m", "unittest", claim.dotted_test_name],
        cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )
    combined_output = proc.stdout + proc.stderr

    if proc.returncode == 0:
        return ClaimResult(
            claim, GROUNDED,
            f"'{claim.dotted_test_name}' passed just now (exit 0)."
        )
    if _LOADER_FAILURE_MARKER in combined_output:
        return ClaimResult(
            claim, BROKEN_REFERENCE,
            f"'{claim.dotted_test_name}' could not be loaded (unittest's "
            f"loader reported {_LOADER_FAILURE_MARKER!r}) -- the cited "
            f"test/module doesn't exist or can't be imported."
        )
    return ClaimResult(
        claim, UNGROUNDED,
        f"'{claim.dotted_test_name}' ran and genuinely failed just now "
        f"(exit {proc.returncode})."
    )


def check_claims(claims: List[Claim], cwd: Optional[str] = None) -> List[ClaimResult]:
    """Checks every claim independently -- one subprocess per claim, so
    one test's import error or crash can't take down the whole batch."""
    return [check_claim(c, cwd=cwd) for c in claims]


@dataclass(frozen=True)
class GroundednessReport:
    grounded: int
    ungrounded: int
    broken_reference: int
    untestable: int

    def groundedness_ratio(self) -> Optional[float]:
        """Fraction of TESTABLE, RESOLVABLE claims that are actually
        grounded right now. Denominator deliberately excludes
        UNTESTABLE (never claimed to be checkable) and BROKEN_REFERENCE
        (a different problem -- a citation error, not a failed check).
        Returns None, not 0.0 or 1.0, when the denominator is zero."""
        denom = self.grounded + self.ungrounded
        if denom == 0:
            return None
        return self.grounded / denom

    def summary_line(self) -> str:
        ratio = self.groundedness_ratio()
        ratio_str = f"{ratio:.3f}" if ratio is not None else "N/A (no resolvable testable claims)"
        return (
            f"GROUNDED={self.grounded} UNGROUNDED={self.ungrounded} "
            f"BROKEN_REFERENCE={self.broken_reference} UNTESTABLE={self.untestable} "
            f"groundedness_ratio={ratio_str}"
        )


def summarize(results: List[ClaimResult]) -> GroundednessReport:
    return GroundednessReport(
        grounded=sum(1 for r in results if r.status == GROUNDED),
        ungrounded=sum(1 for r in results if r.status == UNGROUNDED),
        broken_reference=sum(1 for r in results if r.status == BROKEN_REFERENCE),
        untestable=sum(1 for r in results if r.status == UNTESTABLE),
    )


if __name__ == "__main__":
    import os

    print("=" * 78)
    print("  CONSCIOUSNESS UPGRADE PROTOCOL -- STAGE 4: GROUNDEDNESS")
    print("=" * 78)

    here = os.path.dirname(os.path.abspath(__file__))

    claims = [
        Claim(
            "Stage 1's tamper detector catches an undisclosed edit.",
            "test_consciousness_upgrade_self_signature.TestSignatureCreationAndVerification.test_hand_edited_values_without_recomputed_hash_fails_verification",
        ),
        Claim(
            "Stage 2 correctly reports the document's own 'please everyone' example as unsatisfiable.",
            "test_consciousness_upgrade_constraint_pruner.TestSatisfiabilityAgainstBruteForce.test_the_documents_own_please_everyone_example_is_unsatisfiable",
        ),
        Claim(
            "Stage 3 detects exact state reversion.",
            "test_consciousness_upgrade_pattern_registry.TestExactStateReversion.test_reverting_to_initial_state_is_detected",
        ),
        Claim(
            "A deliberately fabricated claim, cited to a test that doesn't exist.",
            "test_consciousness_upgrade_pattern_registry.TestExactStateReversion.test_this_test_does_not_actually_exist",
        ),
        Claim(
            "The pasted document's Stage 4 concept ('groundedness matters') is a design value, not a testable proposition on its own.",
            None,
        ),
    ]

    results = check_claims(claims, cwd=here)
    for r in results:
        print(f"\n[{r.status}] {r.claim.text}")
        print(f"  {r.detail}")

    report = summarize(results)
    print("\n" + "-" * 78)
    print(report.summary_line())
