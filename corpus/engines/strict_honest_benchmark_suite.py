#!/usr/bin/env python3
"""
strict_honest_benchmark_suite.py
Rigorous Standalone Performance & Correctness Benchmark Suite.

HARD CONSTRAINTS ENFORCED:
1. NO SIMULATED COMPARISONS: Standalone absolute numbers only. No artificial delays.
2. NO MISMATCHED COMPARISONS: Correctness verified against analytical ground-truth first.
3. CORRECTNESS BEFORE SPEED: Output verified against known-good reference values.
4. REPORT VARIANCE: 15 runs per benchmark (after 3 warmup runs). Reports Mean, Median, Min, Max, StdDev.
5. DISCLOSE ENVIRONMENT: OS, CPU architecture, Python version, NumPy version disclosed.
6. NO UNVERIFIABLE CLAIMS: Objective technical labels only. No "production-ready" / "enterprise-grade" claims.
7. LIMITATIONS DISCLOSURE: Explicit "Limitations" section printed at conclusion.

License: CC BY-SA 4.0
"""

import sys
import platform
import time
import numpy as np
import statistics

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

N_RUNS = 15
N_WARMUP = 3


# ==============================================================================
# ENVIRONMENT DISCLOSURE
# ==============================================================================
def print_environment_disclosure():
    print("=" * 80)
    print("  ENVIRONMENT DISCLOSURE & BENCHMARK METADATA")
    print("=" * 80)
    print(f"  Operating System      : {platform.system()} {platform.release()}")
    print(f"  CPU Architecture      : {platform.machine()} ({platform.processor() or 'unspecified'})")
    print(f"  Python Version        : {sys.version.split()[0]}")
    print(f"  NumPy Version         : {np.__version__}")
    print(f"  Execution Environment : Unverified — this script cannot detect whether")
    print(f"                          it is running on dedicated hardware, a shared")
    print(f"                          cloud container, or a VM. Reader should not")
    print(f"                          assume dedicated/isolated hardware.")
    clock_info = time.get_clock_info('perf_counter')
    print(f"  Timer Resolution      : {clock_info.resolution:.2e} s (perf_counter)")
    print("=" * 80 + "\n")


def stats_block(samples, unit):
    """Compute and format mean/median/min/max/stdev from a list of timing samples."""
    mean = statistics.mean(samples)
    median = statistics.median(samples)
    stdev = statistics.stdev(samples) if len(samples) > 1 else 0.0
    lo, hi = min(samples), max(samples)
    rel_stdev_pct = (stdev / mean * 100) if mean > 0 else 0.0
    return {
        "mean": mean, "median": median, "stdev": stdev,
        "min": lo, "max": hi, "unit": unit, "rel_stdev_pct": rel_stdev_pct
    }


def print_stats(label, s):
    print(f"   {label}")
    print(f"     Mean   : {s['mean']:.4f} {s['unit']}")
    print(f"     Median : {s['median']:.4f} {s['unit']}")
    print(f"     Min/Max: {s['min']:.4f} / {s['max']:.4f} {s['unit']}")
    print(f"     StdDev : {s['stdev']:.4f} {s['unit']} ({s['rel_stdev_pct']:.1f}% of mean)")
    if s['rel_stdev_pct'] > 25:
        print(f"     NOTE   : High variance (>{25}% of mean). Treat mean as unstable;")
        print(f"              re-run on quiet system before citing.")


