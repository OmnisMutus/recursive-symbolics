#!/usr/bin/env python3
"""
ddpg_generalization_convergence_study.py

Answers a question ddpg_training_convergence_study.py explicitly could
not: that study measured whether the DDPG loop improves at ONE fixed
task (start altitude z=10, target altitude z=100, every single episode,
every single seed -- confirmed directly by reading
ddpg_quadcopter_rca_engine.py's QuadcopterTakeoffEnv.reset() and
__init__, not assumed). Improvement on a fixed task is consistent with
either genuine altitude-control learning OR partial memorization of one
specific trajectory -- the original study could not distinguish these,
and its own LIMITATIONS section did not claim to.

THE ONE CHANGE, DISCLOSED: RandomizedQuadcopterTakeoffEnv below samples a
NEW start altitude and a NEW target altitude every reset() call, instead
of the original's fixed [10 -> 100]. Nothing else changes -- same
physics (identical Euler integration, identical reward shaping, identical
termination conditions), same DDPGAgent class, same methodology
(N_SEEDS, N_EPISODES, EARLY_LATE_WINDOW, sign test) imported directly
from ddpg_training_convergence_study.py rather than re-specified, so this
is a controlled comparison -- one variable changed, everything else held
fixed, per this repo's own "change one thing at a time" discipline.

WHY ONLY ALTITUDE IS RANDOMIZED, STATED HONESTLY: read directly (not
assumed) that the base engine's own physics never varies x, y, roll, or
pitch either -- angular_v is never set anywhere in step(), so pose[3]
(roll) and pose[4] (pitch) are permanently dead state, and pose[0]/pose[1]
(x, y) never move regardless of action. The base environment is,
underneath its 6-dimensional-looking pose vector, a 1D altitude-control
problem. This variant randomizes the one axis that's actually alive,
rather than randomizing dimensions the base physics doesn't model in the
first place -- extending to true 3D flight would require adding real x/y
and roll/pitch dynamics to the base engine, which is out of scope for
this specific generalization check (see LIBER_0.md for what's deferred
and why).

Start/target ranges are disjoint (start in [5,20], target in [60,140])
so every sampled episode is still genuinely a takeoff (target always
above start) -- this tests generalization across DIFFERENT takeoffs, not
a qualitatively different task (e.g. descent) the reward/termination
logic was never designed for.
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


class RandomizedQuadcopterTakeoffEnv(eng.QuadcopterTakeoffEnv):
    """Identical physics/reward/termination to the base
    QuadcopterTakeoffEnv -- only reset() differs, sampling a fresh start
    altitude and target altitude every episode instead of reusing the
    same fixed [10 -> 100] every time."""

    def __init__(self, start_z_range=(5.0, 20.0), target_z_range=(60.0, 140.0)):
        self.start_z_range = start_z_range
        self.target_z_range = target_z_range
        super().__init__(target_pos=[0.0, 0.0, 100.0])  # placeholder; reset() overwrites it

    def reset(self):
        start_z = float(np.random.uniform(*self.start_z_range))
        target_z = float(np.random.uniform(*self.target_z_range))
        self.target_pos = np.array([0.0, 0.0, target_z])
        self.pose = np.array([0.0, 0.0, start_z, 0.0, 0.0, 0.0], dtype=np.float64)
        self.v = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.angular_v = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.pose_history = [np.copy(self.pose) for _ in range(3)]
        self.step_count = 0
        return self._get_obs()


def run_one_trial_randomized(seed):
    """Mirrors ddpg_training_convergence_study.run_one_trial() exactly,
    with only the environment class swapped -- deliberately duplicated
    rather than parameterizing the original (which is already VERIFIED
    and left untouched) to keep this a clean, isolated comparison.

    ALSO tracks a second, task-difficulty-NORMALIZED metric alongside raw
    reward, computed from the SAME single training run (not a second,
    separately-trained pass): closure_fraction = 1 - final_dist/initial_dist,
    where initial_dist = |start_z - target_z| and final_dist =
    |final_z - target_z|. Added after the raw-reward result came back
    with much higher variance than the fixed-task study (std ~11.7 here
    vs. all improvements within [0.4, 4.0] there) -- a real, identified
    confound: under a randomized target, total reward swings with WHICH
    target got sampled that episode, not just policy quality, which can
    mask a real learning signal the raw-reward sign test isn't sensitive
    enough to detect. closure_fraction is invariant to how far or high
    the sampled target was, isolating "did the agent get proportionally
    closer" from "how hard was this particular episode's task"."""
    np.random.seed(seed)
    random.seed(seed)

    agent = eng.DDPGAgent()
    env = RandomizedQuadcopterTakeoffEnv()

    episode_rewards = []
    closure_fractions = []
    for _ in range(study.N_EPISODES):
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


RESULTS_PATH = Path(__file__).parent / "ddpg_generalization_convergence_results.json"


