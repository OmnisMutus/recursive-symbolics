#!/usr/bin/env python3
"""
run_all_correspondence_ledgers.py
Master aggregate runner for the philosophical layer, mirroring what
test_all_engines.py already does for the 24 engines: one command that
gives the complete picture instead of running 5 separate ledger scripts
by hand and hoping nothing was missed.

Before this script existed, seeing the full state of all 5 correspondence
ledgers (sephirotic_correspondence_ledger.py, attractor_correspondence_ledger.py,
rca_sandbox_gamma_correspondence_ledger.py, ddpg_correspondence_ledger.py,
glyph_emotion_correspondence_ledger.py) required running each one
individually. That made it easy to check the engine layer
(test_all_engines.py) while never touching the philosophical layer at
all -- exactly what happened in the first Gemini status report checked
in GEMINI_EXPERIMENT_LOG.md, which reported the engine scoreboard and
said nothing about the ledgers.

## On "expected" failures

CORRECTION (dated, see LIBER_0.md): ddpg_correspondence_ledger.py's
"Tiphereth / Binah (Actor-Critic Reconciliation)" correspondence used to
be DELIBERATELY registered as FAILED here -- the underlying claim ("the
actor and critic are genuinely trained end-to-end") really was false,
and this project's discipline was to say so rather than hide it. That
gap is now genuinely fixed (real backprop through every layer of both
networks, a real deterministic policy gradient for the actor, and a
second, previously undiscovered LayerNorm-degenerate bug in the critic's
output layer fixed alongside it), so `KNOWN_EXPECTED_FAILURES` below is
now empty. It's kept as a live mechanism, not deleted, for the same
reason it existed in the first place:

A naive aggregate runner that just checks "did anything fail" would
either (a) report a scary-looking failure for a gap that's already
known, documented, and not a regression, or (b) have to be told to
ignore ALL failures, which would silently swallow a real new one if a
different ledger broke tomorrow.

This script resolves that by keeping an explicit, small, named list --
KNOWN_EXPECTED_FAILURES -- the same pattern test_all_engines.py already
uses for SUPPLEMENTARY_TEST_SUITES (an explicit exception list, not a
blanket rule). A FAILED entry NOT in that list is reported as an
UNEXPECTED FAILURE and fails this script's exit code. A FAILED entry
that IS in the list is reported plainly as a known gap, not an alarm.
And if an entry in the list stops failing, that's flagged too -- either
the gap got fixed for real (good news, update this list) or something
else changed that's worth a second look. (This is exactly what happened
with the DDPG entry: it stopped failing because the gap was actually
fixed, not because the check weakened -- confirmed by two break-it
proofs in LIBER_0.md's dated entry on this fix.)

## Design note

The aggregation logic (`run_ledgers()`) is deliberately separate from
reporting (`print_report()`), the same split `CorrespondenceLedger`
itself uses between `.run()` and `.report()`. This is what makes
test_run_all_correspondence_ledgers.py able to test the unexpected/
resolved-failure detection logic directly, against hand-built toy
ledgers with known outcomes, without needing to capture stdout.

Usage:
    python run_all_correspondence_ledgers.py
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Set, Tuple

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
# Ledgers now live in ledgers/ and cross-import their engines from engines/
# (the engines/protocols/ledgers/tests reorg) -- both need to be on
# sys.path for the bare `import x_correspondence_ledger` / `import x as eng`
# statements inside those modules to keep resolving.
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(BASE_DIR / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import sephirotic_correspondence_ledger
import attractor_correspondence_ledger
import rca_sandbox_gamma_correspondence_ledger
import ddpg_correspondence_ledger
import glyph_emotion_correspondence_ledger

from correspondence_ledger import STATUS_VERIFIED, STATUS_FAILED, STATUS_UNTESTABLE
from correspondence_ledger_history import (
    load_history, save_history, record_run, format_freshness_report,
)
from correspondence_ledger_target_staleness import (
    compute_staleness_flags, format_staleness_report,
)

LEDGERS = [
    ("sephirotic_correspondence_ledger.py", sephirotic_correspondence_ledger),
    ("attractor_correspondence_ledger.py", attractor_correspondence_ledger),
    ("rca_sandbox_gamma_correspondence_ledger.py", rca_sandbox_gamma_correspondence_ledger),
    ("ddpg_correspondence_ledger.py", ddpg_correspondence_ledger),
    ("glyph_emotion_correspondence_ledger.py", glyph_emotion_correspondence_ledger),
]

# (ledger filename, exact Correspondence.pattern string). Keep this list
# current -- it is checked both ways (a FAILED entry not listed here is
# unexpected; a listed entry that stops failing is also flagged). Empty as
# of this writing -- the one entry that used to live here (DDPG's
# actor-critic gap) is fixed; see the module docstring's dated correction.
KNOWN_EXPECTED_FAILURES: Set[Tuple[str, str]] = set()


@dataclass
class LedgerRunResult:
    filename: str
    verified: int
    failed: int
    untestable: int
    total: int
    failed_entries: List[Tuple[str, str]] = field(default_factory=list)  # (pattern, detail)


@dataclass
class AggregateResult:
    ledger_results: List[LedgerRunResult]
    total_verified: int
    total_failed: int
    total_untestable: int
    total: int
    unexpected_failures: List[Tuple[str, str, str]]  # (filename, pattern, detail)
    resolved_known_failures: List[Tuple[str, str]]    # (filename, pattern)

    @property
    def ok(self) -> bool:
        """A run is OK if there are no unexpected failures. A resolved
        known failure (a documented gap that stopped failing) does NOT
        make a run non-OK -- that's good news, not a regression."""
        return not self.unexpected_failures


