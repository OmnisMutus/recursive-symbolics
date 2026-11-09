# Composing the Four Consciousness Upgrade Protocol Stages: Does the Bridge Actually Hold?

*Register note: Register B throughout. Every claim below is about what
`consciousness_upgrade_pipeline.py` actually did when run, checked by
direct inspection of the real records/results, following the same
discipline as `engine_composition_loop_report.md` for the two RCA
engines: composing two (here, four) already-VERIFIED pieces requires an
explicit bridge, and the bridge itself has to be checked, not assumed to
work just because both sides were independently verified.*

## The real problem this answers

Stages 1–4 were each independently VERIFIED, but nothing had wired them
together, and they don't share a type: Stage 1's self-signature values
are free-text strings; Stage 2's constraints are numeric intervals. Two
independently-correct modules composing cleanly is not guaranteed just
because each one is correct on its own — the same lesson
`engine_composition_loop_report.md` drew from the sephirotic bridge
(where the interesting result turned out to be mostly an artifact of
template wording and dict key order, not a deep property of either
engine). This report asks the equivalent question here: what actually
happens when Stage 1 and Stage 2 are wired together, and is the result a
real, checkable property or an artifact of how the bridge was written?

## The bridge, stated once, precisely

If one or more OTHER sources have a numeric `Constraint` on belief `B`,
proposing a new self-signature value for `B` is treated as a POINT
constraint (`low == high == that number`) from source `"self"`. Stage 2's
`check_belief()` runs on `[external constraints] + [this point
constraint]` BEFORE Stage 1's `propose_change()` is allowed to execute.
Unsatisfiable → refused, nothing written to the signature or the ledger.
Beliefs with no external numeric constraint pass through completely
unaffected.

This is a real, disclosed, single convention — not a "correspondence" in
the Kabbalistic-mapping sense the earlier composition report examined,
and it doesn't have that report's problem (template wording secretly
encoding the expected answer): the bridge's behavior is arithmetic
(`max(lows) <= min(highs)`), not textual similarity scoring, so there's
no analogous "leading question" risk to check for here. What DOES need
checking is whether the composition actually refuses when it should,
accepts when it should, and correctly propagates real objects (not
stand-ins) into Stage 3 and Stage 4.

## Result: the conflict-refusal composition holds, checked directly

Scenario: `team_lead` requires `hours ∈ [15, 40]`, `mentor` requires
`hours ∈ [10, 20]` — jointly, `hours ∈ [15, 20]` (by hand:
`max(15,10)=15`, `min(40,20)=20`).

- Proposing `hours="10"` (outside `[15,20]`): **refused**. `ledger`
  unchanged (0 records), returned signature's hash identical to the
  pre-attempt signature, `verify_signature()` still `True` on it.
- Proposing `hours="18"` (inside `[15,20]`): **accepted**, ledger gets
  exactly 1 new record, signature hash changes.
- Boundary check: `hours="15"` and `hours="20"` (the closed interval's
  exact edges) both **accepted** — consistent with Stage 2's own
  touching-bounds convention (`<=`, not `<`).
- All-or-nothing check: proposing `{"hours": "10", "style": "warm"}`
  together (one key conflicts, one doesn't) is **refused entirely** —
  `style` is NOT silently applied even though it alone would have been
  fine. A self-signature is one declared state; the bridge does not
  partially commit some keys and reject others.
- Non-numeric value on a constrained belief (`hours="a lot"`) **raises**
  rather than silently skipping the check — confirmed directly, not
  assumed.

## Result: Stage 3 correctly sees the REAL composed history — with a genuinely subtle correct behavior

Running the full demo scenario (refused 10-hour attempt, accepted 18-hour
attempt, then an oscillation on `communication_style`) and scanning the
resulting real `ChangeLedger` with Stage 3's registry:

```
exact_state_reversion: 1 match(es)
  - Record 2's new_hash matches the state that existed at index 0
repeated_reason_across_different_keys: 0 match(es)
high_frequency_change_on_same_key: 0 match(es)
```

The refused attempt produced NO record at all (confirmed above), so the
ledger only ever contained the 3 *accepted* changes — record indices in
Stage 3's output correctly refer to that shorter, real sequence, not to
an assumed 4-step history. The reversion found is subtle and correct:
`communication_style` returned to `"direct"`, but the state it reverted
to is the one AFTER accepting 18 hours (record index 0), not the
original 10-hour state — because Stage 3 only detects whole-state
identity, and the original state's `hours` value differs from the
current one. This is exactly the documented scope limit in Stage 3's own
hand-verification doc, now confirmed to hold correctly under real
composed input rather than only under hand-built test records.

A second scenario (`hours` goes `18 → 20 → 18` while `style` changes
`direct → warm` along the way) confirms the negative case directly:
despite `hours` numerically reverting, NO `exact_state_reversion` fires,
because the full state never repeats. Pinned by
`test_no_reversion_reported_when_only_a_partial_key_changes_back`.

## Result: Stage 4 catches a real composition-level bug, not just stage-level bugs

The break-it proof (below) is the most direct evidence the composition
is real rather than decorative: Stage 4's groundedness check, pointed at
a claim about the PIPELINE's own refusal behavior, is a live subprocess
that re-runs the actual test right now. When the bridge was broken, that
subprocess re-run genuinely failed, and Stage 4 correctly reported the
claim `UNGROUNDED` instead of the label simply being trusted. This is the
clearest sign the four stages are functioning as one system here, not
four modules that happen to import each other.

## Break-it proof (performed, not just described)

Introduced a realistic bug: skip the constraint check entirely whenever
`new_values` has only one key (`len(new_values) > 1` guard added around
`affected_beliefs`) — the kind of mistake a well-meaning "optimization"
might introduce, assuming single-field changes are always safe. Result:

```
FAIL: test_refused_change_does_not_touch_the_ledger
  AssertionError: 1 != 0
FAIL: test_the_refusal_claim_is_grounded_by_a_real_passing_test
  AssertionError: 'UNGROUNDED' != 'GROUNDED'
... (4 of 12 failed total)
```

4 of 12 tests failed, including — notably — the Stage-4-mediated test,
confirming groundedness checking itself remained sensitive to the
composition breaking even though nothing about `check_claim()` was
touched. Reverted; `diff -q` against a pre-edit backup confirmed
byte-identical.

## Honest conclusion

Unlike the earlier RCA-engine composition (where the "interesting"
result mostly dissolved into template wording and a dict-order tie-break
once inspected), this composition's central claim — conflicting
self-declarations get refused, non-conflicting ones don't, and nothing is
partially applied — holds up under direct, adversarial inspection with no
comparable artifact discovered. The one real, disclosed limitation is the
bridge convention itself: it only applies when some OTHER source has
already numerically bounded a belief, and it requires the proposed value
to be literally numeric in that case. That's a scope statement, not a
hidden flaw — stated here the same way Stage 3's whole-state-only
limitation was stated in its own hand-verification doc.

## Files

- [`../consciousness_upgrade_pipeline.py`](../consciousness_upgrade_pipeline.py) — the composition and full bridge documentation.
- [`../test_consciousness_upgrade_pipeline.py`](../test_consciousness_upgrade_pipeline.py) — 12 tests: the conflict-refusal scenario, boundary cases, all-or-nothing application, real-ledger pattern scanning (positive and negative), and Stage-4-mediated checks of two of the pipeline's own claims.
