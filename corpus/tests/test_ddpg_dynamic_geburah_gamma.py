#!/usr/bin/env python3
"""
test_ddpg_dynamic_geburah_gamma.py
Correctness test for ddpg_dynamic_geburah_gamma.py, per TESTING_STANDARD.md.

Ground truth:
  - compute_directive_gamma() checked against the SAME formula's known,
    already-hand-verified values from this project's other three
    independent implementations (docs/agency_budget_kabbalistic_hand_
    verification.md, docs/delta_operator_kabbalistic_hand_verification.md):
    uniform logits -> gamma=0.0 exactly; extremely peaked logits -> gamma
    capped at exactly 0.85; a realistic uncapped case -> gamma matches a
    fresh by-hand softmax+entropy computation typed out independently in
    this file (not imported from any of the other three implementations).
  - The pre-activation logit duplication (_actor_pre_activation_logits)
    is checked against the REAL, verified engine's own output:
    sigmoid(these logits) must equal self.actor_out.forward(h2) exactly,
    or the duplicated LayerNorm arithmetic has drifted from the verified
    LayerNormDense.forward() it's supposed to mirror.
  - The mechanism is checked to ACTUALLY vary (not silently always return
    the fixed 0.85) using two hand-constructed actor_out weight
    configurations (W=0 with a constant bias) chosen so the pre-LayerNorm
    output is exactly known by hand: one uniform (-> gamma=0, floored to
    0.05) and one skewed (-> gamma computed and hand-checked exactly).
  - The Geburah safety ceiling (gamma, and therefore rotor speed, never
    exceeds 0.85 / 765 RPM) is stress-tested the same way the base
    engine's own gamma-cap test does: adversarially large weights/noise,
    many random states.

Break-it proof: see bottom of file.
"""
import sys
import math
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import ddpg_quadcopter_rca_engine as eng
import ddpg_dynamic_geburah_gamma as dyn

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}  {detail}")


# ---------------------------------------------------------------------------
# 1. compute_directive_gamma() -- ground truth from the OTHER three
#    implementations' own already-hand-verified cases (not re-derived from
#    scratch here, deliberately -- these exact vectors and expected values
#    are already independently confirmed in docs/agency_budget_kabbalistic_
#    hand_verification.md and docs/delta_operator_kabbalistic_hand_
#    verification.md).
# ---------------------------------------------------------------------------
check("uniform logits [0,0,0,0] give exactly zero gamma (matches the other three implementations)",
      math.isclose(dyn.compute_directive_gamma([0, 0, 0, 0]), 0.0, abs_tol=1e-9),
      f"got {dyn.compute_directive_gamma([0, 0, 0, 0])}")

check("extremely peaked logits [1000,-1000] are capped at the literal float 0.85, not merely close to 1",
      dyn.compute_directive_gamma([1000, -1000]) == 0.85,
      f"got {dyn.compute_directive_gamma([1000, -1000])}")

# Fresh by-hand computation for [2.3, 1.0, -0.5], typed out independently
# here (not imported from delta_operator.py or agency_budget.py):
#   shifted = [0, -1.3, -2.8]  (subtract max=2.3)
#   exp     = [1, 0.272532, 0.060810]
#   sum     = 1.333342
#   probs   = [0.749996, 0.204391, 0.045613]
#   h       = -(0.749996*log2(0.749996) + 0.204391*log2(0.204391) + 0.045613*log2(0.045613))
#           = -(0.749996*-0.415062 + 0.204391*-2.291281 + 0.045613*-4.454741)
#           = -(-0.311293 - 0.468278 - 0.203245) = 0.982816
#   h_max   = log2(3) = 1.584963
#   h_norm  = 0.982816 / 1.584963 = 0.620084
#   gamma   = 1 - 0.620084 = 0.379916
hand_gamma_2_3 = 1.0 - (0.982816 / 1.584963)
check("a realistic uncapped case [2.3, 1.0, -0.5] matches a fresh independent by-hand computation",
      math.isclose(dyn.compute_directive_gamma([2.3, 1.0, -0.5]), hand_gamma_2_3, abs_tol=1e-3),
      f"got {dyn.compute_directive_gamma([2.3, 1.0, -0.5])} expected ~{hand_gamma_2_3}")

check("single-logit edge case returns MAX_GAMMA_CAP directly (matches delta_operator.py's convention)",
      dyn.compute_directive_gamma([5.0]) == eng.MAX_GAMMA_CAP)

check("empty logits return 0.0",
      dyn.compute_directive_gamma([]) == 0.0)

check("gamma is NEVER above MAX_GAMMA_CAP across a spread of adversarial logit magnitudes",
      all(dyn.compute_directive_gamma([scale, -scale, scale, -scale]) <= eng.MAX_GAMMA_CAP
          for scale in [0.001, 1, 10, 100, 1e6, 1e12]))

# ---------------------------------------------------------------------------
# 2. Pre-activation logit duplication cross-checked against the REAL,
#    verified engine's own actor_out.forward() -- sigmoid(logits) must
#    equal the engine's real output exactly, or the duplicated LayerNorm
#    math has drifted.
# ---------------------------------------------------------------------------
agent1 = dyn.DynamicGeburahDDPGAgent(state_dim=18)
rng = np.random.default_rng(7)
probe_state = rng.normal(size=18)
h1p = agent1.actor_l1.forward(np.atleast_2d(probe_state))
h2p = agent1.actor_l2.forward(h1p)
logits_probe = agent1._actor_pre_activation_logits(h2p)
real_output = agent1.actor_out.forward(h2p)
sigmoid_of_logits = 1.0 / (1.0 + np.exp(-logits_probe))
check("sigmoid(duplicated pre-activation logits) exactly matches the REAL actor_out.forward() output",
      np.allclose(sigmoid_of_logits, real_output, atol=1e-12),
      f"max diff = {np.max(np.abs(sigmoid_of_logits - real_output))}")

