#!/usr/bin/env python3
# Ported from Thoth/solo (ledgers/correspondence_ledger.py), written for that repo by OmnisMutus.
# Kept as it is in substance: a claim is pattern + target + meaning with a validator that re-runs an
# existing adversarially-tested check, validator=None means untestable in principle, and a ledger of
# nothing but UNTESTABLE rows can never report success.
"""
correspondence_ledger.py
Generic framework for the pattern this repo has now applied by hand three
times (sephirotic_reward_engine.py, standalone_rca_sandbox.py, the
Kabbalistic Lens in studies/EXERCISES.md): an external symbolic pattern
(a Sephirotic name) meets a technical system, a specific translation claim
gets made about it, that claim gets adversarially tested where it CAN be
tested, and the boundary between tested and untestable correspondences
gets stated explicitly rather than left implicit.

This module makes that four-step shape a first-class, runnable object
instead of prose scattered across docstrings and markdown. A
Correspondence is a single claim: "pattern X applied to technical target Y
means Z." Running a CorrespondenceLedger walks every registered claim and
either runs its validator (an adversarially-tested check) or marks it
UNTESTABLE -- and, critically, a ledger where every entry is UNTESTABLE
can never report overall success. That's the same honesty-guard principle
already used in test_all_engines.py (RAN_ONLY is not VERIFIED) and
test_reconstructed_frameworks_comparison.py (all-skipped is not passing).

This is deliberately NOT a competing test framework. Validators are meant
to be thin wrappers that re-run EXISTING, already break-it-proofed
unittest test methods -- see sephirotic_correspondence_ledger.py for the
worked example against sephirotic_reward_engine.py. The ledger's job is
only to make the mapping between "this metaphor" and "this proof" (or
explicit absence of proof) enumerable in one place.

Not every test file in this repo uses unittest.TestCase, though -- some
(test_ddpg_quadcopter_rca_engine.py, test_dht_rca_node.py) use a simpler
module-level check()/PASS/FAIL script style, executed top-to-bottom, with
a nonzero exit code on any failure. from_unittest_methods() can't wrap
those (there's no TestCase class to instantiate a method on), so
from_script_exit_code() below re-runs the whole script as a subprocess
and treats its real exit code as ground truth -- still reusing an
existing, already-tested script rather than re-implementing its checks,
just at script granularity instead of method granularity. See
ddpg_correspondence_ledger.py for the worked example.
"""

import sys
import subprocess
import unittest
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence


STATUS_VERIFIED = "VERIFIED"
STATUS_FAILED = "FAILED"
STATUS_UNTESTABLE = "UNTESTABLE"
STATUS_UNCHECKED = "UNCHECKED"

STATUS_ICON = {
    STATUS_VERIFIED: "[OK]",
    STATUS_FAILED: "[X]",
    STATUS_UNTESTABLE: "[--]",
    STATUS_UNCHECKED: "[ ]",
}


@dataclass
class ValidationResult:
    """What a validator returns: whether the claim held, and why."""
    passed: bool
    detail: str = ""


@dataclass
class Correspondence:
    """One claimed mapping between an external pattern and a technical
    target. `validator` is None for claims that are explicitly out of
    scope for testing (analogical/philosophical), not for claims someone
    just hasn't gotten around to testing yet -- if it's testable, it
    should have a validator; if it can't be tested even in principle,
    that's what None means here."""
    pattern: str
    target: str
    claim: str
    validator: Optional[Callable[[], ValidationResult]] = None
    status: str = STATUS_UNCHECKED
    detail: str = ""


