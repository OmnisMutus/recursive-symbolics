#!/usr/bin/env python3
"""
consciousness_upgrade_pattern_registry.py

Grounds Stage 3 ("Pattern Transparency" -- the pasted "Consciousness
Upgrade Protocol" document's framing of surfacing implicit/"subconscious"
behavioral patterns instead of letting them run silently) in real,
checkable detection over the ONE piece of history this project already
has: consciousness_upgrade_self_signature.py's ChangeLedger (Stage 1).
The pasted document's own Stage 3 vocabulary ("hidden Yesod modules
behind private imports," a file named `habit_fear.py`) is Register
A/metaphor and is not built toward here -- no such modules or files exist
anywhere in this repo, and inventing them to match the metaphor would be
exactly the kind of unearned specificity this project's discipline exists
to catch.

WHAT'S ACTUALLY AVAILABLE TO DETECT PATTERNS FROM, STATED HONESTLY:
ChangeRecord stores timestamps, old_hash, new_hash, changed_keys, and
reason -- it does NOT store the actual before/after values (Stage 1 is a
tamper-evidence scheme, not a value store). This constrains what "pattern
transparency" can honestly mean here: no detector below claims to know
WHAT a value changed to, only what's derivable from hashes, key names,
timestamps, and reason strings. This turned out to enable one clean, real
signal rather than requiring new infrastructure:

  EXACT STATE REVERSION: if two different points in a signature's history
  share the identical content_hash, the full value-set at those two points
  was byte-identical (modulo a SHA-256 collision, not a practical concern).
  This is checkable by nothing more than string equality -- no need to
  know what the values actually were.

Two further detectors work from `reason` and `changed_keys` alone, both
literal, position-based facts about the ledger, not inferred psychology:

  REPEATED REASON ACROSS DIFFERENT KEYS: the same reason string used
  (case/whitespace-normalized) across changes touching genuinely
  different keys, at or above a threshold count.

  HIGH-FREQUENCY CHANGE ON THE SAME KEY: a single key appears in
  `changed_keys` at or above a threshold count within a given time
  window, using the ledger's own ISO-8601 timestamps.

None of these detectors claim to explain WHY a pattern occurred or
whether it's good or bad -- consistent with constraint_pruner.py's
Principle of Agency & Sovereignty precedent, PatternRegistry.scan()
reports what fired; it does not recommend a response.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from consciousness_upgrade_self_signature import ChangeRecord


def _parse_ts(ts: str) -> datetime:
    """Parses the ledger's ISO-8601 'Z'-suffixed timestamps. Isolated as
    its own function so every detector uses one consistent parse, rather
    than each rolling its own."""
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class PatternMatch:
    """One firing of one registered pattern. `record_indices` are indices
    into the exact `records` list passed to scan() -- callable can go
    look at the real ChangeRecord objects, not just trust a summary."""
    pattern_name: str
    record_indices: List[int]
    explanation: str


@dataclass(frozen=True)
class Pattern:
    name: str
    description: str
    detector: Callable[[List[ChangeRecord], Optional[str]], List[PatternMatch]]


class PatternRegistry:
    """Holds named patterns and runs every one of them against a history,
    surfacing ALL firings explicitly -- scan() never silently drops a
    detector's output, and register() refuses to silently overwrite an
    existing pattern name (same fail-loud discipline as
    constraint_pruner.prune() and self_signature.propose_change())."""

    def __init__(self):
        self._patterns: Dict[str, Pattern] = {}

    def register(self, pattern: Pattern) -> None:
        if pattern.name in self._patterns:
            raise ValueError(
                f"Pattern {pattern.name!r} is already registered -- refusing "
                f"to silently overwrite it. Use a different name if this is "
                f"meant to be a distinct pattern."
            )
        self._patterns[pattern.name] = pattern

    def scan(self, records: List[ChangeRecord], initial_hash: Optional[str] = None
              ) -> Dict[str, List[PatternMatch]]:
        """Runs every registered pattern's detector against `records`.
        `initial_hash` is the hash of the signature BEFORE any recorded
        change (Stage 1's ChangeLedger only stores changes, not the
        genesis state) -- passing it lets exact_state_reversion detect a
        return to the very first declared state, not just to some
        mid-history state. Returns a dict keyed by EVERY registered
        pattern name, including ones with zero matches (an empty list is
        real information -- "checked, found nothing" -- not silently
        absent, the same anti-vacuous-truth convention
        find_unsatisfiable_beliefs() already uses)."""
        return {
            name: pattern.detector(records, initial_hash)
            for name, pattern in self._patterns.items()
        }


def detect_exact_state_reversion(
    records: List[ChangeRecord], initial_hash: Optional[str] = None
) -> List[PatternMatch]:
    """Flags any record whose new_hash matches a hash seen at an EARLIER
    point in the same history (either `initial_hash` or an earlier
    record's own new_hash/old_hash) -- meaning the full value-set reverted
    to a byte-identical earlier state. Pure hash-string equality; no
    knowledge of the actual values is needed or used."""
    matches: List[PatternMatch] = []
    seen_hashes: Dict[str, int] = {}  # hash -> earliest index it appeared at (-1 = initial)
    if initial_hash is not None:
        seen_hashes[initial_hash] = -1

    for i, rec in enumerate(records):
        if rec.old_hash not in seen_hashes:
            seen_hashes[rec.old_hash] = i - 1 if i > 0 else -1
        if rec.new_hash in seen_hashes:
            earlier_at = seen_hashes[rec.new_hash]
            matches.append(PatternMatch(
                pattern_name="exact_state_reversion",
                record_indices=[i],
                explanation=(
                    f"Record {i}'s new_hash ({rec.new_hash[:12]}...) matches "
                    f"the state that existed at index {earlier_at} -- the "
                    f"full self-signature reverted to a byte-identical "
                    f"earlier state."
                ),
            ))
        if rec.new_hash not in seen_hashes:
            seen_hashes[rec.new_hash] = i
    return matches


def make_repeated_reason_detector(threshold: int = 2) -> Pattern:
    """Returns a Pattern flagging any `reason` string (normalized:
    stripped, lowercased) used across changes touching DIFFERENT keys at
    least `threshold` times. Reused verbatim reasons across unrelated keys
    is a literal, countable fact about the ledger -- this does not claim
    to know whether the reuse is legitimate (a genuinely recurring
    justification) or a canned rubber-stamp; it only surfaces the count
    for a human to judge, the same non-prescriptive stance as
    constraint_pruner.prune()."""

    def detector(records: List[ChangeRecord], initial_hash: Optional[str] = None
                 ) -> List[PatternMatch]:
        by_reason: Dict[str, List[int]] = defaultdict(list)
        keys_touched_by_reason: Dict[str, set] = defaultdict(set)
        for i, rec in enumerate(records):
            norm = rec.reason.strip().lower()
            by_reason[norm].append(i)
            keys_touched_by_reason[norm].update(rec.changed_keys)

        out: List[PatternMatch] = []
        for norm, indices in by_reason.items():
            if len(indices) >= threshold and len(keys_touched_by_reason[norm]) > 1:
                out.append(PatternMatch(
                    pattern_name="repeated_reason_across_different_keys",
                    record_indices=indices,
                    explanation=(
                        f"Reason {norm!r} used {len(indices)} times across "
                        f"{len(keys_touched_by_reason[norm])} different keys "
                        f"{sorted(keys_touched_by_reason[norm])} -- worth a "
                        f"human checking whether that's a genuinely recurring "
                        f"justification or a copy-pasted one."
                    ),
                ))
        return out

    return Pattern(
        name="repeated_reason_across_different_keys",
        description=(
            f"Same reason text used >= {threshold} times across changes to "
            f"genuinely different keys."
        ),
        detector=detector,
    )


def make_high_frequency_key_detector(threshold: int = 3, window_seconds: float = 3600.0) -> Pattern:
    """Returns a Pattern flagging any single key that appears in
    `changed_keys` at least `threshold` times within any `window_seconds`
    span, using the ledger's own timestamps. A literal rate computation,
    not a judgment about whether the frequency is a problem."""

    def detector(records: List[ChangeRecord], initial_hash: Optional[str] = None
                 ) -> List[PatternMatch]:
        by_key: Dict[str, List[int]] = defaultdict(list)
        for i, rec in enumerate(records):
            for k in rec.changed_keys:
                by_key[k].append(i)

        out: List[PatternMatch] = []
        for key, indices in by_key.items():
            timestamps = [_parse_ts(records[i].timestamp) for i in indices]
            # Slide a window over the sorted timestamps (indices are already
            # in ledger/chronological order) looking for >= threshold
            # touches within window_seconds of each other.
            for start in range(len(timestamps)):
                count = 1
                window_indices = [indices[start]]
                for j in range(start + 1, len(timestamps)):
                    if (timestamps[j] - timestamps[start]).total_seconds() <= window_seconds:
                        count += 1
                        window_indices.append(indices[j])
                if count >= threshold:
                    out.append(PatternMatch(
                        pattern_name="high_frequency_change_on_same_key",
                        record_indices=window_indices,
                        explanation=(
                            f"Key {key!r} changed {count} times within "
                            f"{window_seconds}s (records {window_indices})."
                        ),
                    ))
                    break  # one report per key is enough; avoid duplicate overlapping windows
        return out

    return Pattern(
        name="high_frequency_change_on_same_key",
        description=(
            f"A single key changed >= {threshold} times within "
            f"{window_seconds} seconds."
        ),
        detector=detector,
    )


EXACT_STATE_REVERSION = Pattern(
    name="exact_state_reversion",
    description="The full self-signature reverted to a byte-identical earlier state.",
    detector=detect_exact_state_reversion,
)


def default_registry(reason_threshold: int = 2, freq_threshold: int = 3,
                       freq_window_seconds: float = 3600.0) -> PatternRegistry:
    """Convenience constructor wiring up the three built-in patterns with
    caller-supplied thresholds, rather than hardcoding them."""
    reg = PatternRegistry()
    reg.register(EXACT_STATE_REVERSION)
    reg.register(make_repeated_reason_detector(reason_threshold))
    reg.register(make_high_frequency_key_detector(freq_threshold, freq_window_seconds))
    return reg


if __name__ == "__main__":
    from consciousness_upgrade_self_signature import (
        create_signature, propose_change, ChangeLedger,
    )

    print("=" * 78)
    print("  CONSCIOUSNESS UPGRADE PROTOCOL -- STAGE 3: PATTERN REGISTRY")
    print("=" * 78)

    ledger = ChangeLedger()
    sig0 = create_signature({"how_i_show_up": "direct"}, now="2026-01-01T00:00:00Z")
    sig1 = propose_change(sig0, {"how_i_show_up": "conflict-avoidant"},
                           reason="trying something different", ledger=ledger,
                           now="2026-01-01T01:00:00Z")
    sig2 = propose_change(sig1, {"how_i_show_up": "direct"},
                           reason="that didn't feel right", ledger=ledger,
                           now="2026-01-01T02:00:00Z")

    registry = default_registry()
    results = registry.scan(ledger.records, initial_hash=sig0.content_hash)
    for pattern_name, matches in results.items():
        print(f"\n{pattern_name}: {len(matches)} match(es)")
        for m in matches:
            print(f"  - {m.explanation}")