# ==============================================================================
# BENCHMARK 1: Forward Pass (Correctness-Verified)
# ==============================================================================
def benchmark_forward_pass():
    print("\n" + "-" * 80)
    print("BENCHMARK 1: Neural Network Forward Pass")
    print("-" * 80)
    print("Real-world scenario claimed: steering microservice control step")
    print("(18-dim state -> 32 hidden -> 4-dim action, ReLU + Sigmoid + clip)\n")

    state_dim, hidden_dim, action_dim = 18, 32, 4
    iters_per_run = 1000

    rng = np.random.default_rng(seed=42)
    state = rng.standard_normal(state_dim)
    W1 = rng.standard_normal((state_dim, hidden_dim)) / np.sqrt(state_dim)
    W2 = rng.standard_normal((hidden_dim, action_dim)) / np.sqrt(hidden_dim)
    b1 = np.zeros(hidden_dim)
    b2 = np.zeros(action_dim)

    def forward(s):
        h = np.maximum(0, np.dot(s, W1) + b1)
        logits = np.dot(h, W2) + b2
        probs = 1.0 / (1.0 + np.exp(-logits))
        return np.clip(probs, 0.05, 0.95)

    # --- CORRECTNESS CHECK (before timing) ---
    # Verify against an independently-computed reference using plain Python loops
    # (slow but unambiguous ground truth for this one input — deliberately not
    # sharing any NumPy vectorized code path with the implementation under test).
    import math
    def forward_reference(s):
        h = [max(0.0, sum(s[i] * W1[i, j] for i in range(state_dim)) + b1[j]) for j in range(hidden_dim)]
        out = [1.0 / (1.0 + math.exp(-(sum(h[j] * W2[j, k] for j in range(hidden_dim)) + b2[k]))) for k in range(action_dim)]
        return np.clip(np.array(out), 0.05, 0.95)

    vectorized_result = forward(state)
    reference_result = forward_reference(state)
    max_error = np.max(np.abs(vectorized_result - reference_result))
    correctness_pass = max_error < 1e-9

    print(f"   Correctness check: vectorized vs. independent pure-Python reference")
    print(f"     Max absolute error: {max_error:.2e}")
    print(f"     Result: {'PASS' if correctness_pass else 'FAIL'}")
    if not correctness_pass:
        print("     WARNING: correctness check failed. Timing results below are not valid.")

    # --- WARMUP (discarded) ---
    for _ in range(N_WARMUP):
        for _ in range(iters_per_run):
            forward(state)

    # --- TIMED RUNS ---
    samples_us = []
    for _ in range(N_RUNS):
        start = time.perf_counter()
        for _ in range(iters_per_run):
            forward(state)
        elapsed = time.perf_counter() - start
        per_step_us = (elapsed / iters_per_run) * 1e6
        samples_us.append(per_step_us)

    s = stats_block(samples_us, "µs/step")
    print()
    print_stats(f"Per-step latency ({N_RUNS} runs x {iters_per_run} iters each)", s)
    return {"correctness_pass": correctness_pass, "stats": s}


# ==============================================================================
# BENCHMARK 2: Ridge Regression Solver (Correctness-Verified)
# ==============================================================================
def benchmark_ridge_solver():
    print("\n" + "-" * 80)
    print("BENCHMARK 2: Ridge Regression Closed-Form Solver")
    print("-" * 80)
    print("Real-world scenario claimed: fitting a diagnostic model to")
    print("100 observations x 20 features with L2 regularization\n")

    N, D = 100, 20
    rng = np.random.default_rng(seed=7)
    X = rng.standard_normal((N, D))
    true_beta = rng.standard_normal(D)
    noise = rng.standard_normal(N) * 0.1
    y = X @ true_beta + noise
    alpha = 1.0

    XtX = X.T @ X
    Xty = X.T @ y
    ridge_matrix = XtX + alpha * np.eye(D)

    # --- CORRECTNESS CHECK ---
    # Ground truth: sklearn-equivalent closed form, verified via independent
    # pseudo-inverse computation (different algorithm path than np.linalg.solve).
    beta_solve = np.linalg.solve(ridge_matrix, Xty)
    beta_pinv = np.linalg.pinv(ridge_matrix) @ Xty
    cross_method_error = np.max(np.abs(beta_solve - beta_pinv))
    # Sanity: recovered beta should be reasonably close to true_beta (regularized, so not exact)
    recovery_error = np.linalg.norm(beta_solve - true_beta) / np.linalg.norm(true_beta)
    correctness_pass = cross_method_error < 1e-6

    print(f"   Correctness check: np.linalg.solve() vs. np.linalg.pinv() (independent method)")
    print(f"     Max coefficient difference: {cross_method_error:.2e}")
    print(f"     Result: {'PASS' if correctness_pass else 'FAIL'}")
    print(f"   Sanity check: relative error vs. true synthetic beta: {recovery_error:.4f}")
    print(f"     (nonzero is expected — this is regularized, not exact recovery)")

    # --- WARMUP ---
    for _ in range(N_WARMUP):
        np.linalg.solve(ridge_matrix, Xty)

    # --- TIMED RUNS (each run = 50 solves, matching original claimed workload) ---
    fits_per_run = 50
    samples_ms = []
    for _ in range(N_RUNS):
        start = time.perf_counter()
        for _ in range(fits_per_run):
            np.linalg.solve(ridge_matrix, Xty)
        elapsed = time.perf_counter() - start
        per_fit_ms = (elapsed / fits_per_run) * 1000
        samples_ms.append(per_fit_ms)

    s = stats_block(samples_ms, "ms/fit")
    print()
    print_stats(f"Per-fit latency ({N_RUNS} runs x {fits_per_run} fits each)", s)
    return {"correctness_pass": correctness_pass, "stats": s}


