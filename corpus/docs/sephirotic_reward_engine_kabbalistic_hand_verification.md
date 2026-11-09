# Hand-Verifying `sephirotic_reward_engine.py`

Unlike the attractor engine, this module's Sephirotic correspondence isn't
an added lens — it's the engine's own stated design (see its module
docstring and `SEPHIROTIC_MAPPING_ANALYSIS.md`). Chesed (expansion) and
Geburah (restriction) are computed independently, then reconciled by
Tifereth. This document just shows the arithmetic is exactly what the
names claim, with numbers you can check on a calculator.

Register note (per the discipline established in
`fixed_point_closure_and_the_y_combinator.md`): this is a **design
principle claim**, stated explicitly in the module's own docstring — not
a performance claim. Structuring a reward this way is not claimed to
train better than an unstructured one; that's a separate empirical
question this module doesn't answer.

---

## 1. Chesed — the Expansion Term

```
chesed = ||velocity|| + max(0, altitude_gain)
```

**By hand**: velocity `(3, 4, 0)` m/s, altitude_gain `2.0` m.
```
||velocity|| = √(3² + 4² + 0²) = √25 = 5
chesed = 5 + max(0, 2.0) = 7.0
```
Structural claim being checked: this term must rise with more energetic,
exploratory motion, and must be blind to instability — there is no
angular-velocity or crash term anywhere in this formula. You can confirm
that by inspection: nothing here can go down because the craft is
unstable.

## 2. Geburah — the Restriction Term

```
geburah = ||angular_velocity|| + (100 if crashed else 0) + max(0, constraint_violation)
```

**By hand**, stable case: angular_velocity `(0.1, 0.2, 0.1)` rad/s, not
crashed, no constraint violation.
```
||angular_velocity|| = √(0.01 + 0.04 + 0.01) = √0.06 ≈ 0.245
geburah = 0.245 + 0 + 0 ≈ 0.245
```
**By hand**, crashed case, same angular velocity:
```
geburah = 0.245 + 100 + 0 = 100.245
```
The `100.0` crash penalty is a hard constant, not scaled by anything else
in the formula — one crash outweighs any plausible instability reading.

## 3. Tifereth — the Reconciliation

```
tifereth = (chesed_weight × chesed) − (geburah_weight × geburah)
```
Default weights are both `1.0`.

**By hand**, stable case (from above): `tifereth = 7.0 − 0.245 = 6.755`.
Exploration dominates — the craft moved fast and climbed, without
instability, so the combined score is strongly positive.

**By hand**, crashed case, same chesed: `tifereth = 7.0 − 100.245 = −93.245`.
Restriction dominates completely — no amount of speed or altitude gain in
this formula can outweigh a single crash, because the penalty (100) is an
order of magnitude larger than any realistic chesed value. This is the
concrete arithmetic behind the module's stated claim that "a crash should
dominate any amount of exploration" — you can verify it by picking your
own chesed value and confirming it would need to exceed 100 (an
essentially impossible combination of speed and altitude gain in one
step) before the crash penalty stops dominating.

## 4. What This Does and Doesn't Establish

Confirms, by hand: Chesed only responds to motion/altitude terms, Geburah
only responds to instability/crash/violation terms, and Tifereth is a
genuine difference (not a fixed blend) where either side can dominate
depending on the inputs. Does not establish, and doesn't claim to, that
this reward structure produces better-trained policies than an
unstructured reward — that would require actual training runs and is out
of scope here, exactly as the module's own docstring says.

---

## Provenance

Extends the hand-verification pattern established in
`attractor_engine_kabbalistic_hand_verification.md`, applied to an engine
whose Sephirotic structure was original to its own design rather than
added as a lens afterward.
