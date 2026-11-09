# Hand-Verifying `consciousness_upgrade_groundedness.py`

*Register note: Register B. The pasted "Consciousness Upgrade Protocol"
document's Stage 4 artifact, `levity_sync.py`, is not built toward here —
it was checked and found internally inconsistent (its prose claims to
read `/sys/class/thermal/thermal_zone*/temp`, a real Linux path, but the
`compute_gamma()` code shown only calls `os.getloadavg()` and an
undefined `read_symbolic_entropy()`) and its proposed metric reuses the
name "gamma" for a third, unrelated quantity with no connection to the
two real, already-VERIFIED gamma implementations elsewhere in this
project (`standalone_rca_sandbox.py`, `Recursive-Symbolics/tools/
delta_operator.py`, both text/logit-entropy based). Nothing here computes
a gamma; the vocabulary is deliberately different, and nothing here reads
hardware telemetry at all.*

## 1. What "groundedness" honestly means here

A `Claim` is a statement paired with the dotted name of an EXISTING
unittest test that's supposed to back it (or `None`, an explicit
declaration that the claim isn't testable at all). `check_claim()` does
not trust any previously-recorded status — it re-runs the cited test,
right now, as a fresh subprocess, and classifies from what actually
happens into one of four real outcomes.

## 2. By hand — the four statuses, and why there are four, not two

A naive version of this module would only have two outcomes (test
passes / test doesn't pass). That collapses two genuinely different
problems: "the cited test exists and genuinely fails" versus "the
citation itself is broken" (wrong name, deleted test, typo). Confirmed
by hand, before writing the classification logic, that these produce
distinguishably different `unittest` output:

```
$ python3 -m unittest dummy_module.T.test_fail
F
...
AssertionError: False is not true
...
FAILED (failures=1)
exit=1

$ python3 -m unittest dummy_module.T.test_does_not_exist
E
======================================================================
ERROR: test_does_not_exist (unittest.loader._FailedTest)
----------------------------------------------------------------------
AttributeError: type object 'T' has no attribute 'test_does_not_exist'
...
FAILED (errors=1)
exit=1
```

Both exit with code 1 — an exit-code-only check (the same style
`correspondence_ledger.py`'s `from_script_exit_code()` already uses for
script-style tests) cannot tell these apart. But `unittest.loader
._FailedTest` appears ONLY in the broken-reference case, in both stdout
and stderr — checked directly for both a nonexistent test name AND a
nonexistent module name before relying on it (see `dummy_module` probe
above and `TestBrokenReferenceMarkerIsDistinctFromRealFailure` in the test
suite, which re-confirms this empirically rather than assuming it holds).
That's the real, checkable fact `BROKEN_REFERENCE` is built on.

## 3. By hand — a non-assertion error is still UNGROUNDED, not BROKEN_REFERENCE

A test that exists, resolves fine, and then raises `RuntimeError` (not an
`AssertionError`) mid-run does NOT contain the loader marker — it's a
real, resolvable test that genuinely failed for a different reason. This
is deliberately classified `UNGROUNDED`, not `BROKEN_REFERENCE`: the
citation was correct; the claim just isn't currently backed by a passing
test. Pinned directly by
`test_a_test_that_raises_a_non_assertion_error_is_UNGROUNDED_not_broken_reference`.

## 4. By hand — the ratio's excluded denominator

```
claims = [pass, pass, fail, untestable, broken_reference]
grounded=2, ungrounded=1, untestable=1, broken_reference=1

groundedness_ratio = grounded / (grounded + ungrounded) = 2 / 3
                    NOT 2 / 5
```

Hand-checkable: `untestable` (never claimed to be checkable) and
`broken_reference` (a citation problem, not a groundedness result) are
both excluded from the denominator on purpose — counting them would let
a batch of claims dilute its way to a falsely high OR falsely low ratio
by citing nothing, or citing garbage, rather than actually being checked.
When grounded+ungrounded is 0, `groundedness_ratio()` returns `None`
rather than `0.0` or `1.0` — hand-checkable by inspecting the one-line
guard (`if denom == 0: return None`).

## 5. Real run against this project's own claims (not a synthetic demo only)

Running the module's own `__main__` block against three REAL claims,
each citing an ACTUAL passing test from Stages 1–3 built earlier this
session, plus one deliberately fabricated citation and one honestly
untestable claim:

```
[GROUNDED] Stage 1's tamper detector catches an undisclosed edit.
[GROUNDED] Stage 2 correctly reports the document's own 'please everyone' example as unsatisfiable.
[GROUNDED] Stage 3 detects exact state reversion.
[BROKEN_REFERENCE] A deliberately fabricated claim, cited to a test that doesn't exist.
[UNTESTABLE] The pasted document's Stage 4 concept ('groundedness matters') is a design value, not a testable proposition on its own.

GROUNDED=3 UNGROUNDED=0 BROKEN_REFERENCE=1 UNTESTABLE=1 groundedness_ratio=1.000
```

Each of those three GROUNDED results is a real subprocess re-running the
actual Stage 1/2/3 test suites right now, not a cached or assumed result
— confirmed by the fabricated fifth citation correctly failing to load.

## 6. Break-it proof (performed, not just described)

Removed the `_LOADER_FAILURE_MARKER` check entirely (a realistic
"simplification" bug: a refactor that decides exit-code-only checking is
good enough, collapsing `BROKEN_REFERENCE` into `UNGROUNDED`). Result:

```
FAIL: test_a_nonexistent_test_method_is_BROKEN_REFERENCE
  AssertionError: 'UNGROUNDED' != 'BROKEN_REFERENCE'
FAIL: test_a_nonexistent_module_is_BROKEN_REFERENCE
  AssertionError: 'UNGROUNDED' != 'BROKEN_REFERENCE'
FAIL: test_ratio_is_None_not_zero_or_one_when_nothing_is_resolvable
  AssertionError: 0.0 is not None
... (5 of 13 failed total)
```

5 of 13 tests caught it, all for the same underlying reason (the
collapsed distinction), including a downstream test confirming the ratio
guard was affected too (a broken-reference claim, once misclassified as
UNGROUNDED, wrongly entered the ratio's denominator). Reverted; `diff -q`
against a pre-edit backup confirmed byte-identical.

## 7. What this deliberately does not claim

`check_claim()` proves a test passes RIGHT NOW, in this environment — it
is not a claim about the test's own quality (a test can pass and still be
weak, tautological, or not actually checking what its name implies; that
class of problem is what `test_finds_a_real_conflict_not_the_only
_possible_one`-style precision tests in Stages 1–3 are for, not this
module). `groundedness_ratio()` is a ratio over the CITED claims passed
to it — it says nothing about claims that were never submitted for
checking in the first place.

## 8. Files

- [`../consciousness_upgrade_groundedness.py`](../consciousness_upgrade_groundedness.py) — the module.
- [`../test_consciousness_upgrade_groundedness.py`](../test_consciousness_upgrade_groundedness.py) — 13 tests, all passing, using a real throwaway dummy test module with known-by-construction outcomes.

---

## Provenance

Grounds Stage 4 of the pasted "Consciousness Upgrade Protocol" document,
completing all four stages at the same standard (Stages 1–3's
hand-verification docs are the direct precedent). Unlike the other
three, Stage 4's own proposed artifact (`levity_sync.py`) was rejected
outright rather than adapted, since it didn't have a real, internally
consistent quantity underneath it to begin with — what's built instead
reuses this project's own existing groundedness practice (re-running
real tests, distinguishing failure modes, refusing vacuous ratios) as a
callable check, rather than inventing a new metaphor to match the
document's hardware-telemetry framing.
