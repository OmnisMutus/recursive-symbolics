#!/usr/bin/env python3
"""
ddpg_goal_conditioned_convergence_study.py

The properly-scoped follow-up logged in FUTURE_WORK.md after
ddpg_generalization_convergence_report.py found a null generalization
result and traced it to a real root cause: QuadcopterTakeoffEnv's
observation never includes the target position, so under a randomized
target the agent cannot know what it's being asked to reach. Two quick,
informal 4-seed probes there suggested goal-conditioning ALONE, at the
same modest budget, didn't immediately fix it either -- this script is
the properly-scoped confirmation: the FULL 8-seed/2-metric methodology,
not a 4-seed probe, with the fix built as a real subclass rather than a
one-off monkey-patch.

METHODOLOGY, FIXED BEFORE RUNNING (same discipline as both prior
studies -- decided here, not after seeing results):

  - N_SEEDS = 8 (0..7), same as both prior studies, so report_from_rows()
    and its sign test can be reused directly, unmodified.
  - N_EPISODES = 800 (4x the original 200) -- chosen because the
    randomized task's effective state space is substantially larger
    (start_z spans 15 units, target_z spans 80 units, vs. one fixed
    point each in the original study) and the earlier 4x-budget probe
    used this same figure, so it isn't picked after seeing this
    specific run's results.
  - EARLY_LATE_WINDOW = 200 -- kept at the same 25% proportion of
    N_EPISODES as the original study's 50/200 (25%), not shrunk or
    grown to flatter a particular outcome.
  - DELIBERATELY NOT retuning lr/tau/batch_size: changing multiple
    things at once (goal-conditioning AND hyperparameters AND budget)
    after a null result would make it impossible to attribute any
    change in outcome to a specific cause, and risks exactly the
    tune-until-it-works pattern this project's own discipline (see
    ddpg_training_convergence_study.py's docstring) exists to avoid.
    Only ONE new lever is pulled here (goal-conditioning), plus the
    budget increase already justified above and already tried at
    smaller scale.

THE FIX, AS A REAL SUBCLASS NOT A PATCH: GoalConditionedDDPGAgent below
properly rebuilds the state_dim-dependent layers (actor_l1, critic_l1,
and their target copies) at construction time, closing the disclosed gap
that DDPGAgent.__init__'s state_dim parameter is accepted but never
threaded into those layers' actual sizes (both hardcoded to 18). This is
scoped to the subclass -- ddpg_quadcopter_rca_engine.py itself is left
untouched, consistent with composing new things on top of a VERIFIED
module rather than editing it in place.
"""

import sys
import random
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import ddpg_quadcopter_rca_engine as eng
import ddpg_training_convergence_study as study
import ddpg_generalization_convergence_study as gen

N_EPISODES = 800
EARLY_LATE_WINDOW = 200


class GoalConditionedDDPGAgent(eng.DDPGAgent):
    """Properly fixes the disclosed state_dim gap: DDPGAgent.__init__
    accepts state_dim but hardcodes actor_l1/critic_l1 to 18 regardless.
    Rebuilds exactly those layers (and their target-network clones) at
    the correct input size after the parent constructor runs -- a real,
    documented, reusable fix, not an inline monkey-patch."""

    def __init__(self, state_dim=19, action_dim=4, max_rpm=900.0):
        super().__init__(state_dim=18, action_dim=action_dim, max_rpm=max_rpm)
        self.actor_l1 = eng.LayerNormDense(state_dim, 32, 'relu')
        self.critic_l1 = eng.LayerNormDense(state_dim + action_dim, 32, 'relu')
        self.target_actor_l1 = self.actor_l1.clone()
        self.target_critic_l1 = self.critic_l1.clone()
        self.state_dim = state_dim


class GoalConditionedRandomizedEnv(gen.RandomizedQuadcopterTakeoffEnv):
    """Identical to RandomizedQuadcopterTakeoffEnv, except the
    observation appends the target altitude -- closing the root cause
    ddpg_generalization_convergence_report.py identified: the base
    environment's _get_obs() never reveals the goal."""

    def _get_obs(self):
        base = np.concatenate(self.pose_history)
        return np.concatenate([base, [self.target_pos[2]]])


