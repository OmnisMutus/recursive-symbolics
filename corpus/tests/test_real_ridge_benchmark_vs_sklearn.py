#!/usr/bin/env python3
"""
test_real_ridge_benchmark_vs_sklearn.py
Correctness verification for real_ridge_benchmark_vs_sklearn.py per
TESTING_STANDARD.md.

Ground truth used: the ACTUAL installed scikit-learn library
(sklearn.linear_model.Ridge), imported and run for real in this test --
the strongest tier of ground truth per TESTING_STANDARD.md ("a real,
independent library"). This is the same comparison the benchmark script
itself performs; this test reproduces it independently (fresh datasets,
fresh RidgeRegression/Ridge instances) rather than importing and trusting
the script's own printed "agree: True" line.
"""

import sys
import subprocess
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

import iitd_mth432_stat_learning as rca_eng

try:
    from sklearn.linear_model import Ridge as SKRidge
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@unittest.skipUnless(HAS_SKLEARN, "scikit-learn not installed -- cannot run the real comparison")
class TestRCAMatchesRealSklearn(unittest.TestCase):

    def _agree(self, X, y, alpha):
        rca = rca_eng.RidgeRegression(alpha=alpha)
        rca.fit(X, y)
        rca_pred = rca.predict(X)

        sk = SKRidge(alpha=alpha, fit_intercept=True)
        sk.fit(X, y)
        sk_pred = sk.predict(X)

        max_diff = float(np.max(np.abs(rca_pred - sk_pred)))
        return max_diff, np.allclose(rca_pred, sk_pred, atol=1e-6)

    def test_matches_sklearn_standard_case(self):
        rng = np.random.default_rng(7)
        N, D = 100, 20
        X = rng.normal(size=(N, D))
        true_beta = rng.normal(size=D)
        y = X @ true_beta + rng.normal(scale=0.1, size=N)
        max_diff, agree = self._agree(X, y, alpha=1.0)
        self.assertTrue(agree, f"RCA and sklearn Ridge predictions diverged (max diff {max_diff:.3e})")

    def test_matches_sklearn_alpha_zero_no_regularization(self):
        rng = np.random.default_rng(3)
        N, D = 50, 5
        X = rng.normal(size=(N, D))
        true_beta = rng.normal(size=D)
        y = X @ true_beta + rng.normal(scale=0.05, size=N)
        max_diff, agree = self._agree(X, y, alpha=0.0)
        self.assertTrue(agree, f"Diverged at alpha=0 (max diff {max_diff:.3e})")

    def test_matches_sklearn_small_dataset(self):
        rng = np.random.default_rng(99)
        N, D = 8, 3
        X = rng.normal(size=(N, D))
        true_beta = rng.normal(size=D)
        y = X @ true_beta + rng.normal(scale=0.1, size=N)
        max_diff, agree = self._agree(X, y, alpha=1.0)
        self.assertTrue(agree, f"Diverged on small dataset (max diff {max_diff:.3e})")

    def test_matches_sklearn_high_alpha(self):
        # Heavy regularization -- coefficients should shrink toward zero on
        # both sides identically, not just "both small" independently.
        rng = np.random.default_rng(21)
        N, D = 60, 10
        X = rng.normal(size=(N, D))
        true_beta = rng.normal(size=D)
        y = X @ true_beta + rng.normal(scale=0.1, size=N)
        max_diff, agree = self._agree(X, y, alpha=50.0)
        self.assertTrue(agree, f"Diverged at high alpha (max diff {max_diff:.3e})")


class TestScriptActuallyRuns(unittest.TestCase):
    def test_script_exits_zero_and_reports_agreement(self):
        result = subprocess.run(
            [sys.executable, str(BASE_DIR.parent / "engines" / "real_ridge_benchmark_vs_sklearn.py")],
            capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, f"Script did not exit 0: {result.stderr[:300]}")
        self.assertIn("agree", result.stdout.lower())
        self.assertIn("True", result.stdout)


def run_unit_test_suite():
    print("=" * 72)
    print("  REAL RIDGE BENCHMARK VS SKLEARN — CORRECTNESS TEST SUITE")
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