def run_ledgers(ledgers: Sequence[Tuple[str, object]],
                known_expected_failures: Set[Tuple[str, str]]) -> AggregateResult:
    """Runs every (filename, module) pair's build_ledger(), aggregates
    counts, and classifies every FAILED entry as either a known/expected
    gap or an unexpected failure. Pure computation, no printing -- see
    print_report() for the human-readable rendering of this result."""
    ledger_results: List[LedgerRunResult] = []
    total_verified = total_failed = total_untestable = 0
    unexpected_failures: List[Tuple[str, str, str]] = []
    seen_known: Set[Tuple[str, str]] = set()

    for fname, module in ledgers:
        ledger = module.build_ledger()
        ledger.run()

        v = sum(1 for c in ledger.entries if c.status == STATUS_VERIFIED)
        f = sum(1 for c in ledger.entries if c.status == STATUS_FAILED)
        u = sum(1 for c in ledger.entries if c.status == STATUS_UNTESTABLE)
        failed_entries = [(c.pattern, c.detail) for c in ledger.entries if c.status == STATUS_FAILED]

        ledger_results.append(LedgerRunResult(
            filename=fname, verified=v, failed=f, untestable=u,
            total=len(ledger.entries), failed_entries=failed_entries,
        ))
        total_verified += v
        total_failed += f
        total_untestable += u

        for c in ledger.entries:
            if c.status != STATUS_FAILED:
                continue
            key = (fname, c.pattern)
            if key in known_expected_failures:
                seen_known.add(key)
            else:
                unexpected_failures.append((fname, c.pattern, c.detail))

    resolved_known_failures = [k for k in known_expected_failures if k not in seen_known]

    total = total_verified + total_failed + total_untestable
    return AggregateResult(
        ledger_results=ledger_results,
        total_verified=total_verified,
        total_failed=total_failed,
        total_untestable=total_untestable,
        total=total,
        unexpected_failures=unexpected_failures,
        resolved_known_failures=resolved_known_failures,
    )


