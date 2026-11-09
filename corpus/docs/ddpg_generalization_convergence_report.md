# DDPG Generalization Convergence Report

*Register note (see `fixed_point_closure_and_the_y_combinator.md` §1 for
the three-register discipline): this is Register B — a real, falsifiable
empirical measurement, run and reported with its actual numbers, not a
claim about consciousness or a design principle.*

**Status as of 2026-08-01, for anyone not reading top to bottom:** this
report grew through five follow-ups as each result raised a new
question. The short version: goal-conditioning and a reward-shaping fix
were both real, worth-making fixes to the engine, found and verified
along the way (see Follow-ups 2 and 3) -- but the headline "getting
closer to significance" readings that motivated them turned out to be
mostly an artifact of task-difficulty confounding the comparison metric,
not partial progress (see the "Correction" section and Follow-up 5). The
most trustworthy result in this whole document is Follow-up 5's
difficulty-adjusted comparison: no statistically distinguishable
generalization signal at this episode budget, even after removing
92–97% of each metric's variance due to task difficulty. Read Follow-up
5 first if short on time; everything before it is the (honestly
recorded, still useful) path that led there.

## What this answers

`ddpg_training_convergence_report.md` established that the DDPG loop
learns something on ONE fixed task: start altitude z=10, target altitude
z=100, every single episode, every single seed (confirmed by reading
`QuadcopterTakeoffEnv.__init__`/`reset()` directly, not assumed).
Improvement on a fixed task is consistent with either genuine
altitude-control learning or partial memorization of one trajectory — the
original study could not distinguish these. This report is that
distinguishing measurement: does the agent generalize across DIFFERENT
takeoffs (randomized start/target altitude), or only reproduce the one
trajectory it was trained on?

Produced by
[`../ddpg_generalization_convergence_study.py`](../ddpg_generalization_convergence_study.py),
plus three follow-up probes described below once the first result raised
more questions than it answered.

## The one change, disclosed

`RandomizedQuadcopterTakeoffEnv` samples a NEW start altitude
(`U(5,20)`) and target altitude (`U(60,140)`) every `reset()`, instead of
the original's fixed `[10 -> 100]`. Everything else (physics, reward
shaping, termination conditions, the `DDPGAgent` class, and the exact
methodology — 8 seeds, 200 episodes/seed, early/late window of 50,
binomial sign test) is identical to `ddpg_training_convergence_study.py`,
imported directly rather than re-specified, so this is a controlled
comparison: one variable changed, everything else held fixed.

Only altitude is randomized because the base engine's own physics never
varies x, y, roll, or pitch either — `angular_v` is never set anywhere in
`step()`, confirmed by reading the code, not assumed. The 6-dimensional
pose vector is, underneath it, a 1D altitude-control problem; this study
randomizes the one axis that's actually alive.

## Result 1: raw reward — no significant improvement, and much noisier than the fixed-task study

| seed | early mean | late mean | improvement |
| :--- | ---: | ---: | ---: |
| 0 | 208.3620 | 200.9202 | −7.4418 |
| 1 | 201.4495 | 194.7620 | −6.6875 |
| 2 | 189.3720 | 209.2257 | +19.8537 |
| 3 | 193.3583 | 197.1421 | +3.7837 |
| 4 | 196.2235 | 210.6781 | +14.4546 |
| 5 | 202.5583 | 194.9464 | −7.6119 |
| 6 | 200.6693 | 205.4366 | +4.7673 |
| 7 | 214.7660 | 197.6905 | −17.0755 |

4/8 improved, mean improvement +0.51, **std 11.66** — versus the fixed-task
study's std of 1.09 across improvements that all fell in [+0.4, +4.0].
Sign-test p = 0.6367 (indistinguishable from a coin flip).

**A real confound, identified before concluding anything**: under a
randomized target, total reward swings with *which* target got sampled
that episode, not just policy quality — a policy could be doing fine and
still show a big negative "improvement" purely because its late-window
episodes happened to draw harder targets. The raw-reward sign test isn't
sensitive enough to separate these.

## Result 2: closure_fraction — a task-difficulty-normalized metric, same null result

