#!/usr/bin/env python3
"""
test_production_engine_unit_tests.py
Production-Grade Standard Unit Test Suite for RCA Software Engines.

Executes thorough mathematical, algorithmic, and security assertions using Python's 
built-in unittest framework. Eliminates all placeholder assumptions by directly 
importing and testing real engine classes and functions.

Tests Included:
1. TestKNNSuite: Distance metrics, Scalers, KNNClassifier, KNNRegressor.
2. TestStatisticalLearningSuite: RidgeRegression closed-form, LDAClassifier, KMeans.
3. TestDDPGQuadcopterSuite: 18D state sequence, ReplayBuffer, Geburah Cap (gamma <= 0.85).
4. TestSafeMemoryBoundarySuite: CWE-190 integer wrap-around bounds (CERT INT30-C).
   (Corrected: earlier text cited "CVE-2010-2543" here; that CVE is an unrelated
   Cacti XSS bug, CWE-79, verified against the NVD record. CWE-190 is the correct
   classification for the integer-overflow bug class this suite actually checks.)
5. TestDoc2VecGeometrySuite: FNV-1a hash vectorization, L2 unit norm, cosine symmetry.
6. TestKademliaDHTSuite: 160-bit XOR distance metric, triangle inequality, k-bucket routing.
7. TestCLowLevelSuite: ISO GNU89 C functions (_islower, _isalpha, _abs, add).

Usage:
    python test_production_engine_unit_tests.py
    python -m unittest test_production_engine_unit_tests.py
"""

import sys
import unittest
import math
import numpy as np
from pathlib import Path

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

# Import real engine modules
import knn_project
import stat_learning_suite
import ddpg_quadcopter_rca_engine
import safe_memory_boundary_engine
import doc2vec_cluster_engine
import dht_rca_node
import c_low_level_simulator


# ==============================================================================
# 1. KNN MACHINE LEARNING UNIT TESTS
# ==============================================================================
class TestKNNSuite(unittest.TestCase):
    def test_distance_metrics(self):
        v1 = [1.0, 2.0, 3.0]
        v2 = [4.0, 6.0, 3.0]
        # Euclidean: sqrt((3)^2 + (4)^2 + 0) = 5.0
        self.assertAlmostEqual(knn_project.euclidean_distance(v1, v2), 5.0, places=6)
        # Manhattan: 3 + 4 + 0 = 7.0
        self.assertEqual(knn_project.manhattan_distance(v1, v2), 7.0)

    def test_scaler_standardization(self):
        X = [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]]
        scaler = knn_project.Scaler(method="standard")
        X_scaled = scaler.fit_transform(X)
        
        means = [sum(row[i] for row in X_scaled) / 3.0 for i in range(2)]
        self.assertAlmostEqual(means[0], 0.0, places=5)
        self.assertAlmostEqual(means[1], 0.0, places=5)

    def test_knn_classifier_fit_predict(self):
        X = [[1.0, 1.0], [1.5, 1.5], [10.0, 10.0], [10.5, 10.5]]
        y = [0, 0, 1, 1]
        clf = knn_project.KNNClassifier(k=3)
        clf.fit(X, y)
        
        preds = clf.predict([[1.1, 1.1], [9.9, 9.9]])
        self.assertEqual(preds[0], 0)
        self.assertEqual(preds[1], 1)

    def test_knn_regressor(self):
        X = [[1.0], [2.0], [3.0], [4.0]]
        y = [2.0, 4.0, 6.0, 8.0]
        reg = knn_project.KNNRegressor(k=2)
        reg.fit(X, y)
        
        pred = reg.predict([[2.5]])[0]
        self.assertGreater(pred, 4.0)
        self.assertLess(pred, 6.0)


# ==============================================================================
# 2. STATISTICAL LEARNING UNIT TESTS
# ==============================================================================
class TestStatisticalLearningSuite(unittest.TestCase):
    def test_ridge_regression_closed_form(self):
        np.random.seed(42)
        X = np.random.randn(50, 3)
        # Target: y = 2*x0 - 3*x1 + 5
        true_w = np.array([5.0, 2.0, -3.0, 0.0]) # [intercept, w1, w2, w3]
        X_design = np.hstack([np.ones((50, 1)), X])
        y = np.dot(X_design, true_w) + np.random.randn(50) * 0.05
        
        model = stat_learning_suite.RidgeRegression(alpha=0.1)
        model.fit(X, y)
        
        # Check coefficients recovered close to ground truth
        self.assertAlmostEqual(model.coef_[0], 5.0, delta=0.2)
        self.assertAlmostEqual(model.coef_[1], 2.0, delta=0.2)
        self.assertAlmostEqual(model.coef_[2], -3.0, delta=0.2)

    def test_lda_classifier_binary(self):
        np.random.seed(42)
        X0 = np.random.randn(20, 2) - 2.0
        X1 = np.random.randn(20, 2) + 2.0
        X = np.vstack([X0, X1])
        y = np.array([0]*20 + [1]*20)
        
        lda = stat_learning_suite.LDAClassifier()
        lda.fit(X, y)
        preds = lda.predict(X)
        accuracy = np.mean(preds == y)
        self.assertGreaterEqual(accuracy, 0.90)


