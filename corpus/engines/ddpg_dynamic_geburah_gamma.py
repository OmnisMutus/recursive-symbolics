#!/usr/bin/env python3
"""
ddpg_dynamic_geburah_gamma.py

Applies the RCA framework's own Geburah directivity mechanism to
ddpg_quadcopter_rca_engine.py for real, rather than leaving it as the
fixed constant `MAX_GAMMA_CAP = 0.85` the engine has used since it was
written.

BACKGROUND: the entropy-based "directive strength gamma" formula --
softmax over some logits, normalized Shannon entropy, `gamma = clip(1 -
h_norm, 0, 0.85)` -- already exists as THREE independent implementations
elsewhere in this project:
  - `standalone_rca_sandbox.py`'s `compute_gamma()` (text-frequency
    version, over token counts)
  - `Recursive-Symbolics/tools/delta_operator.py`'s `compute_gamma()`
    (NumPy, over arbitrary logits)
  - `Recursive-Symbolics/tools/agency_budget.py`'s `compute_gamma()`
    (pure Python, cross-checked against delta_operator's to 9 decimal
    places)
In every one of those three, gamma is a STANDALONE reported number (a
confidence/restriction score attached to some output), never actually
used to bound anything downstream. `ddpg_quadcopter_rca_engine.py`'s own
Geburah cap, by contrast, DOES bound something real (rotor RPM) -- but
it's a fixed constant, never computed from anything about the actor's
own behavior. This module is the first place the entropy-based gamma
formula and a REAL bound on system output are the same mechanism: the
DDPG actor's own rotor-speed decisiveness, each step, sets how far
Geburah lets that step's action diverge from the safe midpoint.

THE MECHANISM: `DynamicGeburahDDPGAgent.act()` computes gamma from the
actor's own PRE-SIGMOID rotor logits (the 4-dimensional LayerNorm output
for `actor_out`, before the final sigmoid squash) instead of receiving a
fixed `gamma_cap` argument. High entropy across those 4 logits (the
actor is undifferentiated -- no rotor is meaningfully favored over the
others) tightens the cap toward the existing 0.05 floor. Low entropy (a
confident, skewed preference for particular rotor settings) allows the
cap up toward the existing 0.85 ceiling. Geburah's restriction now
responds to how decisive the policy actually is at that instant, rather
than being a number chosen once at design time.

WHY THIS DOESN'T EDIT THE VERIFIED ENGINE FILE: consistent with this
project's own discipline (see `ddpg_goal_conditioned_convergence_study.py`
and `ddpg_retuned_hyperparameter_study.py`'s docstrings), new capability
is composed on top of the VERIFIED `DDPGAgent`/`LayerNormDense` via
subclassing, not edited in place. The one piece of arithmetic duplicated
here (LayerNormDense's pre-activation LayerNorm step, WITHOUT its final
sigmoid) is cross-checked directly against the real, verified
`actor_out.forward()` in `test_ddpg_dynamic_geburah_gamma.py` --
`sigmoid(these_logits)` must equal `actor_out.forward(h2)` exactly, or
the duplication is wrong.

ONE DISCLOSED ADAPTATION FROM THE OTHER THREE IMPLEMENTATIONS: this
module clips gamma to `[0.05, 0.85]`, not the `[0.0, 0.85]` every other
implementation uses. The other three report gamma as a standalone
number with no floor needed. Here gamma is the UPPER end of a two-sided
clip band `[0.05, gamma]` applied to real rotor speeds -- if gamma were
allowed down to 0.0, that band would invert (`0.05 > 0.0`) and
`np.clip()`'s behavior on an inverted range is not something to rely on
silently. The floor is the engine's own pre-existing 0.05 constant, not
a new number invented for this module.

Register B (see `fixed_point_closure_and_the_y_combinator.md` §1): a
real, checkable mechanism change (verified by tests, cross-checked
against the same formula's known behavior elsewhere), not a claim about
consciousness or artistic license.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import ddpg_quadcopter_rca_engine as eng

MAX_GAMMA_CAP = eng.MAX_GAMMA_CAP  # 0.85, imported from the engine rather than restated
MIN_GAMMA_FLOOR = 0.05             # the engine's own existing rotor-speed floor, reused as gamma's floor


def compute_directive_gamma(logits):
    """Fourth independent implementation of this project's entropy-based
    directive-strength formula (see module docstring for the other
    three). Deliberately written from scratch here, matching the
    others' formula and edge-case handling, rather than importing one of
    them -- consistent with how the existing three are each independent
    (agency_budget.py's hand-verification doc cross-checks it against
    delta_operator.py's for exactly this reason: independent
    implementations of the same formula are a cross-check, not
    duplication to clean up).

        probs   = softmax(logits)
        h       = -sum(p * log2(p))          (Shannon entropy, bits)
        h_max   = log2(len(logits))
        h_norm  = h / h_max
        gamma   = clip(1 - h_norm, 0.0, MAX_GAMMA_CAP)

    Edge cases (matching delta_operator.compute_gamma()'s convention):
    empty input returns 0.0; a single logit (nothing to have entropy
    over) returns MAX_GAMMA_CAP directly.
    """
    if logits is None or len(logits) == 0:
        return 0.0

    arr = np.array(logits, dtype=np.float64)
    if len(arr) <= 1:
        return float(MAX_GAMMA_CAP)

    exp_logits = np.exp(arr - np.max(arr))  # subtract max for numerical stability, standard softmax practice
    probs = exp_logits / np.sum(exp_logits)

    h = -np.sum(probs * np.log2(probs + 1e-12))  # 1e-12 epsilon guards log2(0) for any near-zero probability
    h_max = np.log2(len(probs))
    h_norm = h / h_max if h_max > 0 else 0.0

    raw_gamma = 1.0 - h_norm
    return float(np.clip(raw_gamma, 0.0, MAX_GAMMA_CAP))


class DynamicGeburahDDPGAgent(eng.DDPGAgent):
    """Identical to DDPGAgent in every respect except act(): the Geburah
    gamma cap is computed per step from the actor's own pre-activation
    rotor logits, instead of always being the fixed MAX_GAMMA_CAP
    constant. Nothing about training (step()), the critic, or the target
    networks is touched -- this only changes how the LIVE actor's output
    is bounded at action-selection time.
    """

    def _actor_pre_activation_logits(self, h2):
        """Duplicates LayerNormDense.forward()'s computation for
        actor_out ONLY as far as the LayerNorm affine step -- stopping
        BEFORE the final sigmoid, since sigmoid-squashed values in [0,1]
        would badly distort the softmax+entropy computation (a sigmoid
        already discards most of the relative-magnitude information a
        softmax needs). Mirrors LayerNormDense.forward() line-for-line
        rather than reimplementing the normalization differently; see
        test_ddpg_dynamic_geburah_gamma.py for the cross-check that
        sigmoid(this method's output) exactly equals
        self.actor_out.forward(h2) (the real, verified engine output) --
        the duplication either matches the verified layer's real
        computation or the test catches it.
        """
        layer = self.actor_out
        z = np.dot(h2, layer.W) + layer.b
        if layer.use_ln:
            mean = np.mean(z, axis=-1, keepdims=True)
            var = np.var(z, axis=-1, keepdims=True)
            std = np.sqrt(var + 1e-5)
            n = (z - mean) / std
        else:
            n = z
        return n

    def act(self, state, add_noise=True):
        """Same contract as DDPGAgent.act() (returns rotor_speeds only,
        no signature change, so this subclass drops into any existing
        caller unchanged) -- gamma_cap is no longer an argument, since
        it's now computed internally every call. The computed value is
        stashed on self.last_gamma_cap and self.last_directive_entropy
        for observability/testing, exactly the kind of telemetry a real
        deployed directive-strength cap would need to expose."""
        s = np.atleast_2d(state)
        h1 = self.actor_l1.forward(s)
        h2 = self.actor_l2.forward(h1)
        raw_signal = self.actor_out.forward(h2)[0]

        logits = self._actor_pre_activation_logits(h2)[0]
        raw_gamma = compute_directive_gamma(logits)
        # Floor at MIN_GAMMA_FLOOR (0.05), not 0.0 -- see module docstring's
        # "ONE DISCLOSED ADAPTATION" section for why.
        dynamic_gamma = max(raw_gamma, MIN_GAMMA_FLOOR)

        if add_noise:
            raw_signal = raw_signal + self.noise.sample() * 0.1

        bounded_signal = np.clip(raw_signal, MIN_GAMMA_FLOOR, dynamic_gamma)
        rotor_speeds = bounded_signal * self.max_rpm

        self.last_gamma_cap = dynamic_gamma
        self.last_raw_gamma = raw_gamma  # pre-floor value, for tests/telemetry that want to see it uncensored
        return rotor_speeds
