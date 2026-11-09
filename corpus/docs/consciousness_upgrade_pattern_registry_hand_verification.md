# Hand-Verifying `consciousness_upgrade_pattern_registry.py`

*Register note: Register B. The pasted "Consciousness Upgrade Protocol"
document's Stage 3 framing ("hidden Yesod modules behind private
imports," a file named `habit_fear.py`) is Register A/metaphor and is not
built toward — no such modules exist anywhere in `solo/` or
`Recursive-Symbolics`. What's verified below is a smaller, real thing:
three detectors over Stage 1's `ChangeLedger` history, each checkable by
hand from the ledger's literal fields (hashes, key names, timestamps,
reason strings) with no claim about what the underlying values actually
were.*

## 1. What's honestly available to detect from

`ChangeRecord` (Stage 1) stores `timestamp`, `old_hash`, `new_hash`,
`changed_keys`, `reason` — not the actual before/after values. Every
detector below is checkable using only those fields; none infers or
assumes a value it doesn't have.

## 2. By hand — exact state reversion

```
v0 = {"x": "a"};  hash(v0) = H0
v1 = {"x": "b"};  hash(v1) = H1

record[0]: old_hash=H0, new_hash=H1
record[1]: old_hash=H1, new_hash=H0   <- same as record[0].old_hash

detect_exact_state_reversion sees record[1].new_hash == H0, which was
already seen (as record[0]'s old_hash, or as initial_hash if supplied)
-> flags record 1.
```

Hand-checkable: this requires no arithmetic, only string equality between
two hash values already sitting in the ledger. Confirmed directly by
running the module (see script output below), not just asserted:

```
exact_state_reversion: 1 match(es)
  - Record 1's new_hash (e4a46760597b...) matches the state that existed
    at index -1 -- the full self-signature reverted to a byte-identical
    earlier state.
```

`index -1` here refers to `initial_hash` (the state before any recorded
change) — confirmed against the demo script's own `sig0`/`sig1`/`sig2`
construction, where `sig2`'s values are hand-set identical to `sig0`'s.

## 3. By hand — why this can't claim more than it does

Two DIFFERENT value sets that happen to produce the same content are the
only way this fires — a coincidental SHA-256 collision between two
genuinely different value sets is not a practical concern (same standard
already applied in the Stage 1 doc). What it does NOT detect: a *partial*
reversion (one key reverts while another doesn't) — the hash is over the
WHOLE value set, so a partial reversion produces a genuinely new hash and
correctly does not fire. This is a real scope limit, stated here rather
than glossed over: pattern transparency here is coarse (whole-state) not
fine-grained (per-key), because that's what the underlying hash actually
lets you check.

## 4. By hand — repeated reason across different keys

```
record[0]: changed_keys=["a"], reason="cleanup"
record[1]: changed_keys=["b"], reason="cleanup"

by_reason["cleanup"] = [0, 1]
keys_touched_by_reason["cleanup"] = {"a", "b"}   (2 distinct keys)

len(indices)=2 >= threshold(2), len(keys)=2 > 1  -> FLAGGED
```

Contrast, also hand-checkable:

```
record[0]: changed_keys=["a"], reason="iterating"
record[1]: changed_keys=["a"], reason="iterating"

keys_touched_by_reason["iterating"] = {"a"}   (only 1 distinct key)
len(keys)=1, NOT > 1  -> NOT flagged
```

The second case is deliberately not flagged: repeating the same reason
while iterating on the *same* key is ordinary, not suspicious; the
detector is specifically about the same canned reason spanning
*unrelated* keys.

## 5. By hand — high-frequency change on the same key

```
record[0] at 00:00:00, changed_keys=["k"]
record[1] at 00:20:00, changed_keys=["k"]
record[2] at 00:40:00, changed_keys=["k"]

window_seconds = 3600
(00:40:00 - 00:00:00) = 2400s <= 3600s, count=3 >= threshold(3) -> FLAGGED
```

Boundary case, checked directly (not assumed): two changes exactly 3600
seconds apart with `threshold=2, window_seconds=3600` — `(t1-t0) <= 3600`
uses `<=`, so exactly-3600 counts as within the window and fires. Pinned
by `test_exactly_at_window_boundary_counts_as_within`, the same kind of
boundary discipline as the Stage 2 touching-bounds case.

## 6. Break-it proof (performed, not just described)

Removed the three lines that populate `seen_hashes` from a record's
`old_hash` (a realistic bug: a refactor that only tracks `new_hash`,
forgetting a change's *starting* hash also needs to be tracked so a
reversion to the very first state — when `initial_hash` isn't supplied —
can still be found via `record[0].old_hash`). Result:

```
FAIL: test_without_initial_hash_still_detects_mid_history_reversion
  AssertionError: 0 != 1
```

Exactly one test failed, for exactly the reason the bug should cause
(the other 16, including the *with*-`initial_hash` reversion test, still
passed — confirming the bug is narrowly about the no-`initial_hash`
fallback path, not the whole detector). Reverted; `diff -q` against a
pre-edit backup confirmed byte-identical.

## 7. What this deliberately does not claim

No detector here judges whether a flagged pattern is good, bad, healthy,
or unhealthy — `scan()` reports what fired and cites the exact record
indices; a human decides what (if anything) to do about it, the same
non-prescriptive stance as `constraint_pruner.prune()` requiring the
caller to name what to discard rather than choosing for them. Thresholds
(`reason_threshold`, `freq_threshold`, `freq_window_seconds`) are
caller-supplied, not asserted as universally correct defaults.

## 8. Files

- [`../consciousness_upgrade_pattern_registry.py`](../consciousness_upgrade_pattern_registry.py) — the module.
- [`../test_consciousness_upgrade_pattern_registry.py`](../test_consciousness_upgrade_pattern_registry.py) — 17 tests, all passing, hand-constructed `ChangeRecord`s bypassing `propose_change()` entirely.

---

## Provenance

Grounds Stage 3 of the pasted "Consciousness Upgrade Protocol" document,
following the same discipline as Stage 1 and Stage 2's hand-verification
docs: the document's own vocabulary for this stage doesn't correspond to
anything in either connected repo, so nothing was built to match it;
instead, the one real, already-existing data source (Stage 1's
`ChangeLedger`) was checked for what it can honestly support, and that
turned out to be a real, if narrower, capability.
