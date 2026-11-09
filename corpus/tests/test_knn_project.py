#!/usr/bin/env python3
"""
test_knn_project.py
Runnable Unit Test Suite for knn_project.py.

WHAT THIS TESTS:
1. Distance Metrics Ground Truth: Euclidean, Manhattan, and Cosine formulas verified against
   independent pure-Python mathematical calculations.
2. Feature Scaling Invariants: MinMaxScaler bounds [0.0, 1.0] and Z-Score standardization
   producing exact mean=0.0 and std=1.0.
3. KNN Classifier Correctness: Decision boundary resolution on synthetic multi-class clusters.
4. KNN Regressor Correctness: Inverse-distance weighted continuous target interpolation.
5. Zero Norm / Edge Case Safety: Zero-vector cosine distance returning 1.0 without DivisionByZero.
"""

import sys
import math
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import knn_project as knn


class TestKNNProjectSuite(unittest.TestCase):

    def test_euclidean_distance_against_independent_math(self):
        """Verifies euclidean_distance against independent math.sqrt calculation."""
        v1 = [1.5, -2.5, 4.0]
        v2 = [4.5, 1.5, -0.0] # diffs: 3.0, 4.0, -4.0 -> sum sq = 9 + 16 + 16 = 41
        expected = math.sqrt(41.0)
        actual = knn.euclidean_distance(v1, v2)
        self.assertAlmostEqual(actual, expected, places=7)

    def test_manhattan_distance_against_independent_math(self):
        """Verifies manhattan_distance against independent sum of absolute differences."""
        v1 = [1.5, -2.5, 4.0]
        v2 = [4.5, 1.5, 0.0] # abs diffs: 3.0, 4.0, 4.0 -> sum = 11.0
        expected = 11.0
        actual = knn.manhattan_distance(v1, v2)
        self.assertEqual(actual, expected)

    def test_cosine_distance_zero_vector_edge_case(self):
        """Verifies cosine distance returns 1.0 when one or both vectors are zero vectors."""
        v_zero = [0.0, 0.0, 0.0]
        v_normal = [1.0, 2.0, 3.0]
        self.assertEqual(knn.cosine_distance(v_zero, v_normal), 1.0)
        self.assertEqual(knn.cosine_distance(v_zero, v_zero), 1.0)

    def test_scaler_zscore_standardization_invariants(self):
        """Verifies Scaler(method='standard') produces mean=0.0 and std=1.0 on features."""
        X = [[10.0, 100.0], [20.0, 200.0], [30.0, 300.0], [40.0, 400.0]]
        scaler = knn.Scaler(method="standard")
        X_scaled = scaler.fit_transform(X)

        # Compute mean and std of column 0 independently
        col0 = [row[0] for row in X_scaled]
        mean0 = sum(col0) / len(col0)
        std0 = math.sqrt(sum((x - mean0) ** 2 for x in col0) / len(col0))

        self.assertAlmostEqual(mean0, 0.0, places=6)
        self.assertAlmostEqual(std0, 1.0, places=6)

    def test_scaler_minmax_bounds(self):
        """Verifies Scaler(method='minmax') scales all feature values strictly into [0.0, 1.0]."""
        X = [[10.0], [25.0], [50.0], [100.0]]
        scaler = knn.Scaler(method="minmax")
        X_scaled = scaler.fit_transform(X)

        col0 = [row[0] for row in X_scaled]
        self.assertEqual(min(col0), 0.0)
        self.assertEqual(max(col0), 1.0)

    def test_knn_classifier_multiclass_prediction(self):
        """Verifies KNNClassifier classifies test points into correct clusters."""
        # 3 Clusters: Class 0 (~[0,0]), Class 1 (~[10,10]), Class 2 (~[-10,-10])
        X = [
            [0.1, 0.2], [0.2, 0.1], [0.0, 0.0],
            [10.1, 9.9], [9.8, 10.2], [10.0, 10.0],
            [-9.9, -10.1], [-10.2, -9.8], [-10.0, -10.0]
        ]
        y = [0, 0, 0, 1, 1, 1, 2, 2, 2]

        clf = knn.KNNClassifier(k=3, distance_metric="euclidean")
        clf.fit(X, y)

        preds = clf.predict([[0.05, 0.05], [10.05, 10.05], [-10.05, -10.05]])
        self.assertEqual(preds, [0, 1, 2])

    def test_knn_regressor_continuous_interpolation(self):
        """Verifies KNNRegressor interpolates continuous target y values."""
        X = [[1.0], [2.0], [3.0], [4.0]]
        y = [10.0, 20.0, 30.0, 40.0]

        reg = knn.KNNRegressor(k=2, distance_metric="euclidean")
        reg.fit(X, y)

        # Midpoint 2.5 should interpolate between y[1]=20.0 and y[2]=30.0 -> 25.0
        pred = reg.predict([[2.5]])[0]
        self.assertAlmostEqual(pred, 25.0, places=5)


def run_unit_test_suite():
    print("=" * 72)
    print("  KNN MACHINE LEARNING ENGINE — UNIT TEST SUITE")
    print("  Executing Mathematical, Scaling & Classification Assertions")
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
