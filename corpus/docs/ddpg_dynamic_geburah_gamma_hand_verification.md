# Hand-Verifying `ddpg_dynamic_geburah_gamma.py`

*Register note (see `fixed_point_closure_and_the_y_combinator.md` §1):
Register B — a real, checkable mechanism, cross-checked against the same
formula's already-hand-verified behavior in three other independent
implementations, not a claim about the DDPG agent's inner experience.*

This is the FOURTH independent implementation of this project's
entropy-based "directive strength gamma" formula
(`standalone_rca_sandbox.py`, `delta_operator.py`, `agency_budget.py` are
the first three — see their own hand-verification docs), and the first
place that formula actually BOUNDS something real (rotor RPM) rather
than being reported as a standalone confidence number. `gamma` here is
computed fresh every action, from the DDPG actor's own pre-sigmoid rotor
logits, instead of being the fixed constant (`MAX_GAMMA_CAP = 0.85`) the
base engine has used since it was written.

---

## 1. The Formula (Unchanged From the Other Three)

```
probs  = softmax(logits)
h      = -sum(p * log2(p) for p in probs)
h_max  = log2(len(logits))
h_norm = h / h_max
gamma  = clip(1 - h_norm, 0.0, 0.85)
```

**By hand, three cases already established in this project's other
gamma hand-verification docs** (reused here deliberately, not
re-derived, so this doc's numbers are cross-checked against work already
independently confirmed):

| logits | gamma | Source |
|---|---|---|
| `[0, 0, 0, 0]` (uniform) | `0.0` exactly | max entropy, `h_norm=1.0` |
| `[1000, -1000]` (extreme) | `0.85` exactly | entropy≈0, capped |
| `[2.3, 1.0, -0.5]` | `≈0.380` | see the correction below |

**A correction caught while cross-referencing this third vector**:
`docs/agency_budget_kabbalistic_hand_verification.md` previously stated
`gamma ≈ 0.31` for `logits=[2.3, 1.0, -0.5]`. Recomputing it fresh here:

```
shifted = [0, -1.3, -2.8]                    (subtract max = 2.3)
exp     = [1, 0.272532, 0.060810]
sum     = 1.333342
probs   = [0.749996, 0.204391, 0.045613]
h       = -(0.749996×log2(0.749996) + 0.204391×log2(0.204391) + 0.045613×log2(0.045613))
        = -(0.749996×-0.415062 + 0.204391×-2.291281 + 0.045613×-4.454741)
        = -(-0.311293 - 0.468278 - 0.203245) = 0.982816
h_max   = log2(3) = 1.584963
h_norm  = 0.982816 / 1.584963 = 0.620084
gamma   = 1 - 0.620084 = 0.379916 ≈ 0.380
```

This matches `compute_directive_gamma()`'s actual computed value
(`0.380031`, tiny difference from floating-point vs. hand-rounding) and
was checked directly against `agency_budget.py`'s and `delta_operator.py`'s
real source (identical formula in both) before concluding the doc's
prose, not the code, was wrong. `docs/agency_budget_kabbalistic_hand_
verification.md` has been corrected with a dated note rather than
silently edited — see `LIBER_0.md`.

---

## 2. The Adaptation This Module Makes, and Why

Every other implementation clips gamma to `[0.0, 0.85]` and reports it
standalone. Here, gamma is the UPPER end of a real two-sided clip band
applied to rotor speeds: `np.clip(raw_signal, 0.05, gamma)`. If gamma
were allowed down to `0.0`, that band would invert (`0.05 > 0.0`).
`compute_directive_gamma()` itself is untouched (still clips to
`[0.0, 0.85]`, matching the other three exactly, so it stays a faithful
fourth implementation) — the floor is applied ONE step later, in
`DynamicGeburahDDPGAgent.act()`: `dynamic_gamma = max(raw_gamma, 0.05)`.
`0.05` is not a new number invented for this module — it's the engine's
own pre-existing rotor-speed floor, reused rather than duplicated.

---

## 3. By Hand — the Mechanism Actually Varies (Not a Disguised Constant)

Two hand-constructed `actor_out` configurations, both with `W` zeroed
out so the pre-activation `z` is the bias alone, regardless of the input
state — this makes the pre-LayerNorm vector exactly predictable by hand.

