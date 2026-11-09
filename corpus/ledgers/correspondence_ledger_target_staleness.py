#!/usr/bin/env python3
"""
correspondence_ledger_target_staleness.py
Change-aware staleness for the correspondence ledger suite -- the second
half of the freshness-tracking idea started in correspondence_ledger_history.py.

correspondence_ledger_history.py already answers "how long has it been
since this ledger was last checked" (real elapsed time, not a fabricated
decay percentage). That's useful but incomplete on its own: a ledger
checked 0.7 days ago is reported as "fresh" even if the file it actually
depends on was edited three times in that same 0.7 days, and a ledger
checked 30 days ago is reported as "stale" even if nothing it depends on
has changed at all in that time. Elapsed time and actual relevance are
two different signals, and only the first one existed before this file.

This module adds the second: for each ledger, has any file it genuinely
depends on -- determined by reading each ledger's own real imports (and
each underlying test file's own real imports), not guessed from a
ledger's prose "target" description -- been committed to git more
recently than the ledger's own last recorded check? That's a real,
checkable fact from git's own history, not an invented score. Consistent
with this project's discipline of building the honest, computable
version of an idea rather than the aspirational one (see
docs/recursive_symbolics_foundation_reference.md section 2's rejected
"Decay of Unverified Consensus" formula, and correspondence_ledger_
history.py's own docstring for why real elapsed-time tracking was built
instead of that).

Before building this, the alternative idea it replaced -- a DDPG/RL-style
learned prioritizer choosing which ledger to check "first" -- was checked
against reality and rejected: running all 5 ledgers takes well under a
second, so there is no real scarcity for a prioritizer to allocate.
Building one anyway would have been solving a problem that doesn't exist
here, purely to manufacture training data. This module targets a
friction point that's actually real: telling "nothing changed" apart
from "something changed but you haven't re-checked it yet," which the
existing elapsed-time tracker genuinely cannot do.

Usage: see run_all_correspondence_ledgers.py for how this is wired into
the master runner's own report.
"""

import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent
# This module now lives in ledgers/, one directory deeper than the old flat
# layout -- REPO_ROOT is the actual repo root (solo/), used both as the
# default git cwd below and to prefix every TARGET_FILES entry with its
# real post-reorg subdirectory (engines/, protocols/, ledgers/, tests/).
REPO_ROOT = BASE_DIR.parent

# (ledger filename) -> list of real file paths (relative to the repo
# root) whose changes could make that ledger's cached result stale. Built
# by reading each ledger's actual imports and each underlying test file's
# actual imports -- not a guess from the ledger's own prose "target"
# field, which is a human-readable description, not a dependency list.
# Paths below carry their real subdirectory since the engines/protocols/
# ledgers/tests reorg (dict KEYS stay bare filenames -- they're matched
# against history's ledger-name keys, which are also bare filenames).
TARGET_FILES: Dict[str, List[str]] = {
    "sephirotic_correspondence_ledger.py": [
        "ledgers/sephirotic_correspondence_ledger.py",
        "tests/test_sephirotic_reward_engine.py",
        "engines/sephirotic_reward_engine.py",
    ],
    "attractor_correspondence_ledger.py": [
        "ledgers/attractor_correspondence_ledger.py",
        "tests/test_recursive_attractor_engine.py",
        "engines/recursive_attractor_engine.py",
    ],
    "rca_sandbox_gamma_correspondence_ledger.py": [
        "ledgers/rca_sandbox_gamma_correspondence_ledger.py",
        "tests/test_standalone_rca_sandbox.py",
        "engines/standalone_rca_sandbox.py",
    ],
    "ddpg_correspondence_ledger.py": [
        "ledgers/ddpg_correspondence_ledger.py",
        "tests/test_ddpg_quadcopter_rca_engine.py",
        "engines/ddpg_quadcopter_rca_engine.py",
    ],
    "glyph_emotion_correspondence_ledger.py": [
        "ledgers/glyph_emotion_correspondence_ledger.py",
        "tests/test_glyph_emotion_codex.py",
        "engines/glyph_emotion_codex.py",
        # A real data dependency, not code: glyph_emotion_codex.py parses
        # this document's own table directly at call time (see that
        # module's docstring), so an edit here can change results with no
        # .py file changing at all. docs/ did not move, so no prefix change.
        "docs/glyph_correspondence_codex.md",
    ],
}


def get_last_commit_utc(relpath: str, repo_root: Path = REPO_ROOT) -> Optional[datetime.datetime]:
    """Returns the UTC datetime of the most recent git commit that
    touched relpath, or None if the file has no commit history (never
    committed yet, or git itself is unavailable in this environment).
    A real, checkable fact from git's own log -- not a guess."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", relpath],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    if not output:
        return None
    return datetime.datetime.fromtimestamp(int(output), tz=datetime.timezone.utc)


def compute_staleness_flags(history: Dict[str, dict],
                              target_files: Dict[str, List[str]] = TARGET_FILES,
                              repo_root: Path = REPO_ROOT) -> Dict[str, dict]:
    """For each ledger with a recorded last_run_utc in `history`, checks
    whether any of its real target files were committed more recently
    than that check. Returns, per ledger filename:

        {"has_baseline": bool,              # was there a prior check to compare against?
         "changed_since_check": bool|None,   # None only if has_baseline is False
         "most_recent_change_file": str|None,
         "most_recent_change_utc": str|None} # ISO string, or None if no
                                              # target file has any commit history

    Pure computation, no printing -- see format_staleness_report() for
    the human-readable rendering."""
    flags: Dict[str, dict] = {}
    for ledger_name, files in target_files.items():
        record = history.get(ledger_name)
        if record is None:
            flags[ledger_name] = {
                "has_baseline": False, "changed_since_check": None,
                "most_recent_change_file": None, "most_recent_change_utc": None,
            }
            continue

        last_run = datetime.datetime.fromisoformat(record["last_run_utc"])
        most_recent_file = None
        most_recent_time = None
        for relpath in files:
            commit_time = get_last_commit_utc(relpath, repo_root)
            if commit_time is None:
                continue
            if most_recent_time is None or commit_time > most_recent_time:
                most_recent_time = commit_time
                most_recent_file = relpath

        changed = most_recent_time is not None and most_recent_time > last_run
        flags[ledger_name] = {
            "has_baseline": True,
            "changed_since_check": changed,
            "most_recent_change_file": most_recent_file,
            "most_recent_change_utc": most_recent_time.isoformat() if most_recent_time else None,
        }
    return flags


def format_staleness_report(flags: Dict[str, dict]) -> str:
    lines = []
    lines.append("  TARGET-CHANGE CHECK")
    lines.append("  (does \"checked N days ago\" also mean nothing relevant changed?")
    lines.append("   checked against real git history, not assumed)")
    for ledger_name in sorted(flags):
        f = flags[ledger_name]
        if not f["has_baseline"]:
            lines.append(f"    {ledger_name}: no prior recorded check to compare against")
        elif f["changed_since_check"] is True:
            lines.append(
                f"    {ledger_name}: [REVIEW SUGGESTED] {f['most_recent_change_file']} "
                f"was committed after this ledger's last recorded check"
            )
        elif f["most_recent_change_utc"] is None:
            lines.append(
                f"    {ledger_name}: none of its target files have git history yet "
                f"(untracked, or git unavailable) -- can't compare"
            )
        else:
            lines.append(f"    {ledger_name}: no target-file changes since last check")
    return "\n".join(lines)
