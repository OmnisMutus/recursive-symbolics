#!/usr/bin/env python3
"""
ddpg_training_convergence_study.py
Does the now-fixed DDPG actor-critic loop actually converge to a better
policy over training -- not "does the gradient flow correctly" (already
proven in test_ddpg_quadcopter_rca_engine.py's 33 checks), but "does real,
repeated training measurably improve episode reward."

This is the one thing every previous fix to ddpg_quadcopter_rca_engine.py
(the actor-critic gradient bug, the degenerate-LayerNorm critic bug, the
target networks) left explicitly out of scope -- see
docs/ddpg_engine_kabbalistic_hand_verification.md's "does not establish
that the agent learns an *effective* takeoff policy" note. This script is
that measurement, not another mechanism check.

METHODOLOGY (fixed BEFORE running, not tuned after seeing results -- the
same discipline real_ridge_benchmark_vs_sklearn.py uses for its own
comparison):
  - N_SEEDS independent trials, each with a fresh DDPGAgent and
    QuadcopterTakeoffEnv, seeded via both np.random.seed() and
    random.seed() for full reproducibility.
  - N_EPISODES episodes per trial. Metric: total reward per episode
    (the same quantity ddpg_quadcopter_rca_engine.py's own demo script
    already prints).
  - Per trial: mean total reward over the EARLY window (episodes
    [0:EARLY_LATE_WINDOW]) vs the LATE window (episodes
    [N_EPISODES-EARLY_LATE_WINDOW:N_EPISODES]). improvement = late - early.
  - Aggregate significance: a sign test across the N_SEEDS trials (how
    many showed improvement > 0), evaluated against the null hypothesis
    that improvement direction is a coin flip (p=0.5), via a hand-rolled
    binomial tail probability -- no scipy dependency, consistent with
    this repo's zero-dependency engine layer.

This will report whatever it actually finds, including "no significant
improvement" or "inconsistent across seeds" if that's what happens --
per this project's own discipline (see ANTI_ECHO_ISOLATION_POLICY.md,
LIBER_0.md) of reporting real findings rather than the flattering one.

Usage:
    python ddpg_training_convergence_study.py
"""

import sys
import math
import time
import random
import platform
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import ddpg_quadcopter_rca_engine as eng

N_SEEDS = 8
N_EPISODES = 200
EARLY_LATE_WINDOW = 50  # episodes [0:50] vs [150:200]


def run_one_trial(seed):
    """Fresh agent + env, seeded, run N_EPISODES episodes, return the list
    of total_reward per episode (length N_EPISODES)."""
    np.random.seed(seed)
    random.seed(seed)

    agent = eng.DDPGAgent()
    env = eng.QuadcopterTakeoffEnv()

    episode_rewards = []
    for _ in range(N_EPISODES):
        state = env.reset()
        total_reward = 0.0
        while True:
            action = agent.act(state)
            next_state, reward, done, _ = env.step(action)
            agent.step(state, action, reward, next_state, done)
            total_reward += reward
            state = next_state
            if done:
                break
        episode_rewards.append(total_reward)
    return episode_rewards


def binomial_upper_tail(n_trials, n_success, p=0.5):
    """P(X >= n_success) for X ~ Binomial(n_trials, p). Hand-rolled with
    math.comb to avoid a scipy dependency."""
    return sum(
        math.comb(n_trials, k) * (p ** k) * ((1 - p) ** (n_trials - k))
        for k in range(n_success, n_trials + 1)
    )


RESULTS_PATH = Path(__file__).parent / "ddpg_training_convergence_results.json"


def run_single_seed_to_file(seed):
    """Runs exactly one seed's trial and appends its result to
    RESULTS_PATH (JSON lines). Exists so a single seed's ~8s run can be
    executed per shell call, since the full N_SEEDS run exceeds a single
    call's time budget in this environment -- the methodology itself
    (N_SEEDS, N_EPISODES, windows) is unchanged, only how the run is
    split across separate invocations."""
    import json
    rewards = run_one_trial(seed)
    early_mean = float(np.mean(rewards[:EARLY_LATE_WINDOW]))
    late_mean = float(np.mean(rewards[-EARLY_LATE_WINDOW:]))
    row = {"seed": seed, "early_mean": early_mean, "late_mean": late_mean,
           "improvement": late_mean - early_mean}
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"seed {seed}: early={early_mean:.4f} late={late_mean:.4f} "
          f"improvement={row['improvement']:.4f}")


def main():
    print("=" * 78)
    print("  ENVIRONMENT DISCLOSURE")
    print("=" * 78)
    print(f"  Python : {platform.python_version()}")
    print(f"  NumPy  : {np.__version__}")
    print(f"  Timer  : time.perf_counter()")
    print("=" * 78)

    print("\n" + "=" * 78)
    print("  METHODOLOGY (fixed before running)")
    print("=" * 78)
    print(f"  Seeds                 : {N_SEEDS} (0..{N_SEEDS - 1})")
    print(f"  Episodes per seed     : {N_EPISODES}")
    print(f"  Early window          : episodes [0:{EARLY_LATE_WINDOW}]")
    print(f"  Late window           : episodes [{N_EPISODES - EARLY_LATE_WINDOW}:{N_EPISODES}]")
    print(f"  Metric                : total reward per episode")
    print(f"  Significance          : sign test (binomial, p=0.5) across seeds")
    print("=" * 78)

    t0 = time.perf_counter()
    improvements = []
    per_seed_rows = []
    for seed in range(N_SEEDS):
        rewards = run_one_trial(seed)
        early_mean = float(np.mean(rewards[:EARLY_LATE_WINDOW]))
        late_mean = float(np.mean(rewards[-EARLY_LATE_WINDOW:]))
        improvement = late_mean - early_mean
        improvements.append(improvement)
        per_seed_rows.append((seed, early_mean, late_mean, improvement))
    elapsed = time.perf_counter() - t0

    print(f"\n  Total run time: {elapsed:.2f}s for {N_SEEDS} seeds x {N_EPISODES} episodes\n")

    report_from_rows(per_seed_rows)