# ==============================================================================
# BENCHMARK 3: Deterministic State Transition Consistency
# ==============================================================================
def benchmark_determinism():
    print("\n" + "-" * 80)
    print("BENCHMARK 3: Deterministic State Transition Consistency")
    print("-" * 80)
    print("Claim under test: S_(n+1) = F(S_n, E_n) produces bitwise-identical")
    print("output across independent runs given identical inputs and seed.\n")

    def state_transition(s, e):
        output = np.sin(s + e) + np.cos(s - e)
        output = (output + 2) / 4
        gamma = 1.0 - np.mean(np.abs(np.diff(output)))
        return output, np.clip(gamma, 0, 1)

    def run_sequence(seed, n_steps=10_000):
        rng = np.random.default_rng(seed)
        gammas = np.empty(n_steps)
        for i in range(n_steps):
            s = rng.standard_normal(5)
            e = rng.standard_normal(5)
            _, gamma = state_transition(s, e)
            gammas[i] = gamma
        return gammas

    run_a = run_sequence(seed=42)
    run_b = run_sequence(seed=42)
    max_diff = np.max(np.abs(run_a - run_b))
    exact_match = np.array_equal(run_a, run_b)

    print(f"   Two independent runs, 10,000 steps each, identical seed")
    print(f"   Max absolute difference : {max_diff:.2e}")
    print(f"   Bitwise identical       : {exact_match}")
    print(f"   Result: {'PASS' if exact_match else 'FAIL — nondeterminism detected'}")

    return {"correctness_pass": bool(exact_match), "max_diff": float(max_diff)}


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print_environment_disclosure()
    print("Each timed benchmark: 3 warmup runs (discarded) + 15 measured runs.")
    print("Correctness is verified BEFORE timing for every benchmark that")
    print("produces a numerical result.\n")

    r1 = benchmark_forward_pass()
    r2 = benchmark_ridge_solver()
    r3 = benchmark_determinism()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    all_correct = r1["correctness_pass"] and r2["correctness_pass"] and r3["correctness_pass"]
    print(f"  Forward pass   : {r1['stats']['mean']:.4f} µs/step (mean, n={N_RUNS})  "
          f"[correctness: {'PASS' if r1['correctness_pass'] else 'FAIL'}]")
    print(f"  Ridge solver   : {r2['stats']['mean']:.4f} ms/fit  (mean, n={N_RUNS})  "
          f"[correctness: {'PASS' if r2['correctness_pass'] else 'FAIL'}]")
    print(f"  Determinism    : {'exact match' if r3['correctness_pass'] else 'MISMATCH'} "
          f"(max diff {r3['max_diff']:.2e})")
    print(f"\n  Overall correctness: {'ALL PASS' if all_correct else 'AT LEAST ONE FAILURE — do not cite these numbers'}")

    print("\n" + "=" * 80)
    print("LIMITATIONS — READ BEFORE CITING THESE NUMBERS")
    print("=" * 80)
    print("""
  1. NO COMPARATIVE BASELINE. This suite does not benchmark against PyTorch,
     scikit-learn, or any other framework. All numbers are absolute,
     standalone measurements of this implementation only. Any claim of
     being "faster than X" would require actually running X's real code
     on the same machine in the same session — that has not been done here.

  2. SINGLE-MACHINE, SINGLE-SESSION. These numbers reflect one machine at
     one point in time. CPU frequency scaling, thermal state, background
     processes, and OS scheduling all affect results. Run-to-run variance
     within this session is reported above (StdDev); variance ACROSS
     different sessions/machines/times of day may be larger and has not
     been characterized.

  3. MICROBENCHMARK, NOT SYSTEM BENCHMARK. These test isolated function
     calls in a tight loop. They do not include network I/O, disk I/O,
     process startup, concurrent load, or integration overhead. Real
     end-to-end latency in a deployed system will be higher than these
     numbers, likely substantially.

  4. SMALL, FIXED PROBLEM SIZES. Forward pass uses an 18/32/4 architecture;
     ridge solver uses 100x20 data. Performance at other scales has not
     been measured and should not be assumed to follow the same numbers
     or even the same scaling behavior.

  5. "DETERMINISTIC" HERE MEANS: this specific computation, on this
     machine, with this NumPy/BLAS build, is repeatable within a session.
     It does NOT establish bitwise reproducibility across different
     hardware, OS, NumPy versions, or BLAS backends (MKL vs OpenBLAS vs
     Accelerate can produce different floating-point results for the
     same operations).

  6. NOT INDEPENDENTLY REPRODUCED. These results have been generated by
     the author's own script on the author's own claim. They have not
     been verified by a third party or run on separate hardware by
     someone else. A skeptical reader should re-run this script
     themselves before relying on the numbers in a decision.
""")
    print("=" * 80)

    # BUG FIX (found during test_all_engines.py verification pass): this
    # function used to print "FAIL" on a correctness check and still return
    # normally, meaning the process always exited 0 -- the exact "exit code
    # 0 means nothing" failure mode TESTING_STANDARD.md exists to prevent,
    # undetected in the one file whose whole purpose is preventing it.
    # Confirmed via injection: corrupting benchmark_forward_pass()'s internal
    # computation made it print "Result: FAIL" while the script still exited
    # 0. Gate the exit code on the actual correctness results now so a
    # calling harness (e.g. test_all_engines.py) can tell the difference
    # between "ran" and "ran and was correct."
    return all_correct


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
