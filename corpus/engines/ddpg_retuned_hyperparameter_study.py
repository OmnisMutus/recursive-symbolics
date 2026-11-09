#!/usr/bin/env python3
"""
ddpg_retuned_hyperparameter_study.py

Follow-up 4 in the generalization thread (see
docs/ddpg_generalization_convergence_report.md). The prior three
follow-ups each isolated ONE mechanism at a time, in this order:
  1. Goal-conditioning (append target altitude to the observation) --
     the agent structurally could not know the target otherwise.
  2. Reward-shaping (decay the target-reached bonus with overshoot,
     instead of a flat +10.0) -- fixed a real reward-honesty flaw, but
     did not by itself produce a positive training result; both metrics
     landed near a coin flip instead.
  3. THIS SCRIPT: hyperparameter retuning. lr/tau/batch_size were reused
     unchanged from the original FIXED-task engine in every follow-up so
     far, specifically to isolate the other mechanisms above -- that was
     deliberate, not an oversight, and this script is the first place
     those three numbers are touched.

WHY THESE THREE ARE TREATED AS ONE LEVER, NOT THREE: goal-conditioning
and reward-shaping are each a distinct MECHANISM (what the agent can
observe; what it's rewarded for). lr/tau/batch_size are not separate
mechanisms in that sense -- they are the three knobs of the same
mechanism (how the existing gradient signal is stepped and stabilized),
and standard DDPG practice tunes them together for a given task
difficulty rather than one at a time. Treating them as a single
"hyperparameter retuning" lever, changed together, is consistent with
how the report already named this as "the next lever" (singular).

METHODOLOGY, FIXED BEFORE RUNNING:
  - Builds on BOTH prior fixes unchanged: GoalConditionedDDPGAgent's
    observation fix and the engine's decayed-overshoot reward, both
    already committed and VERIFIED elsewhere. This script changes
    nothing about the environment or the observation -- only the
    learning hyperparameters below.
  - N_SEEDS = 8, N_EPISODES = 800, EARLY_LATE_WINDOW = 200 -- identical
    to the goal-conditioned follow-up, so this is a clean single-variable
    comparison against that study's already-recorded results (kept in
    ddpg_goal_conditioned_convergence_results.json), not a new baseline.
  - The three retuned values, and the reasoning for each (standard DDPG
    stability heuristics for a harder/noisier task, decided here, before
    any run of this script, not adjusted afterward):
      * batch_size: 16 -> 64. A randomized target spans z in [60, 140];
        a 16-sample minibatch drawn from replay can easily be dominated
        by transitions from very different targets, giving a noisy,
        occasionally contradictory gradient. A larger batch averages
        over more of that diversity per step.
      * lr: 0.01 -> 0.005 (halved). A noisier per-batch gradient
        (from the wider task diversity above) is standard justification
        for a smaller step size -- taking the same size step on a
        noisier signal is more likely to overshoot or oscillate.
      * tau: 0.01 -> 0.005 (halved, in step with lr). The target
        network's soft-update rate should track the live network's own
        rate of change; halving lr without also slowing tau would let
        the target drift out of sync with how fast the live network is
        (no longer) moving.
    All three move in the same direction (slower, more averaged, more
    conservative) for the same underlying reason -- a harder, noisier
    task calls for more conservative learning dynamics. This is offered
    as a coherent, principled retuning, not a grid search.

Reports whatever this actually finds, including a null result, per this
project's own discipline (see ANTI_ECHO_ISOLATION_POLICY.md, LIBER_0.md).

Usage:
    python ddpg_retuned_hyperparameter_study.py --seed N
    python ddpg_retuned_hyperparameter_study.py --report
"""

import sys
import random
import pickle
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
import ddpg_goal_conditioned_convergence_study as gc

N_EPISODES = gc.N_EPISODES  # 800, unchanged -- isolate hyperparameters only
EARLY_LATE_WINDOW = gc.EARLY_LATE_WINDOW  # 200, unchanged

RETUNED_LR = 0.005
RETUNED_TAU = 0.005
RETUNED_BATCH_SIZE = 64


class RetunedDDPGAgent(gc.GoalConditionedDDPGAgent):
    """Identical to GoalConditionedDDPGAgent (which already carries the
    observation fix), except lr and tau are retuned per the module
    docstring above. batch_size is not an instance attribute on
    DDPGAgent -- it's supplied by the caller to step() -- so it's
    applied per-call in run_single_seed_to_file() below, not here, since
    batch_size isn't a stored instance attribute on the base DDPGAgent."""

    def __init__(self, state_dim=19, action_dim=4, max_rpm=900.0):
        super().__init__(state_dim=state_dim, action_dim=action_dim, max_rpm=max_rpm)
        self.lr = RETUNED_LR
        self.tau = RETUNED_TAU