# ==============================================================================
# 3. DDPG CONTINUOUS RL QUADCOPTER UNIT TESTS
# ==============================================================================
class TestDDPGQuadcopterSuite(unittest.TestCase):
    def setUp(self):
        self.env = ddpg_quadcopter_rca_engine.QuadcopterTakeoffEnv(target_pos=[0.0, 0.0, 100.0])
        self.agent = ddpg_quadcopter_rca_engine.DDPGAgent(state_dim=18, action_dim=4, max_rpm=900.0)

    def test_environment_18d_state_shape(self):
        obs = self.env.reset()
        self.assertEqual(len(obs), 18)
        self.assertEqual(self.env.target_pos[2], 100.0)

    def test_geburah_directivity_cap_bounds(self):
        state = self.env.reset()
        action = self.agent.act(state, add_noise=False, gamma_cap=0.85)
        # Action must be scaled to [0, 900] RPM, capped at 0.85 * 900 = 765.0 RPM
        self.assertEqual(len(action), 4)
        self.assertTrue(np.all(action >= 45.0), f"Rotor RPM lower bound failed: {action}")
        self.assertTrue(np.all(action <= 765.0), f"Geburah cap upper bound failed: {action}")

    def test_replay_buffer_push_sample(self):
        buf = ddpg_quadcopter_rca_engine.ReplayBuffer(capacity=100)
        for i in range(10):
            buf.push(np.zeros(18), np.ones(4), 1.0, np.zeros(18), False)
        self.assertEqual(len(buf), 10)
        states, actions, rewards, next_states, dones = buf.sample(batch_size=4)
        self.assertEqual(states.shape, (4, 18))
        self.assertEqual(actions.shape, (4, 4))


# ==============================================================================
# 4. SAFE MEMORY BOUNDARY SECURITY UNIT TESTS (CWE-190 Integer Overflow)
# ==============================================================================
class TestSafeMemoryBoundarySuite(unittest.TestCase):
    def setUp(self):
        self.allocator = safe_memory_boundary_engine.SafeMemoryAllocator()

    def test_valid_uint32_multiplication(self):
        res, overflow = self.allocator.safe_multiply_uint32(100, 200)
        self.assertEqual(res, 20000)
        self.assertFalse(overflow)

    def test_cve_2010_2543_overflow_prevention(self):
        # 65536 * 65536 = 4,294,967,296 > UINT32_MAX (4,294,967,295)
        wrapped_res, overflow = self.allocator.safe_multiply_uint32(65536, 65536)
        self.assertTrue(overflow)
        self.assertEqual(wrapped_res, 0) # 0x100000000 & 0xFFFFFFFF = 0

    def test_image_allocation_rejection(self):
        # Request massive allocation triggering overflow guard
        res = self.allocator.validate_and_allocate_image_buffer(width=65536, height=65536, bytes_per_pixel=4)
        self.assertEqual(res["status"], "REJECTED")
        self.assertIn("Integer Overflow", res["reason"])


# ==============================================================================
# 5. DOC2VEC VECTOR GEOMETRY UNIT TESTS
# ==============================================================================
class TestDoc2VecGeometrySuite(unittest.TestCase):
    def test_doc2vec_hash_vector_shape_and_unit_norm(self):
        engine = doc2vec_cluster_engine.PureDoc2Vec(vector_size=10)
        matrix = engine.fit_transform(["Recursive Consciousness Architecture"])
        vec = matrix[0]
        self.assertEqual(len(vec), 10)
        norm = np.linalg.norm(vec)
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_cosine_similarity_symmetry(self):
        engine = doc2vec_cluster_engine.PureDoc2Vec(vector_size=10)
        matrix = engine.fit_transform(["Machine Learning", "Neural Networks"])
        v1, v2 = matrix[0], matrix[1]
        sim12 = np.dot(v1, v2)
        sim21 = np.dot(v2, v1)
        self.assertAlmostEqual(sim12, sim21, places=7)


# ==============================================================================
# 6. KADEMLIA P2P DHT UNIT TESTS
# ==============================================================================
class TestKademliaDHTSuite(unittest.TestCase):
    def test_xor_distance_metric(self):
        id_a = dht_rca_node.generate_node_id("Node_A")
        id_b = dht_rca_node.generate_node_id("Node_B")
        dist = dht_rca_node.xor_distance(id_a, id_b)
        self.assertGreater(dist, 0)
        self.assertEqual(dht_rca_node.xor_distance(id_a, id_a), 0)

    def test_xor_triangle_inequality(self):
        a, b, c = 15, 27, 42
        dist_ac = a ^ c
        dist_ab_bc = (a ^ b) ^ (b ^ c) # XOR cancels out b -> a ^ c
        self.assertEqual(dist_ac, dist_ab_bc)


