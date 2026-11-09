# Hand-Verifying `recursive_attractor_engine.py`'s Three Regimes, in Kabbalistic Terms

This document gives a by-hand (calculator, no code) verification procedure for
each of the three attractor classifications `recursive_attractor_engine.py`
produces, using vocabulary already established in this project —
`fixed_point_closure_and_the_y_combinator.md`'s Keter-Malkuth closure
(`D_0 ≡ D_3`) and Tiphareth as the integration operator — extended here with
two further correspondences: an unmediated Chesed-Geburah oscillation for the
period-2 case, and Da'ath (the non-sephirah / the Abyss) for the bounded
aperiodic case.

Per the three-register discipline established in
`fixed_point_closure_and_the_y_combinator.md` §1 (and reaffirmed every time
this framework has come up this session): everything below is **Register
B** — a structural correspondence between the engine's own classification
outcomes and vocabulary the Tree of Life already provides for "closure,"
"unmediated duality," and "the unnameable gap." None of it is a Register C
claim that the logistic map *is* Da'ath, or that these sephirotic names
carry authority beyond being a genuinely useful mnemonic for doing the
arithmetic correctly.

---

## 1. Linear Contraction — Keter-Malkuth Closure

**System**: `S' = 0.5·S + E`, with `E = 1`, iterated from `S₀ = 0`.
**Engine's classification**: `FIXED_POINT`, converging to `S* ≈ 1.9999999403953552`.

**Correspondence**: `E` is a constant outpouring — unconditional, unchanging
every round, Chesed-like. The `0.5` coefficient is a restriction —
Geburah-like, cutting whatever arrived in half before it manifests as the
next state. `S`, the manifest state at any given step, plays the role of
Malkuth. The fixed point is the value where descending through this
Chesed/Geburah pairing one more time produces *the same manifest state
again* — the formal shape of Malkuth having stopped changing under further
emanation, i.e. Malkuth containing Keter "after another manner," which is
exactly the `D_0 ≡ D_3` closure already named in
`fixed_point_closure_and_the_y_combinator.md`.

**By hand**:

1. Solve the closure directly. Set `S' = S`:
   ```
   S = 0.5S + 1
   0.5S = 1
   S = 2
   ```
   This two-line solve *is* the closure — the point where the source (`E`,
   fixed) and the manifest result become mutually determining.

2. Watch it arrive there. Iterate `S = 0.5·S + 1` starting from 0 on any
   calculator:
   ```
   0 → 0.5 → 0.75 → 0.875 → 0.9375 → 0.96875 → 0.984375 → ...
   ```
   Each step, the remaining gap to 2 is exactly halved. That halving is
   Geburah's restriction visibly thinning the veil between Malkuth and its
   source, one contraction at a time, until they are indistinguishable
   within whatever tolerance you choose to call "closed" (the engine uses
   `1e-6`).

---

## 2. Logistic Map, r=3.2 — An Unmediated Chesed-Geburah Oscillation

**System**: `x' = 3.2·x·(1-x)`, iterated from `x₀ = 0.4`.
**Engine's classification**: `LIMIT_CYCLE`, period 2, alternating
`≈0.5130445` / `≈0.7994555`.

