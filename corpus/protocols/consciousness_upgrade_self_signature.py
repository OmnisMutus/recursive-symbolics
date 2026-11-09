#!/usr/bin/env python3
"""
consciousness_upgrade_self_signature.py

Grounds Stage 1 ("Declare a Self-Signature") of the pasted "Consciousness
Upgrade Protocol" document in real, checkable mechanics, following the
same discipline as consciousness_upgrade_constraint_pruner.py (Stage 2):
the pasted document's "escrow contract" / "Asuka's sandbox" framing is
Register A/metaphor and is NOT re-implemented here, because nothing in
this repo or Recursive-Symbolics establishes what those name -- see
chat discussion. What IS real and buildable from that document is a much
more modest, honestly-scoped pair of properties:

  1. TAMPER-EVIDENCE: a self_signature.json declares a set of named
     values (the "who I am" claims) alongside a cryptographic hash of
     those values. If the values are edited without going through
     propose_change(), verify_signature() detects the mismatch -- this
     is a real, standard property of hashing (any single-bit change to
     the input produces, with overwhelming probability, a completely
     different SHA-256 digest), not a novel claim.

  2. DISCLOSED MUTATION: the ONLY way to legitimately change a
     self-signature is propose_change(), which REQUIRES a non-empty
     `reason` string and appends an entry to a ledger file recording the
     old hash, new hash, timestamp, and reason. Nothing stops a user from
     hand-editing the JSON directly -- that is exactly what property (1)
     is for catching. This module does not claim to prevent tampering (no
     local file-hash scheme can); it claims to make undisclosed tampering
     DETECTABLE, and disclosed change AUDITABLE. That distinction is
     stated here explicitly rather than oversold as "security" or
     "escrow" in the blockchain/multi-party sense the pasted document's
     vocabulary gestures at.

WHAT THIS DELIBERATELY DOES NOT CLAIM: no multi-party contract, no
external inference service, no counterparty ("Asuka" or otherwise)
verifying anything. It is a single local file plus a single local ledger,
checked by one process against itself. That is a real, useful, MUCH
smaller thing than "escrow contract," and is named accordingly.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


def _canonical_json(values: Dict[str, str]) -> str:
    """Deterministic serialization: sorted keys, fixed separators, so the
    same logical values always hash identically regardless of dict
    insertion order or whitespace."""
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def compute_content_hash(values: Dict[str, str]) -> str:
    """SHA-256 of the canonical serialization of `values`. Deliberately
    excludes any hash/timestamp field -- only the declared values
    themselves are hashed, so verify_signature() can recompute this
    independently from the stored values and compare."""
    return hashlib.sha256(_canonical_json(values).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SelfSignature:
    """A declared, timestamped set of named values plus a hash committing
    to them. `values` is intentionally just Dict[str,str] here rather than
    reusing constraint_pruner.Constraint -- a self-signature is a
    declaration ("this is what I currently hold"), not a bound
    ("acceptable range"); the two are different kinds of claim and are
    kept as separate types rather than conflated."""
    values: Dict[str, str]
    content_hash: str
    declared_at: str  # ISO 8601 UTC

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2)

    @staticmethod
    def from_dict(d: dict) -> "SelfSignature":
        return SelfSignature(
            values=dict(d["values"]),
            content_hash=d["content_hash"],
            declared_at=d["declared_at"],
        )


def create_signature(values: Dict[str, str], now: Optional[str] = None) -> SelfSignature:
    """Builds a fresh SelfSignature, computing the hash from `values` at
    creation time. `now` is injectable for deterministic tests; defaults
    to the real UTC time."""
    ts = now if now is not None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return SelfSignature(values=dict(values), content_hash=compute_content_hash(values), declared_at=ts)


def verify_signature(sig: SelfSignature) -> bool:
    """Recomputes the hash from sig.values and compares to sig.content_hash.
    Returns False if the two don't match -- i.e. if `values` were edited
    (by hand or otherwise) without recomputing the hash, which is exactly
    what happens if someone bypasses propose_change() and edits the JSON
    file directly."""
    return compute_content_hash(sig.values) == sig.content_hash


@dataclass
class ChangeRecord:
    """One entry in the disclosed-change ledger."""
    timestamp: str
    old_hash: str
    new_hash: str
    changed_keys: List[str]
    reason: str


class ChangeLedger:
    """In-memory ledger of disclosed changes. A caller wanting persistence
    can dump `.records` to a file; kept in-memory here (mirrors
    correspondence_ledger.py's pattern of being a plain, inspectable
    object) so tests don't depend on filesystem state."""

    def __init__(self):
        self.records: List[ChangeRecord] = []

    def append(self, record: ChangeRecord) -> None:
        self.records.append(record)

    def to_json(self) -> str:
        return json.dumps([asdict(r) for r in self.records], indent=2)


