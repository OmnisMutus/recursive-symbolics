#!/usr/bin/env python3
"""
ddpg_difficulty_adjusted_convergence_study.py

Follow-up 5 in the generalization thread (see
docs/ddpg_generalization_convergence_report.md's "Correction" section).
Every prior 8-seed study in this thread (the original null study, both
goal-conditioned runs, the retuned-hyperparameter run) compared raw
early-window vs. late-window MEANS of two metrics -- and that comparison
was then shown to be confounded: closure_fraction and raw reward are
each strongly driven by the randomized task difficulty (`initial_dist`)
of whichever episodes happen to land in a given window, independent of
whether any learning occurred (confirmed directly with a completely
untrained agent: corr(initial_dist, reward) = -0.98,
corr(initial_dist, closure) = +0.96, with NO training happening at all).

THIS SCRIPT is the properly difficulty-controlled comparison named as
the open next step in that correction, rather than another raw
early/late mean comparison. Same environment, same fixes already in
place (goal-conditioning + the reward-shaping fix, both already part of
the VERIFIED engine / this repo's other modules) -- nothing about the
agent or environment changes here, only the ANALYSIS.

METHODOLOGY, FIXED BEFORE RUNNING:
  - N_SEEDS = 8, N_EPISODES = 800, EARLY_LATE_WINDOW = 200 -- identical
    to the goal-conditioned and retuned-hyperparameter studies, so this
    is a clean re-analysis of the same experimental design, not a new
    one invented to chase a particular outcome.
  - Hyperparameters: back to the ENGINE'S DEFAULTS (lr=0.01, tau=0.01,
    batch_size=16), NOT the retuned values from
    ddpg_retuned_hyperparameter_study.py -- that retuning was tried and
    showed no benefit, so stacking it here would only add an unvalidated
    change on top of the one thing actually being tested (the analysis
    method). GoalConditionedDDPGAgent's default constructor already uses
    the engine's stock lr/tau.
  - THE ADJUSTMENT: for each seed, log per-episode (initial_dist,
    total_reward, closure_fraction) across all 800 episodes (not just
    aggregated early/late means, which is all prior studies kept). Fit
    ONE linear regression of each metric on initial_dist, using ONLY the
    EARLY window's 200 episodes (`metric ~ a + b * initial_dist`, plain
    least squares via np.polyfit). This model captures "what does task
    difficulty alone predict about this metric, calibrated before most
    of training happened." Apply that SAME fixed model to compute
    residuals (actual - predicted) for BOTH the early and late windows.
    Compare mean residual in the late window against the early window
    via the same binomial sign test used throughout this thread. Fitting
    the adjustment model on early data only (not pooled across all 800
    episodes) is deliberate: it keeps the difficulty-adjustment
    calibration independent of whatever the late window's residuals
    turn out to be, so a late-window improvement can't leak into the
    model doing the adjusting.
  - HONESTY CHECK REPORTED ALONGSIDE THE RESULT: each seed's early-window
    R^2 (how much of the metric's variance across episodes is explained
    by initial_dist alone) is reported per seed. If R^2 is low, task
    difficulty isn't actually explaining much for that particular seed's
    early window and the "adjustment" isn't doing serious work; if R^2
    is high (expected, given the untrained-agent diagnostic found
    |r|>=0.95 relationships), the adjustment is doing exactly what it's
    meant to.

Reports whatever this actually finds, including a null or still-
inconclusive result, per this project's own discipline (see
ANTI_ECHO_ISOLATION_POLICY.md, LIBER_0.md).

Usage:
    python ddpg_difficulty_adjusted_convergence_study.py --seed N
    python ddpg_difficulty_adjusted_convergence_study.py --report
"""

import sys
import json
import random
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import ddpg_training_convergence_study as study
import ddpg_goal_conditioned_convergence_study as gc

N_EPISODES = gc.N_EPISODES          # 800, unchanged
EARLY_LATE_WINDOW = gc.EARLY_LATE_WINDOW  # 200, unchanged

RESULTS_PATH = Path(__file__).parent / "ddpg_difficulty_adjusted_results.json"


def run_one_trial(seed):
    """Same environment/agent as the goal-conditioned study (observation
    fix + reward-shaping fix already live in the engine), engine-default
    hyperparameters (retuning showed no benefit, so not stacked here).
    Returns per-episode arrays instead of just early/late aggregates."""
    np.random.seed(seed)
    random.seed(seed)

    agent = gc.GoalConditionedDDPGAgent()
    env = gc.GoalConditionedRandomizedEnv()

    initial_dists = []
    rewards = []
    closures = []
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
        initial_dists.append(initial_dist)
        rewards.append(total_reward)
        closures.append(closure)

    return initial_dists, rewards, closures


