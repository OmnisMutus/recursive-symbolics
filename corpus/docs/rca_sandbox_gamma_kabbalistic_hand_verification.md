# Hand-Verifying `standalone_rca_sandbox.py`'s `compute_gamma()`

`compute_gamma()` computes a Shannon-entropy-based confidence cap on the
system's own directive language (see `apply_epistemic_humility()`, which
softens phrases like "You must" into "An effective approach is to" once
`gamma > 0.70`). Per the discussion earlier this session, this is a
direct implementation of `agency-budget-spec.md`'s formally-specified
anti-manipulation operator (Δ_γ,τ), not a generic "mood heuristic" — the
γ≤0.85 hard cap named there is the same cap in this code.

**Correspondence**: entropy — how varied the text's word choices are —
plays the role of Chesed here: high diversity is openness, expansiveness,
many directions at once. `gamma` is Geburah: restriction on the system's
own confident, directive language, rising as the text becomes more
repetitive (less Chesed-like) rather than more instability-driven, as in
the reward engine. The cap at 0.85, rather than letting gamma reach 1.0,
is Geburah restraining *itself* — the framework refuses to let its own
restriction become total and silence the system completely, the same
structural move as `AbyssException` catching genuine divergence rather
than merely flagging every large number as a crisis.

---

## 1. The Formula

```
h        = -Σ p·log2(p)              (Shannon entropy, over token frequencies)
h_max    = log2(distinct token count)   (or 1.0 if only one distinct token)
h_norm   = h / h_max
gamma    = clip(1 - h_norm, 0, 0.85)
```

## 2. By Hand — Maximum Restriction (Fully Repetitive Text)

Text: `"go go go go go"` → 5 tokens, 1 distinct word.