def report_from_rows(per_seed_rows):
    improvements = [row[3] for row in per_seed_rows]

    print("=" * 78)
    print("  PER-SEED RESULTS")
    print("=" * 78)
    print(f"  {'seed':<6}{'early mean':>14}{'late mean':>14}{'improvement':>16}")
    for seed, early_mean, late_mean, improvement in per_seed_rows:
        flag = "improved" if improvement > 0 else "did NOT improve"
        print(f"  {seed:<6}{early_mean:>14.4f}{late_mean:>14.4f}{improvement:>16.4f}   ({flag})")

    n_improved = sum(1 for imp in improvements if imp > 0)
    mean_improvement = float(np.mean(improvements))
    std_improvement = float(np.std(improvements))
    p_value = binomial_upper_tail(N_SEEDS, n_improved, p=0.5)

    print("\n" + "=" * 78)
    print("  AGGREGATE FINDING")
    print("=" * 78)
    print(f"  Seeds showing improvement (late > early) : {n_improved} / {N_SEEDS}")
    print(f"  Mean improvement across seeds             : {mean_improvement:.4f}")
    print(f"  Std of improvement across seeds           : {std_improvement:.4f}")
    print(f"  Sign-test p-value (H0: 50/50 chance)      : {p_value:.4f}")
    print()
    if n_improved == N_SEEDS and p_value < 0.05:
        print("  HONEST CONCLUSION: every seed improved, and this is unlikely by")
        print("  chance alone (p < 0.05). Real evidence of learning across")
        print("  training, not proof of a GOOD policy -- see limitations below.")
    elif n_improved > N_SEEDS / 2 and p_value < 0.05:
        print("  HONEST CONCLUSION: a majority of seeds improved, and this is")
        print("  unlikely by chance alone (p < 0.05). Evidence of learning, but")
        print("  not universal across every seed tried.")
    else:
        print("  HONEST CONCLUSION: improvement was NOT statistically distinguishable")
        print("  from a coin flip across these seeds. This does NOT confirm the")
        print("  training loop fails to learn -- it means this specific study, at")
        print("  this episode count and seed count, did not find reliable evidence")
        print("  either way. Reported as such rather than as a negative or positive")
        print("  result it doesn't actually support.")

    print("\n" + "=" * 78)
    print("  LIMITATIONS")
    print("=" * 78)
    print("  - 'Improvement' here means total reward per episode increased between")
    print("    an early and late window -- it does NOT mean the agent reaches or")
    print("    stays near the z=100m target, which is a stronger, unmeasured claim.")
    print(f"  - {N_EPISODES} episodes/seed, {N_SEEDS} seeds is a modest budget (chosen for")
    print("    a genuinely cheap, honest check, not a publication-grade study). A")
    print("    null or weak result here does not rule out convergence over a much")
    print("    longer run.")
    print("  - Hyperparameters (lr=0.01, tau=0.01, batch_size defaults) were used")
    print("    as already set in ddpg_quadcopter_rca_engine.py, not tuned for this")
    print("    study -- this measures the engine as shipped, not a best-case tune.")
    print("  - This is a measurement script, not a TESTING_STANDARD.md correctness")
    print("    test -- there is no single 'right answer' to assert VERIFIED/FAILED")
    print("    against, which is why this isn't registered in a correspondence")
    print("    ledger or test_all_engines.py.")
    print("=" * 78)


def report_from_file():
    """Reads every seed's row from RESULTS_PATH and runs the same
    aggregate report main() would have produced from an in-memory run --
    used when seeds were executed one-per-call (see run_single_seed_to_file)
    instead of in a single process."""
    import json
    rows = []
    with open(RESULTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rows.append((d["seed"], d["early_mean"], d["late_mean"], d["improvement"]))
    rows.sort(key=lambda r: r[0])
    seeds_present = [r[0] for r in rows]
    expected = list(range(N_SEEDS))
    if seeds_present != expected:
        print(f"WARNING: expected seeds {expected}, got {seeds_present} -- "
              f"report below may be incomplete or duplicated.")
    print("=" * 78)
    print("  ENVIRONMENT DISCLOSURE")
    print("=" * 78)
    print(f"  Python : {platform.python_version()}")
    print(f"  NumPy  : {np.__version__}")
    print("=" * 78)
    print("\n" + "=" * 78)
    print("  METHODOLOGY (fixed before running)")
    print("=" * 78)
    print(f"  Seeds                 : {N_SEEDS} (0..{N_SEEDS - 1})")
    print(f"  Episodes per seed     : {N_EPISODES}")
    print(f"  Early window          : episodes [0:{EARLY_LATE_WINDOW}]")
    print(f"  Late window           : episodes [{N_EPISODES - EARLY_LATE_WINDOW}:{N_EPISODES}]")
    print(f"  Metric                : total reward per episode")
    print(f"  Significance          : sign test (binomial, p=0.5) across seeds")
    print("  (Executed one seed per process call due to this environment's")
    print("   per-call time limit -- methodology itself is unchanged.)")
    print("=" * 78 + "\n")
    report_from_rows(rows)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        run_single_seed_to_file(int(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "--report":
        report_from_file()
    else:
        main()
