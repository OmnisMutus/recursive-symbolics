#!/usr/bin/env python3
"""
test_doc2vec_cluster_engine.py
Correctness test for doc2vec_cluster_engine.py, per TESTING_STANDARD.md.

Ground truth: numpy's own np.dot / np.linalg.norm, called directly in this
test file (a different code path than the engine's hand-rolled
vector_norm()/dot_product() functions in cosine_distance_pure()).

Edge cases covered: empty vectors, zero vectors, identical vectors,
orthogonal vectors, opposite vectors, documents with no alnum tokens,
single-document corpus.

Break-it proof: see BREAK_IT_INSTRUCTIONS at the bottom of this file.
"""
import sys
import math
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import doc2vec_cluster_engine as eng

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}  {detail}")

def numpy_ground_truth_cosine_distance(v1, v2):
    a, b = np.array(v1, dtype=float), np.array(v2, dtype=float)
    n1, n2 = np.linalg.norm(a), np.linalg.norm(b)
    if n1 == 0 or n2 == 0:
        return 1.0
    cos_sim = float(np.dot(a, b) / (n1 * n2))
    return max(0.0, min(2.0, 1.0 - cos_sim))

# ---------------------------------------------------------------------------
# 1. GROUND TRUTH: compare pure-python implementation against numpy, on
#    randomized vectors it has never seen (not corpus-derived, not tuned to).
# ---------------------------------------------------------------------------
rng = np.random.default_rng(42)
for trial in range(20):
    v1 = rng.uniform(-5, 5, size=10).tolist()
    v2 = rng.uniform(-5, 5, size=10).tolist()
    got = eng.cosine_distance_pure(v1, v2)
    expected = numpy_ground_truth_cosine_distance(v1, v2)
    check(f"cosine_distance_pure matches numpy ground truth (trial {trial})",
          math.isclose(got, expected, abs_tol=1e-9),
          f"got={got} expected={expected}")

# ---------------------------------------------------------------------------
# 2. BOUNDARY / EDGE CASES
# ---------------------------------------------------------------------------
check("identical vectors -> distance 0",
      math.isclose(eng.cosine_distance_pure([1,2,3], [1,2,3]), 0.0, abs_tol=1e-9))

check("orthogonal unit vectors -> distance 1",
      math.isclose(eng.cosine_distance_pure([1,0], [0,1]), 1.0, abs_tol=1e-9))

check("opposite vectors -> distance 2",
      math.isclose(eng.cosine_distance_pure([1,0], [-1,0]), 2.0, abs_tol=1e-9))

check("zero vector vs nonzero -> defined as 1.0 (no div-by-zero crash)",
      eng.cosine_distance_pure([0,0,0], [1,2,3]) == 1.0)

check("both zero vectors -> defined as 1.0, not NaN",
      eng.cosine_distance_pure([0,0,0], [0,0,0]) == 1.0)

check("empty vector lists don't crash -> distance 1.0",
      eng.cosine_distance_pure([], []) == 1.0)

# fit_transform edge cases
model = eng.PureDoc2Vec(vector_size=10)

empty_corpus_matrix = model.fit_transform([])
check("empty document corpus -> empty matrix, no crash",
      len(empty_corpus_matrix) == 0)

punct_only_matrix = model.fit_transform(["!!! ??? --- ..."])
v = punct_only_matrix[0]
v_list = v.tolist() if hasattr(v, "tolist") else v
check("document with no alnum tokens -> zero vector (all filtered out)",
      all(x == 0.0 for x in v_list), f"got {v_list}")

single_doc_matrix = model.fit_transform(["hello world"])
check("single-document corpus -> 1xD matrix",
      len(single_doc_matrix) == 1 and len(single_doc_matrix[0]) == 10)

identical_docs_matrix = model.fit_transform(["same text here", "same text here"])
d = eng.cosine_distance_pure(
    identical_docs_matrix[0].tolist() if hasattr(identical_docs_matrix[0], "tolist") else identical_docs_matrix[0],
    identical_docs_matrix[1].tolist() if hasattr(identical_docs_matrix[1], "tolist") else identical_docs_matrix[1],
)
check("identical documents -> pairwise distance ~0", math.isclose(d, 0.0, abs_tol=1e-9), f"got {d}")

# ---------------------------------------------------------------------------
# 3. KNOWN, REAL, PRE-EXISTING DEFECTS this test suite surfaces
#    (not injected -- found while writing this test against the current file)
# ---------------------------------------------------------------------------
print("\n  --- Known defects found in current implementation (informational) ---")

# Defect A: hash() is randomized per-process by default in CPython (PEP 456 /
# PYTHONHASHSEED), so hash(w) % vector_size assigns different dimensions to
# the same word across separate process runs. Document embeddings -- and
# therefore every downstream statistic (dist_mean, cluster_radius, etc.) --
# are NOT reproducible run-to-run unless PYTHONHASHSEED is fixed externally.
import subprocess
r1 = subprocess.run([sys.executable, "-c",
    "import sys; sys.path.insert(0,'.'); import doc2vec_cluster_engine as e; "
    "m=e.PureDoc2Vec(10); x=m.fit_transform(['china economy growth']); "
    "print((x[0].tolist() if hasattr(x[0],'tolist') else x[0]))"],
    cwd=str(Path(__file__).parent.parent / "engines"), capture_output=True, text=True)
r2 = subprocess.run([sys.executable, "-c",
    "import sys; sys.path.insert(0,'.'); import doc2vec_cluster_engine as e; "
    "m=e.PureDoc2Vec(10); x=m.fit_transform(['china economy growth']); "
    "print((x[0].tolist() if hasattr(x[0],'tolist') else x[0]))"],
    cwd=str(Path(__file__).parent.parent / "engines"), capture_output=True, text=True)
same_across_runs = (r1.stdout == r2.stdout)
print(f"  [DEFECT-A] Same document embedded in two fresh processes -> "
      f"{'IDENTICAL (no bug)' if same_across_runs else 'DIFFERENT (confirmed: not reproducible across runs)'}")
print(f"             run1: {r1.stdout.strip()}")
print(f"             run2: {r2.stdout.strip()}")

# Defect B: hardcoded fallback constant when numpy is absent (line ~143):
#   eig_ratio = 0.046073  # "Standard spectral baseline estimate"
# This is a fabricated number, not a computed one -- it does not depend on
# the actual input data at all in the no-numpy path.
import inspect
src = inspect.getsource(eng.compute_cluster_summary_stats)
has_hardcoded_fallback = "0.046073" in src
print(f"  [DEFECT-B] Hardcoded non-data-dependent eig_ratio fallback present: {has_hardcoded_fallback}")

print(f"\n  SUMMARY: {PASS} passed, {FAIL} failed (out of {PASS+FAIL} correctness checks)")
sys.exit(1 if FAIL > 0 else 0)

# ---------------------------------------------------------------------------
# BREAK_IT_INSTRUCTIONS (per TESTING_STANDARD.md, section III):
# In doc2vec_cluster_engine.py, cosine_distance_pure(), change:
#     return max(0.0, min(2.0, 1.0 - cos_sim))
# to:
#     return max(0.0, min(2.0, 1.0 + cos_sim))
# Expected result: the "identical vectors -> distance 0" and "opposite
# vectors -> distance 2" checks must flip and FAIL. Confirmed live in the
# assistant's response to the user, then reverted.
# ---------------------------------------------------------------------------
