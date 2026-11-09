# Hand-Verifying `ddpg_quadcopter_rca_engine.py`

Like `sephirotic_reward_engine.py`, this engine's Sephirotic structure is
original to its own design — the module's section headers name it
directly: the environment is the **Malkuth Layer** (physical world), the
replay buffer and exploration noise are the **Chesed Layer** (expansive,
stochastic search), the actor/critic networks are the **Tiphereth &
Binah Layers** (integration and structured evaluation), and the action
cap is the **RCA Geburah Directivity Guardrail**. This document verifies
four of those pieces by hand, reusing the vocabulary the engine already
committed to rather than adding new correspondences.

---

## 1. The Reward Formula (Malkuth's Feedback Signal)

```
l1_penalty   = 0.003 × Σ|pose[:3] − target_pos|
ascent_bonus = 0.01 × v_z
raw_reward   = 1.0 − l1_penalty + ascent_bonus
reward       = tanh(raw_reward)
```

**By hand**: starting pose `(0, 0, 10)`, target `(0, 0, 100)`, `v_z = 0`.
```
Σ|pose - target| = |0-0| + |0-0| + |10-100| = 90
l1_penalty = 0.003 × 90 = 0.27
ascent_bonus = 0.01 × 0 = 0
raw_reward = 1.0 − 0.27 + 0 = 0.73
```
`tanh(0.73)` by hand, using `tanh(x) = (eˣ − e⁻ˣ)/(eˣ + e⁻ˣ)` and
`e^0.73 ≈ 2.0751`, `e^-0.73 ≈ 0.4819` (both computable on any scientific
calculator):
```
tanh(0.73) = (2.0751 − 0.4819) / (2.0751 + 0.4819) = 1.5932 / 2.5570 ≈ 0.6231
```

## 2. Euler Integration (One Physics Step)

```
total_thrust = Σ(speeds) × 0.025
az = (total_thrust / mass) − gravity
v_z += az × dt
pose_z += v_z × dt
```
With `mass = 1.25`, `gravity = 9.81`, `dt = 0.05`.

**By hand**, all four rotors at max (900 RPM each):
```
total_thrust = (900×4) × 0.025 = 3600 × 0.025 = 90.0
az = (90.0 / 1.25) − 9.81 = 72.0 − 9.81 = 62.19
v_z = 0 + 62.19 × 0.05 = 3.1095 m/s
pose_z = 10 + 3.1095 × 0.05 = 10.155475 m
```
This is exactly the arithmetic `test_ddpg_quadcopter_rca_engine.py`
checks the engine against — no simulation trust required, just four
lines of arithmetic.

## 3. Termination Boundaries and the Target Bonus

```
done = (pose_z <= 0.0) OR (pose_z >= 150.0) OR (step_count >= 100)
if pose_z >= target_pos[2]:
    overshoot = pose_z - target_pos[2]
    reward += max(0.0, 10.0 - 0.01 * overshoot)
```
**By hand**: these are exact inequalities, checkable by picking boundary
values directly — `pose_z = 150.0` exactly should trigger `done`,
`pose_z = 149.999...` should not; `step_count = 100` should trigger,
`99` should not.

THIRD CORRECTION (dated, see `LIBER_0.md`): the target bonus used to be
an unconditional flat `+10.0`, applied identically whether the drone was
exactly at the target or 50 meters past it. The goal-conditioning
follow-up study (`docs/ddpg_generalization_convergence_report.md`) traced
this as the most likely reason raw reward and a task-difficulty-
normalized `closure_fraction` metric moved in *opposite* directions under
training: the flat bonus rewarded "climb past the target and keep going"
exactly as much as "arrive precisely." The bonus now decays linearly with
overshoot distance, floored at 0.

**By hand**, two zero-thrust steps (`az = -gravity`, since thrust = 0),
target `z = 100`, starting one step before overshoot in each case:

Small overshoot, starting at `z = 100.05`:
```
az = 0/1.25 - 9.81 = -9.81
v_z = 0 + (-9.81)(0.05) = -0.4905
z_new = 100.05 + (-0.4905)(0.05) = 100.05 - 0.024525 = 100.025475
overshoot = 100.025475 - 100 = 0.025475
bonus = 10.0 - 0.01(0.025475) = 9.99974525
```

Large overshoot, starting at `z = 140.0` (same physics, only the starting
altitude differs):
```
z_new = 140.0 - 0.024525 = 139.975475
overshoot = 139.975475 - 100 = 39.975475
bonus = 10.0 - 0.01(39.975475) = 9.60024525
```

The two bonuses differ by hand: `9.99974525 - 9.60024525 = 0.3995`,
exactly `0.01 × (39.975475 - 0.025475) = 0.01 × 39.95 = 0.3995` — the
decay rate applied to the difference in overshoot, nothing more exotic.
This is a real but modest effect at the coefficient chosen (`0.01`,
carried over unchanged from `FUTURE_WORK.md`'s pre-registered proposal
rather than tuned after seeing results) — a 40-meter difference in
overshoot only costs about 4% of the bonus. Reported honestly as a small
effect rather than adjusted after the fact to look larger; see
`docs/ddpg_generalization_convergence_report.md` for whether this
coefficient was strong enough to actually reunify the raw-reward and
closure_fraction metrics in the re-run study.

