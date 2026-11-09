#!/usr/bin/env python3
"""
Computational Kabbalah: Honest Performance Benchmark Suite
Real NumPy-based computational validation (no simulated delays, no unfair comparisons)

LICENSING:
This benchmark is provided as-is under CC BY-SA 4.0.
All measurements are genuine, reproducible, and documented.

Author: Recursive Symbolics Observatory
Date: August 2026
"""

import sys
import time
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


class HonestBenchmarkSuite:
    """Production-grade benchmarks for Recursive Symbolics core operations."""
    
    def __init__(self):
        self.results = {}
        
    def benchmark_forward_pass(self):
        """BENCHMARK 1: Neural Network Forward Pass (DDPG-style control)
        
        Real-world scenario: A language model steering microservice processes
        an 18-dimensional state vector through a shallow network (18 → 32 → 4).
        
        Measures: Matrix multiplication + nonlinearities + clipping
        Iterations: 1,000 forward passes
        """
        print("\n BENCHMARK 1: Neural Network Forward Pass")
        print("   Context: DDPG control step in steering microservice")
        
        state_dim, hidden_dim, action_dim = 18, 32, 4
        iterations = 1_000

        # TESTABILITY FIX: seeded so the computed output is reproducible and
        # independently checkable (was previously unseeded np.random.randn(),
        # meaning no test could ever verify the computed values -- only that
        # timing was positive). Matches the seeding approach already used in
        # strict_honest_benchmark_suite.py.
        np.random.seed(123)
        # Initialize matrices (production-realistic scale)
        state = np.random.randn(state_dim)
        W1 = np.random.randn(state_dim, hidden_dim) / np.sqrt(state_dim)
        W2 = np.random.randn(hidden_dim, action_dim) / np.sqrt(hidden_dim)
        bias1 = np.zeros(hidden_dim)
        bias2 = np.zeros(action_dim)
        
        # Warmup (JIT cache, CPU scheduling)
        for _ in range(10):
            h = np.maximum(0, np.dot(state, W1) + bias1)
            _ = 1.0 / (1.0 + np.exp(-np.dot(h, W2) + bias2))
        
        # Actual benchmark
        start = time.perf_counter()
        for _ in range(iterations):
            h = np.maximum(0, np.dot(state, W1) + bias1)  # ReLU
            logits = np.dot(h, W2) + bias2
            probs = 1.0 / (1.0 + np.exp(-logits))  # Sigmoid
            action = np.clip(probs, 0.05, 0.95)  # Action bounds
        
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        per_step_us = (elapsed_ms / iterations) * 1000.0
        
        print(f"   Total Time    : {elapsed_ms:.3f} ms ({iterations} steps)")
        print(f"   Per-Step      : {per_step_us:.4f} µs")
        print(f"   Throughput    : {iterations / (elapsed_ms / 1000):.0f} steps/sec")
        print(f"   (raw timing only -- no correctness check performed in this file;")
        print(f"    see strict_honest_benchmark_suite.py for the version with")
        print(f"    independent-reference correctness checks before timing)")

        self.results['forward_pass_us'] = per_step_us
        self.results['forward_pass_sample_action'] = action.copy()
        return per_step_us
    
    def benchmark_matrix_solver(self):
        """BENCHMARK 2: Ridge Regression Solver (Closed-Form)
        
        Real-world scenario: Fitting a linear model to 100 observations
        with 20 features and L2 regularization.
        
        Measures: Closed-form (X^T X + λI)^-1 X^T y
        Iterations: 50 separate fits (simulating repeated diagnostics)
        """
        print("\n BENCHMARK 2: Ridge Regression Solver (Closed-Form)")
        print("   Context: Fitting team state diagnostic model")
        
        N, D = 100, 20  # 100 observations, 20 features
        np.random.seed(456)  # TESTABILITY FIX -- see benchmark_forward_pass note above
        X = np.random.randn(N, D)
        y = np.random.randn(N)
        alpha = 1.0  # Regularization strength
        
        # Pre-compute constant terms
        XtX = np.dot(X.T, X)
        Xty = np.dot(X.T, y)
        ridge_matrix = XtX + alpha * np.eye(D)
        
        # Warmup
        for _ in range(3):
            _ = np.linalg.solve(ridge_matrix, Xty)
        
        # Benchmark
        start = time.perf_counter()
        for _ in range(50):
            beta = np.linalg.solve(ridge_matrix, Xty)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        per_fit_ms = elapsed_ms / 50
        
        # Verify correctness (residual norm)
        residual = np.linalg.norm(np.dot(X, beta) - y)
        
        print(f"   Total Time    : {elapsed_ms:.3f} ms (50 fits)")
        print(f"   Per-Fit       : {per_fit_ms:.4f} ms")
        print(f"   L2 Residual   : {residual:.6f}")
        print(f"   (residual reported for reference only -- 'optimal for this scale'")
        print(f"    is a comparative claim with no baseline measured here)")

        self.results['ridge_solver_ms'] = per_fit_ms
        self.results['ridge_residual'] = float(residual)
        self.results['ridge_beta'] = beta.copy()
        self.results['ridge_X'] = X.copy()
        self.results['ridge_y'] = y.copy()
        return per_fit_ms
    
    def benchmark_entropy_calculation(self):
        """BENCHMARK 3: Shannon Entropy Calculation
        
        Real-world scenario: Computing symbolic entropy (H_s) from a
        probability distribution over 1 million state samples.
        
        Measures: H = -Σ p_i log(p_i) with numerical stability
        Iterations: 1 million values
        """
        print("\n BENCHMARK 3: Shannon Entropy Calculation (H_s)")
        print("   Context: Computing state entropy for diagnostic feedback")
        
        n_samples = 1_000_000
        np.random.seed(789)  # TESTABILITY FIX -- see benchmark_forward_pass note above
        values = np.random.rand(n_samples)
        values = values / values.sum()  # Normalize to probability distribution
        
        # Warmup
        _ = -np.sum(values[:1000] * np.log(values[:1000] + 1e-15))
        
        # Benchmark
        start = time.perf_counter()
        mask = values > 1e-10
        entropy = -np.sum(values[mask] * np.log(values[mask]))
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        
        print(f"   Total Time    : {elapsed_ms:.3f} ms ({n_samples:,} values)")
        print(f"   Entropy (bits): {entropy / np.log(2):.4f}")
        print(f"   (raw timing only -- no ground-truth entropy reference checked here)")

        self.results['entropy_ms'] = elapsed_ms
        self.results['entropy_bits'] = float(entropy / np.log(2))
        return elapsed_ms
    
    def benchmark_deterministic_consistency(self):
        """BENCHMARK 4: Deterministic State Transitions
        
        Real-world scenario: Verifying that S_{n+1} = F(S_n, E_n) produces
        identical results when called with the same inputs.
        
        Measures: Exact numerical consistency across 10,000 state transitions
        Requirement: Zero numerical divergence (bitwise identical)
        """
        print("\n BENCHMARK 4: Deterministic State Consistency")
        print("   Context: Verifying reproducibility of state transitions")
        
        def state_transition(s, e):
            """Simplified state evolution function."""
            output = np.sin(s + e) + np.cos(s - e)
            output = (output + 2) / 4  # Normalize to [0, 1]
            gamma = 1.0 - np.mean(np.abs(np.diff(output)))
            gamma = np.clip(gamma, 0, 1)
            return output, gamma
        
        # Run 1: Set seed, execute 10k steps
        seed = 42
        np.random.seed(seed)
        results_run1 = []
        for _ in range(10_000):
            s = np.random.randn(5)
            e = np.random.randn(5)
            _, gamma = state_transition(s, e)
            results_run1.append(gamma)
        
        # Run 2: Reset seed, execute same 10k steps
        np.random.seed(seed)
        results_run2 = []
        for _ in range(10_000):
            s = np.random.randn(5)
            e = np.random.randn(5)
            _, gamma = state_transition(s, e)
            results_run2.append(gamma)
        
        # Verify perfect consistency
        run1_array = np.array(results_run1)
        run2_array = np.array(results_run2)
        max_diff = np.max(np.abs(run1_array - run2_array))
        is_deterministic = np.allclose(run1_array, run2_array, atol=1e-15)
        
        print(f"   Runs Compared : 2 independent runs × 10,000 steps")
        print(f"   Max Diff      : {max_diff:.2e}")
        print(f"   Deterministic : {is_deterministic}")
        print(f"   (this is the one check in this file with a pass/fail condition;")
        print(f"    it is a within-session check only -- see limitations in")
        print(f"    strict_honest_benchmark_suite.py, item 5)")

        self.results['deterministic'] = is_deterministic
        return is_deterministic
    
    def run_full_suite(self):
        """Execute all benchmarks and print summary."""
        print("\n" + "=" * 80)
        print("  COMPUTATIONAL KABBALAH: HONEST BENCHMARK SUITE")
        print("  Real NumPy Performance Validation")
        print("=" * 80)
        
        self.benchmark_forward_pass()
        self.benchmark_matrix_solver()
        self.benchmark_entropy_calculation()
        self.benchmark_deterministic_consistency()
        
        # Summary
        # HONESTY FIX (found during test_all_engines.py verification pass):
        # this used to print " Status" claims for every benchmark
        # unconditionally -- not gated on any actual check -- and closed
        # with an unverifiable "production-ready" claim, exactly what
        # TESTING_STANDARD.md exists to prevent. Of the four benchmarks
        # here, only "Deterministic" computes an actual pass/fail condition;
        # the other three are raw timings with no correctness reference in
        # this file (see strict_honest_benchmark_suite.py for versions of
        # benchmarks 1 and 2 with independent-reference correctness checks).
        print("\n" + "=" * 80)
        print("  SUMMARY: RAW LATENCY NUMBERS (TIMING ONLY, SEE NOTES ABOVE)")
        print("=" * 80)
        print(f"  Forward Pass        : {self.results['forward_pass_us']:.4f} µs  (timing only, no correctness check here)")
        print(f"  Ridge Solver        : {self.results['ridge_solver_ms']:.4f} ms  (timing only, no correctness check here)")
        print(f"  Entropy Calc (1M)   : {self.results['entropy_ms']:.3f} ms  (timing only, no correctness check here)")
        print(f"  Deterministic       : {self.results['deterministic']}  (this one is an actual checked condition)")
        if self.results['deterministic']:
            print("\n  The one checkable claim in this file (determinism) held. The other")
            print("  three numbers are raw timings, not correctness-verified in this file.")
        else:
            print("\n  DETERMINISM CHECK FAILED -- state transitions were not reproducible.")
        print("=" * 80)
        return bool(self.results['deterministic'])


if __name__ == "__main__":
    suite = HonestBenchmarkSuite()
    ok = suite.run_full_suite()
    sys.exit(0 if ok else 1)