RESULTS_PATH = Path(__file__).parent / "ddpg_retuned_hyperparameter_results.json"
CHUNK_SIZE = 200  # ~11-12s/chunk measured at batch_size=64 -- comfortably under any per-call time limit;
                  # 800/200 = 4 chunks/seed. Chunking is purely an execution-environment accommodation
                  # (this machine's per-command time budget doesn't fit 800 episodes at batch_size=64 in
                  # one call) -- it does NOT change the methodology: still one continuous 800-episode run
                  # per seed, same RNG stream throughout, just resumed across process invocations via a
                  # checkpoint of the agent's weights, replay buffer, and RNG state.


def checkpoint_path_for(seed):
    return Path(__file__).parent / f"ddpg_retuned_checkpoint_seed{seed}.pkl"


def run_single_seed_to_file(seed):
    """Advances ONE chunk (CHUNK_SIZE episodes) of the given seed's 800-episode
    run. Call this repeatedly with the same seed until it prints 'FINALIZED'
    -- each call resumes exactly where the last left off (agent weights,
    replay buffer, and both RNG streams are checkpointed), so the full run is
    equivalent to one uninterrupted 800-episode trial, not four independent
    200-episode ones."""
    import json
    ckpt_path = checkpoint_path_for(seed)

    if ckpt_path.exists():
        with open(ckpt_path, "rb") as f:
            ck = pickle.load(f)
        agent = ck["agent"]
        np.random.set_state(ck["np_state"])
        random.setstate(ck["py_state"])
        episode_rewards = ck["episode_rewards"]
        closure_fractions = ck["closure_fractions"]
        start_ep = ck["episodes_done"]
    else:
        np.random.seed(seed)
        random.seed(seed)
        agent = RetunedDDPGAgent()
        episode_rewards = []
        closure_fractions = []
        start_ep = 0

    env = gc.GoalConditionedRandomizedEnv()
    end_ep = min(start_ep + CHUNK_SIZE, N_EPISODES)

    for _ in range(start_ep, end_ep):
        state = env.reset()
        start_z = float(env.pose[2])
        target_z = float(env.target_pos[2])
        initial_dist = abs(start_z - target_z)
        total_reward = 0.0
        while True:
            action = agent.act(state)
            next_state, reward, done, _ = env.step(action)
            agent.step(state, action, reward, next_state, done, batch_size=RETUNED_BATCH_SIZE)
            total_reward += reward
            state = next_state
            if done:
                break
        final_z = float(env.pose[2])
        final_dist = abs(final_z - target_z)
        closure = 1.0 - (final_dist / initial_dist) if initial_dist > 1e-9 else 0.0
        episode_rewards.append(total_reward)
        closure_fractions.append(closure)

    if end_ep < N_EPISODES:
        with open(ckpt_path, "wb") as f:
            pickle.dump({
                "agent": agent,
                "np_state": np.random.get_state(),
                "py_state": random.getstate(),
                "episode_rewards": episode_rewards,
                "closure_fractions": closure_fractions,
                "episodes_done": end_ep,
            }, f)
        print(f"seed {seed}: checkpointed at episode {end_ep}/{N_EPISODES} "
              f"(run again with --seed {seed} to continue)")
        return

    # Final chunk -- compute stats and write the completed row.
    rewards, closures = episode_rewards, closure_fractions
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
    try:
        ckpt_path.unlink()
    except OSError:
        # Known filesystem quirk on this Windows-mounted mount: unlink can
        # fail with "Operation not permitted" even though rename succeeds.
        ckpt_path.rename(ckpt_path.with_suffix(".pkl.done"))
    print(f"seed {seed}: FINALIZED -- reward early={r_early:.4f} late={r_late:.4f} "
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
    print("  DDPG RETUNED-HYPERPARAMETER STUDY (FOLLOW-UP 4, FULL 8-SEED)")
    print("=" * 78)
    print(f"  Seeds={study.N_SEEDS}, Episodes/seed={N_EPISODES}, window={EARLY_LATE_WINDOW}")
    print(f"  Unchanged from goal-conditioned study: observation fix, reward-shaping fix, episode budget")
    print(f"  Retuned: lr {0.01}->{RETUNED_LR}, tau {0.01}->{RETUNED_TAU}, batch_size 16->{RETUNED_BATCH_SIZE}")
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
        print("Usage: python ddpg_retuned_hyperparameter_study.py --seed N")
        print("       python ddpg_retuned_hyperparameter_study.py --report")