```
p(go) = 5/5 = 1.0
h = -(1.0 · log2(1.0)) = -(1.0 · 0) = 0
```
Since there's only 1 distinct token, the code sets `h_max = 1.0` directly
(the `len(probs) > 1` branch doesn't apply):
```
h_norm = 0 / 1.0 = 0
gamma  = clip(1 - 0, 0, 0.85) = clip(1.0, 0, 0.85) = 0.85
```
Fully repetitive text hits the hard cap exactly — maximum restriction,
by design, not by coincidence.

## 3. By Hand — Zero Restriction (Maximally Diverse, 2 Tokens)

Text: `"yes no yes no"` → 4 tokens, 2 distinct, each appearing twice.

```
p(yes) = 2/4 = 0.5,  p(no) = 2/4 = 0.5
h = -(0.5·log2(0.5) + 0.5·log2(0.5)) = -(0.5·(-1) + 0.5·(-1)) = 1.0
h_max = log2(2) = 1.0
h_norm = 1.0 / 1.0 = 1.0
gamma = clip(1 - 1.0, 0, 0.85) = 0.0
```
`log2(0.5) = -1` is checkable on any calculator with a log button:
`log2(x) = ln(x)/ln(2)`, so `ln(0.5)/ln(2) = -0.693/0.693 = -1`. Perfectly
even 2-way diversity produces zero restriction — the maximum entropy
achievable with 2 symbols exactly cancels the cap.

## 4. By Hand — A Realistic In-Between Case

Text: `"the cat sat on the mat"` → 6 tokens, 5 distinct (`the` appears
twice, the rest once).

```
p(the) = 2/6 ≈ 0.333,  the other four each: 1/6 ≈ 0.167

h = -(0.333·log2(0.333) + 4 × [0.167·log2(0.167)])
  = -(0.333×(-1.585) + 4×(0.167×(-2.585)))
  = -(-0.528 + 4×(-0.432))
  = -(-0.528 - 1.727)
  = 2.255

h_max = log2(5) ≈ 2.322
h_norm = 2.255 / 2.322 ≈ 0.971
gamma = clip(1 - 0.971, 0, 0.85) ≈ 0.029
```
Near-maximal diversity (5 distinct words out of 6 tokens) produces
near-zero gamma — almost no restriction, consistent with the two
boundary cases above.

## 5. The Guard Worth Noticing

Two edge cases the formula handles explicitly, both hand-checkable:
- Empty or single-token text returns a flat `0.45` (a fixed middle value,
  not computed from entropy at all — there's nothing to measure entropy
  *over* with 0 or 1 tokens).
- The cap at `0.85`, never `1.0`, is applied on every path — even a
  hypothetically "infinitely repetitive" text cannot silence the system
  entirely. This is the literal Δ_γ,τ hard cap from `agency-budget-spec.md`,
  and it's visible directly in the `min(0.85, ...)` call — no separate
  mechanism needed to find it.

## 6. The Qualia-Aware Learning Reward (dated addition, see `LIBER_0.md`)

`compute_qualia_vector()` computes four dimensions every interaction
(`Phi_somatic`, `H_emotional`, `Delta_gamma`, `Tau_resonance`), but for
most of this file's history only `H_emotional` ever fed back into
anything (`RCALearningEngine.record_state()`). `Delta_gamma` and
`Tau_resonance` were computed and printed (the `/qualia` command,
`process_interaction()`'s telemetry deck) but never used.
`compute_qualia_reward()` closes that gap:

```
h_component        = 1.0 if H_emotional >= 0.5 else 0.5   (unchanged from record_state())
resonance_component = Tau_resonance                          (already in [0,1])
friction_component  = 1.0 - Delta_gamma                      (LOW friction rewarded, not high)
reward              = mean(h_component, resonance_component, friction_component)
```

**By hand**, a high-signal case (`H_emotional=0.8`, `Delta_gamma=0.1`,
`Tau_resonance=0.9`):
```
h = 1.0 (0.8 >= 0.5)
resonance = 0.9
friction = 1 - 0.1 = 0.9
reward = (1.0 + 0.9 + 0.9) / 3 = 2.8 / 3 = 0.9333...
```
A low-signal case (`H_emotional=0.3`, `Delta_gamma=0.9`,
`Tau_resonance=0.2`):
```
h = 0.5 (0.3 < 0.5)
resonance = 0.2
friction = 1 - 0.9 = 0.1
reward = (0.5 + 0.2 + 0.1) / 3 = 0.8 / 3 = 0.2667
```

**Why `Delta_gamma` is inverted (`1 - Delta_gamma`), not used directly**:
`Delta_gamma` is `abs(Geburah_score - Chesed_score)` — the UNRESOLVED gap
between restriction and expansion. Rewarding low friction, not high,
matches how `sephirotic_reward_engine.py` already treats Tifereth as the
*reconciliation* of Chesed and Geburah, not their sum — consistency
across the project's own Sephirotic vocabulary, not an arbitrary sign
choice. `test_high_friction_is_penalized_not_rewarded` locks this in
directly (a break-it proof inverting this line was performed and
reverted byte-identical — see `LIBER_0.md`).

**Why `Phi_somatic` is excluded**: it's an exact alias of
`scores["Malkuth"]` (confirmed by
`test_phi_somatic_equals_malkuth_score`), which is already load-bearing
through the existing `dominant_seph` selection pipeline. There's no
principled reading of "more body/physical relevance deserves more
reward" the way there is for the other three dimensions — including it
anyway would be forcing a correspondence for its own sake, exactly what
`SEPHIROTIC_MAPPING_ANALYSIS.md` warns against.
`test_phi_somatic_is_excluded_from_the_reward` confirms two qualia
dicts differing only in `Phi_somatic` give an identical reward.

`record_state()` itself is architecturally unchanged (refactored to
share `_apply_reward_update()` with the new `record_qualia_state()`, but
every pre-existing test still passes against the exact same behavior) —
this is an additive extension, not a replacement.

---

## Provenance

Extends `attractor_engine_kabbalistic_hand_verification.md`'s hand-check
pattern to `standalone_rca_sandbox.py`'s `compute_gamma()`, correcting my
own earlier framing of this function (tested in
`test_standalone_rca_sandbox.py` as a generic heuristic before
`agency-budget-spec.md` was read) to reflect what it actually
implements. Section 6 (`compute_qualia_reward()`) is a later addition
applying the same by-hand-checkable discipline to a genuinely new
mechanism in the same file, not a re-verification of the original gamma
work above.