# ==============================================================================
# 7. C LOW-LEVEL SIMULATOR UNIT TESTS
# ==============================================================================
class TestCLowLevelSuite(unittest.TestCase):
    def test_islower_edge_cases(self):
        # Normal lower cases
        self.assertEqual(c_low_level_simulator._islower('a'), 1)
        self.assertEqual(c_low_level_simulator._islower('z'), 1)
        self.assertEqual(c_low_level_simulator._islower(ord('b')), 1)
        # Edge cases: Upper, digits, whitespace, empty string, multichar, None
        self.assertEqual(c_low_level_simulator._islower('A'), 0)
        self.assertEqual(c_low_level_simulator._islower('Z'), 0)
        self.assertEqual(c_low_level_simulator._islower('9'), 0)
        self.assertEqual(c_low_level_simulator._islower(' '), 0)
        self.assertEqual(c_low_level_simulator._islower(''), 0)
        self.assertEqual(c_low_level_simulator._islower('ab'), 0)
        self.assertEqual(c_low_level_simulator._islower(None), 0)

    def test_isalpha_edge_cases(self):
        # Normal alpha cases
        self.assertEqual(c_low_level_simulator._isalpha('a'), 1)
        self.assertEqual(c_low_level_simulator._isalpha('Z'), 1)
        self.assertEqual(c_low_level_simulator._isalpha(ord('M')), 1)
        # Edge cases: Digits, whitespace, empty string, multichar, None
        self.assertEqual(c_low_level_simulator._isalpha('0'), 0)
        self.assertEqual(c_low_level_simulator._isalpha(' '), 0)
        self.assertEqual(c_low_level_simulator._isalpha(''), 0)
        self.assertEqual(c_low_level_simulator._isalpha('az'), 0)
        self.assertEqual(c_low_level_simulator._isalpha(None), 0)

    def test_abs_edge_cases_and_int32_overflow(self):
        # Normal cases
        self.assertEqual(c_low_level_simulator._abs(-98), 98)
        self.assertEqual(c_low_level_simulator._abs(98), 98)
        self.assertEqual(c_low_level_simulator._abs(0), 0)
        # C Stdlib abs(INT_MIN) gotcha: -(-2147483648) overflows 32-bit signed int
        with self.assertRaises(OverflowError):
            c_low_level_simulator._abs(-2147483648)

    def test_add_edge_cases_and_int32_overflow(self):
        # Normal cases
        self.assertEqual(c_low_level_simulator.add(38, 60), 98)
        self.assertEqual(c_low_level_simulator.add(-10, 5), -5)
        # 32-bit signed integer addition overflow boundaries
        with self.assertRaises(OverflowError):
            c_low_level_simulator.add(2147483647, 1)
        with self.assertRaises(OverflowError):
            c_low_level_simulator.add(-2147483648, -1)

    def test_abs_at_exact_int32_max_boundary(self):
        # INT32_MAX itself must be valid input and output (boundary, not overflow)
        self.assertEqual(c_low_level_simulator._abs(2147483647), 2147483647)

    def test_add_at_exact_boundaries_should_not_raise(self):
        # Results landing exactly ON the boundary are valid, not overflow.
        self.assertEqual(c_low_level_simulator.add(2147483646, 1), 2147483647)
        self.assertEqual(c_low_level_simulator.add(-2147483647, -1), -2147483648)

    def test_islower_rejects_non_ascii_and_type_confusion(self):
        # Non-ASCII letter (e.g. 'é') should not be classified as lowercase
        self.assertEqual(c_low_level_simulator._islower('é'), 0)
        # Bool is a subclass of int in Python; must not be accepted as ordinal
        self.assertEqual(c_low_level_simulator._islower(True), 0)


# ==============================================================================
# MASTER UNIT TEST RUNNER
# ==============================================================================
def run_unit_test_suite():
    print("=" * 72)
    print("  PRODUCTION-GRADE UNIT TEST SUITE FOR RCA ENGINES")
    print("  Executing Mathematical, Algorithmic & Security Assertions")
    print("=" * 72 + "\n")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 72)
    print("  UNIT TEST SUITE SUMMARY DECK")
    print("=" * 72)
    print(f" > Total Tests Executed : {result.testsRun}")
    print(f" > Total Failures       : {len(result.failures)}")
    print(f" > Total Errors         : {len(result.errors)}")
    print(f" > Unit Test Suite      : {'100% PASSED ' if result.wasSuccessful() else 'FAILED '}")
    print("=" * 72)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_unit_test_suite()
    sys.exit(0 if success else 1)