def run_single_seed_to_file(seed):
    """Mirrors ddpg_training_convergence_study.run_single_seed_to_file():
    this environment's per-call time budget is smaller than a full
    N_SEEDS x N_EPISODES run, so each seed is executed in its own process
    and appended to RESULTS_PATH -- the methodology is unchanged, only
    how the run is split across invocations (same reason the original
    study needed this). Records BOTH metrics (raw reward and
    closure_fraction) from the single training run, not two separate runs."""
    import json
    rewards, closures = run_one_trial_randomized(seed)

    reward_early = float(np.mean(rewards[:study.EARLY_LATE_WINDOW]))
    reward_late = float(np.mean(rewards[-study.EARLY_LATE_WINDOW:]))
    closure_early = float(np.mean(closures[:study.EARLY_LATE_WINDOW]))
    closure_late = float(np.mean(closures[-study.EARLY_LATE_WINDOW:]))

    row = {
        "seed": seed,
        "early_mean": reward_early, "late_mean": reward_late,
        "improvement": reward_late - reward_early,
        "closure_early_mean": closure_early, "closure_late_mean": closure_late,
        "closure_improvement": closure_late - closure_early,
    }
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"seed {seed}: reward early={reward_early:.4f} late={reward_late:.4f} "
          f"improvement={row['improvement']:.4f}  |  "
          f"closure_fraction early={closure_early:.4f} late={closure_late:.4f} "
          f"improvement={row['closure_improvement']:.4f}")


def report_from_file():
    import json
    rows = []
    with open(RESULTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rows.append(d)
    rows.sort(key=lambda r: r["seed"])
    seeds_present = [r["seed"] for r in rows]
    expected = list(range(study.N_SEEDS))
    if seeds_present != expected:
        print(f"WARNING: expected seeds {expected}, got {seeds_present} -- "
              f"report below may be incomplete or duplicated.")

    print("=" * 78)
    print("  DDPG GENERALIZATION CHECK: RANDOMIZED START/TARGET ALTITUDE")
    print("=" * 78)
    print(f"  Same methodology as ddpg_training_convergence_study.py:")
    print(f"  Seeds={study.N_SEEDS}, Episodes/seed={study.N_EPISODES}, "
          f"window={study.EARLY_LATE_WINDOW}")
    print(f"  ONLY CHANGE: start_z ~ U(5,20), target_z ~ U(60,140) every reset()")
    print("=" * 78 + "\n")

    print("  METRIC 1: raw total reward (same metric the fixed-task study used)\n")
    reward_rows = [(r["seed"], r["early_mean"], r["late_mean"], r["improvement"]) for r in rows]
    study.report_from_rows(reward_rows)

    print("\n\n  METRIC 2: closure_fraction = 1 - final_dist/initial_dist")
    print("  (task-difficulty-normalized -- added because metric 1's variance")
    print("   was much larger here than in the fixed-task study, a real")
    print("   confound worth checking rather than assuming away)\n")
    closure_rows = [(r["seed"], r["closure_early_mean"], r["closure_late_mean"],
                      r["closure_improvement"]) for r in rows]
    study.report_from_rows(closure_rows)


def main():
    import time
    print("=" * 78)
    print("  DDPG GENERALIZATION CHECK: RANDOMIZED START/TARGET ALTITUDE")
    print("=" * 78)
    print(f"  Same methodology as ddpg_training_convergence_study.py:")
    print(f"  Seeds={study.N_SEEDS}, Episodes/seed={study.N_EPISODES}, "
          f"window={study.EARLY_LATE_WINDOW}")
    print(f"  ONLY CHANGE: start_z ~ U(5,20), target_z ~ U(60,140) every reset()")
    print("=" * 78)

    t0 = time.perf_counter()
    reward_rows = []
    closure_rows = []
    for seed in range(study.N_SEEDS):
        rewards, closures = run_one_trial_randomized(seed)
        r_early = float(np.mean(rewards[:study.EARLY_LATE_WINDOW]))
        r_late = float(np.mean(rewards[-study.EARLY_LATE_WINDOW:]))
        reward_rows.append((seed, r_early, r_late, r_late - r_early))
        c_early = float(np.mean(closures[:study.EARLY_LATE_WINDOW]))
        c_late = float(np.mean(closures[-study.EARLY_LATE_WINDOW:]))
        closure_rows.append((seed, c_early, c_late, c_late - c_early))
    elapsed = time.perf_counter() - t0
    print(f"\n  Total run time: {elapsed:.2f}s\n")

    print("  METRIC 1: raw total reward\n")
    study.report_from_rows(reward_rows)
    print("\n\n  METRIC 2: closure_fraction\n")
    study.report_from_rows(closure_rows)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        run_single_seed_to_file(int(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "--report":
        report_from_file()
    else:
        main()