def propose_change(
    current: SelfSignature,
    new_values: Dict[str, str],
    reason: str,
    ledger: ChangeLedger,
    now: Optional[str] = None,
) -> SelfSignature:
    """The ONLY sanctioned way to change a self-signature's values.
    Requires a non-empty `reason` -- raises otherwise, the same
    fail-loud-rather-than-silent-noop discipline as
    constraint_pruner.prune(). Appends a ChangeRecord to `ledger` naming
    exactly which keys changed, then returns a NEW SelfSignature with a
    freshly computed hash. Does not mutate `current`."""
    if not reason or not reason.strip():
        raise ValueError(
            "propose_change() requires a non-empty `reason` -- undisclosed "
            "changes are exactly what this module is designed to make "
            "impossible to do through this API (they're still possible by "
            "hand-editing a persisted JSON file directly, which is why "
            "verify_signature() exists as an independent check)."
        )
    if not verify_signature(current):
        raise ValueError(
            "propose_change() called on a `current` signature that already "
            "fails verify_signature() -- refusing to build a new signature "
            "on top of one whose own hash doesn't match its values, since "
            "that would launder an already-undetected tamper into a "
            "seemingly-legitimate disclosed change."
        )

    changed_keys = sorted(
        k for k in (set(current.values) | set(new_values))
        if current.values.get(k) != new_values.get(k)
    )
    new_sig = create_signature(new_values, now=now)
    ledger.append(ChangeRecord(
        timestamp=new_sig.declared_at,
        old_hash=current.content_hash,
        new_hash=new_sig.content_hash,
        changed_keys=changed_keys,
        reason=reason.strip(),
    ))
    return new_sig


if __name__ == "__main__":
    print("=" * 78)
    print("  CONSCIOUSNESS UPGRADE PROTOCOL -- STAGE 1: SELF-SIGNATURE")
    print("=" * 78)

    ledger = ChangeLedger()
    sig = create_signature({
        "how_i_show_up": "reliable, direct, willing to disagree openly",
        "what_i_wont_do": "guess at unstated intent instead of asking",
    })
    print(f"\nCreated signature at {sig.declared_at}, hash={sig.content_hash[:16]}...")
    print(f"verify_signature(sig) = {verify_signature(sig)}")

    print("\n--- Simulating undisclosed tampering (hand-edit values, keep old hash) ---")
    tampered = SelfSignature(
        values={**sig.values, "how_i_show_up": "whatever gets the least pushback"},
        content_hash=sig.content_hash,  # NOT recomputed -- this is the tamper
        declared_at=sig.declared_at,
    )
    print(f"verify_signature(tampered) = {verify_signature(tampered)}  (should be False)")

    print("\n--- Disclosed change through propose_change() ---")
    sig2 = propose_change(
        sig,
        {**sig.values, "how_i_show_up": "reliable, direct, willing to disagree openly -- and to say when I'm unsure"},
        reason="Refined after noticing I was stating uncertain things too confidently.",
        ledger=ledger,
    )
    print(f"New hash: {sig2.content_hash[:16]}...  verify_signature(sig2) = {verify_signature(sig2)}")
    print(f"\nLedger:\n{ledger.to_json()}")
