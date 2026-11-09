#!/usr/bin/env python3
"""
sephirotic_reward_engine.py
Reward shaping for the quadcopter RL controller, structured around the
Sephirotic correspondences that survived structural analysis (not the
full 10 -- only the ones with a genuine structural match, see
SEPHIROTIC_MAPPING_ANALYSIS.md for the reasoning and the pairs that were
deliberately excluded as too weak: Keter/initialization was dropped).

THE ACTUAL CLAIM BEING MADE (stated explicitly, not left implicit):
This reward function is structured as an explicit balance between an
EXPANSION term (Chesed: rewards exploratory, energetic, ambitious flight
behavior) and a RESTRICTION term (Geburah: penalizes instability, crashes,
constraint violations), reconciled into a single scalar (Tifereth) via a
weighted combination -- rather than the manual's original flat, unstructured
"positive for altitude, negative for energy" formula, which had no
organizing structure at all.

THIS IS A DESIGN PRINCIPLE CLAIM, NOT A PERFORMANCE CLAIM.
Structuring a reward this way does NOT automatically train better than an
unstructured reward -- that is a separate, empirical question this module
does not claim to answer. What this module claims, and what its test suite
checks, is narrower and falsifiable: that the Chesed term actually behaves
like an expansion term (increases with exploratory/energetic behavior,
independent of the Geburah term), that the Geburah term actually behaves
like a restriction term (increases with instability, independent of the
Chesed term), and that Tifereth is genuinely their reconciliation (moves
toward whichever term dominates, not a fixed blend that ignores both).

License: CC BY-SA 4.0
"""

import numpy as np


class SephiroticRewardComponents:
    """
    Computes the two independent reward sub-terms (Chesed, Geburah) and
    their Tifereth reconciliation for one simulation step.

    Binah (the clip) and Malkuth (the executed action) are NOT reward
    terms -- per the mapping analysis, they correspond to the action
    bounding step and the physical output itself, which live in the
    policy/environment, not in the reward function. Including them here
    as reward terms would be exactly the kind of forced-symmetry error
    the mapping analysis flagged (Keter) -- not everything needs a reward
    term just because it has a Sephirotic label.
    """

    def __init__(self, chesed_weight: float = 1.0, geburah_weight: float = 1.0):
        if chesed_weight < 0 or geburah_weight < 0:
            raise ValueError("Weights must be non-negative")
        self.chesed_weight = chesed_weight
        self.geburah_weight = geburah_weight

    def chesed_expansion_term(self, velocity: np.ndarray, altitude_gain: float) -> float:
        """
        EXPANSION term. Structural claim: this must increase monotonically
        with more energetic/exploratory motion (higher speed, more altitude
        gained), and must NOT depend on stability/instability at all --
        it is purely "how much is being explored/attempted," independent
        of whether that attempt is safe.
        """
        speed = float(np.linalg.norm(velocity))
        return speed + max(0.0, altitude_gain)

    def geburah_restriction_term(self, angular_velocity: np.ndarray,
                                   is_crashed: bool,
                                   constraint_violation: float) -> float:
        """
        RESTRICTION term. Structural claim: this must increase with
        instability (angular velocity magnitude = spinning/tumbling),
        crashes, and constraint violations, and must NOT depend on how
        much altitude was gained or how fast the craft is moving in a
        controlled way -- it is purely "how much is going wrong,"
        independent of ambition.
        """
        instability = float(np.linalg.norm(angular_velocity))
        crash_penalty = 100.0 if is_crashed else 0.0
        return instability + crash_penalty + max(0.0, constraint_violation)

    def tifereth_reconciliation(self, chesed_value: float, geburah_value: float) -> float:
        """
        RECONCILIATION. Structural claim: this must be a genuine balance,
        not a fixed blend that's insensitive to one side -- meaning if
        Geburah (restriction) dominates, the combined score must trend
        negative/low even if Chesed (expansion) is high, and vice versa.
        A "reconciliation" that always just returns, say, a constant
        regardless of the inputs would fail this claim; a fixed 50/50
        average that never lets restriction override expansion in extreme
        cases would also weakly fail it (a crash should dominate any
        amount of exploration).
        """
        return (self.chesed_weight * chesed_value) - (self.geburah_weight * geburah_value)

    def compute_reward(self, velocity, altitude_gain, angular_velocity,
                        is_crashed, constraint_violation):
        """Full step reward: Chesed and Geburah computed independently, then reconciled."""
        chesed = self.chesed_expansion_term(velocity, altitude_gain)
        geburah = self.geburah_restriction_term(angular_velocity, is_crashed, constraint_violation)
        tifereth = self.tifereth_reconciliation(chesed, geburah)
        return {
            "chesed_expansion": chesed,
            "geburah_restriction": geburah,
            "tifereth_reward": tifereth,
        }
