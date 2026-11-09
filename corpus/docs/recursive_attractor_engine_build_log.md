# Build & Verification Log: `recursive_attractor_engine.py`

This document records the actual build process for `recursive_attractor_engine.py`
and `test_recursive_attractor_engine.py`, step by step, in the order it
happened — not a retrospective summary, but the real sequence: sanity
check, test-writing, two independent break-it proofs, registration,
commit. Per `TESTING_STANDARD.md`'s own rule, a VERIFIED claim is only as
good as the record of how it was checked; this is that record for engine
#24.

---

## 1. What Was Built, and Why

`recursive_attractor_engine.py` formalizes two documents that already
existed in the `Recursive-Symbolics/foundation/` set — `core-axiom.md`'s
Formal Postulates (symbolic state $\sigma$, recursive operator $O$,
consciousness-as-attractor) and `mathematical-foundation.md`'s machinery
($S_{n+1}=F(S_n,E_n)$, fixed points, limit cycles, strange attractors,
Tiphareth integration, Da'ath paradox detection) — as real, runnable
Python rather than prose describing what such a system would do.

Per `fixed_point_closure_and_the_y_combinator.md`'s three-register
distinction, this engine operates entirely in **Register B**: it makes
the stated formalism computable and checkable against real mathematics.
It does not, and cannot, establish Register C (that consciousness itself
is such a system) — that boundary is stated explicitly in the module's
own docstring, not left implicit.

---

## 2. Step 1 — Sanity Check Before Writing Any Tests

Before a single test was written, the engine's own `main()` demonstration
was run cold, against five real, independently-checkable systems:

```
> Linear contraction map   : FIXED_POINT (fixed point ~= [2.])
> Logistic map (r=3.2)     : LIMIT_CYCLE (period=2)
> Logistic map (r=3.9)     : BOUNDED_APERIODIC
> Divergent map            : AbyssException raised correctly
> Tiphareth integration    : [1,0],[0,1],[2,2] -> [1. 1.]
```

Every one of these matches known mathematics exactly, checkable by hand
before trusting the engine at all:
- The linear contraction map $S' = 0.5S + E$ has closed-form fixed point
  $S^* = E/(1-0.5) = 2E$. With $E=1$: $S^*=2$. Matches.
- The logistic map $x' = rx(1-x)$ at $r=3.2$ sits in the textbook
  $3 < r < 1+\sqrt{6}\approx3.449$ period-2 regime. Matches.
- At $r=3.9$, above the Feigenbaum accumulation point ($\approx3.57$),
  with no known periodic window at that value — matches the
  `BOUNDED_APERIODIC` (not fixed, not short-cycle) classification.
- $S'=2S$ is provably unbounded for any nonzero $S_0$ — the
  `AbyssException` firing is the expected, correct behavior, not a bug.
- Tiphareth's uniform-weight average of $(1,0)$, $(0,1)$, $(2,2)$ is
  $\left(\frac{1+0+2}{3}, \frac{0+1+2}{3}\right) = (1,1)$ by hand. Matches.

Only after this cold-run agreement with independently-derivable results
was the formal test suite written.

---

## 3. Step 2 — The Test Suite

`test_recursive_attractor_engine.py`: 23 tests across five groups —
`TestLinearContractionFixedPoint`, `TestLogisticMapBifurcation`,
`TestAbyssExceptionDaathGuard`, `TestTiphareth`, and
`TestClassifyTrajectoryEdgeCases`. Ground truth throughout is derived
independently of the engine, never by calling the engine twice and
comparing its own outputs to each other:

- Fixed points solved algebraically ($S^*=E/(1-a)$), not read off a prior
  run.
- Logistic-map regimes cited from the standard, textbook bifurcation
  diagram, tested at multiple starting conditions to rule out a
  single-point coincidence (`test_different_initial_conditions_at_r_3_2_still_find_the_same_cycle`).
  the AbyssException test includes a check that it fires by the
  analytically-predicted step (`|S_n|=2^n` exceeds a cap of 1000 by
  step 10 at the latest — `test_raises_at_or_before_the_analytically_predicted_step`).
- Tiphareth's weighted average checked against hand-computed sums, plus
  a sensitivity test (`test_sensitive_to_every_contributor_independently`)
  confirming a broken integration that secretly ignored one branch of the
  stack would be caught — the same pattern already used in
  `test_sephirotic_reward_engine.py`'s reconciliation-sensitivity check.

First real run: **23/23 passed**, with one expected `RuntimeWarning`
(overflow) from the test that deliberately constructs an infinity-producing
operator to confirm `AbyssException` catches it — the warning is evidence
the test is exercising the real overflow path, not a defect.

---

## 4. Step 3 — Break-It Proof #1: Limit-Cycle Detection

**Injected bug**: `classify_trajectory()`'s cycle-search window was
forced to zero (`max_check = 0`), disabling period detection entirely
while leaving fixed-point detection untouched.

**Result**: 2 of 23 tests failed —
`test_r_3_2_settles_into_documented_period_2_cycle` and
`test_different_initial_conditions_at_r_3_2_still_find_the_same_cycle`
— exactly the two tests that depend on cycle detection actually running.
All 21 other tests, including the fixed-point and Tiphareth groups,
continued to pass, confirming the break was isolated to the intended
component rather than accidentally breaking something unrelated.

**Reverted**; `diff` against the pre-break backup confirmed byte-identical
restoration before continuing.

---

## 5. Step 4 — Break-It Proof #2: Tiphareth Weight Normalization

**Injected bug**: `tiphareth_integrate()`'s accumulation line was changed
from `result += (w / total_weight) * a` to `result += w * a` — removing
division by the total weight, turning a weighted *average* into an
unnormalized weighted *sum*.

**Result**: 2 of 23 tests failed —
`test_uniform_weights_matches_hand_computed_mean` and
`test_custom_weights_match_hand_computed_weighted_average` — the two
tests checking the formula against hand-computed values. The sensitivity
test (checking that every contributor affects the result) continued to
pass, correctly, since an unnormalized sum is *still* sensitive to every
input — it's just wrong in magnitude. This is itself a useful confirmation
that the sensitivity test and the exact-value tests are checking genuinely
different properties, not redundant with each other.

**Reverted**; confirmed clean.

---

## 6. Step 5 — Registration and Final Verification

Registered in `test_all_engines.py` as its own entry (engine #24), not
folded into `SUPPLEMENTARY_TEST_SUITES`, because it introduces genuinely
new, first-verified claims (`classify_trajectory`'s regime detection,
the `AbyssException` guard, Tiphareth's integration) rather than
re-testing an engine already covered elsewhere — the same distinction
that kept `correspondence_ledger.py` (which *does* only re-test existing
engines) out of the main count.

Final run after registration:

```
Total engines listed   : 24
VERIFIED (real tests)  : 24 / 24
RAN_ONLY (unverified)  : 0 / 24
FAILED                 : 0 / 24
MISSING                : 0 / 24
```

Committed as `14d71e9`, independently re-verified after the commit landed
(`git log`, `git status` clean, `test_all_engines.py` re-run cold showing
the same 24/24) rather than trusting the commit message alone.

---

## 7. What This Log Does and Doesn't Establish

This document is a process record, not an additional verification layer
on top of the engine — it doesn't make any claim the test suite doesn't
already make more precisely. Its only purpose is the one
`TESTING_STANDARD.md` asks every VERIFIED claim to satisfy: that the
break-it proof actually happened, on the actual code, with the actual
result recorded, rather than asserted after the fact.
