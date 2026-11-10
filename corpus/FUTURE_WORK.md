# Future Work

Ideas captured for later — not yet built, not yet scoped in detail.
Logged here rather than left to evaporate at the end of a conversation.
Entries are dated when added; move an entry to `LIBER_0.md` (with a real
build log) once actual work starts on it, rather than duplicating it in
both places indefinitely.

---

### 2026-08-01 — Sefirotic Reading Companion for *The Book of the New Sun* (Gene Wolfe)

**The idea:** Apply the Sephirot as a literary reading lens to Wolfe's
novel, either as (a) a real reading-companion document keyed to the
book's sections, structured as a Descent/Ascent arc (Geburah = the
Guild/Torturer chapters, Tiferet = the journey through Nessus, Chesed =
the movement toward the New Sun, a return-to-Keter framing for the
novel's circular structure), or (b) a graphic novel treatment — a
significantly bigger undertaking, since adapting Wolfe's text visually
would require real panel/page structure and a visual language per
Sefirah, not just annotation.

**Why it's a genuinely good fit, not a forced correspondence:** Wolfe's
unreliable narrator and the novel's cyclical structure (the ending
recontextualizes the beginning) suit this kind of lens better than most
novels would — this isn't the same risk profile as forcing a
correspondence onto code that has no natural fit (the caution already on
record in `SEPHIROTIC_MAPPING_ANALYSIS.md` re: Keter/initialization, and
in `engine_composition_loop_report.md` re: template wording secretly
encoding the expected answer).

**Real link, not an invented one:** the pasted proposal's "1=10
principle" callback for the novel's circularity is a genuine reference
to this repo's own `docs/fixed_point_closure_and_the_y_combinator.md`
(the fixed-point/Y-combinator equivalence, $F(S)=S$), not a fabricated
new claim — worth building on that existing, already-VERIFIED formal
grounding if this gets picked up, rather than re-deriving the metaphor
from scratch.

**Practical structure proposed** (from the pasted source, worth
preserving as a starting point): a "Sefirotic Log" kept while reading —
a Geburah log (moments of constraint/forced cruelty), a Chesed log
(moments of unplanned mercy), a Binah log (moments a "technical" truth
surfaces behind a "mythic" description) — with the claim that where
Geburah and Chesed logs reach equilibrium marks a Tifereth/epiphany
point in the text.

**Status:** Not started. Logged per the user's request rather than
built immediately, since this is genuinely a scope decision (reading
companion vs. graphic novel are very different undertakings) worth
deciding deliberately rather than defaulting into.

---

### 2026-08-01 — Properly-Scoped Goal-Conditioned Generalization Study for the DDPG Sandbox

**The idea:** `docs/ddpg_generalization_convergence_report.md` found that
the DDPG agent does NOT show significant learning under randomized
start/target altitudes (null result on both raw reward and a
task-difficulty-normalized closure_fraction metric), and that neither a
4× bigger training budget nor adding the target to the observation
(goal-conditioning) alone flipped this into a clean positive result —
but both of those were quick, informal 4-seed probes, not the full
pre-registered 8-seed/200-episode methodology the main study used.

**What's actually needed:** a proper follow-up combining ALL of: (1) the
goal-conditioned observation (fix `DDPGAgent`'s `state_dim` not actually
being threaded into `actor_l1`/`critic_l1` — currently hardcoded to 18,
a real, disclosed limitation surfaced while probing this), (2) a bigger
episode budget appropriate to the larger effective task space, and (3)
hyperparameters (`lr`, `tau`, batch size) actually retuned for the
harder randomized-target task rather than reused as-shipped from the
fixed-task engine — run at the full 8-seed methodology, not a 4-seed
probe, before drawing any confident conclusion either way.

**Status:** DONE — see the "Follow-up: the full 8-seed, pre-registered
goal-conditioned study" section added to
`docs/ddpg_generalization_convergence_report.md`. Result: goal-
conditioning moved the raw-reward metric meaningfully closer to
significance (6/8 seeds improved, p=0.14, vs. the null baseline's 4/8,
p=0.64) but not across the conventional 0.05 threshold; the
task-difficulty-normalized closure_fraction metric moved the OPPOSITE
direction. Traced the divergence to a real property of the reward
function itself (a flat "+10 per step at or above target" bonus that
rewards overshoot the same as precision), not a flaw in the fix.
Hyperparameters were deliberately NOT retuned (isolating the
goal-conditioning effect specifically), so that remains a real,
unexplored lever — see the new entry below.

---

### 2026-08-01 — Reward Shaping Fix for the Quadcopter Sandbox (new lead from the goal-conditioning follow-up)

**The idea:** The goal-conditioned follow-up above found raw reward and
closure_fraction diverging under training, most likely because
`QuadcopterTakeoffEnv.get_reward()`'s `+10.0` bonus applies on every step
at or above the target with no penalty for overshooting further past it.
A more honest reward shape would penalize distance from the target in
BOTH directions (e.g. replace the flat bonus with something like
`-0.01 * max(0, pose[2] - target_pos[2])`, an overshoot penalty
proportional to how far past the target the drone has gone, alongside
the existing undershoot penalty) so "hold precisely at the target" is
actually rewarded more than "blow past it and keep climbing."

**Why this is worth doing before further hyperparameter or budget
changes:** changing the reward function addresses a traced, disclosed
mechanism rather than throwing more compute at an already-partially-
understood gap — cheaper and more targeted than the "retune everything"
option logged above.

**Status:** DONE — implemented as a THIRD CORRECTION in
`ddpg_quadcopter_rca_engine.py` (the exact `0.01` coefficient proposed
above, fixed before re-running rather than tuned after), with new
hand-computed regression tests (`test_ddpg_quadcopter_rca_engine.py`,
36/36 passing), a break-it proof (reverting to the flat `+10.0` bonus
correctly fails 3 of the new checks), and an updated
`docs/ddpg_engine_kabbalistic_hand_verification.md`.