def print_report(result: AggregateResult, known_expected_failures: Set[Tuple[str, str]]) -> None:
    print("=" * 78)
    print("  MASTER CORRESPONDENCE LEDGER RUNNER")
    print("  Philosophical Layer -- Full Picture Across All 5 Ledgers")
    print("=" * 78)

    for lr in result.ledger_results:
        print(f"\n  [{lr.filename}]")
        print(f"    {lr.verified} VERIFIED / {lr.failed} FAILED / {lr.untestable} UNTESTABLE"
              f"  (of {lr.total} total)")
        for pattern, detail in lr.failed_entries:
            key = (lr.filename, pattern)
            tag = "KNOWN GAP, not a regression" if key in known_expected_failures else "UNEXPECTED FAILURE"
            print(f"      [{tag}] {pattern}")
            print(f"        {detail}")

    print("\n" + "=" * 78)
    print("  GRAND TOTAL")
    print("=" * 78)
    print(f"  Ledgers run             : {len(result.ledger_results)}")
    print(f"  Total correspondences   : {result.total}")
    print(f"  VERIFIED                : {result.total_verified} / {result.total}")
    print(f"  FAILED                  : {result.total_failed} / {result.total}"
          f"  ({len(known_expected_failures)} known/documented, {len(result.unexpected_failures)} unexpected)")
    print(f"  UNTESTABLE (by design)  : {result.total_untestable} / {result.total}")

    if result.unexpected_failures:
        print("\n  UNEXPECTED FAILURES (not in KNOWN_EXPECTED_FAILURES -- investigate):")
        for fname, pattern, detail in result.unexpected_failures:
            print(f"    - [{fname}] {pattern}")
            print(f"      {detail}")

    if result.resolved_known_failures:
        print("\n  NOTE: entries in KNOWN_EXPECTED_FAILURES did NOT fail this run:")
        for fname, pattern in result.resolved_known_failures:
            print(f"    - [{fname}] {pattern}")
        print("    If this gap is genuinely fixed, update KNOWN_EXPECTED_FAILURES")
        print("    and say so in LIBER_0.md -- do not just let this note appear silently.")

    print("\n  Honest claim this run supports:")
    print(f"    {result.total_verified} of {result.total} correspondence claims across all 5")
    print(f"    ledgers were adversarially checked and held. {result.total_untestable} of")
    print(f"    {result.total} are explicitly out of scope for testing (analogical, not")
    print(f"    falsifiable by code). {result.total_failed} of {result.total} FAILED:")
    print(f"    {len(known_expected_failures)} already-known, deliberately-registered")
    print(f"    gap(s), not a regression; {len(result.unexpected_failures)} unexpected.")
    print("=" * 78)


def main(history_path=None) -> int:
    """history_path lets callers (tests) point freshness tracking at a
    temp file instead of the real repo's correspondence_ledger_run_history.json
    -- defaults to that real file when not given, which is what running
    this script from the command line does."""
    from correspondence_ledger_history import DEFAULT_HISTORY_PATH
    history_path = history_path or DEFAULT_HISTORY_PATH

    result = run_ledgers(LEDGERS, KNOWN_EXPECTED_FAILURES)
    print_report(result, KNOWN_EXPECTED_FAILURES)

    # Freshness tracking (see correspondence_ledger_history.py) -- the
    # honest, computable version of "Decay of Unverified Consensus":
    # record that every ledger was actually re-run just now, and report
    # how long it had been since the PRIOR recorded run for each one.
    history = load_history(history_path)
    ledger_summaries = [
        (lr.filename, lr.verified, lr.failed, lr.untestable, lr.total)
        for lr in result.ledger_results
    ]
    new_history, previous_records = record_run(history, ledger_summaries)
    save_history(new_history, history_path)
    print()
    print(format_freshness_report(previous_records))
    print()

    # Target-change staleness (see correspondence_ledger_target_staleness.py)
    # -- the second, more actionable signal beyond elapsed time: does any
    # file a ledger actually depends on have a real git commit more recent
    # than that ledger's last recorded check. Computed against
    # previous_records (the state BEFORE this run), same baseline the
    # freshness report above uses.
    staleness_flags = compute_staleness_flags(previous_records, repo_root=BASE_DIR)
    print(format_staleness_report(staleness_flags))
    print()

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