def run_single_seed_to_file(seed):
    initial_dists, rewards, closures = run_one_trial(seed)
    row = {
        "seed": seed,
        "initial_dists": initial_dists,
        "rewards": rewards,
        "closures": closures,
    }
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"seed {seed}: logged {len(rewards)} episodes "
          f"(initial_dist range [{min(initial_dists):.2f}, {max(initial_dists):.2f}])")


def fit_and_residuals(x_fit, y_fit, x_all, y_all):
    """Least-squares fit y = a + b*x on the FIT set only, then returns
    (residuals over x_all/y_all using that fixed model, R^2 of the fit
    on the fit set itself)."""
    b, a = np.polyfit(x_fit, y_fit, 1)  # np.polyfit returns [slope, intercept]
    y_pred_fit = a + b * np.array(x_fit)
    ss_res = np.sum((np.array(y_fit) - y_pred_fit) ** 2)
    ss_tot = np.sum((np.array(y_fit) - np.mean(y_fit)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")

    y_pred_all = a + b * np.array(x_all)
    residuals = np.array(y_all) - y_pred_all
    return residuals, r2


def report_from_file():
    rows = []
    with open(RESULTS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: r["seed"])
    seeds_present = [r["seed"] for r in rows]
    expected = list(range(study.N_SEEDS))
    if seeds_present != expected:
        print(f"WARNING: expected seeds {expected}, got {seeds_present} -- "
              f"report below may be incomplete or duplicated.")

    print("=" * 78)
    print("  DDPG DIFFICULTY-ADJUSTED CONVERGENCE STUDY (FOLLOW-UP 5, FULL 8-SEED)")
    print("=" * 78)
    print(f"  Seeds={study.N_SEEDS}, Episodes/seed={N_EPISODES}, window={EARLY_LATE_WINDOW}")
    print("  Adjustment: metric ~ a + b*initial_dist, fit on EARLY window only,")
    print("  applied to both windows; comparing residual means, not raw means.")
    print("=" * 78 + "\n")

    reward_rows = []
    closure_rows = []
    r2_reward_list = []
    r2_closure_list = []

    for row in rows:
        seed = row["seed"]
        d = np.array(row["initial_dists"])
        r = np.array(row["rewards"])
        c = np.array(row["closures"])

        d_early, d_late = d[:EARLY_LATE_WINDOW], d[-EARLY_LATE_WINDOW:]
        r_early, r_late = r[:EARLY_LATE_WINDOW], r[-EARLY_LATE_WINDOW:]
        c_early, c_late = c[:EARLY_LATE_WINDOW], c[-EARLY_LATE_WINDOW:]

        # Reward: fit on early window, evaluate residuals on early+late.
        resid_r, r2_r = fit_and_residuals(d_early, r_early,
                                           np.concatenate([d_early, d_late]),
                                           np.concatenate([r_early, r_late]))
        resid_r_early = resid_r[:EARLY_LATE_WINDOW]
        resid_r_late = resid_r[EARLY_LATE_WINDOW:]
        reward_rows.append((seed, float(np.mean(resid_r_early)), float(np.mean(resid_r_late)),
                             float(np.mean(resid_r_late) - np.mean(resid_r_early))))
        r2_reward_list.append(r2_r)

        # closure_fraction: same treatment.
        resid_c, r2_c = fit_and_residuals(d_early, c_early,
                                           np.concatenate([d_early, d_late]),
                                           np.concatenate([c_early, c_late]))
        resid_c_early = resid_c[:EARLY_LATE_WINDOW]
        resid_c_late = resid_c[EARLY_LATE_WINDOW:]
        closure_rows.append((seed, float(np.mean(resid_c_early)), float(np.mean(resid_c_late)),
                              float(np.mean(resid_c_late) - np.mean(resid_c_early))))
        r2_closure_list.append(r2_c)

    print("  HONESTY CHECK: early-window R^2 of metric ~ initial_dist per seed\n")
    print(f"  {'seed':>4}  {'reward R^2':>12}  {'closure R^2':>12}")
    for i, seedrow in enumerate(rows):
        print(f"  {seedrow['seed']:>4}  {r2_reward_list[i]:>12.4f}  {r2_closure_list[i]:>12.4f}")
    print(f"\n  mean reward R^2  = {np.mean(r2_reward_list):.4f}")
    print(f"  mean closure R^2 = {np.mean(r2_closure_list):.4f}\n")

    print("  METRIC 1: difficulty-adjusted raw reward (residual improvement)\n")
    study.report_from_rows(reward_rows)

    print("\n\n  METRIC 2: difficulty-adjusted closure_fraction (residual improvement)\n")
    study.report_from_rows(closure_rows)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        run_single_seed_to_file(int(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "--report":
        report_from_file()
    else:
        print("Usage: python ddpg_difficulty_adjusted_convergence_study.py --seed N")
        print("       python ddpg_difficulty_adjusted_convergence_study.py --report")
