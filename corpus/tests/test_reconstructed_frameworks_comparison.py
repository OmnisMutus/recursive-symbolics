#!/usr/bin/env python3
"""
test_reconstructed_frameworks_comparison.py
Correctness verification for reconstructed_frameworks_comparison.py per
TESTING_STANDARD.md.

ENVIRONMENT NOTE (stated plainly): this test requires real PyTorch to be
installed. It could NOT be executed in the sandbox this test suite was
written in -- that sandbox's network policy blocks the CPU-only wheel index
(download.pytorch.org returns 403 "blocked-by-allowlist") and the default
PyPI build's CUDA dependency chain (cudnn, nccl, cusparselt, etc.) exceeds
the sandbox's disk quota even after clearing everything else. This was
confirmed directly, not assumed. The test is written to skip cleanly
(unittest.skipUnless) rather than fail or fake a pass when torch is
unavailable -- run it in an environment where `pip install torch` actually
succeeds (e.g. where reconstructed_frameworks_comparison.py itself was
already confirmed to run) to get a real VERIFIED result.

Ground truth used: this test checks a STRONGER claim than the script itself
does. The script only tracks whether actor_pt.fc1.weight changes after
training to claim "full multi-layer autograd" -- this test independently
snapshots and checks every actor and critic layer (fc1, fc2, out, and their
LayerNorm parameters) individually, so a bug where e.g. fc2 or the critic's
layers silently receive no gradient (while fc1 does) would be caught here
even though it wouldn't be caught by the script's own weaker check.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

if HAS_TORCH:
    from reconstructed_frameworks_comparison import (
        PyTorchActor, PyTorchCritic, run_framework_comparison
    )
    import numpy as np
    import torch.nn as nn
    import torch.optim as optim


@unittest.skipUnless(HAS_TORCH, "PyTorch not installed in this environment -- see module docstring")
class TestFullMultiLayerAutogradClaim(unittest.TestCase):
    """The script's headline claim is 'full multi-layer autograd' -- verify
    ALL layers actually receive gradient updates, not just the one layer
    the script itself happens to check (actor_pt.fc1.weight)."""

    def test_every_actor_layer_receives_a_gradient_update(self):
        torch.manual_seed(0)
        actor = PyTorchActor()
        critic = PyTorchCritic()
        actor_opt = optim.Adam(actor.parameters(), lr=1e-2)
        critic_opt = optim.Adam(critic.parameters(), lr=1e-2)

        state = torch.randn(8, 18)
        action = torch.rand(8, 4) * 0.8 + 0.05

        # Snapshot every actor parameter before any update.
        before = {name: p.clone() for name, p in actor.named_parameters()}

        for _ in range(20):
            critic_opt.zero_grad()
            target = torch.randn(8, 1)
            loss_c = nn.MSELoss()(critic(state, action), target)
            loss_c.backward()
            critic_opt.step()

            actor_opt.zero_grad()
            loss_a = -critic(state, actor(state)).mean()
            loss_a.backward()
            actor_opt.step()

        unchanged = [name for name, p in actor.named_parameters()
                     if torch.allclose(before[name], p)]
        self.assertEqual(unchanged, [],
            f"These actor parameters never received a gradient update: {unchanged}")

    def test_every_critic_layer_receives_a_gradient_update(self):
        torch.manual_seed(1)
        actor = PyTorchActor()
        critic = PyTorchCritic()
        actor_opt = optim.Adam(actor.parameters(), lr=1e-2)
        critic_opt = optim.Adam(critic.parameters(), lr=1e-2)

        state = torch.randn(8, 18)
        action = torch.rand(8, 4) * 0.8 + 0.05

        before = {name: p.clone() for name, p in critic.named_parameters()}

        for _ in range(20):
            critic_opt.zero_grad()
            target = torch.randn(8, 1)
            loss_c = nn.MSELoss()(critic(state, action), target)
            loss_c.backward()
            critic_opt.step()

        unchanged = [name for name, p in critic.named_parameters()
                     if torch.allclose(before[name], p)]
        self.assertEqual(unchanged, [],
            f"These critic parameters never received a gradient update: {unchanged}")


@unittest.skipUnless(HAS_TORCH, "PyTorch not installed in this environment -- see module docstring")
class TestNetworkShapesAndBounds(unittest.TestCase):
    def test_actor_output_is_within_sigmoid_range(self):
        torch.manual_seed(2)
        actor = PyTorchActor()
        out = actor(torch.randn(5, 18))
        self.assertEqual(tuple(out.shape), (5, 4))
        self.assertTrue(torch.all(out >= 0.0))
        self.assertTrue(torch.all(out <= 1.0))

    def test_critic_output_is_scalar_per_row(self):
        torch.manual_seed(3)
        critic = PyTorchCritic()
        state = torch.randn(5, 18)
        action = torch.rand(5, 4)
        out = critic(state, action)
        self.assertEqual(tuple(out.shape), (5, 1))


@unittest.skipUnless(HAS_TORCH, "PyTorch not installed in this environment -- see module docstring")
class TestRunFrameworkComparisonIntegration(unittest.TestCase):
    def test_returns_expected_keys_and_positive_timings(self):
        result = run_framework_comparison(num_updates=5, batch_size=8)
        self.assertIn("pytorch_time_ms", result)
        self.assertIn("numpy_time_ms", result)
        self.assertIn("ratio", result)
        self.assertIn("torch_autograd_verified", result)
        self.assertGreater(result["pytorch_time_ms"], 0.0)
        self.assertGreater(result["numpy_time_ms"], 0.0)
        self.assertTrue(result["torch_autograd_verified"])

    def test_ratio_matches_the_two_timings(self):
        result = run_framework_comparison(num_updates=5, batch_size=8)
        expected_ratio = result["pytorch_time_ms"] / max(result["numpy_time_ms"], 1e-6)
        self.assertAlmostEqual(result["ratio"], expected_ratio, places=6)


def run_unit_test_suite():
    print("=" * 72)
    print("  RECONSTRUCTED FRAMEWORKS COMPARISON — CORRECTNESS TEST SUITE")
    if not HAS_TORCH:
        print("  PyTorch not installed -- all tests will be SKIPPED, not failed.")
        print("  This is an environment limitation, not a correctness claim either way.")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  "
          f"Errors: {len(result.errors)}  Skipped: {len(result.skipped)}")

    # HONESTY GUARD: unittest's wasSuccessful() returns True even if every
    # single test was skipped -- that would let test_all_engines.py report
    # this as VERIFIED when in fact nothing was checked at all in this
    # environment (no torch installed). "Ran and passed" and "never ran"
    # must not produce the same exit code.
    nothing_actually_ran = result.testsRun > 0 and len(result.skipped) == result.testsRun
    if nothing_actually_ran:
        print("  Result: NOT VERIFIED IN THIS ENVIRONMENT -- every test skipped (no PyTorch).")
        print("           This is NOT the same as passing. Run where torch is installed.")
        print("=" * 72)
        return False

    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
