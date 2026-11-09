#!/usr/bin/env python3
"""
test_ctypes_math_accelerator.py
Correctness verification for ctypes_math_accelerator.py per TESTING_STANDARD.md.

NAMING NOTE (stated plainly, not hidden): despite the "ctypes" name and the
"Sub-Microsecond ... C Speed" claim in the engine's own printed banner,
fast_dot_product() wraps its inputs in ctypes.c_double arrays and then sums
them in a plain Python for-loop -- ctypes array access from Python does not
run at C speed; the loop is still interpreted Python. This test verifies
CORRECTNESS only (the numbers are right); it does not test or endorse the
speed claim, which is a separate, unverified claim this test takes no
position on.

Ground truth used: hand-computed dot products / norms via plain Python
sum() and math.sqrt(), written independently of (not calling into) the
engine's own fast_dot_product/fast_vector_norm methods.
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

from ctypes_math_accelerator import CTypesMathAccelerator


def reference_dot(a, b):
    """Independent reference: plain Python, no ctypes, no zip-truncation choice hidden."""
    n = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(n))


def reference_norm(v):
    return math.sqrt(sum(x * x for x in v))


def reference_cosine_distance(a, b):
    na, nb = reference_norm(a), reference_norm(b)
    if na == 0 or nb == 0:
        return 1.0
    cos_sim = reference_dot(a, b) / (na * nb)
    return max(0.0, min(2.0, 1.0 - cos_sim))


class TestFastDotProduct(unittest.TestCase):
    def setUp(self):
        self.acc = CTypesMathAccelerator()

    def test_known_vector_ground_truth(self):
        # [1,2,3] . [4,5,6] = 4+10+18 = 32, hand-computed
        self.assertAlmostEqual(self.acc.fast_dot_product([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]), 32.0)

    def test_matches_independent_reference_random(self):
        import random
        rng = random.Random(7)
        a = [rng.uniform(-10, 10) for _ in range(20)]
        b = [rng.uniform(-10, 10) for _ in range(20)]
        self.assertAlmostEqual(self.acc.fast_dot_product(a, b), reference_dot(a, b), places=9)

    def test_empty_vectors(self):
        self.assertEqual(self.acc.fast_dot_product([], []), 0.0)

    def test_negative_values(self):
        self.assertAlmostEqual(self.acc.fast_dot_product([-1.0, -2.0], [1.0, 2.0]), -5.0)

    def test_mismatched_lengths_truncate_to_shorter(self):
        # Documented (if surprising) behavior: n = min(len(vec1), len(vec2)).
        # [1,2,3,4] . [1,1] should only use the first 2 elements of each: 1+2=3
        self.assertAlmostEqual(self.acc.fast_dot_product([1.0, 2.0, 3.0, 4.0], [1.0, 1.0]), 3.0)

    def test_zero_vector(self):
        self.assertEqual(self.acc.fast_dot_product([0.0, 0.0, 0.0], [5.0, 5.0, 5.0]), 0.0)


class TestFastVectorNorm(unittest.TestCase):
    def setUp(self):
        self.acc = CTypesMathAccelerator()

    def test_known_3_4_5_triangle(self):
        # Classic Pythagorean vector: norm of [3,4] must be exactly 5.0
        self.assertAlmostEqual(self.acc.fast_vector_norm([3.0, 4.0]), 5.0)

    def test_empty_vector_norm_is_zero(self):
        self.assertEqual(self.acc.fast_vector_norm([]), 0.0)

    def test_zero_vector_norm_is_zero(self):
        self.assertEqual(self.acc.fast_vector_norm([0.0, 0.0, 0.0]), 0.0)

    def test_negative_components(self):
        # norm must be positive regardless of sign of components: [-3,-4] -> 5.0
        self.assertAlmostEqual(self.acc.fast_vector_norm([-3.0, -4.0]), 5.0)

    def test_matches_independent_reference(self):
        v = [1.5, -2.25, 3.75, -0.5]
        self.assertAlmostEqual(self.acc.fast_vector_norm(v), reference_norm(v), places=9)


class TestFastCosineDistanceMatrix(unittest.TestCase):
    def setUp(self):
        self.acc = CTypesMathAccelerator()

    def test_identical_vectors_have_zero_distance(self):
        matrix = [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]]
        dist = self.acc.fast_cosine_distance_matrix(matrix)
        self.assertAlmostEqual(dist[0][1], 0.0, places=9)

    def test_diagonal_is_always_zero(self):
        matrix = [[1.0, 0.0], [0.0, 1.0], [5.0, 5.0]]
        dist = self.acc.fast_cosine_distance_matrix(matrix)
        for i in range(len(matrix)):
            self.assertEqual(dist[i][i], 0.0)

    def test_orthogonal_vectors_distance_is_one(self):
        # cos(90 deg) = 0 -> distance = 1 - 0 = 1.0, hand-derived
        matrix = [[1.0, 0.0], [0.0, 1.0]]
        dist = self.acc.fast_cosine_distance_matrix(matrix)
        self.assertAlmostEqual(dist[0][1], 1.0, places=9)

    def test_opposite_vectors_clamp_to_two(self):
        # cos(180 deg) = -1 -> distance = 1 - (-1) = 2.0, the maximum clamp value
        matrix = [[1.0, 0.0], [-1.0, 0.0]]
        dist = self.acc.fast_cosine_distance_matrix(matrix)
        self.assertAlmostEqual(dist[0][1], 2.0, places=9)

    def test_zero_vector_gives_distance_one_not_crash(self):
        # A zero-norm row must not raise ZeroDivisionError -- must return 1.0
        matrix = [[0.0, 0.0], [1.0, 1.0]]
        dist = self.acc.fast_cosine_distance_matrix(matrix)
        self.assertEqual(dist[0][1], 1.0)

    def test_matrix_is_symmetric(self):
        import random
        rng = random.Random(3)
        matrix = [[rng.uniform(-5, 5) for _ in range(4)] for _ in range(6)]
        dist = self.acc.fast_cosine_distance_matrix(matrix)
        for i in range(6):
            for j in range(6):
                self.assertAlmostEqual(dist[i][j], dist[j][i], places=12)

    def test_single_vector_matrix(self):
        dist = self.acc.fast_cosine_distance_matrix([[1.0, 2.0, 3.0]])
        self.assertEqual(dist, [[0.0]])

    def test_matches_independent_reference_full_matrix(self):
        import random
        rng = random.Random(11)
        matrix = [[rng.uniform(-3, 3) for _ in range(5)] for _ in range(4)]
        dist = self.acc.fast_cosine_distance_matrix(matrix)
        for i in range(4):
            for j in range(4):
                expected = 0.0 if i == j else reference_cosine_distance(matrix[i], matrix[j])
                self.assertAlmostEqual(dist[i][j], expected, places=9)


def run_unit_test_suite():
    print("=" * 72)
    print("  CTYPES MATH ACCELERATOR — CORRECTNESS TEST SUITE")
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
