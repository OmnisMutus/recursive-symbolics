#!/usr/bin/env python3
"""
test_ddpg_correspondence_ledger.py
Independent correctness test for ledgers/ddpg_correspondence_ledger.py's
_classify_weight_changes() and _validate_actor_critic_is_genuinely_trained().

WHY THIS FILE EXISTS (found during a conversation, not a routine sweep):
every other worked-example ledger in this repo (sephirotic_, attractor_,
rca_sandbox_gamma_, glyph_emotion_) validates a claim purely by re-running
Layer 1's *existing* test methods via from_unittest_methods() -- Layer 2
never touches the engine (Layer 0) directly, and adds zero new facts, per
correspondence_ledger_meta_tool_spec.md's own stated discipline ("Layer 2...
does not call chesed_expansion_term() itself... adds zero new facts").

ddpg_correspondence_ledger.py's second entry is the one documented
exception: it has no from_unittest_methods()-compatible test to reuse (the
snapshot-before/train/compare-after check has no named sub-method to
select), so it computes brand-new evidence directly against the engine.
That's a deliberate, acknowledged departure from the framework's own
hierarchy discipline -- and, tellingly, it was also the ONE piece of novel
Layer 2 logic in the whole framework with no dedicated correctness test of
its own (unlike all_testable_passed() and from_script_exit_code(), both of
which have their own ground-truth tests in test_correspondence_ledger.py).
This file closes that specific gap.

GROUND TRUTH: _classify_weight_changes() is tested against hand-constructed
fake "agent" objects (via types.SimpleNamespace, not the real DDPGAgent)
whose nested attributes and pre/post values are chosen so the correct
classification is known in advance by construction -- not derived from
running any part of the engine. This is deliberately independent of
whether the real DDPGAgent's actor ever learns anything; that question is
tested separately below, against the real engine, as an integration check.
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import ddpg_correspondence_ledger as dcl  # noqa: E402


def _fake_agent(**leaf_values):
    """Builds a minimal duck-typed stand-in for DDPGAgent with exactly the
    nested attribute shape _classify_weight_changes() expects
    ("actor_l1.W" -> agent.actor_l1.W), populated with hand-picked numpy
    arrays. Not the real DDPGAgent -- deliberately so, since the point is
    to control the "current value" independent of any real training."""
    agent = SimpleNamespace()
    layers = {}
    for dotted_name, value in leaf_values.items():
        layer_name, attr = dotted_name.split(".")
        layers.setdefault(layer_name, SimpleNamespace())
        setattr(layers[layer_name], attr, value)
    for layer_name, ns in layers.items():
        setattr(agent, layer_name, ns)
    return agent


class TestClassifyWeightChangesGroundTruth(unittest.TestCase):
    """_classify_weight_changes(snapshot, agent) in isolation, against
    fake agents whose classification is known by hand construction."""

    def test_identical_array_is_unchanged(self):
        w = np.array([[1.0, 2.0], [3.0, 4.0]])
        snapshot = {"l1.W": w.copy()}
        agent = _fake_agent(**{"l1.W": w.copy()})
        unchanged, changed = dcl._classify_weight_changes(snapshot, agent)
        self.assertEqual(unchanged, ["l1.W"])
        self.assertEqual(changed, [])

    def test_clearly_different_array_is_changed(self):
        snapshot = {"l1.W": np.array([1.0, 2.0, 3.0])}
        agent = _fake_agent(**{"l1.W": np.array([9.0, 9.0, 9.0])})
        unchanged, changed = dcl._classify_weight_changes(snapshot, agent)
        self.assertEqual(unchanged, [])
        self.assertEqual(changed, ["l1.W"])

    def test_multiple_names_classified_independently(self):
        # Hand-picked: l1 identical, l2 changed, l3 identical -- exercises
        # that one changed entry doesn't contaminate the others' results.
        snapshot = {
            "l1.W": np.array([1.0, 1.0]),
            "l2.W": np.array([2.0, 2.0]),
            "l3.W": np.array([3.0, 3.0]),
        }
        agent = _fake_agent(**{
            "l1.W": np.array([1.0, 1.0]),
            "l2.W": np.array([99.0, 99.0]),
            "l3.W": np.array([3.0, 3.0]),
        })
        unchanged, changed = dcl._classify_weight_changes(snapshot, agent)
        self.assertEqual(sorted(unchanged), ["l1.W", "l3.W"])
        self.assertEqual(changed, ["l2.W"])

    def test_within_default_allclose_tolerance_counts_as_unchanged(self):
        # np.allclose defaults: rtol=1e-05, atol=1e-08. A difference of
        # 1e-10 is well inside that tolerance -- hand-computed, not derived
        # from the function under test: |1e-10| <= 1e-08 + 1e-05*|1.0|.
        snapshot = {"l1.W": np.array([1.0])}
        agent = _fake_agent(**{"l1.W": np.array([1.0 + 1e-10])})
        unchanged, changed = dcl._classify_weight_changes(snapshot, agent)
        self.assertEqual(unchanged, ["l1.W"])
        self.assertEqual(changed, [])

    def test_just_outside_default_allclose_tolerance_counts_as_changed(self):
        # A difference of 1.0 (rtol*|1.0| + atol = 1.00001e-05) is far
        # outside tolerance regardless of rounding -- unambiguous by
        # construction.
        snapshot = {"l1.W": np.array([1.0])}
        agent = _fake_agent(**{"l1.W": np.array([2.0])})
        unchanged, changed = dcl._classify_weight_changes(snapshot, agent)
        self.assertEqual(changed, ["l1.W"])

    def test_two_level_dotted_path_resolves_correctly(self):
        # Confirms the getattr-chain walk itself (name.split(".")[:-1])
        # correctly reaches a nested attribute two levels deep, not just
        # one -- the real usage is always exactly two levels
        # (agent.actor_l1.W), so this is the realistic shape, hand-verified
        # by directly inspecting what object the dotted path SHOULD reach.
        w_unchanged = np.array([5.0, 5.0])
        w_changed = np.array([6.0, 6.0])
        snapshot = {"actor_l1.W": w_unchanged.copy(), "critic_out.W": w_changed.copy()}
        agent = _fake_agent(**{
            "actor_l1.W": w_unchanged.copy(),
            "critic_out.W": np.array([60.0, 60.0]),
        })
        unchanged, changed = dcl._classify_weight_changes(snapshot, agent)
        self.assertEqual(unchanged, ["actor_l1.W"])
        self.assertEqual(changed, ["critic_out.W"])

    def test_empty_snapshot_returns_two_empty_lists(self):
        unchanged, changed = dcl._classify_weight_changes({}, _fake_agent())
        self.assertEqual(unchanged, [])
        self.assertEqual(changed, [])


class TestValidateActorCriticAgainstRealEngine(unittest.TestCase):
    """Integration check against the real, already-independently-verified
    DDPGAgent/QuadcopterTakeoffEnv (see test_ddpg_quadcopter_rca_engine.py).
    This does NOT re-derive its expected answer from the validator itself --
    the expected answer is the documented, dated fix in
    ddpg_correspondence_ledger.py's own module docstring (backprop now
    reaches every layer of both networks), which is an independent claim
    checked here by actually running the real training loop, not assumed."""

    def test_reports_success_now_that_the_gradient_bug_is_fixed(self):
        result = dcl._validate_actor_critic_is_genuinely_trained()
        self.assertTrue(
            result.passed,
            f"Expected all actor weights to change after real training "
            f"(the documented gradient-flow fix), but got: {result.detail}",
        )
        self.assertIn("all actor weights changed", result.detail)


def run_unit_test_suite():
    print("=" * 72)
    print("  DDPG_CORRESPONDENCE_LEDGER.PY -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("Test") and isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