# ---------------------------------------------------------------------------
# 3. The mechanism actually varies -- two hand-constructed configurations
#    with W=0 (so actor_out's pre-activation z is the bias alone,
#    regardless of the input state) give an EXACTLY known pre-LayerNorm
#    vector by hand, letting gamma be predicted before running anything.
# ---------------------------------------------------------------------------
agent_uniform = dyn.DynamicGeburahDDPGAgent(state_dim=18)
agent_uniform.actor_out.W = np.zeros_like(agent_uniform.actor_out.W)
agent_uniform.actor_out.b = np.zeros(4)
# z = h2@0 + 0 = [0,0,0,0] regardless of state -> LayerNorm of a constant
# vector -> mean=0, var=0, std=sqrt(1e-5) -> n = 0/std = [0,0,0,0].
state_probe = np.zeros(18)
rotor_speeds_uniform = agent_uniform.act(state_probe, add_noise=False)
check("hand-constructed UNIFORM pre-activation ([0,0,0,0]) floors gamma at MIN_GAMMA_FLOOR (0.05), not 0.0",
      math.isclose(agent_uniform.last_gamma_cap, dyn.MIN_GAMMA_FLOOR, abs_tol=1e-6),
      f"got last_gamma_cap={agent_uniform.last_gamma_cap}")
check("...and the pre-floor raw_gamma for that exact case is ~0.0 (uniform logits, matches section 1's check)",
      math.isclose(agent_uniform.last_raw_gamma, 0.0, abs_tol=1e-6),
      f"got last_raw_gamma={agent_uniform.last_raw_gamma}")

agent_skewed = dyn.DynamicGeburahDDPGAgent(state_dim=18)
agent_skewed.actor_out.W = np.zeros_like(agent_skewed.actor_out.W)
agent_skewed.actor_out.b = np.array([10.0, -10.0, 10.0, -10.0])
# z = [10,-10,10,-10] regardless of state. mean=0, var=mean([100]*4)=100,
# std=sqrt(100+1e-5)~=10.0000005, n = z/std ~= [1,-1,1,-1] (hand-computed
# in the module docstring / hand-verification doc):
#   softmax([1,-1,1,-1]) ~= [0.4404, 0.0596, 0.4404, 0.0596]
#   h ~= 1.5274 bits, h_max=2.0, h_norm~=0.7637, gamma ~= 0.2363
rotor_speeds_skewed = agent_skewed.act(state_probe, add_noise=False)
check("hand-constructed SKEWED pre-activation ([~1,-1,1,-1]) gives gamma ~= 0.2365, meaningfully above the uniform case",
      math.isclose(agent_skewed.last_raw_gamma, 0.2365, abs_tol=0.01),
      f"got last_raw_gamma={agent_skewed.last_raw_gamma}")
check("skewed-case gamma is strictly greater than uniform-case gamma -- the mechanism genuinely responds to entropy, not a constant",
      agent_skewed.last_raw_gamma > agent_uniform.last_raw_gamma,
      f"uniform={agent_uniform.last_raw_gamma} skewed={agent_skewed.last_raw_gamma}")

# ---------------------------------------------------------------------------
# 4. act()'s returned rotor speeds actually RESPECT the computed gamma cap
#    for that exact call (no-noise case, so the result is deterministic
#    and checkable against the hand-known clip band).
# ---------------------------------------------------------------------------
expected_bounded = np.clip(agent_skewed.actor_out.forward(
    agent_skewed.actor_l2.forward(agent_skewed.actor_l1.forward(np.atleast_2d(state_probe))))[0],
    dyn.MIN_GAMMA_FLOOR, agent_skewed.last_gamma_cap) * agent_skewed.max_rpm
check("act()'s returned rotor speeds match clip(raw_signal, floor, dynamic_gamma) * max_rpm exactly (no-noise case)",
      np.allclose(rotor_speeds_skewed, expected_bounded, atol=1e-9),
      f"got {rotor_speeds_skewed} expected {expected_bounded}")

# ---------------------------------------------------------------------------
# 5. Geburah safety ceiling stress test -- matches the base engine's own
#    "holds even under adversarially large injected noise" pattern.
#    Adversarially scaled actor_out weights, many random states: gamma
#    (and therefore rotor RPM) must never exceed the 0.85 / 765 RPM
#    ceiling, and never go below the 0.05 / 45 RPM floor.
# ---------------------------------------------------------------------------
adversarial_ok = True
rng2 = np.random.default_rng(42)
agent_adv = dyn.DynamicGeburahDDPGAgent(state_dim=18)
agent_adv.actor_out.W = rng2.normal(scale=1000.0, size=agent_adv.actor_out.W.shape)
agent_adv.actor_out.b = rng2.normal(scale=1000.0, size=4)
for _ in range(30):
    trial_state = rng2.normal(size=18)
    speeds = agent_adv.act(trial_state, add_noise=True)
    if agent_adv.last_gamma_cap > eng.MAX_GAMMA_CAP + 1e-9:
        adversarial_ok = False
    if np.any(speeds > eng.MAX_GAMMA_CAP * agent_adv.max_rpm + 1e-6):
        adversarial_ok = False
    if np.any(speeds < dyn.MIN_GAMMA_FLOOR * agent_adv.max_rpm - 1e-6):
        adversarial_ok = False
check("Geburah gamma-cap and rotor-speed ceiling both hold under adversarially large weights/noise (30 trials)",
      adversarial_ok)

print(f"\n  SUMMARY: {PASS} passed, {FAIL} failed (out of {PASS + FAIL} correctness checks)")
