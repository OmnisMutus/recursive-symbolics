#!/usr/bin/env python3
"""
test_iitd_mth432_stat_learning.py
Runnable Unit Test Suite for iitd_mth432_stat_learning.py.

WHAT THIS TESTS:
1. Ridge L2 Regression Closed-Form Recovery: Verifies beta = (X^T X + alpha I)^-1 X^T y
   recovers synthetic true parameters (intercept=5.0, w1=2.0, w2=-3.0).
2. Ground-Truth Scikit-Learn Comparison for Ridge: Compares custom Ridge coefficients
   directly against sklearn.linear_model.Ridge.
3. LDA Binary Classification: Verifies Linear Discriminant Analysis decision boundary
   separates Gaussian clusters with >= 90% accuracy.
4. Ground-Truth Scikit-Learn Cluster Agreement for K-Means: Compares custom KMeansClustering
   centroids and labels against sklearn.cluster.KMeans on well-separated clusters.
"""

import sys
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

import iitd_mth432_stat_learning as stat


class TestStatisticalLearningSuite(unittest.TestCase):

    def test_ridge_regression_closed_form_recovery(self):
        """Verifies Ridge L2 regression recovers synthetic target parameters."""
        np.random.seed(42)
        X = np.random.randn(100, 2)
        # Target: y = 5.0 + 2.0*x0 - 3.0*x1
        true_w = np.array([5.0, 2.0, -3.0])
        X_design = np.hstack([np.ones((100, 1)), X])
        y = np.dot(X_design, true_w) + np.random.randn(100) * 0.01

        model = stat.RidgeRegression(alpha=0.01)
        model.fit(X, y)

        # Assert recovered coefficients match ground truth
        self.assertAlmostEqual(model.coef_[0], 5.0, delta=0.1)
        self.assertAlmostEqual(model.coef_[1], 2.0, delta=0.1)
        self.assertAlmostEqual(model.coef_[2], -3.0, delta=0.1)

    def test_ridge_regression_matches_sklearn_ground_truth(self):
        """Verifies custom Ridge coefficients match sklearn.linear_model.Ridge exactly."""
        try:
            from sklearn.linear_model import Ridge
        except ImportError:
            self.skipTest("scikit-learn is not installed in current environment")

        np.random.seed(42)
        X = np.random.randn(50, 3)
        y = 2.5 + 1.5 * X[:, 0] - 3.0 * X[:, 1] + 0.5 * X[:, 2] + np.random.randn(50) * 0.1

        # Fit Custom Ridge (alpha=0.5)
        custom_model = stat.RidgeRegression(alpha=0.5)
        custom_model.fit(X, y)

        # Fit Sklearn Ridge (alpha=0.5)
        sk_model = Ridge(alpha=0.5, fit_intercept=True)
        sk_model.fit(X, y)

        # Verify Intercept
        self.assertAlmostEqual(custom_model.coef_[0], sk_model.intercept_, places=4)
        # Verify Slopes
        np.testing.assert_almost_equal(custom_model.coef_[1:], sk_model.coef_, decimal=4)

    def test_lda_binary_classification_accuracy(self):
        """Verifies LDA classifier achieves >= 90% accuracy on separated Gaussian clusters."""
        np.random.seed(42)
        X0 = np.random.randn(30, 2) - 3.0
        X1 = np.random.randn(30, 2) + 3.0
        X = np.vstack([X0, X1])
        y = np.array([0] * 30 + [1] * 30)

        lda = stat.LDAClassifier()
        lda.fit(X, y)
        preds = lda.predict(X)

        accuracy = np.mean(preds == y)
        self.assertGreaterEqual(accuracy, 0.90)

    def test_kmeans_clustering_matches_sklearn_cluster_assignments(self):
        """Verifies KMeansClustering matches sklearn.cluster.KMeans on well-separated clusters."""
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            self.skipTest("scikit-learn is not installed in current environment")

        np.random.seed(42)
        X0 = np.random.randn(25, 2) - 10.0
        X1 = np.random.randn(25, 2) + 10.0
        X = np.vstack([X0, X1])

        # Fit Custom KMeans (k=2)
        custom_kmeans = stat.KMeansClustering(k=2, max_iter=100)
        custom_labels = custom_kmeans.fit(X)

        # Fit Sklearn KMeans (k=2)
        sk_kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        sk_labels = sk_kmeans.fit_predict(X)

        # Compute cluster label agreement (handles label permutation 0<->1)
        agreement = np.mean(custom_labels == sk_labels)
        if agreement < 0.5:
            agreement = np.mean(custom_labels == (1 - sk_labels))

        self.assertEqual(agreement, 1.0, "K-Means cluster assignments must match sklearn 100%")


def run_unit_test_suite():
    print("=" * 72)
    print("  IITD MTH432 STATISTICAL LEARNING ENGINE — UNIT TEST SUITE")
    print("  Executing Closed-Form Ridge & Sklearn Ground-Truth Assertions")
    print("=" * 72 + "\n")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 72)
    print("  UNIT TEST SUITE SUMMARY")
    print("=" * 72)
    print(f"  Total Tests Executed : {result.testsRun}")
    print(f"  Total Failures       : {len(result.failures)}")
    print(f"  Total Errors         : {len(result.errors)}")
    status = "ALL PASSED  (correctness verified per-assertion above)" if result.wasSuccessful() else "FAILED  — see output above"
    print(f"  Result               : {status}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_unit_test_suite()
    sys.exit(0 if success else 1)
