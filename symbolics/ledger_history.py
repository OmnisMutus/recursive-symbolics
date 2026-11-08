#!/usr/bin/env python3
# Inherited from the Recursive Symbolics framework (its correspondence ledger, by OmnisMutus).
# Kept as it is in substance: a claim is pattern + target + meaning with a validator that re-runs an
# existing adversarially-tested check, validator=None means untestable in principle, and a ledger of
# nothing but UNTESTABLE rows can never report success.
"""
correspondence_ledger_history.py
Persistent run-history tracking for the correspondence ledger suite --
the honest, computable version of "Decay of Unverified Consensus" from
docs/recursive_symbolics_foundation_reference.md section 2.

The original idea (confidence decays 15% per iteration cycle unless
anchored by fresh external measurement data) has no operational
definition anywhere in this codebase for what "15%" or "confidence"
equal as numbers -- adopting it literally would repeat the exact
fabrication pattern this project's own testing discipline exists to
catch (see LIBER_0.md's documentation-audit entries, and the grounding
caveat already added to the Confidence Calibration formula in
docs/recursive_symbolics_foundation_reference.md section 1).

This module implements the same underlying concern honestly instead:
track the one real, computable fact available -- WHEN was each ledger
last actually re-run, and what did it report -- and surface the elapsed
time since then as a plain fact, not a fabricated percentage. A long gap
since the last real check is a legitimate reason to treat a VERIFIED
claim more cautiously (the underlying code could have changed since);
a decay formula with invented constants is not.

Persisted as a single JSON file (correspondence_ledger_run_history.json)
committed to the repo, so the record survives across sessions and is
visible to any agent -- human, Claude, or Gemini -- reading this repo,
not just whichever process most recently ran the suite.
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_HISTORY_PATH = Path(__file__).parent / "correspondence_ledger_run_history.json"


def load_history(path: Path = DEFAULT_HISTORY_PATH) -> Dict[str, dict]:
    """Returns {} if the file doesn't exist yet -- a fresh checkout, or
    the very first time this tool has ever been run, must report
    'no history yet' rather than crash."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_history(history: Dict[str, dict], path: Path = DEFAULT_HISTORY_PATH) -> None:
    path.write_text(json.dumps(history, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_run(history: Dict[str, dict],
                ledger_summaries: List[Tuple[str, int, int, int, int]],
                now: Optional[datetime.datetime] = None
                ) -> Tuple[Dict[str, dict], Dict[str, Optional[dict]]]:
    """ledger_summaries: list of (filename, verified, failed, untestable,
    total) -- the per-ledger counts from this run.

    Returns (new_history, previous_records). previous_records[filename]
    is the record that existed BEFORE this call overwrote it (None if
    that ledger has never been recorded before) -- callers use this to
    report the real gap between the last check and this one, not a
    trivially-zero gap against the record this call just wrote."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    new_history = dict(history)
    previous_records: Dict[str, Optional[dict]] = {}
    for filename, verified, failed, untestable, total in ledger_summaries:
        previous_records[filename] = history.get(filename)
        new_history[filename] = {
            "last_run_utc": now.isoformat(),
            "verified": verified,
            "failed": failed,
            "untestable": untestable,
            "total": total,
        }
    return new_history, previous_records


def days_since(record: Optional[dict], now: Optional[datetime.datetime] = None) -> Optional[float]:
    """None if record is None (never run before). Otherwise the elapsed
    days between record['last_run_utc'] and now."""
    if record is None:
        return None
    now = now or datetime.datetime.now(datetime.timezone.utc)
    last_run = datetime.datetime.fromisoformat(record["last_run_utc"])
    return (now - last_run).total_seconds() / 86400.0


def format_freshness_report(previous_records: Dict[str, Optional[dict]],
                             stale_threshold_days: float = 30.0,
                             now: Optional[datetime.datetime] = None) -> str:
    """Human-readable freshness report. Reports the gap since the PRIOR
    recorded run for each ledger (not the run that just happened -- that
    would trivially always read ~0 days and say nothing useful)."""
    lines = []
    lines.append("  FRESHNESS CHECK")
    lines.append("  (honest version of \"Decay of Unverified Consensus\" -- see")
    lines.append("   docs/recursive_symbolics_foundation_reference.md section 2)")
    for filename in sorted(previous_records):
        record = previous_records[filename]
        gap = days_since(record, now=now)
        if gap is None:
            lines.append(f"    {filename}: first recorded run (no prior history)")
        else:
            flag = "  [STALE -- prior check was over the threshold]" if gap > stale_threshold_days else ""
            lines.append(f"    {filename}: prior check was {gap:.2f} day(s) ago{flag}")
    return "\n".join(lines)
