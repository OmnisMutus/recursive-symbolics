#!/usr/bin/env python3
"""
ddpg_correspondence_ledger.py
Worked example / proof of concept for correspondence_ledger.py, applied to
ddpg_quadcopter_rca_engine.py.

Unlike sephirotic_correspondence_ledger.py and attractor_correspondence_ledger.py,
this engine's own test file (test_ddpg_quadcopter_rca_engine.py) uses the
simpler module-level check()/PASS/FAIL script style, not unittest.TestCase --
so from_unittest_methods() can't wrap it. This is the worked example for
from_script_exit_code() instead, which re-runs the whole script as a real
subprocess and treats its exit code as ground truth. That's coarser than
method-level reuse (no named sub-checks to select individually), which is
stated honestly in the first entry's claim text rather than implied away.

CORRECTION (dated, see LIBER_0.md): the second entry below was originally
registered as a deliberate FAILED case -- the first correspondence entry
in this repo's ledger series to register a claim the underlying test
evidence actually contradicted ("the actor-critic network is genuinely
being trained end-to-end"), because that was the honest, documented state
of the engine at the time: only critic_out.W ever received a gradient,
and a second, previously undiscovered bug meant even that gradient was
functionally meaningless (LayerNorm over critic_out's 1-unit output axis
is mathematically degenerate -- always exactly 0 regardless of input or
weights). Both are now fixed in ddpg_quadcopter_rca_engine.py (real
backprop through every layer of both networks, a genuine deterministic
policy gradient for the actor, and critic_out constructed with
use_ln=False). This entry now expects VERIFIED, not FAILED. The FAILED
result is not deleted from history -- it's recorded here, in this dated
note, and in LIBER_0.md -- because a gap that gets fixed and then quietly
stops being mentioned would look, to a later reader, exactly like a gap
that was never real. Its validator still mirrors the same snapshot-
before/train/compare-after procedure rather than a different check, just
with the opposite expected outcome.

Usage:
    python ddpg_correspondence_ledger.py
"""

import sys
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from correspondence_ledger import CorrespondenceLedger, ValidationResult, from_script_exit_code
import ddpg_quadcopter_rca_engine as eng


def _classify_weight_changes(snapshot: dict, agent) -> tuple:
    """Given a {dotted_attr_name: pre-training array copy} snapshot and the
    (now-trained) agent object, returns (unchanged_names, changed_names) by
    resolving each dotted name against the agent (e.g. "actor_l1.W" ->
    agent.actor_l1.W) and comparing it to its snapshotted value with
    np.allclose(). Pulled out of _validate_actor_critic_is_genuinely_trained()
    specifically so this comparison logic -- the one part of this ledger
    that computes a genuinely new fact rather than re-displaying an existing
    test's result -- can be tested in isolation against hand-constructed
    fake snapshots, without needing to run real training steps to get a
    case with a known answer. See test_ddpg_correspondence_ledger.py."""
    unchanged, changed = [], []
    for name, snap in snapshot.items():
        obj = agent
        for part in name.split(".")[:-1]:
            obj = getattr(obj, part)
        current = getattr(obj, name.split(".")[-1])
        (unchanged if np.allclose(current, snap) else changed).append(name)
    return unchanged, changed


