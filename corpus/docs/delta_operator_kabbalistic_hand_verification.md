# Hand-Verifying `delta_operator.py`'s `compute_gamma()`

*Scope note: `delta_operator.py` lives in the sibling `Recursive-Symbolics`
folder, not in this repo. It is included in this hand-verification series
because it implements the same Agency Budget formula
(`docs/recursive_symbolics_foundation_reference.md` section 14) that
`standalone_rca_sandbox.py`'s `compute_gamma()` already has a doc for
(`rca_sandbox_gamma_kabbalistic_hand_verification.md`) — same formula
shape, different input domain. This is the first time a file outside
`solo/` has been brought under this repo's own TESTING_STANDARD.md
discipline: `Recursive-Symbolics/tools/test_delta_operator.py` (16 tests,
break-it proof performed and reverted — see `LIBER_0.md`) is the actual
VERIFIED artifact; this document is its by-hand companion, same as every
other entry in this series.*

**The one real difference from the sandbox version, stated precisely**:
`standalone_rca_sandbox.py`'s `compute_gamma()` takes raw text, tokenizes
it, and computes Shannon entropy over *word frequencies*.
`delta_operator.py`'s `compute_gamma()` takes a list of *logits* (raw
model scores), runs them through softmax first, and computes Shannon
entropy over the resulting *probability distribution*. Same downstream
formula (`gamma = clip(1 - h_norm, 0, 0.85)`), different upstream
quantity being measured. Conflating "how varied is this text" with "how
concentrated is this model's output distribution" would be a real error;
they are kept distinct here.

---

## 1. The Formula

```
probs    = softmax(logits) = exp(x - max(x)) / sum(exp(x - max(x)))
h        = -Σ p·log2(p + 1e-12)        (Shannon entropy, over softmax'd logits)
h_max    = log2(len(logits))
h_norm   = h / h_max
gamma    = clip(1 - h_norm, 0, 0.85)
```

Two special cases short-circuit the formula entirely: an empty logit
list returns `0.0`; a single-element list returns the cap, `0.85`,
directly — there is no second value to compute a distribution over, so
the code defines this as maximum directivity rather than computing
`0/0` or raising.

## 2. By Hand — Two Equal Logits (Maximum-Entropy Case)

Logits: `[5.0, 5.0]`.

```
softmax: exp(5-5)=1, exp(5-5)=1  →  probs = [0.5, 0.5]
h = -(0.5·log2(0.5) + 0.5·log2(0.5)) = -(0.5×(-1) + 0.5×(-1)) = 1.0
h_max = log2(2) = 1.0
h_norm = 1.0
gamma = clip(1 - 1.0, 0, 0.85) = 0.0
```
Two equal logits produce the flattest possible softmax distribution —
zero directive strength, the mirror image of the sandbox version's
`"yes no yes no"` case.

## 3. By Hand — One Logit Dominant (`[1.0, 0.0]`)

```
softmax: exp(1-1)=1, exp(0-1)=e^-1≈0.36788
sum = 1.36788
probs ≈ [0.73106, 0.26894]

h = -(0.73106·log2(0.73106) + 0.26894·log2(0.26894))
log2(0.73106) = ln(0.73106)/ln(2) ≈ -0.3133/0.6931 ≈ -0.4520
log2(0.26894) = ln(0.26894)/ln(2) ≈ -1.3133/0.6931 ≈ -1.8951

h ≈ -(0.73106×(-0.4520) + 0.26894×(-1.8951))
  ≈ -(-0.3305 - 0.5097)
  ≈ 0.8402

h_max = log2(2) = 1.0
h_norm ≈ 0.8402
gamma ≈ clip(1 - 0.8402, 0, 0.85) ≈ 0.1598
```
Matches `test_delta_operator.py`'s `test_moderately_skewed_logits_uncapped_value`
(asserted to 6 places against the full-precision reference: `0.160058`).
The small arithmetic rounding above (0.1598 vs. 0.160058) is exactly what
hand-rounding intermediate logs should produce — this is the point of
doing it by hand with a calculator rather than claiming exactness.

## 4. By Hand — Softmax Shift Invariance (A Real Property, Not an Implementation Detail)

Softmax is mathematically invariant to adding a constant to every input:
`softmax(x + c) = softmax(x)` for any scalar `c`, because the constant
cancels in the ratio `exp(xᵢ+c) / Σexp(xⱼ+c) = exp(xᵢ)·exp(c) /
(exp(c)·Σexp(xⱼ))`. This means `[1.0, 0.0]` and `[101.0, 100.0]` must
produce *exactly* the same gamma — not approximately, exactly, since the
same cancellation applies before any entropy is computed.
`test_softmax_shift_invariance` checks this directly (`[1,0]`, `[101,
100]`, and `[-99,-100]` all assert equal to 9 decimal places), and it
held on the first run — this is also the mathematical reason
`delta_operator.py`'s `np.max`-subtraction trick (`exp(arr - np.max(arr))`)
is numerically safe for large logits: it's applying exactly this
invariance to keep the exponentials from overflowing, not an arbitrary
implementation choice.

## 5. The Cap, Verified by Deliberately Removing It

Section 5 of the sandbox version's doc notes the `0.85` cap is "visible
directly in the code, no separate mechanism needed to find it." The
same is true here, and this time it was checked by actually breaking it:
`np.clip(raw_gamma, 0.0, MAX_GAMMA_CAP)` was changed to
`np.clip(raw_gamma, 0.0, 1.0)` (simulating the cap silently disappearing),
the test suite was re-run, and **6 of 16 tests failed** — every test that
exercised a highly-skewed or single-element input (which should hit
`0.85` exactly) instead returned `1.0`. The file was then reverted and
confirmed byte-identical to the pre-break version (`diff -q`, no output),
and the full suite passed again (16/16). This is the adversarial
break-it proof `TESTING_STANDARD.md` requires, run against a file outside
`solo/` for the first time — see `LIBER_0.md`'s dated entry for the full
log.

---

## Provenance

Extends `rca_sandbox_gamma_kabbalistic_hand_verification.md`'s pattern to
`delta_operator.py`'s `compute_gamma()` in the `Recursive-Symbolics`
folder — the two functions implement the same Agency Budget formula over
different inputs (text-frequency entropy vs. logit-softmax entropy), and
this document exists to keep that distinction explicit rather than
treating them as identical because they share a name and a cap value.