## 4. Geburah's Directivity Cap — What 0.85 Actually Bounds

```
bounded_signal = clip(raw_signal, 0.05, 0.85)
rotor_speeds = bounded_signal × 900.0
```
**By hand**: the cap isn't abstract — multiply it out. `0.85 × 900 = 765`.
The Geburah guardrail means this agent can *never* command more than
765 RPM per rotor, regardless of what the actor network's raw output
says, and never less than `0.05 × 900 = 45` RPM. The restriction is a
literal, computable ceiling on physical thrust, not a metaphorical one —
you can verify it by picking any raw actor output above 0.85 (say, 0.99)
and confirming by hand that `clip(0.99, 0.05, 0.85) = 0.85`, not 0.99.

## 5. LayerNorm's Defining Property (Binah's Structuring Step)

```
normed = (z − mean(z)) / (std(z) + 1e-5)
```
**By hand**, a toy 4-value example `z = [1, 2, 3, 4]` (small enough to
compute without a calculator):
```
mean = (1+2+3+4)/4 = 2.5
variance = mean((z-mean)²) = mean([2.25, 0.25, 0.25, 2.25]) = 1.25
std = √1.25 ≈ 1.1180
normed ≈ [(1-2.5)/1.118, (2-2.5)/1.118, (3-2.5)/1.118, (4-2.5)/1.118]
       ≈ [-1.342, -0.447, 0.447, 1.342]
```
Check the defining property directly: `mean(normed) = 0` (the four
values are symmetric around zero by construction), and
`std(normed) ≈ 1` (verify: `mean(normed²) = (1.342² + 0.447² + 0.447² +
1.342²)/4 = (1.801+0.200+0.200+1.801)/4 = 1.0005 ≈ 1`). This is exactly
what `test_ddpg_quadcopter_rca_engine.py` checks — per-sample mean ≈ 0,
std ≈ 1 — on real 18-dimensional layer output rather than this toy
vector, but the arithmetic is identical in kind.

---

## What This Does and Doesn't Establish

Confirms, by hand: the reward formula, the physics integration, the
termination boundaries, the Geburah RPM ceiling, and LayerNorm's
defining property all match their stated formulas exactly.

CORRECTION (dated, see `LIBER_0.md`): this section previously said the
`step()` method's gradient update only touched `critic_out.W`, and that
multi-layer backpropagation would require an autograd engine or a
PyTorch backend. Both halves were true when written and are false now:
real backprop through every layer of both the actor and critic networks
is implemented by hand in pure NumPy (`LayerNormDense.forward()`/
`backward()`), including a genuine deterministic policy gradient for the
actor. A second, previously undiscovered bug was fixed alongside it:
LayerNorm over the critic's 1-unit output layer is mathematically
degenerate (always exactly 0 regardless of input or weights), which is
part of why `critic_out.W` updating alone was never sufficient. This
does not establish that the agent learns an *effective* takeoff
policy in the sense of converging to a good flight controller within a
small number of episodes — that would require actual comparative
training-outcome measurement, which remains out of scope here, same as
for `sephirotic_reward_engine.py`. What's now established is narrower
but real: the gradient genuinely flows through every parameter of both
networks, and training measurably improves the critic's own Q-estimate
of the actor's actions (see `test_ddpg_quadcopter_rca_engine.py`'s
finite-difference and learning-progress checks) — which it previously,
provably, did not.

FURTHER UPDATE (dated, see `LIBER_0.md`): target actor/critic networks
were added after the correction above — independent, soft-updated
copies of both networks (`self.tau`, defined from the start but unused
until now) used for the Bellman bootstrap in `step()` instead of the
live networks. This is canonical DDPG's actual stabilization mechanism,
not an approximation of it. Verified by corrupting the target critic
directly (leaving the live critic and actor untouched) and confirming
`step()`'s own returned loss reacts to it — proof that the bootstrap
inside `step()` itself reads the target network, not just a standalone
reconstruction of the formula.

FURTHER UPDATE 2 (dated, see `LIBER_0.md`): the "does not establish an
*effective* takeoff policy" gap named above is now partially closed —
see `docs/ddpg_training_convergence_report.md`. A pre-registered, 8-seed
study measured real training reward over 200 episodes per seed: all 8
seeds showed higher mean reward late in training than early, a pattern
unlikely by chance (binomial sign-test p=0.0039). This is real evidence
the fixed training loop learns something, not proof of a strong flight
controller — the improvement is modest (roughly 1–2% over an
already-high baseline, given the reward function's generous per-step
target bonus), and target-reaching rate or flight stability remain
unmeasured, stronger claims. Reported with its actual numbers rather
than summarized as "it works now."

---

## Provenance

Extends the hand-verification series
(`attractor_engine_kabbalistic_hand_verification.md`,
`sephirotic_reward_engine_kabbalistic_hand_verification.md`,
`rca_sandbox_gamma_kabbalistic_hand_verification.md`,
`correspondence_ledger_kabbalistic_hand_verification.md`) to the engine
whose own section comments were the first to name Malkuth, Chesed,
Tiphereth, Binah, and Geburah as literal architectural layers, not an
added lens.