class CorrespondenceLedger:
    def __init__(self, name: str):
        self.name = name
        self.entries: List[Correspondence] = []

    def register(self, pattern: str, target: str, claim: str,
                 validator: Optional[Callable[[], ValidationResult]] = None) -> Correspondence:
        c = Correspondence(pattern=pattern, target=target, claim=claim, validator=validator)
        self.entries.append(c)
        return c

    def run(self) -> None:
        for c in self.entries:
            if c.validator is None:
                c.status = STATUS_UNTESTABLE
                c.detail = "no validator registered -- analogical/philosophical claim, out of scope by design"
                continue
            try:
                result = c.validator()
            except Exception as e:
                c.status = STATUS_FAILED
                c.detail = f"validator raised {type(e).__name__}: {e}"
                continue
            c.status = STATUS_VERIFIED if result.passed else STATUS_FAILED
            c.detail = result.detail

    def all_testable_passed(self) -> bool:
        """HONESTY GUARD: a ledger consisting entirely of UNTESTABLE
        entries must not be able to report success -- that would let an
        entirely unverified metaphor claim 'passing' status with zero
        actual checks run, same failure mode as unittest's
        wasSuccessful() returning True when every test was skipped."""
        testable = [c for c in self.entries if c.status != STATUS_UNTESTABLE]
        if not testable:
            return False
        return all(c.status == STATUS_VERIFIED for c in testable)

    def report(self) -> str:
        lines = []
        lines.append("=" * 72)
        lines.append(f"  CORRESPONDENCE LEDGER: {self.name}")
        lines.append("=" * 72)
        for c in self.entries:
            icon = STATUS_ICON[c.status]
            lines.append(f"\n {icon} {c.pattern}  ->  {c.target}")
            lines.append(f"     Claim  : {c.claim}")
            lines.append(f"     Status : {c.status}")
            if c.detail:
                lines.append(f"     Detail : {c.detail}")
        verified = sum(1 for c in self.entries if c.status == STATUS_VERIFIED)
        failed = sum(1 for c in self.entries if c.status == STATUS_FAILED)
        untestable = sum(1 for c in self.entries if c.status == STATUS_UNTESTABLE)
        total = len(self.entries)
        lines.append("\n" + "=" * 72)
        lines.append(" SUMMARY")
        lines.append("=" * 72)
        lines.append(f"  Total correspondences  : {total}")
        lines.append(f"  VERIFIED               : {verified} / {total}")
        lines.append(f"  FAILED                 : {failed} / {total}")
        lines.append(f"  UNTESTABLE (by design)  : {untestable} / {total}")
        lines.append("")
        lines.append("  Honest claim this run supports:")
        lines.append(f"    {verified} of {total} correspondence claims were adversarially checked")
        lines.append(f"    and held. {untestable} of {total} are explicitly out of scope for testing")
        lines.append(f"    (analogical, not falsifiable by code) -- their absence from the")
        lines.append(f"    VERIFIED count is not a defect, it's the point of this framework.")
        if failed:
            lines.append(f"    {failed} of {total} FAILED -- the claimed correspondence does NOT")
            lines.append(f"    currently hold against its own stated definition.")
        lines.append("=" * 72)
        return "\n".join(lines)


def from_unittest_methods(test_case_cls, method_names: List[str]) -> Callable[[], ValidationResult]:
    """Build a validator that re-runs existing unittest test methods
    rather than re-implementing assertions. Every method must pass for
    the correspondence to be VERIFIED; failures are named in the detail
    so a FAILED status says exactly which sub-check broke, not just that
    something did."""
    def validator() -> ValidationResult:
        failed = []
        for name in method_names:
            suite = unittest.TestSuite([test_case_cls(name)])
            result = unittest.TestResult()
            suite.run(result)
            if not result.wasSuccessful():
                failed.append(name)
        if failed:
            return ValidationResult(False, f"failed sub-checks ({len(failed)}/{len(method_names)}): {', '.join(failed)}")
        return ValidationResult(True, f"{len(method_names)}/{len(method_names)} sub-checks passed")
    return validator


def from_script_exit_code(script_path, args: Optional[Sequence[str]] = None) -> Callable[[], ValidationResult]:
    """Build a validator that re-runs an EXISTING script-style test file
    (module-level check()/PASS/FAIL, exit(1) on any failure -- e.g.
    test_ddpg_quadcopter_rca_engine.py, test_dht_rca_node.py) as a real
    subprocess, exactly as test_all_engines.py does, and treats its real
    exit code as ground truth. Coarser than from_unittest_methods(): a
    script like this has no named sub-checks to select individually, so
    one call here speaks for everything the script checks, not one
    specific claim -- callers should say so honestly in the
    Correspondence's `claim` text rather than implying method-level
    granularity that doesn't exist for this style of test.

    Runs with cwd set to the script's own directory so its relative
    imports resolve the same way they do under test_all_engines.py."""
    script_path = Path(script_path)
    def validator() -> ValidationResult:
        cmd = [sys.executable, str(script_path)] + list(args or [])
        result = subprocess.run(cmd, capture_output=True, text=True,
                                 cwd=str(script_path.parent), timeout=120)
        if result.returncode != 0:
            tail_lines = (result.stdout + result.stderr).strip().splitlines()[-5:]
            return ValidationResult(False, f"{script_path.name} exited {result.returncode} -- tail: " +
                                     " | ".join(tail_lines))
        return ValidationResult(True, f"{script_path.name} exited 0 (full script passed)")
    return validator
