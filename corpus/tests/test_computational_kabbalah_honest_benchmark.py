#!/usr/bin/env python3
"""
test_computational_kabbalah_honest_benchmark.py
Correctness verification for computational_kabbalah_honest_benchmark.py per
TESTING_STANDARD.md.

PRE-EXISTING LIMITATION FIXED TO ENABLE THIS TEST: the four benchmark methods
in this file used unseeded np.random calls and returned only a timing scalar
-- no computed value was ever exposed, meaning nothing about their actual
math could be checked against ground truth (only "it ran and returned a
positive number"). Fixed by seeding each method's random draws and storing
the computed values (not just timing) in self.results. This test verifies
those newly-exposed values against independent ground truth.

Ground truth used:
- Forward pass: independent pure-Python (non-NumPy) recomputation of the
  same seeded network.
- Ridge solver: cross-checked against np.linalg.lstsq (a different solver
  path than np.linalg.solve).
- Entropy: independent recomputation via scipy-free manual Shannon entropy
  on the same seeded distribution.
- Determinism: the file's own internal two-run comparison (already a real
  ground-truth-free structural check -- two independent runs must match).
"""

import sys
import math
import unittest
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from computational_kabbalah_honest_benchmark import HonestBenchmarkSuite


class TestForwardPassCorrectness(unittest.TestCase):
    def test_computed_action_matches_independent_python_reference(self):
        suite = HonestBenchmarkSuite()
        suite.benchmark_forward_pass()
        actual_action = suite.results['forward_pass_sample_action']

        # Independent reference: same seed, reconstructed here with a
        # completely separate (plain-loop) implementation.
        np.random.seed(123)
        state_dim, hidden_dim, action_dim = 18, 32, 4
        state = np.random.randn(state_dim)
        W1 = np.random.randn(state_dim, hidden_dim) / np.sqrt(state_dim)
        W2 = np.random.randn(hidden_dim, action_dim) / np.sqrt(hidden_dim)

        h = [max(0.0, sum(state[i] * W1[i, j] for i in range(state_dim))) for j in range(hidden_dim)]
        logits = [sum(h[j] * W2[j, k] for j in range(hidden_dim)) for k in range(action_dim)]
        probs = [1.0 / (1.0 + math.exp(-x)) for x in logits]
        expected_action = np.clip(np.array(probs), 0.05, 0.95)

        max_diff = np.max(np.abs(actual_action - expected_action))
        self.assertLess(max_diff, 1e-9, f"Independent reference disagrees, max diff {max_diff:.2e}")

    def test_action_values_within_documented_clip_bounds(self):
        suite = HonestBenchmarkSuite()
        suite.benchmark_forward_pass()
        action = suite.results['forward_pass_sample_action']
        self.assertTrue(np.all(action >= 0.05))
        self.assertTrue(np.all(action <= 0.95))


class TestRidgeSolverCorrectness(unittest.TestCase):
    def test_beta_matches_independent_lstsq_ground_truth(self):
        suite = HonestBenchmarkSuite()
        suite.benchmark_matrix_solver()
        beta = suite.results['ridge_beta']
        X = suite.results['ridge_X']
        y = suite.results['ridge_y']

        # Independent ground truth: solve the SAME regularized normal
        # equations via a different linear algebra routine (lstsq on the
        # augmented system) rather than np.linalg.solve.
        D = X.shape[1]
        alpha = 1.0
        A_aug = np.vstack([X, np.sqrt(alpha) * np.eye(D)])
        b_aug = np.concatenate([y, np.zeros(D)])
        expected_beta, *_ = np.linalg.lstsq(A_aug, b_aug, rcond=None)

        max_diff = np.max(np.abs(beta - expected_beta))
        self.assertLess(max_diff, 1e-6, f"Ridge beta disagrees with lstsq ground truth, max diff {max_diff:.2e}")

    def test_residual_is_nonnegative_and_matches_recomputation(self):
        suite = HonestBenchmarkSuite()
        suite.benchmark_matrix_solver()
        residual = suite.results['ridge_residual']
        X = suite.results['ridge_X']
        y = suite.results['ridge_y']
        beta = suite.results['ridge_beta']
        expected_residual = float(np.linalg.norm(X @ beta - y))
        self.assertGreaterEqual(residual, 0.0)
        self.assertAlmostEqual(residual, expected_residual, places=9)


class TestEntropyCorrectness(unittest.TestCase):
    def test_entropy_bits_is_within_theoretical_bounds(self):
        # For 1,000,000 samples the entropy in bits must be positive and,
        # since it's a near-uniform distribution over that many mass points,
        # should be close to but not exceed log2(n_samples).
        suite = HonestBenchmarkSuite()
        suite.benchmark_entropy_calculation()
        entropy_bits = suite.results['entropy_bits']
        self.assertGreater(entropy_bits, 0.0)
        self.assertLessEqual(entropy_bits, math.log2(1_000_000) + 1e-6)

    def test_entropy_matches_independent_recomputation_same_seed(self):
        suite = HonestBenchmarkSuite()
        suite.benchmark_entropy_calculation()
        actual_bits = suite.results['entropy_bits']

        np.random.seed(789)
        values = np.random.rand(1_000_000)
        values = values / values.sum()
        mask = values > 1e-10
        expected_entropy = -np.sum(values[mask] * np.log(values[mask]))
        expected_bits = expected_entropy / np.log(2)

        self.assertAlmostEqual(actual_bits, expected_bits, places=6)


class TestDeterminismCheck(unittest.TestCase):
    def test_deterministic_consistency_holds(self):
        suite = HonestBenchmarkSuite()
        result = suite.benchmark_deterministic_consistency()
        self.assertTrue(result)


def run_unit_test_suite():
    print("=" * 72)
    print("  COMPUTATIONAL KABBALAH BENCHMARK — CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
