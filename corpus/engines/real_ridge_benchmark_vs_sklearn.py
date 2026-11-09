#!/usr/bin/env python3
"""
real_ridge_benchmark_vs_sklearn.py
Genuine head-to-head benchmark: RCA closed-form Ridge vs real scikit-learn Ridge.

This REPLACES the fabricated comparison in benchmark_simulation_vs_current.py,
which used time.sleep() to simulate a competitor instead of running one.
This script imports and runs actual scikit-learn -- no simulation.

Per TESTING_STANDARD.md: correctness is checked BEFORE timing, environment is
disclosed, and warmup runs are discarded before measurement.
"""
import sys
import platform
import time
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import stat_learning_suite as eng

try:
    import sklearn
    from sklearn.linear_model import Ridge as SKRidge
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def main():
    print("=" * 78)
    print("  ENVIRONMENT DISCLOSURE")
    print("=" * 78)
    print(f"  Python     : {platform.python_version()}")
    print(f"  NumPy      : {np.__version__}")
    print(f"  scikit-learn: {sklearn.__version__ if HAS_SKLEARN else 'NOT INSTALLED'}")
    print(f"  Timer      : time.perf_counter()")
    print("=" * 78)

    if not HAS_SKLEARN:
        print("scikit-learn not installed -- cannot run real comparison. Exiting.")
        sys.exit(1)

    rng = np.random.default_rng(7)
    N, D = 100, 20
    X = rng.normal(size=(N, D))
    true_beta = rng.normal(size=D)
    y = X @ true_beta + rng.normal(scale=0.1, size=N)

    # --- Correctness FIRST, before any timing ---
    rca = eng.RidgeRegression(alpha=1.0)
    rca.fit(X, y)
    rca_pred = rca.predict(X)

    sk = SKRidge(alpha=1.0, fit_intercept=True)
    sk.fit(X, y)
    sk_pred = sk.predict(X)

    max_diff = float(np.max(np.abs(rca_pred - sk_pred)))
    agree = np.allclose(rca_pred, sk_pred, atol=1e-6)
    print(f"\nCorrectness check: RCA vs sklearn predictions agree (atol=1e-6): {agree}")
    print(f"Max abs prediction difference: {max_diff:.3e}")
    if not agree:
        print("STOP: implementations disagree -- timing comparison would be meaningless.")
        sys.exit(1)

    # --- Timing: 3 warmup trials discarded, then 5 measured trials of 50 fits each ---
    def time_fits(fit_fn, n=50, repeats=5):
        times = []
        for _ in range(repeats):
            start = time.perf_counter()
            for _ in range(n):
                fit_fn()
            times.append((time.perf_counter() - start) * 1000.0)
        return times

    for _ in range(3):
        eng.RidgeRegression(alpha=1.0).fit(X, y)
        SKRidge(alpha=1.0).fit(X, y)

    rca_times = time_fits(lambda: eng.RidgeRegression(alpha=1.0).fit(X, y))
    sk_times = time_fits(lambda: SKRidge(alpha=1.0, fit_intercept=True).fit(X, y))

    print(f"\nRCA closed-form  (50 fits/trial, 5 trials): "
          f"mean {np.mean(rca_times):.4f} ms, std {np.std(rca_times):.4f}, "
          f"min {np.min(rca_times):.4f}, max {np.max(rca_times):.4f}")
    print(f"sklearn Ridge    (50 fits/trial, 5 trials): "
          f"mean {np.mean(sk_times):.4f} ms, std {np.std(sk_times):.4f}, "
          f"min {np.min(sk_times):.4f}, max {np.max(sk_times):.4f}")
    print(f"\nReal measured ratio (sklearn/RCA): {np.mean(sk_times)/np.mean(rca_times):.2f}x")

    print("\n" + "=" * 78)
    print("  LIMITATIONS")
    print("=" * 78)
    print("  - Single dataset shape (100x20), alpha=1.0. Not swept across sizes.")
    print("  - scikit-learn's Ridge solver defaults (solver='auto') were used as-is;")
    print("    no attempt was made to pick the fastest sklearn solver variant.")
    print("  - This does NOT benchmark DDPG vs PyTorch -- that comparison has been")
    print("    retracted pending a real (non-simulated) implementation.")
    print("=" * 78)


if __name__ == "__main__":
    main()