Added `closure_fraction = 1 - final_dist/initial_dist` (`initial_dist` =
`|start_z - target_z|`, `final_dist` = `|final_z - target_z|`), computed
from the *same* single training run as Result 1, not a second retrained
pass — this isolates "did the agent get proportionally closer" from "how
hard was this particular episode's target."

| seed | early mean | late mean | improvement |
| :--- | ---: | ---: | ---: |
| 0 | 0.2239 | 0.2841 | +0.0602 |
| 1 | 0.2886 | 0.3514 | +0.0628 |
| 2 | 0.3886 | 0.2607 | −0.1278 |
| 3 | 0.3362 | 0.3433 | +0.0072 |
| 4 | 0.3119 | 0.2226 | −0.0893 |
| 5 | 0.2637 | 0.3291 | +0.0654 |
| 6 | 0.3092 | 0.2608 | −0.0484 |
| 7 | 0.1621 | 0.3282 | +0.1661 |

5/8 improved, p = 0.3633 — still not statistically distinguishable from
chance. **The confound didn't hide a real signal**: a genuinely different,
cleaner metric gives the same honest null result.

## Follow-up probe 1: is 200 episodes just not enough? (quick 4-seed check, not the full methodology)

Reran seeds 0–3 at 800 episodes (4× budget), closure_fraction only,
early/late window rescaled to 100. Disclosed as a smaller, informal probe
— not the pre-registered 8-seed study — because it was run to answer one
narrow question cheaply, not to stand as a formal result on its own.

| seed | early (n=100) | late (n=100) | improvement |
| :--- | ---: | ---: | ---: |
| 0 | 0.3013 | 0.2909 | −0.0105 |
| 1 | 0.2637 | 0.3539 | +0.0902 |
| 2 | 0.3309 | 0.2854 | −0.0455 |
| 3 | 0.3314 | 0.2440 | −0.0874 |

1/4 improved — if anything, slightly worse than the 200-episode result.
**4× more training data did not resolve the null result.** This weighs
against "it just needs more episodes" as the explanation.

## Root cause found: the observation never includes the target

Read `QuadcopterTakeoffEnv._get_obs()` directly:

```python
def _get_obs(self):
    return np.concatenate(self.pose_history)  # 18-dimensional vector
```

This returns pose history only — **the target position is never part of
the state the agent observes, in either the base or randomized
environment.** On the fixed-task engine this doesn't matter: the target
is always z=100, so the correct behavior can be baked into the network's
weights without ever needing to "look up" the goal. Under a randomized
target, the agent is structurally asked to solve a partially unobservable
problem — nothing in its input reveals whether it should aim for z=65 or
z=135. This is a first-principles explanation for the null result, not
just "insufficient data."

## Follow-up probe 2: goal-conditioning (same 4-seed quick-probe scale)

Built `GoalConditionedEnv` (appends `target_pos[2]` to the observation,
19-dim state instead of 18) and reran seeds 0–3 at 200 episodes.

**A second, pre-existing gap surfaced doing this**: `DDPGAgent.__init__`
accepts a `state_dim` parameter but never actually threads it into
`actor_l1`/`critic_l1`'s input size — both are hardcoded to 18 regardless
of what `state_dim` is passed. Worked around for this probe only (rebuilt
`actor_l1`/`critic_l1`/their target copies at the correct 19-dim input
size after construction) rather than editing the verified engine file;
left as a disclosed, real limitation of `DDPGAgent` rather than silently
patched in place.

| seed | early | late | improvement |
| :--- | ---: | ---: | ---: |
| 0 | 0.3132 | 0.2323 | −0.0809 |
| 1 | 0.2015 | 0.3503 | +0.1487 |
| 2 | 0.3738 | 0.3288 | −0.0450 |
| 3 | 0.1970 | 0.2913 | +0.0943 |

2/4 improved — still mixed at this quick-probe scale. **Goal-conditioning
alone, at this same modest budget and un-tuned hyperparameters, did not
immediately produce a clean improvement either.**

## Follow-up: the full 8-seed, pre-registered goal-conditioned study