def run_one_trial(seed):
    """Same shape as the prior two studies' run_one_trial functions:
    fresh agent + env, seeded, runs N_EPISODES, returns per-episode
    reward AND closure_fraction (see ddpg_generalization_convergence_study.py
    for closure_fraction's definition and rationale)."""
    np.random.seed(seed)
    random.seed(seed)

    agent = GoalConditionedDDPGAgent()
    env = GoalConditionedRandomizedEnv()

    episode_rewards = []
    closure_fractions = []
    for _ in range(N_EPISODES):
        state = env.reset()
        start_z = float(env.pose[2])
        target_z = float(env.target_pos[2])
        initial_dist = abs(start_z - target_z)
        total_reward = 0.0
        while True:
            action = agent.act(state)
            next_state, reward, done, _ = env.step(action)
            agent.step(state, action, reward, next_state, done)
            total_reward += reward
            state = next_state
            if done:
                break
        final_z = float(env.pose[2])
        final_dist = abs(final_z - target_z)
        closure = 1.0 - (final_dist / initial_dist) if initial_dist > 1e-9 else 0.0
        episode_rewards.append(total_reward)
        closure_fractions.append(closure)
    return episode_rewards, closure_fractions


RESULTS_PATH = Path(__file__).parent / "ddpg_goal_conditioned_convergence_results.json"


def run_single_seed_to_file(seed):
    import json
    rewards, closures = run_one_trial(seed)
    r_early = float(np.mean(rewards[:EARLY_LATE_WINDOW]))
    r_late = float(np.mean(rewards[-EARLY_LATE_WINDOW:]))
    c_early = float(np.mean(closures[:EARLY_LATE_WINDOW]))
    c_late = float(np.mean(closures[-EARLY_LATE_WINDOW:]))
    row = {
        "seed": seed,
        "early_mean": r_early, "late_mean": r_late, "improvement": r_late - r_early,
        "closure_early_mean": c_early, "closure_late_mean": c_late,
        "closure_improvement": c_late - c_early,
    }
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"seed {seed}: reward early={r_early:.4f} late={r_late:.4f} "
          f"improvement={row['improvement']:.4f}  |  "
          f"closure early={c_early:.4f} late={c_late:.4f} "
          f"improvement={row['closure_improvement']:.4f}")


def report_from_file():
    import json
    rows = []
    with open(RESULTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    rows.sort(key=lambda r: r["seed"])
    seeds_present = [r["seed"] for r in rows]
    expected = list(range(study.N_SEEDS))
    if seeds_present != expected:
        print(f"WARNING: expected seeds {expected}, got {seeds_present} -- "
              f"report below may be incomplete or duplicated.")

    print("=" * 78)
    print("  DDPG GOAL-CONDITIONED GENERALIZATION STUDY (FULL 8-SEED METHODOLOGY)")
    print("=" * 78)
    print(f"  Seeds={study.N_SEEDS}, Episodes/seed={N_EPISODES}, window={EARLY_LATE_WINDOW}")
    print(f"  Fix: target altitude appended to observation (19-dim state)")
    print(f"  Unchanged from prior null result: lr, tau, batch_size all as-shipped")
    print("=" * 78 + "\n")

    print("  METRIC 1: raw total reward\n")
    reward_rows = [(r["seed"], r["early_mean"], r["late_mean"], r["improvement"]) for r in rows]
    study.report_from_rows(reward_rows)

    print("\n\n  METRIC 2: closure_fraction (task-difficulty-normalized)\n")
    closure_rows = [(r["seed"], r["closure_early_mean"], r["closure_late_mean"],
                      r["closure_improvement"]) for r in rows]
    study.report_from_rows(closure_rows)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        run_single_seed_to_file(int(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "--report":
        report_from_file()
    else:
        print("Usage: python ddpg_goal_conditioned_convergence_study.py --seed N")
        print("       python ddpg_goal_conditioned_convergence_study.py --report")
