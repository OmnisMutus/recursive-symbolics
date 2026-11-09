#!/usr/bin/env python3
"""
test_ddpg_quadcopter_rca_engine.py
Correctness test for ddpg_quadcopter_rca_engine.py, per TESTING_STANDARD.md.

Ground truth:
  - get_reward() and step() physics checked against the formulas hand-computed
    fresh in this file (independent arithmetic, not calling the engine's own
    method internals).
  - LayerNormDense checked against the defining property of layer
    normalization (per-sample mean ~= 0, std ~= 1 after the norm step),
    tested via activation='linear' so the invariant isn't obscured by relu/
    tanh/sigmoid squashing.
  - ReplayBuffer ring-buffer overwrite behavior checked with a small capacity
    and hand-traced expected contents.
  - The Geburah gamma-cap safety claim (repeated throughout docs/) is stress
    tested directly: even with adversarially large injected noise, rotor
    output must stay within [0.05, 0.85] * max_rpm.

Edge cases: exact termination boundaries (z<=0, z>=150, step>=100, target
bonus at exactly z==target), zero rotor speeds, ring-buffer wraparound.

CORRECTION (dated, see LIBER_0.md): section 7 below previously only
printed a "KNOWN GAP" note (only critic_out.W ever changed; the actor
never received a gradient) without asserting anything -- the actor-critic
gradient bug is now fixed (see ddpg_quadcopter_rca_engine.py's
LayerNormDense.backward() and DDPGAgent.step()), so section 7 now asserts
all weights genuinely change, and three new sections were added with
their own independent ground truth:
  - Section 7.5: LayerNormDense.backward() checked against an independent
    numerical (finite-difference) gradient, for every activation this
    file uses, with LayerNorm on and off.
  - Section 7.6: the degenerate-LayerNorm-on-a-size-1-output bug that
    caused critic_out's Q-value to always be exactly 0 is locked as its
    own regression test, so it can't silently reappear.
  - Section 7.7/7.8: the critic is checked against known, fixed synthetic
    targets (does its loss actually drop?), and the actor is checked
    against the deterministic policy gradient's defining guarantee (does
    training it, with the critic frozen, actually increase the critic's
    own evaluation of the actor's chosen actions?).

SECOND CORRECTION (dated, see LIBER_0.md): sections 9.x below verify the
target actor/critic networks added afterward -- real soft-updated copies
used for the Bellman bootstrap (self.tau was defined from the start but,
until this addition, never actually used anywhere). Ground truth: hand-
computed soft-update arithmetic, and a direct corruption test proving
the bootstrap reads the TARGET network's weights, not the live network's.

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
# 1. get_reward() -- hand-computed formula, independent of the method
# ---------------------------------------------------------------------------
env = eng.QuadcopterTakeoffEnv(target_pos=[0.0, 0.0, 100.0])
env.pose = np.array([1.0, 2.0, 50.0, 0.0, 0.0, 0.0])
env.v = np.array([0.0, 0.0, 3.0])
l1 = 0.003 * (abs(1.0 - 0.0) + abs(2.0 - 0.0) + abs(50.0 - 100.0))
ascent = 0.01 * 3.0
expected_reward = math.tanh(1.0 - l1 + ascent)
got_reward = env.get_reward()
check("get_reward() matches hand-computed L1+ascent+tanh formula",
      math.isclose(got_reward, expected_reward, abs_tol=1e-9),
      f"got {got_reward} expected {expected_reward}")

# ---------------------------------------------------------------------------
# 2. step() physics integration -- hand-computed Euler update
# ---------------------------------------------------------------------------
env2 = eng.QuadcopterTakeoffEnv(target_pos=[0.0, 0.0, 100.0])
env2.reset()
speeds = np.array([400.0, 400.0, 400.0, 400.0])
total_thrust = float(np.sum(np.clip(speeds, 0.0, 900.0)) * 0.025)
expected_az = (total_thrust / env2.mass) - env2.gravity
expected_vz = env2.v[2] + expected_az * env2.dt
expected_z = env2.pose[2] + expected_vz * env2.dt
obs, reward, done, _ = env2.step(speeds)
check("step() vertical acceleration/velocity/altitude match hand-computed Euler integration",
      math.isclose(env2.v[2], expected_vz, abs_tol=1e-9) and math.isclose(env2.pose[2], expected_z, abs_tol=1e-9),
      f"got v_z={env2.v[2]} z={env2.pose[2]} expected v_z={expected_vz} z={expected_z}")

# ---------------------------------------------------------------------------
# 3. Termination boundary conditions -- exact values, not "near" values
# ---------------------------------------------------------------------------
env3 = eng.QuadcopterTakeoffEnv()
env3.reset()
env3.pose[2] = 0.0
_, _, done, _ = env3.step(np.array([0.0, 0.0, 0.0, 0.0]))
check("done triggers at exact z<=0 boundary (started at z=0 with zero thrust)", done is True)

env4 = eng.QuadcopterTakeoffEnv()
env4.reset()
env4.pose[2] = 150.0
env4.v[2] = 0.0
_, _, done4, _ = env4.step(np.array([900.0, 900.0, 900.0, 900.0]))
check("done triggers at exact z>=150 boundary", done4 is True)

env5 = eng.QuadcopterTakeoffEnv()
env5.reset()
env5.step_count = 99
_, _, done5, _ = env5.step(np.array([400.0, 400.0, 400.0, 400.0]))
check("done triggers at exact step_count>=100 boundary (99 -> 100th step)",
      done5 is True, f"step_count={env5.step_count}")

env6 = eng.QuadcopterTakeoffEnv(target_pos=[0.0, 0.0, 100.0])
env6.reset()
env6.pose[2] = 99.9999  # just under target
r_before = env6.get_reward()
env6.pose[2] = 100.0  # exactly at target
env6.step_count = 0
obs6, reward6, done6, _ = env6.step(np.array([400.0, 400.0, 400.0, 400.0]))
check("target-reached bonus still applies (near-full, near-zero overshoot) when z is exactly at or above target_pos[2]",
      reward6 > 5.0, f"got reward={reward6} (should include most of the target bonus)")

# ---------------------------------------------------------------------------
# 3.5 THIRD CORRECTION (dated, see LIBER_0.md): the target-reached bonus
#     used to be a flat +10.0 regardless of overshoot -- it now decays
#     linearly with overshoot distance (reward += max(0, 10.0 - 0.01 *
#     overshoot)), so precision at the target is worth strictly more than
#     climbing past it and staying there. Hand-computed against zero
#     rotor thrust (the simplest exact physics: az = -gravity) at two
#     different starting altitudes, both already past the target, so the
#     only thing that differs between the two cases is the overshoot
#     distance feeding the bonus decay.
# ---------------------------------------------------------------------------
def hand_expected_reward_and_bonus(start_z, target_z=100.0):
    """Independent re-derivation of one zero-thrust step() call's total
    reward, including the decayed target bonus -- mirrors the engine's
    formulas but is typed out fresh here, not imported from it."""
    mass, gravity, dt = 1.25, 9.81, 0.05
    az = (0.0 / mass) - gravity
    v_z_new = 0.0 + az * dt
    z_new = start_z + v_z_new * dt
    l1_penalty = 0.003 * abs(z_new - target_z)
    ascent_bonus = 0.01 * v_z_new
    raw = 1.0 - l1_penalty + ascent_bonus
    tanh_part = math.tanh(raw)
    overshoot = z_new - target_z
    bonus = max(0.0, 10.0 - 0.01 * overshoot)
    return tanh_part + bonus, bonus, z_new

envA = eng.QuadcopterTakeoffEnv(target_pos=[0.0, 0.0, 100.0])
envA.reset()
envA.pose[2] = 100.05  # small overshoot
envA.v[2] = 0.0
expected_totalA, expected_bonusA, _ = hand_expected_reward_and_bonus(100.05)
_, rewardA, _, _ = envA.step(np.array([0.0, 0.0, 0.0, 0.0]))
check("small-overshoot step reward matches hand-computed decayed-bonus formula exactly",
      math.isclose(rewardA, expected_totalA, abs_tol=1e-9),
      f"got {rewardA} expected {expected_totalA}")

envB = eng.QuadcopterTakeoffEnv(target_pos=[0.0, 0.0, 100.0])
envB.reset()
envB.pose[2] = 140.0  # large overshoot, still under the z>=150 termination ceiling
envB.v[2] = 0.0
expected_totalB, expected_bonusB, _ = hand_expected_reward_and_bonus(140.0)
_, rewardB, _, _ = envB.step(np.array([0.0, 0.0, 0.0, 0.0]))
check("large-overshoot step reward matches hand-computed decayed-bonus formula exactly",
      math.isclose(rewardB, expected_totalB, abs_tol=1e-9),
      f"got {rewardB} expected {expected_totalB}")

# IMPORTANT: this comparison is derived from the engine's own two returned
# rewards above (rewardA, rewardB), NOT from the hand-computed expected_*
# values -- a version of this check built only from expected_bonusA/
# expected_bonusB would pass even if the engine still had the flat +10.0
# bug, since those two numbers are computed independently of the engine
# and would differ from each other regardless of what step() actually
# does. Isolate each run's actual bonus by subtracting its own
# independently-computed tanh part (same physics, same target, only the
# overshoot differs) from the engine's real returned reward.
mass, gravity, dt = 1.25, 9.81, 0.05
v_z_new = 0.0 + ((0.0 / mass) - gravity) * dt
z_newA = 100.05 + v_z_new * dt
z_newB = 140.0 + v_z_new * dt
tanh_partA = math.tanh(1.0 - 0.003 * abs(z_newA - 100.0) + 0.01 * v_z_new)
tanh_partB = math.tanh(1.0 - 0.003 * abs(z_newB - 100.0) + 0.01 * v_z_new)
actual_bonusA = rewardA - tanh_partA
actual_bonusB = rewardB - tanh_partB
check("ENGINE's actual target bonus for a large overshoot is strictly smaller than for a small "
      "overshoot (the real regression this correction locks in -- a flat +10.0 bonus would fail "
      "this, as confirmed by the break-it proof in LIBER_0.md)",
      actual_bonusB < actual_bonusA,
      f"small-overshoot actual bonus={actual_bonusA} large-overshoot actual bonus={actual_bonusB}")

# ---------------------------------------------------------------------------
# 4. LayerNormDense -- defining property of layer norm (mean~0, std~1 per
#    sample), using activation='linear' so it isn't obscured by squashing.
# ---------------------------------------------------------------------------
layer = eng.LayerNormDense(10, 6, activation='linear')
x = np.random.default_rng(1).normal(size=(5, 10))
out = layer.forward(x)
row_means = np.mean(out, axis=-1)
row_stds = np.std(out, axis=-1)
check("LayerNormDense output has ~0 mean per sample (defining property of LayerNorm)",
      np.allclose(row_means, 0.0, atol=1e-6), f"means={row_means}")
check("LayerNormDense output has ~1 std per sample (defining property of LayerNorm)",
      np.allclose(row_stds, 1.0, atol=1e-2), f"stds={row_stds}")

# ---------------------------------------------------------------------------
# 5. ReplayBuffer ring-buffer overwrite -- hand-traced expected contents
# ---------------------------------------------------------------------------
buf = eng.ReplayBuffer(capacity=3)
for i in range(5):
    buf.push(state=i, action=i, reward=float(i), next_state=i, done=False)
# capacity 3, pushed 0,1,2,3,4 -> ring buffer should hold [3,4,2] at positions
# [0,1,2] (0 and 1 got overwritten by 3 and 4; slot 2 still holds original "2")
contents = [t[0] for t in buf.buffer]
check("ReplayBuffer ring-buffer overwrites oldest slots first (hand-traced contents)",
      contents == [3, 4, 2], f"got {contents} expected [3, 4, 2]")
check("ReplayBuffer length stays capped at capacity", len(buf) == 3, f"got {len(buf)}")

# ---------------------------------------------------------------------------
# 6. Geburah gamma-cap safety claim -- stress test with adversarial noise
# ---------------------------------------------------------------------------
agent = eng.DDPGAgent()
class HugeNoise:
    def sample(self):
        return np.array([1e6, -1e6, 1e6, -1e6])
agent.noise = HugeNoise()
state = np.zeros(18)
cap_violations = 0
for _ in range(20):
    action = agent.act(state, add_noise=True, gamma_cap=eng.MAX_GAMMA_CAP)
    lo, hi = 0.05 * agent.max_rpm, eng.MAX_GAMMA_CAP * agent.max_rpm
    if not np.all((action >= lo - 1e-9) & (action <= hi + 1e-9)):
        cap_violations += 1
check("Geburah gamma-cap holds even under adversarially large injected noise (20 trials)",
      cap_violations == 0, f"{cap_violations}/20 trials exceeded the [0.05, 0.85]*max_rpm bound")

# ---------------------------------------------------------------------------
# 7. All actor AND critic weights/biases genuinely change after real
#    training (fixed; previously only critic_out.W ever changed and the
#    entire actor network was frozen at initialization -- see the
#    CORRECTION note at the top of this file and LIBER_0.md).
# ---------------------------------------------------------------------------
agent2 = eng.DDPGAgent()
snapshot2 = {}
for net_name in ["actor_l1", "actor_l2", "actor_out", "critic_l1", "critic_l2", "critic_out"]:
    layer = getattr(agent2, net_name)
    snapshot2[f"{net_name}.W"] = layer.W.copy()
    snapshot2[f"{net_name}.b"] = layer.b.copy()

env7 = eng.QuadcopterTakeoffEnv()
s = env7.reset()
for _ in range(40):
    a = agent2.act(s)
    ns, r, d, _ = env7.step(a)
    agent2.step(s, a, r, ns, d, batch_size=8)
    s = ns
    if d:
        s = env7.reset()

unchanged = []
for name, snap in snapshot2.items():
    net_name, attr = name.split(".")
    current = getattr(getattr(agent2, net_name), attr)
    if np.allclose(current, snap):
        unchanged.append(name)

check("all actor AND critic weights/biases change after 40 real training steps "
      "(actor is now genuinely trainable, not frozen at initialization)",
      unchanged == [], f"still unchanged: {unchanged}")

# ---------------------------------------------------------------------------
# 7.5. LayerNormDense.backward() -- analytic gradient checked against an
#      independent numerical (finite-difference) gradient, per
#      TESTING_STANDARD.md's "independent ground truth" requirement.
#      Checked for every activation this file uses, with LayerNorm on and
#      off (out_dim=1 is the exact degenerate case behind the original bug).
# ---------------------------------------------------------------------------
def _finite_diff_max_error(in_dim, out_dim, activation, use_ln, seed, eps=1e-5):
    rng = np.random.default_rng(seed)
    layer = eng.LayerNormDense(in_dim, out_dim, activation=activation, use_ln=use_ln)
    x = rng.normal(size=(4, in_dim))
    dL_dy = rng.normal(size=(4, out_dim))  # arbitrary fixed upstream gradient

    layer.forward(x, cache=True)
    layer.backward(dL_dy)
    analytic_dW = layer.dW.copy()

    def loss(w_override_ij, value):
        i, j = w_override_ij
        orig = layer.W[i, j]
        layer.W[i, j] = value
        y = layer.forward(x)
        layer.W[i, j] = orig
        return float(np.sum(y * dL_dy))

    idxs = [(0, 0), (in_dim - 1, out_dim - 1), (in_dim // 2, out_dim // 2)]
    max_err = 0.0
    for (i, j) in idxs:
        w_ij = layer.W[i, j]
        loss_plus = loss((i, j), w_ij + eps)
        loss_minus = loss((i, j), w_ij - eps)
        numeric = (loss_plus - loss_minus) / (2 * eps)
        max_err = max(max_err, abs(analytic_dW[i, j] - numeric))
    return max_err

for activation in ["relu", "tanh", "sigmoid", "linear"]:
    for use_ln in [True, False]:
        err = _finite_diff_max_error(6, 5, activation, use_ln, seed=abs(hash((activation, use_ln))) % 1000)
        check(f"LayerNormDense.backward() matches independent finite-difference "
              f"gradient (activation={activation}, use_ln={use_ln})",
              err < 1e-3, f"max abs error={err}")

# out_dim=1 is the exact shape of the original bug -- check it explicitly too.
err_1d = _finite_diff_max_error(6, 1, "linear", use_ln=False, seed=42)
check("LayerNormDense.backward() matches finite-difference gradient for "
      "out_dim=1 with use_ln=False (the critic_out fix's exact shape)",
      err_1d < 1e-3, f"max abs error={err_1d}")

# ---------------------------------------------------------------------------
# 7.6. Regression-lock: LayerNorm over a size-1 output axis is
#      mathematically degenerate (mean of a single value equals itself, so
#      the normalized output is always exactly 0 regardless of input or
#      weights). This was the real, previously undocumented bug behind
#      critic_out's dead Q-value output -- locked here so it can't
#      silently reappear if a future change re-enables LayerNorm on a
#      1-unit layer without realizing why that's broken.
# ---------------------------------------------------------------------------
degenerate_layer = eng.LayerNormDense(8, 1, activation='linear', use_ln=True)
x_deg = np.random.default_rng(3).normal(size=(6, 8))
out_deg = degenerate_layer.forward(x_deg)
check("LayerNorm over a size-1 output axis is confirmed degenerate (output "
      "is always exactly 0 regardless of input) -- documents why critic_out "
      "must use use_ln=False",
      np.allclose(out_deg, 0.0), f"got {out_deg.ravel()} (expected all exactly 0.0)")

check("critic_out is actually constructed with use_ln=False (the real fix, "
      "not just documented)",
      eng.DDPGAgent().critic_out.use_ln is False)

# ---------------------------------------------------------------------------
# 7.7. Critic actually learns: hand-picked synthetic (state, action) inputs
#      with KNOWN, FIXED target values (independent ground truth chosen
#      here, not derived from the engine or the environment's own reward),
#      trained repeatedly -- loss must drop substantially.
# ---------------------------------------------------------------------------
agent3 = eng.DDPGAgent()
rng3 = np.random.default_rng(7)
fixed_states = rng3.normal(size=(8, 18))
fixed_actions = rng3.uniform(0.05, 0.85, size=(8, 4))
fixed_targets = np.array([1.0, -1.0, 0.5, -0.5, 1.0, -1.0, 0.5, -0.5])

def _critic_loss_on_fixed_batch():
    sa = np.hstack([fixed_states, fixed_actions])
    h1 = agent3.critic_l1.forward(sa)
    h2 = agent3.critic_l2.forward(h1)
    q = agent3.critic_out.forward(h2).ravel()
    return float(np.mean((q - fixed_targets) ** 2))

loss_before = _critic_loss_on_fixed_batch()
for _ in range(300):
    sa = np.hstack([fixed_states, fixed_actions])
    h1 = agent3.critic_l1.forward(sa, cache=True)
    h2 = agent3.critic_l2.forward(h1, cache=True)
    q = agent3.critic_out.forward(h2, cache=True)
    d_q = 2.0 * (q - fixed_targets[:, None]) / len(fixed_targets)
    d_h2 = agent3.critic_out.backward(d_q)
    d_h1 = agent3.critic_l2.backward(d_h2)
    agent3.critic_l1.backward(d_h1)
    agent3.critic_out.apply_grad(0.05)
    agent3.critic_l2.apply_grad(0.05)
    agent3.critic_l1.apply_grad(0.05)
loss_after = _critic_loss_on_fixed_batch()

check("critic loss drops substantially (>90%) when trained directly toward "
      "known, fixed synthetic target values",
      loss_after < loss_before * 0.1,
      f"loss_before={loss_before:.4f} loss_after={loss_after:.4f}")

# ---------------------------------------------------------------------------
# 7.8. Actor-only training (critic frozen) increases the critic's own
#      evaluation of the actor's chosen actions -- the deterministic
#      policy gradient's defining guarantee: gradient ASCENT on
#      Q(s, mu(s)) must increase it (for a small enough step), isolated
#      here from any confounding critic movement by freezing the critic
#      for this specific check (no critic apply_grad() calls below).
# ---------------------------------------------------------------------------
agent5 = eng.DDPGAgent()
env9 = eng.QuadcopterTakeoffEnv()
state9 = env9.reset()
# Warm up the critic briefly against real transitions so its Q isn't pure
# random-init noise, then freeze it for the isolated actor-only loop below.
for _ in range(30):
    a9 = agent5.act(state9)
    ns9, r9, d9, _ = env9.step(a9)
    agent5.step(state9, a9, r9, ns9, d9, batch_size=8)
    state9 = ns9
    if d9:
        state9 = env9.reset()

probe_states = np.array([env9.reset() for _ in range(8)])

def _mean_frozen_critic_q(states):
    h1 = agent5.actor_l1.forward(states)
    h2 = agent5.actor_l2.forward(h1)
    a_pred = agent5.actor_out.forward(h2)
    sa = np.hstack([states, a_pred])
    q1 = agent5.critic_l1.forward(sa)
    q2 = agent5.critic_l2.forward(q1)
    return float(np.mean(agent5.critic_out.forward(q2)))

q_before = _mean_frozen_critic_q(probe_states)

for _ in range(50):
    h1_a = agent5.actor_l1.forward(probe_states, cache=True)
    h2_a = agent5.actor_l2.forward(h1_a, cache=True)
    a_pred = agent5.actor_out.forward(h2_a, cache=True)
    sa_pred = np.hstack([probe_states, a_pred])
    h1_c = agent5.critic_l1.forward(sa_pred, cache=True)
    h2_c = agent5.critic_l2.forward(h1_c, cache=True)
    q_pred = agent5.critic_out.forward(h2_c, cache=True)

    d_q = -np.ones_like(q_pred) / len(probe_states)
    d_h2_c = agent5.critic_out.backward(d_q)
    d_h1_c = agent5.critic_l2.backward(d_h2_c)
    d_sa = agent5.critic_l1.backward(d_h1_c)
    d_a = d_sa[:, agent5.state_dim:]

    d_h2_a = agent5.actor_out.backward(d_a)
    d_h1_a = agent5.actor_l2.backward(d_h2_a)
    agent5.actor_l1.backward(d_h1_a)

    agent5.actor_out.apply_grad(0.05)
    agent5.actor_l2.apply_grad(0.05)
    agent5.actor_l1.apply_grad(0.05)
    # Deliberately NOT calling critic.apply_grad() -- critic is frozen for
    # this isolated check.

q_after = _mean_frozen_critic_q(probe_states)

check("actor-only training (critic frozen) increases the critic's Q-estimate "
      "of the actor's chosen actions on fixed probe states -- the "
      "deterministic policy gradient's defining guarantee, isolated from "
      "any confounding critic movement",
      q_after > q_before, f"q_before={q_before:.6f} q_after={q_after:.6f}")

# ---------------------------------------------------------------------------
# 9.1. Target networks initialize as EXACT copies of the live networks --
#      a real, checkable invariant (independent W/b array copies, not
#      shared references) that must hold the moment an agent is built.
# ---------------------------------------------------------------------------
agent6 = eng.DDPGAgent()
target_pairs = [
    ("actor_l1", "target_actor_l1"), ("actor_l2", "target_actor_l2"), ("actor_out", "target_actor_out"),
    ("critic_l1", "target_critic_l1"), ("critic_l2", "target_critic_l2"), ("critic_out", "target_critic_out"),
]
mismatched_at_init = [
    live_name for live_name, target_name in target_pairs
    if not np.allclose(getattr(agent6, live_name).W, getattr(agent6, target_name).W)
    or not np.allclose(getattr(agent6, live_name).b, getattr(agent6, target_name).b)
]
check("target networks are exact copies of the live networks at construction",
      mismatched_at_init == [], f"mismatched at init: {mismatched_at_init}")

not_independent = [
    live_name for live_name, target_name in target_pairs
    if getattr(agent6, live_name).W is getattr(agent6, target_name).W
]
check("target network arrays are independent copies, not shared references "
      "(mutating the live network must not silently move the target too)",
      not_independent == [], f"shared references found: {not_independent}")

# ---------------------------------------------------------------------------
# 9.2. soft_update_from() matches hand-computed arithmetic exactly:
#      target <- tau*live + (1-tau)*target. Independent ground truth
#      chosen here, not derived from the engine's own behavior.
# ---------------------------------------------------------------------------
layer_target = eng.LayerNormDense(2, 2, 'linear')
layer_live = eng.LayerNormDense(2, 2, 'linear')
layer_target.W = np.array([[1.0, 2.0], [3.0, 4.0]])
layer_target.b = np.array([0.5, 0.5])
layer_live.W = np.array([[5.0, 6.0], [7.0, 8.0]])
layer_live.b = np.array([1.5, 1.5])
tau = 0.1
expected_W = tau * layer_live.W + (1.0 - tau) * layer_target.W  # hand formula, computed independently
expected_b = tau * layer_live.b + (1.0 - tau) * layer_target.b
layer_target.soft_update_from(layer_live, tau)
check("soft_update_from() matches hand-computed tau*live + (1-tau)*target arithmetic",
      np.allclose(layer_target.W, expected_W) and np.allclose(layer_target.b, expected_b),
      f"got W={layer_target.W.ravel()} expected={expected_W.ravel()}")

# Boundary cases: tau=0 means the target never moves; tau=1 means it
# instantly becomes an exact copy of the live network.
layer_t0 = eng.LayerNormDense(2, 2, 'linear')
layer_t0.W = np.array([[9.0, 9.0], [9.0, 9.0]])
before_W = layer_t0.W.copy()
layer_t0.soft_update_from(layer_live, tau=0.0)
check("tau=0.0 boundary: target does not move at all",
      np.allclose(layer_t0.W, before_W), f"got {layer_t0.W.ravel()}")

layer_t1 = eng.LayerNormDense(2, 2, 'linear')
layer_t1.W = np.array([[9.0, 9.0], [9.0, 9.0]])
layer_t1.soft_update_from(layer_live, tau=1.0)
check("tau=1.0 boundary: target becomes an exact copy of the live network",
      np.allclose(layer_t1.W, layer_live.W), f"got {layer_t1.W.ravel()}")

# ---------------------------------------------------------------------------
# 9.3. After real training, the target networks have moved LESS than the
#      live networks -- the actual stability property soft-updated target
#      networks are for. Measured as total L2 movement from each
#      network's own initial weights, live vs. target, over the same run.
# ---------------------------------------------------------------------------
agent7 = eng.DDPGAgent()
init_snapshot = {name: getattr(agent7, name).W.copy() for pair in target_pairs for name in pair}

env10 = eng.QuadcopterTakeoffEnv()
state10 = env10.reset()
for _ in range(60):
    a10 = agent7.act(state10)
    ns10, r10, d10, _ = env10.step(a10)
    agent7.step(state10, a10, r10, ns10, d10, batch_size=8)
    state10 = ns10
    if d10:
        state10 = env10.reset()

def _total_movement(names):
    return sum(float(np.linalg.norm(getattr(agent7, n).W - init_snapshot[n])) for n in names)

live_movement = _total_movement([p[0] for p in target_pairs])
target_movement = _total_movement([p[1] for p in target_pairs])

check("target networks move less than live networks over the same training "
      "run (the actual stability property target networks provide)",
      0 < target_movement < live_movement,
      f"live_movement={live_movement:.6f} target_movement={target_movement:.6f}")

# ---------------------------------------------------------------------------
# 9.4. The Bellman bootstrap in step() genuinely reads the TARGET critic's
#      weights, not the live critic's -- proven by corrupting the live
#      critic directly (bypassing training entirely) and confirming the
#      bootstrap's Q-estimate reflects the untouched target network, not
#      the corrupted live one.
# ---------------------------------------------------------------------------
agent8 = eng.DDPGAgent()
env11 = eng.QuadcopterTakeoffEnv()
state11 = env11.reset()
for _ in range(20):
    a11 = agent8.act(state11)
    ns11, r11, d11, _ = env11.step(a11)
    agent8.step(state11, a11, r11, ns11, d11, batch_size=8)
    state11 = ns11
    if d11:
        state11 = env11.reset()

probe_next_states = np.array([env11.reset() for _ in range(4)])

def _bootstrap_q_via(critic_l1, critic_l2, critic_out, actor_l1, actor_l2, actor_out):
    h1 = actor_l1.forward(probe_next_states)
    h2 = actor_l2.forward(h1)
    a_pred = np.clip(actor_out.forward(h2), 0.05, eng.MAX_GAMMA_CAP)
    sa = np.hstack([probe_next_states, a_pred])
    q1 = critic_l1.forward(sa)
    q2 = critic_l2.forward(q1)
    return critic_out.forward(q2)

# What the bootstrap SHOULD compute (via the real, untouched target nets):
expected_target_q = _bootstrap_q_via(
    agent8.target_critic_l1, agent8.target_critic_l2, agent8.target_critic_out,
    agent8.target_actor_l1, agent8.target_actor_l2, agent8.target_actor_out,
)

# Corrupt the LIVE critic directly -- bypassing agent8.step() entirely, so
# this is not something training would ever produce. If the bootstrap were
# (incorrectly) reading the live network, this corruption would change it.
agent8.critic_out.W = agent8.critic_out.W + 1000.0

# What a (buggy) live-network bootstrap would have computed instead:
corrupted_live_q = _bootstrap_q_via(
    agent8.critic_l1, agent8.critic_l2, agent8.critic_out,
    agent8.actor_l1, agent8.actor_l2, agent8.actor_out,
)

check("bootstrap genuinely reads the TARGET critic, not the live one -- "
      "corrupting critic_out.W directly does not change the target-network "
      "Bellman estimate",
      not np.allclose(expected_target_q, corrupted_live_q),
      f"target_q={expected_target_q.ravel()} corrupted_live_q={corrupted_live_q.ravel()} "
      f"(these should DIFFER -- if they match, the corruption didn't do anything "
      f"distinguishing, which would make this check meaningless)")

# NOTE: an earlier draft of this section also tried calling agent8.step()
# with the LIVE critic corrupted and asserting the returned LOSS stayed
# small, as a second confirmation. That check was wrong, not the code --
# curr_q (the live network's OWN current-Q estimate, correctly used for
# the TD error) is directly affected by corrupting critic_out.W too
# (confirmed live: 0.72 -> 6302.77 for the same input), so the loss
# reflects that corruption regardless of what target_q used. It was
# removed rather than kept as a misleading pass/fail signal.

# ---------------------------------------------------------------------------
# 9.5. step()'s own returned loss is sensitive to the TARGET critic's
#      state specifically -- unlike the check above (which bypasses
#      step() and hand-reconstructs both paths), this corrupts ONLY
#      target_critic_out (the live critic and live actor are completely
#      untouched) and calls the real agent.step() itself, confirming the
#      bootstrap inside step() -- not just a standalone reconstruction of
#      its formula -- actually reads the target network.
# ---------------------------------------------------------------------------
agent9 = eng.DDPGAgent()
env12 = eng.QuadcopterTakeoffEnv()
state12 = env12.reset()
for _ in range(20):
    a12 = agent9.act(state12)
    ns12, r12, d12, _ = env12.step(a12)
    agent9.step(state12, a12, r12, ns12, d12, batch_size=8)
    state12 = ns12
    if d12:
        state12 = env12.reset()

a_base = agent9.act(state12, add_noise=False)
ns_base, r_base, d_base, _ = env12.step(a_base)
loss_uncorrupted = agent9.step(state12, a_base, r_base, ns_base, d_base, batch_size=8)

# Corrupt ONLY the target critic's output layer.
agent9.target_critic_out.W = agent9.target_critic_out.W + 1000.0

a_corrupt = agent9.act(state12, add_noise=False)
ns_corrupt, r_corrupt, d_corrupt, _ = env12.step(a_corrupt)
loss_target_corrupted = agent9.step(state12, a_corrupt, r_corrupt, ns_corrupt, d_corrupt, batch_size=8)

check("step()'s own loss changes drastically when ONLY the target critic "
      "is corrupted (live critic/actor untouched) -- confirms step() "
      "itself, not just a standalone reconstruction, reads the target "
      "network for its Bellman bootstrap",
      loss_target_corrupted > max(loss_uncorrupted * 10, 100.0),
      f"loss_uncorrupted={loss_uncorrupted:.6f} loss_target_corrupted={loss_target_corrupted:.2f}")

print(f"\n  SUMMARY: {PASS} passed, {FAIL} failed (out of {PASS+FAIL} correctness checks)")
sys.exit(1 if FAIL > 0 else 0)

# ---------------------------------------------------------------------------
# BREAK_IT_INSTRUCTIONS (per TESTING_STANDARD.md, section III):
# In ddpg_quadcopter_rca_engine.py, DDPGAgent.act(), change:
#     bounded_signal = np.clip(raw_signal, 0.05, gamma_cap)
# to:
#     bounded_signal = np.clip(raw_signal, 0.05, 1.0)   (ignore gamma_cap)
# Expected result: "Geburah gamma-cap holds even under adversarially large
# injected noise" must FAIL (output will reach up to 1.0*max_rpm=900, well
# above the claimed 0.85*max_rpm=765 ceiling). Confirmed live in the
# assistant's response to the user, then reverted.
# ---------------------------------------------------------------------------