Re-ran the exact same 8-seed goal-conditioned study with only the reward
function changed: raw reward went from 6/8 seeds improved (p=0.14) to
3/8 (p=0.86); closure_fraction went from 2/8 improved (p=0.96) to 4/8
(p=0.64). Both metrics now sit near a coin flip instead of pointing in
opposite directions — the divergence this fix targeted is gone, but not
because a positive result emerged; the more likely reading is that the
pre-fix raw-reward signal was partly an artifact of the flat overshoot
bonus rather than genuine learning. See
`docs/ddpg_generalization_convergence_report.md`'s "Follow-up 3" section
for the full before/after table and honest discussion.

**New lead surfaced by this result:** retuning `lr`/`tau`/batch size for
the harder randomized-target task (still never attempted, deliberately
deferred across all three follow-ups to isolate one variable at a time)
is now the most clearly implicated untried lever, since both the
observation gap and the reward-shaping flaw have each been fixed in turn
without producing a positive training result on their own.

**UPDATE 2026-08-01 — the lead above was tried, and the underlying
question it answered turned out to be different than assumed.** See the
next entry below.

---

### 2026-08-01 — Hyperparameter Retuning (tried) + a Deeper Correction: the Reward/Closure Divergence Is Mostly a Task-Difficulty Artifact

**Status: DONE.** Retuned `lr` (0.01→0.005), `tau` (0.01→0.005), and
`batch_size` (16→64) together as one lever, chosen a priori (standard
DDPG stability heuristics for a harder/noisier task), and re-ran the
identical 8-seed/800-episode methodology. Null result, same as every
prior follow-up: raw reward 4/8 improved (p=0.64), closure_fraction 3/8
improved (p=0.86) -- the two metrics essentially swapped which one
looked closer to significant, neither meaningfully so.

**The more important finding came from writing that result up.** Checking
the per-seed SIGN relationship between the two metrics (not just each
one's own aggregate sign test) across all four 8-seed studies run so far
showed a near-perfect negative correlation in every single one (r =
-0.985, -0.958, -0.955, -0.935 -- barely moving across three different
fixes). A direct diagnostic -- 300 episodes with a completely UNTRAINED
agent, zero learning happening -- reproduced the same ~-0.98 correlation
from task-difficulty variation alone (`corr(initial_dist, reward) =
-0.98`, `corr(initial_dist, closure) = +0.96`). The two metrics are
built to move oppositely with randomized task difficulty, independent of
policy quality -- this was mostly what Follow-ups 2 and 3 were chasing,
not the goal-conditioning trade-off or the flat-bonus bug those follow-
ups (reasonably, given what had been checked at the time) proposed. Full
details: `docs/ddpg_generalization_convergence_report.md`'s "Follow-up 4"
and "Correction" sections; `LIBER_0.md`'s matching dated entry.

**Genuinely new, next lead:** every study in this entire thread has used
the same early/late sign-test methodology, which this correction shows
is confounded by per-seed task-difficulty sampling. A properly controlled
follow-up, not yet attempted, would need one of: (a) fixed difficulty
bins (e.g., re-run with `target_z` drawn from a small, fixed set of
values per bin rather than continuously, and compare within-bin), or
(b) a regression-adjusted metric (regress `closure_fraction` and/or raw
reward on `initial_dist` first, compare residuals early vs. late instead
of raw means). Neither has been built. This is the honest "is there
still a real, unconfounded generalization signal underneath all four
null-ish results so far" question -- still open.

**UPDATE 2026-08-01 — built and run.** See the next entry below; this
lead is now closed with a decisive (if not exciting) answer.

---

### 2026-08-01 — Follow-up 5: The Difficulty-Controlled Comparison (Closes This Thread's Open Lead)

**Status: DONE.** Built option (b) above --
`ddpg_difficulty_adjusted_convergence_study.py` logs per-episode
(`initial_dist`, reward, closure_fraction) for all 800 episodes/seed,
fits `metric ~ a + b*initial_dist` on the early window only, and compares
mean RESIDUALS (not raw means) late vs. early across the same 8 seeds.

Honesty check confirmed the adjustment does real work: early-window R²
averaged 0.968 (reward) and 0.923 (closure_fraction) across all 8 seeds
-- task difficulty explains the large majority of variance in both
metrics, at full statistical weight, not just in the smaller diagnostic
check from the entry above. After removing that confound: raw reward's
residual improvement was 4/8 seeds (p=0.64), closure_fraction's was 3/8
(p=0.86) -- both still indistinguishable from a coin flip.

**This is the most decisive result in the whole generalization thread,
not just another null one**: because the confound is now properly
regressed out rather than merely suspected, this result can be trusted
as a real "no" rather than an ambiguous one. It also means the goal-
conditioned study's 6/8-seeds/p=0.14 raw-reward reading (called "real
movement in the predicted direction" at the time) was very likely mostly
difficulty-sampling noise, not partial learning progress -- restated
honestly rather than quietly revised. Full details:
`docs/ddpg_generalization_convergence_report.md`'s "Follow-up 5" section;
`LIBER_0.md`'s matching dated entry.

**What's genuinely still open, if anyone wants to pick this back up**:
whether a substantially larger episode budget (well beyond 800/seed)
would produce a real generalization signal -- untested in this entire
five-follow-up thread, and the only lever not yet tried. Everything else
(observation gap, reward shaping, hyperparameters, the metric-confound
itself) has now been checked and, at this budget, doesn't explain a null
result that looks structural rather than a bug.