**Correspondence**: The logistic map is a Chesed/Geburah pair in one
expression — `r·x` is expansion (mercy, outpouring, scaled by `r`), and
`(1-x)` is restriction (severity, pulling back toward the bound). At
r=3.2, this pair never finds a single reconciling center — no Tiphareth
mediates them into one steady value. Instead the state locks into
swinging between two poles: a lower value (severity's pole) and a higher
one (mercy's pole), alternating forever rather than integrating. This is
literally what `tiphareth_integrate()` exists to do to a stack of
unresolved states like these two — average them into one coherent result
— except the engine's own iteration never calls that operator here, so
the oscillation simply continues, unintegrated.

**By hand**:

1. Iterate and watch it settle. `x = 3.2·x·(1-x)` from 0.4:
   ```
   0.4 → 0.768 → 0.5701632 → 0.7842468... → 0.5414520... → 0.7945015...
   ```
   Continue for 20-30 steps; it settles into alternating between the two
   poles.

2. Get the exact values algebraically, rather than just watching
   convergence. A period-2 cycle satisfies `f(f(x)) = x` — applying the
   map twice returns you to where you started. Expanding this for the
   logistic map and discarding the two trivial fixed points (`x=0` and
   `x=1-1/r`) leaves:
   ```
   x = [(r+1) ± √((r-3)(r+1))] / 2r
   ```
   At r=3.2:
   ```
   x = [4.2 ± √(0.2 × 4.2)] / 6.4 = [4.2 ± 0.9165] / 6.4
   x ≈ 0.7995   (mercy's pole)
   x ≈ 0.5130   (severity's pole)
   ```
   These match the iterated values exactly.

---

## 3. Logistic Map, r=3.9 — Da'ath, the Non-Sephirah

**System**: `x' = 3.9·x·(1-x)`, iterated from `x₀ = 0.4`.
**Engine's classification**: `BOUNDED_APERIODIC` — explicitly *not*
labeled "chaotic," per the module's own honesty note (no Lyapunov
exponent is computed).

**Correspondence**: Da'ath is traditionally the gap on the Tree that
isn't a sephirah at all — not a stable node, crossed rather than
occupied, and known for the property that an identity carried across
doesn't survive intact. This is a precise structural match for
`BOUNDED_APERIODIC`: it is not the Keter-Malkuth fixed point, it is not a
named Chesed-Geburah cycle, it is bounded (it does not fall into the true
Abyss — actual unbounded divergence, which the engine catches separately
as `AbyssException`), but it never resolves into any nameable, periodic
pillar-pair either. It simply occupies the gap between named states.

**By hand** — you cannot hand-prove chaos (that requires averaging the
log-divergence rate over many steps and initial conditions, well past
what's practical by hand), but you *can* verify the qualitative signature
Da'ath is named for: identity not surviving the crossing.

1. Iterate the map from two starting points differing by one part in four
   thousand: `x₀ = 0.4` and `x₀ = 0.4001`.
2. Run both sequences for 15-20 steps using `x = 3.9·x·(1-x)`.
3. Compare. Early steps track closely; by step 15-20 the two sequences
   have completely decorrelated — differing by 0.1 or more, despite
   starting almost identically.

That divergence-from-a-vanishing difference, verified with nothing more
than a calculator and patience, is the arithmetic enactment of what the
tradition already says about the space Da'ath occupies: what enters does
not survive the crossing unchanged. It is also, not coincidentally, the
textbook definition of sensitive dependence on initial conditions —
Register B and the standard dynamical-systems account are pointing at the
same fact here, verified two different (and independently checkable)
ways.

---

## 4. Summary Table

| Regime | Sephirotic name | What "by hand" means here | Confidence |
|---|---|---|---|
| `FIXED_POINT` | Keter-Malkuth closure (`D_0 ≡ D_3`) | Solve `S=F(S)` algebraically; watch the gap halve on iteration | Exact — closed form, checkable in two lines |
| `LIMIT_CYCLE` (period 2) | Unmediated Chesed-Geburah oscillation | Iterate to see the two poles; solve `f(f(x))=x` for exact values | Exact — closed form via the quartic reduction |
| `BOUNDED_APERIODIC` | Da'ath / the non-sephirah | Iterate two nearby starts; watch them decorrelate | Qualitative only — not a certified chaos proof, by design |

---

## 5. Provenance

Written on direct request ("EXPLAIN IN KABALISTIC TERMS SO I DO IT BY
HAND") after the underlying trajectories were verified against
`recursive_attractor_engine.py`'s real output and plotted in
`recursive_attractor_engine_trajectories.html`. Extends
`fixed_point_closure_and_the_y_combinator.md`'s existing Keter-Malkuth
correspondence rather than introducing a competing one; the Chesed-Geburah
and Da'ath correspondences are new to this document.