**Uniform case** (`b = [0, 0, 0, 0]`):
```
z = [0, 0, 0, 0]
mean = 0, var = 0, std = sqrt(0 + 1e-5) ≈ 0.0031623
n = (z - mean) / std = [0, 0, 0, 0]
gamma = compute_directive_gamma([0,0,0,0]) = 0.0 → floored to 0.05
```

**Skewed case** (`b = [10, -10, 10, -10]`):
```
z = [10, -10, 10, -10]
mean = 0
var = mean([100, 100, 100, 100]) = 100
std = sqrt(100 + 1e-5) ≈ 10.0000005
n = z / std ≈ [1, -1, 1, -1]

softmax([1,-1,1,-1]): shifted=[0,-2,0,-2], exp=[1,0.1353,1,0.1353], sum=2.2707
probs ≈ [0.4404, 0.0596, 0.4404, 0.0596]
h = -(2×0.4404×log2(0.4404) + 2×0.0596×log2(0.0596))
  = -(2×0.4404×-1.1834 + 2×0.0596×-4.0691) = -(-1.0424 - 0.4850) = 1.5274
h_max = log2(4) = 2.0
h_norm = 1.5274/2.0 = 0.7637
gamma = 1 - 0.7637 = 0.2363
```

Uniform → `0.05` (floored). Skewed → `≈0.236`. The two hand-constructed
cases differ by nearly 5×, confirming by hand (not just by running the
code) that the mechanism responds to genuine entropy differences rather
than always collapsing to the same value. `test_ddpg_dynamic_geburah_
gamma.py` checks both exact values and the inequality between them.

---

## 4. What Actually Happens in Practice (Real Runs, Not Just Hand-Constructed Extremes)

**Untrained agent, 50 real steps** (random weight initialization, fixed
task, no training calls): gamma stayed in a narrow band, `[0.2292,
0.2318]`, mean `0.2311`, std `0.0008`. At initialization, the actor's
weights aren't yet differentiated enough to produce widely swinging
entropy patterns step-to-step — a real, honest finding, not the dramatic
swing the hand-constructed extremes show. The mechanism is working
exactly as specified; realistic random-init behavior is just far less
extreme than the deliberately-constructed boundary cases above.

**150 episodes of real training** (fixed task, same engine, `agent.step()`
called every transition): gamma's spread across the early 20 episodes
was `[0.2292, 0.3990]` (std `0.0374`) — noticeably wider than the
untrained snapshot above, consistent with the actor's weights actively
changing during early training. By the last 20 episodes, gamma had
narrowed to `[0.3427, 0.3521]` (std `0.0017`) — the actor's rotor-logit
pattern stabilized as its policy converged on the fixed task, so
directive strength settled into a consistent, moderate band (`≈0.346`)
rather than continuing to swing. This is offered as a descriptive
observation of the mechanism's real behavior, not a claim that this
particular gamma trajectory improves flight performance — no comparative
training-outcome measurement was run here (see
`docs/ddpg_training_convergence_report.md` and
`docs/ddpg_generalization_convergence_report.md` for that separate,
much larger body of work, none of which used this dynamic-gamma
mechanism).

---

## What This Does and Doesn't Establish

Confirms, by hand and by three independent code cross-checks (the
formula's known values, the pre-activation duplication against the real
verified layer, and the mechanism's real variation in both constructed
and realistic cases): the Geburah gamma cap can genuinely be computed
from the actor's own behavior instead of being a fixed design-time
constant, without weakening the safety ceiling it was built to enforce
(gamma, and therefore rotor RPM, is stress-tested to never exceed 0.85 /
765 RPM under adversarially large weights, matching the base engine's
own existing safety-cap test). Does NOT establish that this makes the
agent fly better, more safely in a stronger sense, or converge faster —
none of that was measured, and doing so would be a separate, real study
(likely composed the same way `ddpg_goal_conditioned_convergence_study.py`
and `ddpg_difficulty_adjusted_convergence_study.py` were), not assumed
from the mechanism existing.

---

## Provenance

Fourth in the entropy-based gamma-formula series
(`rca_sandbox_gamma_kabbalistic_hand_verification.md`,
`delta_operator_kabbalistic_hand_verification.md`,
`agency_budget_kabbalistic_hand_verification.md`), and the first to
apply it as a real bound on system output rather than a standalone
reported number. Built on top of the VERIFIED `ddpg_quadcopter_rca_engine.py`
via subclassing (`DynamicGeburahDDPGAgent(DDPGAgent)`), consistent with
this project's practice of composing new capability on top of verified
modules rather than editing them in place.