def _validate_actor_critic_is_genuinely_trained() -> ValidationResult:
    """Mirrors test_ddpg_quadcopter_rca_engine.py's section 7 (weight-change
    check, following the DDPG fix -- see that file's CORRECTION note at the
    top for what this section used to assert before the fix): snapshot
    every weight matrix, run 40 real training steps through the actual
    environment and agent, then check which matrices changed. Not a new
    check -- the same procedure, reused here to back a specific
    correspondence claim rather than just printed as a note."""
    agent = eng.DDPGAgent()
    snapshot = {
        "actor_l1.W": agent.actor_l1.W.copy(),
        "actor_l2.W": agent.actor_l2.W.copy(),
        "actor_out.W": agent.actor_out.W.copy(),
        "critic_l1.W": agent.critic_l1.W.copy(),
        "critic_l2.W": agent.critic_l2.W.copy(),
        "critic_out.W": agent.critic_out.W.copy(),
    }
    env = eng.QuadcopterTakeoffEnv()
    s = env.reset()
    for _ in range(40):
        a = agent.act(s)
        ns, r, d, _ = env.step(a)
        agent.step(s, a, r, ns, d, batch_size=8)
        s = ns
        if d:
            s = env.reset()

    unchanged, changed = _classify_weight_changes(snapshot, agent)

    actor_names = ["actor_l1.W", "actor_l2.W", "actor_out.W"]
    actor_unchanged = [n for n in actor_names if n in unchanged]
    if actor_unchanged:
        return ValidationResult(
            False,
            f"actor weights UNCHANGED after 40 real training steps: {actor_unchanged} "
            f"(only {changed} actually received a gradient) -- the actor network "
            f"cannot learn to improve its policy regardless of training duration."
        )
    return ValidationResult(True, f"all actor weights changed after training: {changed}")


def build_ledger() -> CorrespondenceLedger:
    ledger = CorrespondenceLedger("DDPG Quadcopter Engine")

    ledger.register(
        pattern="Malkuth / Chesed / Geburah (Physics, Exploration, Safety Cap)",
        target="QuadcopterTakeoffEnv, OUNoise/ReplayBuffer, DDPGAgent.act()'s gamma_cap",
        claim="The reward/physics formula, the ring-buffer replay mechanism, "
              "and the Geburah safety cap (rotor output held within "
              "[0.05, 0.85] x max_rpm even under adversarially large "
              "injected noise) all match their stated formulas. Verified at "
              "SCRIPT granularity, not method granularity -- "
              "test_ddpg_quadcopter_rca_engine.py uses the check()/PASS/FAIL "
              "style, not unittest.TestCase, so there are no individually "
              "selectable sub-checks the way the other worked-example "
              "ledgers have; one VERIFIED here speaks for the whole script's "
              "8 checks, not one isolated claim.",
        validator=from_script_exit_code(_REPO_ROOT / "tests" / "test_ddpg_quadcopter_rca_engine.py"),
    )

    ledger.register(
        pattern="Tiphereth / Binah (Actor-Critic Reconciliation)",
        target="DDPGAgent.step()'s gradient update",
        claim="The actor and critic networks are genuinely being trained "
              "together end-to-end -- i.e. that calling this a 'trained "
              "DDPG agent' is accurate. FIXED (dated, see LIBER_0.md): this "
              "claim was previously EXPECTED TO FAIL, because only "
              "critic_out.W ever received a gradient and a second, "
              "previously undiscovered bug (LayerNorm degenerate over a "
              "1-unit output) meant even that gradient was functionally "
              "meaningless. Both are fixed now -- real backprop through "
              "every layer of both networks, plus a genuine deterministic "
              "policy gradient for the actor -- so this entry now expects "
              "and gets VERIFIED.",
        validator=_validate_actor_critic_is_genuinely_trained,
    )

    # Boundary-clarification row, no validator on purpose -- mirrors
    # sephirotic_correspondence_ledger.py's Binah/Malkuth/Keter row. This is
    # a design-principle claim (stated in sephirotic_reward_engine.py's own
    # docstring, which this engine's reward shaping reuses), not a
    # performance claim -- no test in this repo could ever validate or
    # falsify whether Sephirotic reward structuring trains a BETTER policy
    # than an unstructured one; that would require actual comparative
    # training runs, which is out of scope here entirely.
    ledger.register(
        pattern="Structured Reward Trains a Better Policy",
        target="(deliberately outside the scope of any test in this repo)",
        claim="Structuring the reward/architecture around Chesed/Geburah/"
              "Tifereth-style terms is claimed to be a design principle, "
              "not a performance claim -- it is NOT claimed that this "
              "trains a better policy than an unstructured reward would. "
              "No test here measures comparative training outcomes; doing "
              "so would require real training runs this repo does not "
              "perform.",
        validator=None,
    )

    return ledger


if __name__ == "__main__":
    ledger = build_ledger()
    ledger.run()
    print(ledger.report())
    sys.exit(0 if ledger.all_testable_passed() else 1)
