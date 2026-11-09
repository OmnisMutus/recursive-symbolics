# DDPG Training Convergence Report

*Register note (see `docs/fixed_point_closure_and_the_y_combinator.md` §1
for the three-register discipline): this is Register B — a real,
falsifiable empirical measurement, run and reported with its actual
numbers, not a claim about consciousness or a design principle.*

## What this answers

Every previous fix to `ddpg_quadcopter_rca_engine.py` — the actor-critic
gradient bug, the degenerate-LayerNorm critic bug, the target networks —
verified that the *mechanism* works (gradients flow correctly, weights
move as they should, the deterministic policy gradient's mathematical
guarantee holds). None of them verified the one question that would
actually matter if this engine controlled something real: **does
repeated training measurably improve the reward the agent earns?**

This report is that measurement, produced by
[`../ddpg_training_convergence_study.py`](../ddpg_training_convergence_study.py).

## Methodology (fixed before running, not tuned after seeing results)

- **8 independent seeds** (0–7), each a fresh `DDPGAgent` and
  `QuadcopterTakeoffEnv`, seeded via both `np.random.seed()` and
  `random.seed()` for full reproducibility.
- **200 episodes per seed.** Metric: total reward per episode (the same
  quantity the engine's own demo script already prints).
- **Early window**: episodes 0–49. **Late window**: episodes 150–199.
  `improvement = mean(late) - mean(early)`, per seed.
- **Significance**: a binomial sign test across the 8 seeds (how many
  showed `improvement > 0`), against the null hypothesis that the
  direction of improvement is a coin flip (p=0.5). Computed by hand with
  `math.comb` — no scipy dependency, consistent with this repo's
  zero-dependency engine layer.
- Hyperparameters (`lr=0.01`, `tau=0.01`, batch size defaults) were used
  exactly as already set in the engine — not tuned for this study. This
  measures the engine as shipped, not a best-case configuration.

This methodology was fixed and written into the script's own docstring
before any seed was run, specifically so the analysis couldn't be
adjusted after seeing a result that needed flattering.

## Result (real numbers, one live run)

| seed | early mean | late mean | improvement |
| :--- | ---: | ---: | ---: |
| 0 | 195.3357 | 196.6868 | +1.3512 |
| 1 | 198.3154 | 199.8887 | +1.5733 |
| 2 | 196.9643 | 199.5461 | +2.5818 |
| 3 | 194.7061 | 195.2144 | +0.5083 |
| 4 | 194.9014 | 196.8201 | +1.9187 |
| 5 | 194.4492 | 194.8681 | +0.4190 |
| 6 | 196.7766 | 199.1352 | +2.3586 |
| 7 | 195.4281 | 199.3997 | +3.9716 |

- **8 / 8 seeds improved.**
- Mean improvement across seeds: **+1.8353**. Std: 1.0881.
- Sign-test p-value: **0.0039** (well below 0.05 — very unlikely this
  pattern is a coin flip across 8 independent trials).

**Honest conclusion**: this is real evidence that the now-fixed
actor-critic loop learns something — reward genuinely trends upward with
training, consistently, not by chance. It is **not** evidence of a *good*
policy: the improvement is small in relative terms (roughly 1–2% over
an already-high baseline around 195–200 per episode), and "reward went
up" is a different, weaker claim than "the agent reliably reaches and
holds z=100m." The reward function's own shaping (a `+10.0` bonus added
on *every* step the drone is at or above the target altitude, not once)
means even a mediocre policy that occasionally drifts near the target
racks up a fairly high score — so a modest score increase is a real
signal, not proof of strong flight control.

## Limitations, stated plainly

- 200 episodes and 8 seeds is a deliberately modest, cheap budget (this
  whole run took under two minutes of actual compute), not a
  publication-grade study. A weak or null result at this scale would not
  have ruled out convergence over a much longer run — it happened to
  come back positive and significant, which is reported as what it is,
  not inflated into more than it shows.
- "Improvement" is a within-episode-reward comparison, not a
  target-reaching-rate or flight-stability measurement. Those would be
  stronger, currently unmeasured claims.
- This is a measurement script, not a `TESTING_STANDARD.md` correctness
  test — there's no single right answer to assert VERIFIED/FAILED
  against, which is why it isn't registered in a correspondence ledger
  or `test_all_engines.py`'s engine count.

## Files

- [`../ddpg_training_convergence_study.py`](../ddpg_training_convergence_study.py) — the script itself (supports `--seed N` to run one trial at a time, and `--report` to aggregate already-run results, since a full 8-seed run exceeds a single shell call's time budget in the environment this was built in).
- [`../ddpg_training_convergence_results.json`](../ddpg_training_convergence_results.json) — the raw per-seed results from the run reported above (JSON lines), committed so the numbers in this table are reproducible artifacts, not just prose.
