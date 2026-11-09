# Hand-Verifying `agency_budget.py` (Recursive-Symbolics/tools/)

*Register note: Register B. This is the THIRD independent implementation
of the same directive-strength gamma formula found in this project
(`standalone_rca_sandbox.py`'s text-frequency version, `delta_operator.py`'s
NumPy/logit version, and now this pure-Python one) — verified the same
way the second one was: an independent cross-check plus a from-scratch
reference, not just re-running the module against itself.*

## 1. The formula, unchanged across all three implementations

```
probs = softmax(logits)
h = -sum(p * log2(p) for p in probs)      # Shannon entropy, bits
h_norm = h / log2(n)                       # normalized to [0, 1]
gamma = clip(1 - h_norm, 0.0, 0.85)
```

## 2. Cross-check against `delta_operator.py` — a genuinely different implementation

`delta_operator.compute_gamma()` uses NumPy (`np.exp`, `np.log2`,
`np.clip`); `agency_budget.compute_gamma()` uses plain `math.exp`/
`math.log2` with Python lists — different library, different code,
written independently. Both read/hardcode the same cap: `delta_operator.py`
loads `MAX_GAMMA_CAP` from `sovereignty_config.json`
(`"max_gamma_cap": 0.85`, confirmed by reading the file directly, not
assumed); `agency_budget.py` hardcodes `0.85` in the same place. Ran both
on nine hand-picked cases (uniform, extremely peaked, single-logit,
negative logits, near-ties) — agreement to 9 decimal places on every one
(`test_agrees_with_delta_operator_on_every_case`).

## 3. By hand — uniform logits give exactly zero gamma

`logits = [0, 0, 0, 0]` → softmax gives `probs = [0.25, 0.25, 0.25, 0.25]`
→ `h = -4 * 0.25 * log2(0.25) = -4 * 0.25 * (-2) = 2` → `h_max = log2(4) = 2`
→ `h_norm = 1.0` → `gamma = 1 - 1.0 = 0.0`. Maximum entropy (total
uncertainty) genuinely produces zero directive strength — hand-checkable
without a calculator, confirmed by `test_uniform_logits_give_zero_gamma`.

## 4. By hand — the cap actually engages, and does so exactly

`logits = [1000, -1000]` → softmax collapses to essentially `[1.0, 0.0]`
→ entropy ≈ 0 → `h_norm ≈ 0` → `raw_gamma ≈ 1.0` → clipped to exactly
`0.85`, not `0.999...`. `test_extremely_peaked_logits_are_capped_at_085_not_1`
checks the returned value is the literal float `0.85`, not merely "close
to 1."

## 5. A real, checkable precision catch: `confidence_entropy` and `directive_strength` only sum to 1 when uncapped

`evaluate_sovereignty_metadata()` does NOT call `compute_gamma()`'s
internals — it duplicates the softmax+entropy computation from scratch
(confirmed by reading the code). This means:

- **Uncapped case** (`logits=[2.3, 1.0, -0.5]`, `gamma ≈ 0.380`): `hc` (the
  independently-recomputed normalized entropy) and `gamma` are the same
  underlying quantity computed twice, so `hc + gamma ≈ 1.0` exactly —
  confirmed to 3 decimal places by `test_hc_plus_gamma_equals_one_when_uncapped`.

  CORRECTION (dated, see `LIBER_0.md`): this line previously said
  `gamma ≈ 0.31`. Recomputing this exact vector by hand while
  cross-referencing it for `ddpg_dynamic_geburah_gamma.py`'s hand-
  verification doc (a 4th independent implementation of this same
  formula) gave `≈0.380`, not `0.31` — softmax([2.3,1.0,-0.5]) ≈
  [0.750, 0.204, 0.046], `h ≈ 0.9828` bits, `h_max = log2(3) ≈ 1.5850`,
  `h_norm ≈ 0.6201`, `gamma = 1 - 0.6201 ≈ 0.3799`. Checked against
  `compute_gamma()`'s actual source in both `agency_budget.py` and
  `delta_operator.py` directly (identical formula in both), not just
  against this doc's own prior prose. The number in this doc's prose was
  wrong; `test_hc_plus_gamma_equals_one_when_uncapped` itself was never
  affected, since it computes its own expected value dynamically rather
  than asserting a hardcoded `0.31` — this was a documentation-only
  error, not a code or test defect.
- **Capped case** (`logits=[1000, -1000, -1000]`): `gamma` is clamped to
  `0.85`, but `hc` is NEVER capped — it reports the true near-zero
  entropy. So `hc + gamma` is nowhere near 1 here (`hc < 0.05`, `gamma =
  0.85`, sum ≈ 0.85, not 1.0). This is a real, checkable divergence
  between two fields that look like they should always sum to 1 but
  provably don't in the capped regime — caught and pinned by
  `test_hc_plus_gamma_diverge_when_gamma_is_capped` rather than assumed
  away or left implicit.

## 6. A real, checkable dead-code fact in `apply_style_filter`

The function contains `if gamma > 0.85: gamma = 0.85` before its only
branch, which checks `gamma > 0.4`. Every value that would trigger the
cap (`> 0.85`) already satisfies `> 0.4` before capping — so this line,
while real code, can **never change this function's output**, for any
input. Confirmed directly, not assumed: `test_gamma_above_085_is_capped_
internally_but_has_no_observable_effect` passes a `gamma=5.0` and a
`gamma=0.85` through the function and checks the results are identical.
This is worth stating plainly rather than silently — a line that
compiles, runs, and does something, but never affects the one place its
result is used.

## 7. By hand — the alternatives/hedging truth table

| `alternatives_count` | `gamma` | Note appended? |
| :--- | :--- | :--- |
| 1 | 0.6 | Yes |
| 1 | 0.2 | No |
| 2 | 0.9 | No (enough alternatives already) |
| 1 | exactly 0.4 | No (`>` is strict) |
| 1 | 0.4000001 | Yes |

All five rows are individually asserted, including the exact boundary
(`gamma == 0.4`) — the same touching-bounds discipline as Stage 2's
constraint pruner.

## 8. Break-it proof (performed, not just described)

Changed the cap in `compute_gamma()` from `0.85` to `0.95` (a realistic
"someone tweaked the safety threshold" bug). Result: 5 of 19 tests failed
immediately — the direct cap-boundary tests, the random-sampling
never-exceeds-0.85 check, and (notably) the capped-divergence test in
`evaluate_sovereignty_metadata`, since that test's expected capped value
is the literal `0.85`. Reverted; `diff -q` against a pre-edit backup
confirmed byte-identical.

## 9. Files

- [`../../Recursive-Symbolics/tools/agency_budget.py`](../tools/agency_budget.py) — the module.
- [`../../Recursive-Symbolics/tools/test_agency_budget.py`](../tools/test_agency_budget.py) — 19 tests, all passing: cross-checked against `delta_operator.py` and a from-scratch reference, the capped/uncapped divergence pinned explicitly, and the dead-code cap fact confirmed directly.

---

## Provenance

Second file outside `solo/` brought to VERIFIED (after `delta_operator.py`),
following the exact same discipline: an independent cross-check against
a DIFFERENT existing implementation of the same formula, a from-scratch
reference for cases where two implementations agreeing isn't itself
conclusive, and a real adversarial break-it proof, performed and reverted.
