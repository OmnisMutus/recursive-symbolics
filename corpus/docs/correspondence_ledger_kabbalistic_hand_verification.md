# Hand-Verifying `correspondence_ledger.py`'s Honesty Guard

This one isn't arithmetic — it's boolean logic, and it's hand-checkable
with a truth table rather than a calculator. The interesting part is a
specific logical trap the guard exists to defeat: **vacuous truth**.

**Correspondence**: `all_testable_passed()` plays the same structural
role here that `AbyssException` plays in `recursive_attractor_engine.py`
— a Da'ath-type boundary guard, refusing to let a self-consuming or
self-flattering degenerate case get reported as a real result. Where
Da'ath in the attractor engine catches numerical divergence, this guard
catches *logical* divergence: a ledger that "passes" by having checked
nothing at all.

---

## 1. The Function

```python
def all_testable_passed(self) -> bool:
    testable = [c for c in self.entries if c.status != STATUS_UNTESTABLE]
    if not testable:
        return False
    return all(c.status == STATUS_VERIFIED for c in testable)
```

Two steps: filter out `UNTESTABLE` entries, then check whether every
*remaining* entry is `VERIFIED` — except if nothing remains, return
`False` explicitly, rather than letting the `all()` call run on an empty
list.

## 2. Why the Empty-List Case Needs Its Own Line

This is the fact worth hand-verifying, because it's not obvious unless
you know the rule: **in standard logic, an empty conjunction ("all of
zero things are true") is defined as `True`.** Try it yourself in any
Python shell with no engine involved:

```
>>> all([])
True
```

That's not a bug in Python — it's the correct mathematical convention
(the same reason multiplying zero numbers together gives 1, the
identity). But it's exactly the wrong answer for this ledger: a
CorrespondenceLedger with three entries, all `UNTESTABLE`, all
`validator=None`, has checked *nothing*. If `all_testable_passed()` just
returned `all(c.status == VERIFIED for c in testable)` directly on an
empty `testable` list, it would report `True` — total success — with
zero adversarial checks having run. The explicit `if not testable: return
False` is the one line standing between "nothing was tested" and "it
passed."

## 3. By Hand — Three Truth-Table Cases

Walk these with pencil and paper; each is a direct trace of the two-line
function above.

**Case A — all UNTESTABLE** (e.g. 3 entries, all `validator=None`):
```
entries statuses: [UNTESTABLE, UNTESTABLE, UNTESTABLE]
testable = filter out UNTESTABLE -> []
testable is empty -> return False
```
Result: `False`. This is the guard actually firing.

**Case B — mixed, all testable ones pass** (2 VERIFIED, 1 UNTESTABLE):
```
entries statuses: [VERIFIED, VERIFIED, UNTESTABLE]
testable = [VERIFIED, VERIFIED]
testable is non-empty -> check all(status == VERIFIED)
all([True, True]) = True
```
Result: `True`.

**Case C — one real failure hides among untestables** (1 VERIFIED, 1
FAILED, 1 UNTESTABLE):
```
entries statuses: [VERIFIED, FAILED, UNTESTABLE]
testable = [VERIFIED, FAILED]
all([True, False]) = False
```
Result: `False`. A single genuine failure cannot be diluted into a "pass"
by adding more untestable entries — each UNTESTABLE entry is simply
removed from consideration, it never counts as evidence either way.

## 4. The Break-It Proof, Traceable by Hand

The actual break-it proof recorded for this module (see
`correspondence_ledger_meta_tool_spec.md`) removed the `if not testable:
return False` line — i.e., reverted `all_testable_passed()` to `return
all(c.status == STATUS_VERIFIED for c in testable)` with no guard. Re-run
Case A by hand against *that* version:
```
testable = []
all([]) = True   <- the vacuous-truth trap, now live
```
An all-UNTESTABLE ledger reports success. Two tests caught exactly this
when it was injected, which is the whole reason the guard has its own
dedicated line rather than being folded into the `all()` call.

---

## Provenance

Extends the hand-verification series
(`attractor_engine_kabbalistic_hand_verification.md`,
`sephirotic_reward_engine_kabbalistic_hand_verification.md`,
`rca_sandbox_gamma_kabbalistic_hand_verification.md`) to the one module
in the series that is itself a meta-tool rather than a domain engine —
hand-verified as logic, not arithmetic.