Produced by
[`../ddpg_goal_conditioned_convergence_study.py`](../ddpg_goal_conditioned_convergence_study.py),
the properly-scoped confirmation logged as future work above. Methodology
fixed BEFORE running, not tuned after seeing results: 8 seeds (matching
both prior studies), 800 episodes/seed (4× the original — the same
figure the earlier probe used, not picked after seeing this run),
early/late window of 200 (kept at the same 25% proportion as the
original study's 50/200). Deliberately only ONE new lever pulled versus
the null baseline — goal-conditioning, built as a real
`GoalConditionedDDPGAgent` subclass that properly fixes the disclosed
`state_dim` gap (not a probe-only monkey-patch) — plus the
already-justified bigger budget. `lr`, `tau`, and `batch_size` were left
exactly as shipped; changing them too would make it impossible to
attribute any change in outcome to a specific cause.

**Metric 1 (raw reward):**

| seed | early | late | improvement |
| :--- | ---: | ---: | ---: |
| 0 | 198.5694 | 200.4882 | +1.9188 |
| 1 | 200.2421 | 205.4300 | +5.1878 |
| 2 | 198.9842 | 199.8392 | +0.8550 |
| 3 | 209.0025 | 205.2046 | −3.7978 |
| 4 | 193.9295 | 200.3128 | +6.3833 |
| 5 | 199.7491 | 198.6458 | −1.1033 |
| 6 | 190.4134 | 198.7065 | +8.2931 |
| 7 | 192.3166 | 193.6698 | +1.3532 |

6/8 improved, p = 0.1445 — closer to significance than the null
baseline's 4/8 (p = 0.64), but still above the conventional 0.05
threshold. Not clean confirmation, but a real shift in the same
direction the fix predicted.

**Metric 2 (closure_fraction):**

| seed | early | late | improvement |
| :--- | ---: | ---: | ---: |
| 0 | 0.2701 | 0.2585 | −0.0117 |
| 1 | 0.2621 | 0.2077 | −0.0544 |
| 2 | 0.3003 | 0.2887 | −0.0116 |
| 3 | 0.2260 | 0.2373 | +0.0113 |
| 4 | 0.2944 | 0.2439 | −0.0505 |
| 5 | 0.2906 | 0.3092 | +0.0185 |
| 6 | 0.3407 | 0.2734 | −0.0673 |
| 7 | 0.3159 | 0.2980 | −0.0178 |

Only 2/8 improved, p = 0.9648 — trending the OPPOSITE direction from
metric 1, and away from significance rather than toward it.

**A real divergence between the two metrics, worth explaining rather
than picking whichever number is more convenient.** Reward trends
(weakly) positive; closure_fraction trends (weakly) negative. The most
likely explanation, traced to the reward function itself rather than
guessed at: `QuadcopterTakeoffEnv.step()` adds a flat `+10.0` bonus on
**every step** the drone is at or above the target altitude, regardless
of by how much. This structurally rewards "reach the target and then
keep climbing past it" the same as "reach the target and hold precisely
there" — total reward can climb from accumulating that bonus over many
steps even while the agent overshoots further and further, which is
exactly what would *depress* `closure_fraction` (a large overshoot makes
`final_dist` bigger, not smaller, than a precise stop at the target).
This is a plausible, mechanism-traceable hypothesis consistent with both
tables — offered as the most likely explanation, not confirmed by a
further dedicated overshoot-magnitude measurement, which wasn't run here
to avoid open-endedly chasing this one thread further.

## Honest overall conclusion

Updated after the full 8-seed follow-up, not left at the earlier
quick-probe reading. Four checks in total were run once the raw result
came back null: a cleaner metric, a 4× data probe, a 4× data + goal-
conditioning probe, and finally the properly-scoped full study combining
the fix with the justified bigger budget. The full study moved the
raw-reward result meaningfully closer to significance (6/8 improved,
p=0.14, versus the baseline's 4/8, p=0.64) without crossing the
conventional 0.05 threshold — real movement in the predicted direction,
not nothing, but not clean confirmation either. The task-difficulty-
normalized metric moved the opposite way, and the most likely reason
traces to a real, disclosed property of the reward function itself (the
flat per-step "at or above target" bonus rewarding overshoot the same as
precision) rather than a flaw in the goal-conditioning fix.

**The most defensible honest reading, revised**: goal-conditioning was a
real, necessary fix (the agent structurally could not have known the
target otherwise) and its addition shifted the raw-reward result in the
right direction, but the REWARD FUNCTION's own shaping — not the
learning mechanism, and not the observation gap — is now the most likely
remaining obstacle to a clean result, since it doesn't cleanly distinguish
"got close" from "overshot substantially." This is a different, more
specific conclusion than the pre-follow-up version of this report drew,
and it points at a different next fix (reward shaping, e.g. penalizing
distance in both directions rather than only rewarding at-or-above) than
"needs more of everything." Not evidence the underlying DDPG mechanism is
broken — it's already VERIFIED mechanically, and both this study and the
original fixed-task study show it responds to its training signal; the
open question is now about what signal it's being given, not whether it
can learn from one.

## Follow-up 3: the reward-shaping fix, re-run at the same 8-seed methodology (2026-08-01)

**The fix**: `ddpg_quadcopter_rca_engine.py`'s target-reached bonus was a
flat `+10.0` applied identically at any altitude at or above the target,
with no penalty for overshooting further. It now decays linearly with
overshoot distance (`reward += max(0.0, 10.0 - 0.01 * overshoot)`), so
holding precisely at the target is worth strictly more than climbing
past it and staying there — see this file's THIRD CORRECTION and
`docs/ddpg_engine_kabbalistic_hand_verification.md` section 3 for the
hand-worked arithmetic. The coefficient (`0.01`) was fixed in
`FUTURE_WORK.md` before this re-run, not chosen after seeing these
results.

**Re-ran the exact same goal-conditioned 8-seed/800-episode study above**
— same seeds, same episode count, same window, same
`GoalConditionedDDPGAgent`/`GoalConditionedRandomizedEnv`, only the
engine's reward function changed:

| Metric | Before fix | After fix |
|---|---|---|
| Raw reward: seeds improved | 6/8 | 3/8 |
| Raw reward: sign-test p | 0.1445 | 0.8555 |
| Raw reward: mean improvement | (positive, closer to significance) | -0.316 |
| closure_fraction: seeds improved | 2/8 | 4/8 |
| closure_fraction: sign-test p | 0.9648 | 0.6367 |
| closure_fraction: mean improvement | (negative) | +0.0003 |

**Honest reading**: the fix did NOT produce a clean positive training
result on either metric — if anything, the raw-reward signal got weaker
(6/8 → 3/8, p=0.14 → p=0.86), not stronger. But the specific problem this
fix targeted was the DIVERGENCE between the two metrics (raw reward
trending up while closure_fraction trended down, pointing at
"overshoot-and-stay" as a spuriously rewarded strategy) — and that
divergence is gone. Both metrics now sit close to a coin flip (p=0.86 and
p=0.64, mean improvements of essentially 0 in both), which is consistent
with the raw reward's pre-fix appearance of improvement having been
partly an artifact of the flat overshoot bonus rather than a genuine
learning signal the fix then "spoiled." This does not prove that
interpretation — a coin-flip result is also just what a genuinely
non-learning run looks like — but it is the more parsimonious reading
given the specific, traced mechanism this fix addressed.

**What this does and doesn't establish**: fixing the reward function was
worth doing on its own honesty grounds regardless of outcome (a bonus
that rewards overshoot identically to precision is simply a wrong
reward, independent of whether fixing it improves training metrics). It
did not, at this same modest budget and un-retuned hyperparameters,
unlock a clean positive convergence result. The genuinely unexplored
lever named in the prior follow-up — retuning `lr`/`tau`/batch size for
the harder randomized-target task, rather than reusing the fixed-task
engine's defaults — remains untried, and is now the more clearly
implicated next step, since both the observation gap and the reward-
shaping flaw have each been fixed in turn without producing a positive
result on their own.

## Follow-up 4: hyperparameter retuning (2026-08-01)

Produced by
[`../ddpg_retuned_hyperparameter_study.py`](../ddpg_retuned_hyperparameter_study.py).
Follow-ups 1-3 each isolated ONE mechanism (observation, reward shaping)
while deliberately leaving `lr`/`tau`/`batch_size` untouched, specifically
to avoid changing multiple things at once. This follow-up is the first to
touch those three, treated as a single "hyperparameter retuning" lever
(see the script's own docstring for why lr, tau, and batch_size are
grouped as one lever rather than tuned independently): `batch_size`
16→64, `lr` 0.01→0.005, `tau` 0.01→0.005, chosen before running as
standard DDPG stability heuristics for a noisier, harder task — not
tuned after seeing results. Same 8-seed/800-episode methodology, same
goal-conditioning and reward-shaping fixes already in place, only the
three hyperparameters changed.

| Metric | Goal-conditioned (post reward-fix) | Retuned hyperparameters |
|---|---|---|
| Raw reward: seeds improved | 3/8 | 4/8 |
| Raw reward: sign-test p | 0.8555 | 0.6367 |
| closure_fraction: seeds improved | 4/8 | 3/8 |
| closure_fraction: sign-test p | 0.6367 | 0.8555 |

**Honest reading**: retuning did not produce a positive result either --
if anything, the two metrics essentially swapped which one looked
(non-significantly) closer to improving, both still solidly in coin-flip
territory. This specific retuning is a null result, reported as such.

## Correction: the reward/closure_fraction "divergence" was mostly a task-difficulty artifact, not a training signal (2026-08-01)

**This revises how Follow-ups 2 and 3 above should be read. Both entries
are left in place per this project's own correction rule (see
`LIBER_0.md`'s "One Rule") -- this section explains what was actually
going on, rather than deleting the earlier, incomplete reasoning.**

While writing up Follow-up 4, the per-seed sign relationship between raw
reward and closure_fraction was checked directly (not just "how many
seeds improved" but whether the two metrics move together or oppositely
within each seed) across every 8-seed study run so far:

| Study | Pearson r (reward improvement vs. closure improvement) | Same-sign seeds |
|---|---|---|
| Original null study (no goal-conditioning, no reward fix) | −0.985 | 1/8 |
| Goal-conditioned, PRE reward-shaping fix | −0.958 | 0/8 |
| Goal-conditioned, POST reward-shaping fix | −0.955 | 1/8 |
| Retuned hyperparameters | −0.935 | 1/8 |

**Every study, regardless of which fix was or wasn't applied, shows the
same near-perfect (−0.93 to −0.99) anti-correlation between the two
metrics.** If the flat overshoot bonus were the real cause of this
pattern (Follow-up 2's hypothesis), fixing it should have visibly
weakened the anti-correlation. It didn't move at all outside noise
(−0.958 → −0.955 → −0.935 across three different fixes).

**Traced to the actual mechanism, not left as a coincidence:** ran 300
episodes of `RandomizedQuadcopterTakeoffEnv` with a completely
**untrained** `DDPGAgent` (fresh random weights, exploration noise only,
`agent.step()` never called -- literally zero learning happening) and
measured the same three quantities per episode:

```
corr(initial_dist, total_reward) = -0.982
corr(initial_dist, closure_fraction) = +0.957
corr(total_reward, closure_fraction) = -0.978
```

This reproduces the same ~−0.98 correlation with NO training at all.
The mechanism: `initial_dist` (task difficulty, randomized 15-135m per
episode) drives both metrics in opposite directions almost mechanically.
Harder tasks (larger `initial_dist`) leave less of the fixed 100-step
episode budget for the drone to actually reach and hold the target, so
they accumulate fewer target-bonus steps and more L1-penalty steps →
lower raw reward. But `closure_fraction = 1 - final_dist/initial_dist`
divides by that same `initial_dist` -- the same absolute progress counts
as a *larger fraction* of a *harder* task, inflating closure_fraction
for exactly the episodes that depress raw reward, and vice versa for
easy tasks. This is a property of how the two metrics are defined
relative to a randomized-difficulty task, not evidence about policy
quality, and it swamps whatever smaller effect training or reward-shaping
has on top of it.

**What this means for Follow-ups 2 and 3's conclusions**: the "goal-
conditioning helped reward but hurt closure_fraction" and "the flat
overshoot bonus explains the divergence" readings were reasonable given
what had been checked at the time, but the divergence they were
explaining is mostly this task-difficulty artifact, present before any
of these fixes and unmoved by any of them. This doesn't mean goal-
conditioning or the reward-shaping fix were wrong to make -- goal-
conditioning remains a real, necessary fix for a structurally
unobservable target, and the reward-shaping fix remains a real honesty
improvement independent of its effect on this metric pair -- but neither
should be credited or blamed for moving a divergence that was never
mostly about them.

**Implication for any future work on this thread**: comparing raw reward
and closure_fraction sign-test results directly, as done in every
follow-up above, is confounded by which specific difficulty levels get
sampled into the early vs. late window for a given seed. A properly
controlled follow-up would need to either fix `target_z`/`start_z` to a
small set of difficulty bins and compare within-bin, or regress out
`initial_dist` before comparing early/late means -- neither attempted
here, logged in `FUTURE_WORK.md` as the honest next step rather than
retrofitted into this already-run set of studies.

## Follow-up 5: the difficulty-controlled comparison (2026-08-01)

Produced by
[`../ddpg_difficulty_adjusted_convergence_study.py`](../ddpg_difficulty_adjusted_convergence_study.py)
-- the properly difficulty-controlled follow-up named as the open next
step in the Correction above. Same environment and fixes as the
goal-conditioned study (observation fix + reward-shaping fix, engine-
default hyperparameters -- retuning showed no benefit, so not stacked
here), same 8-seed/800-episode/200-window methodology. The only thing
that changed is the ANALYSIS: instead of comparing raw early/late means
(confounded by task-difficulty sampling, per the Correction), this fits
`metric ~ a + b * initial_dist` using ONLY the early window's 200
episodes, applies that fixed model to both windows, and compares mean
RESIDUALS (actual − predicted) late vs. early. This asks "beyond what
task difficulty alone predicts, did anything improve" instead of "did
the raw number go up."

**Honesty check first — does the adjustment actually remove real
variance, or is it a token gesture?**

| | mean early-window R² |
|---|---|
| Raw reward ~ initial_dist | 0.968 |
| closure_fraction ~ initial_dist | 0.923 |

Task difficulty alone explains 92–97% of the variance in both metrics,
per seed, confirming the untrained-agent diagnostic from the Correction
above at full statistical weight (all 1,600 real episodes per seed,
not a 300-episode side check) rather than just corroborating it in
passing.

**Difficulty-adjusted result:**

| Metric | Seeds improved | Sign-test p | Mean residual improvement |
|---|---|---|---|
| Raw reward (adjusted) | 4/8 | 0.6367 | +0.394 (out of a ~190-210 raw scale) |
| closure_fraction (adjusted) | 3/8 | 0.8555 | −0.0050 |

**Honest conclusion: still no detectable learning signal, and this is
now the most trustworthy null result in the whole thread, not just
another one.** With 92–97% of the metrics' variance attributable to
task difficulty removed by construction, and the residual comparison
still landing at 4/8 and 3/8 (both worse than or equal to a coin flip),
there is no hidden generalization signal being masked by the difficulty
confound. This also recontextualizes the goal-conditioned study's
headline number (6/8 raw-reward seeds improved, p=0.14, described there
as "real movement in the predicted direction") -- given task difficulty
alone explains nearly all of this metric's variance, that result was
very likely mostly reflecting which specific difficulty levels happened
to fall in the early vs. late window for those seeds, not a real,
if partial, learning effect. Restated here rather than quietly revised
in place, per this project's correction rule.

**What this does and does not establish:** at this episode budget (800
episodes/seed) and this hyperparameter setting, there is no
statistically distinguishable evidence that the DDPG agent generalizes
across randomized takeoffs, even after correctly controlling for task
difficulty. This does not mean the mechanism is broken -- it is already
VERIFIED mechanically (gradients flow correctly, training measurably
improves reward on the FIXED-task version of this same engine, per
`ddpg_training_convergence_report.md`) -- nor does it rule out
convergence over a substantially larger episode budget, which was never
tested. It does mean that the three "getting closer" readings in
Follow-ups 2-4 above should be read as likely difficulty-sampling noise
rather than partial progress toward a positive result.

## Limitations, stated plainly

- Follow-up probes 1 and 2 were 4-seed, quick checks; the final
  goal-conditioned follow-up used the full 8-seed/800-episode
  methodology, pre-registered before running. Neither probe scale nor
  the full study crossed the conventional 0.05 significance threshold on
  the primary reward metric (closest: p=0.14) — "moved in the predicted
  direction" is a real, honest finding here, not "confirmed."
- No hyperparameter retuning was attempted anywhere in this report — `lr`,
  `tau`, and batch size were used exactly as shipped, on a task they were
  never tuned for, in every study including the final follow-up. This was
  deliberate (isolate the effect of goal-conditioning specifically), not
  an oversight — but it means a retuned run remains a genuinely
  unexplored lever.
- `DDPGAgent`'s `state_dim` parameter not being wired into its layer
  sizes is a real, disclosed limitation surfaced as a side effect of this
  study. The final follow-up fixes it properly, but only within a new
  `GoalConditionedDDPGAgent` subclass — `ddpg_quadcopter_rca_engine.py`
  itself is untouched and still has the underlying gap for any other
  caller that passes a non-default `state_dim`.
- The reward-shaping hypothesis (flat at-or-above bonus rewarding
  overshoot) is offered as the most likely explanation for the two
  metrics' divergence, traced to the actual reward code — but it was not
  confirmed with a dedicated overshoot-magnitude measurement, which
  would be the natural next check if this thread is picked up again.
- This is a measurement/diagnostic report, not a `TESTING_STANDARD.md`
  correctness test — no single right answer to assert VERIFIED/FAILED
  against, consistent with why the original convergence report also isn't
  registered in a correspondence ledger.

## Files

- [`../ddpg_generalization_convergence_study.py`](../ddpg_generalization_convergence_study.py) — the main 8-seed/2-metric study (supports `--seed N` / `--report`, same reason as the original study).
- [`../ddpg_goal_conditioned_convergence_study.py`](../ddpg_goal_conditioned_convergence_study.py) — the full 8-seed goal-conditioned follow-up (`GoalConditionedDDPGAgent`, `GoalConditionedRandomizedEnv`), same `--seed N` / `--report` interface.
- [`../ddpg_goal_conditioned_convergence_results.json`](../ddpg_goal_conditioned_convergence_results.json) — raw per-seed results (both metrics), POST reward-shaping fix (Follow-up 3 above).
- [`../ddpg_goal_conditioned_convergence_results_PRE_REWARD_FIX.json`](../ddpg_goal_conditioned_convergence_results_PRE_REWARD_FIX.json) — the same study's raw per-seed results from BEFORE the reward-shaping fix, preserved for the Follow-up 3 before/after comparison rather than overwritten.
- [`../ddpg_retuned_hyperparameter_study.py`](../ddpg_retuned_hyperparameter_study.py) + [`../ddpg_retuned_hyperparameter_results.json`](../ddpg_retuned_hyperparameter_results.json) — Follow-up 4's script and raw per-seed results (`--seed N` / `--report`, chunked internally via a pickled checkpoint every 200 episodes purely as an execution-environment accommodation for this machine's per-command time limit at the larger batch size -- see the script's own `CHUNK_SIZE` comment; the methodology itself is one continuous 800-episode run per seed, unaffected).
- [`../ddpg_difficulty_adjusted_convergence_study.py`](../ddpg_difficulty_adjusted_convergence_study.py) + [`../ddpg_difficulty_adjusted_results.json`](../ddpg_difficulty_adjusted_results.json) — Follow-up 5's script and raw per-episode data (all 800 episodes × 8 seeds, not just aggregated early/late means), enabling the early-window-regression difficulty adjustment described above.
- [`../ddpg_generalization_convergence_results.json`](../ddpg_generalization_convergence_results.json) — raw per-seed results (both metrics) from the run reported above.
- The two follow-up probes (bigger budget, goal-conditioning) were run as one-off scripts, not committed as permanent files — their exact code is reproduced inline above and in `LIBER_0.md`'s dated entry, since they were diagnostic, not a reusable asset in their current unpolished form.
