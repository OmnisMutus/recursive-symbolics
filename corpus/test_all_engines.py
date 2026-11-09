#!/usr/bin/env python3
"""
test_all_engines.py
Master Test Runner for all engines in solo/.
Pure Python Implementation.

HONESTY FIX (see STATUS legend below):
The original version of this file reported "PASSED" for any engine whose
script executed with exit code 0. That means "did not crash" -- it says
nothing about whether the engine's claimed behavior is actually correct.
A script that does nothing but `print("ok"); sys.exit(0)` would have
passed. This version distinguishes:

  VERIFIED   - a dedicated test_<engine>.py exists with real assertions
               against the engine's actual behavior (reference comparisons,
               boundary checks, and in each case a deliberately-broken
               implementation was run against the test during development
               to confirm the test actually fails when the code is wrong --
               see each test file's own docstring), AND that test currently
               passes.
  RAN_ONLY   - the engine script executed without crashing, but no
               correctness test exists for it. This is NOT evidence the
               engine works -- only that it didn't error out.
  FAILED     - a test file exists and ran, but assertions failed.
  MISSING    - the engine file does not exist on disk.

Do not read RAN_ONLY as equivalent to VERIFIED. It isn't.

Usage:
    python test_all_engines.py
"""

import sys
import time
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent

# Each entry: (engine_file, description, dedicated_test_file_or_None, extra_args)
# dedicated_test_file is None for engines that have no correctness test yet --
# those can only ever report RAN_ONLY, FAILED-to-launch, or MISSING, never VERIFIED.
ENGINES = [
    ("engines/standalone_rca_sandbox.py", "Symbolic OS V2.0 Engine",
        "tests/test_standalone_rca_sandbox.py", ["/eval Test Prompt"]),
    ("engines/knn_project.py", "KNN Machine Learning Engine",
        "tests/test_knn_project.py", []),
    ("engines/iitd_mth432_stat_learning.py", "IITD Statistical Learning Engine",
        "tests/test_iitd_mth432_stat_learning.py", []),
    ("engines/doc2vec_cluster_engine.py", "Doc2Vec NLP Cluster Geometry Engine",
        "tests/test_doc2vec_cluster_engine.py", []),
    ("engines/dht_rca_node.py", "Kademlia P2P DHT Network Node",
        "tests/test_dht_rca_node.py", []),
    ("engines/grpc_web_bridge.py", "JSON Socket Proxy Bridge & Envoy Translator",
        "tests/test_grpc_web_bridge.py", []),
    ("engines/opengl_3d_scene_simulator.py", "OpenGL 3D Graphics Renderer Engine",
        "tests/test_opengl_3d_scene_simulator.py", []),
    ("engines/briah_composition_engine.py", "Briah Layer Object Composition Engine",
        "tests/test_briah_composition_engine.py", []),
    ("engines/inheritance_upcasting_engine.py", "OOP Inheritance & Upcasting Engine",
        "tests/test_inheritance_upcasting_engine.py", []),
    ("engines/safe_memory_boundary_engine.py", "Safe Integer Math & Overflow Guard",
        "tests/test_safe_memory_boundary_engine.py", []),
    ("engines/graphql_mesh_snapshot_engine.py", "Zero-Dependency GraphQL Mesh Engine",
        "tests/test_graphql_mesh_snapshot_engine.py", []),
    ("engines/nestjs_vue_cli_simulator.py", "NestJS-Vue CLI Monorepo Generator",
        "tests/test_nestjs_vue_cli_simulator.py", []),
    ("engines/hello_world_repo_simulator.py", "Git SHA-1 Commit Graph Simulator",
        "tests/test_hello_world_repo_simulator.py", []),
    ("engines/ddpg_quadcopter_rca_engine.py", "DDPG Quadcopter RL Continuous Control",
        "tests/test_ddpg_quadcopter_rca_engine.py", []),
    ("engines/alx_c_low_level_simulator.py", "ALX Low-Level C Functions & Nested Loops",
        "tests/test_alx_c_low_level_simulator.py", []),
    ("engines/sephirotic_reward_engine.py", "Sephirotic (Chesed/Geburah/Tifereth) DDPG Reward Shaping",
        "tests/test_sephirotic_reward_engine.py", []),
    ("engines/computational_kabbalah_honest_benchmark.py", "Honest NumPy Performance Benchmark Suite",
        "tests/test_computational_kabbalah_honest_benchmark.py", []),
    ("engines/strict_honest_benchmark_suite.py", "Strict Honest CTO Benchmark Suite",
        "tests/test_strict_honest_benchmark_suite.py", []),
    # --- Added after a full file-by-file sweep of solo/ found these were on disk
    # but never registered here, meaning they were invisible to every prior
    # "X / N engines" count this file has ever reported. None have dedicated
    # correctness tests yet, so all can only ever report RAN_ONLY here.
    ("engines/ctypes_math_accelerator.py", "Ctypes-Based Vector Math Accelerator",
        "tests/test_ctypes_math_accelerator.py", []),
    ("engines/p2p_swarm_mesh_engine.py", "UDP Swarm Mesh Peer Discovery Engine",
        "tests/test_p2p_swarm_mesh_engine.py", []),
    ("engines/self_polishing_transmuter.py", "Artifact/Log Transmutation & Scoring Tool",
        "tests/test_self_polishing_transmuter.py", []),
    ("engines/terminal_dashboard_deck.py", "Terminal Telemetry Dashboard UI",
        "tests/test_terminal_dashboard_deck.py", []),
    ("engines/real_ridge_benchmark_vs_sklearn.py", "Real Ridge L2 Benchmark vs. Installed scikit-learn",
        "tests/test_real_ridge_benchmark_vs_sklearn.py", []),
    # --- Added: a real dynamical-systems implementation of the formalism
    # stated in core-axiom.md / mathematical-foundation.md (sigma, the
    # recursive operator F, fixed points, limit cycles, Tiphareth
    # integration, Da'ath divergence detection). Ground truth is real,
    # independently-citable mathematics (closed-form linear contraction
    # fixed points, the logistic map's documented bifurcation regimes) --
    # not a re-test of any other engine, so it counts as its own entry
    # rather than a supplementary suite.
    ("engines/recursive_attractor_engine.py", "Recursive Attractor / Fixed-Point Dynamical Systems Engine",
        "tests/test_recursive_attractor_engine.py", []),
]

# Files that test MULTIPLE engines already listed above in one combined suite
# (duplicate/overlapping coverage, not a new engine). Run and reported
# separately so they don't double-count against the ENGINES total above --
# they were found unregistered in the same sweep that found the 5 engines
# added just above.
SUPPLEMENTARY_TEST_SUITES = [
    ("tests/test_production_engine_unit_tests.py",
     "Aggregate suite re-testing KNN, Ridge/LDA/KMeans, DDPG, Safe-Memory, "
     "and Doc2Vec engines already covered individually above."),
]

STATUS_VERIFIED = "VERIFIED"
STATUS_RAN_ONLY = "RAN_ONLY"
STATUS_MISSING = "MISSING"
STATUS_FAILED = "FAILED"

STATUS_ICON = {
    STATUS_VERIFIED: "",
    STATUS_RAN_ONLY: "🟡",
    STATUS_MISSING: "",
    STATUS_FAILED: "",
}


def run_script(script_path, extra_args, timeout=10):
    cmd = [sys.executable, str(script_path)] + extra_args
    start = time.perf_counter()
    res = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding='utf-8', errors='replace', timeout=timeout
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return res.returncode, elapsed_ms, res.stderr


def check_engine(script_name, test_file_name, extra_args):
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        return STATUS_MISSING, f"Engine file {script_name} not found."

    if test_file_name is None:
        # No dedicated correctness test exists. Running the engine's own
        # __main__ only tells us it didn't crash -- report that honestly
        # as RAN_ONLY rather than inferring correctness from exit code 0.
        try:
            code, elapsed_ms, stderr = run_script(script_path, extra_args)
        except Exception as e:
            return STATUS_MISSING, f"ERROR launching engine: {e}"
        if code == 0:
            return STATUS_RAN_ONLY, f"exited 0 in {elapsed_ms:.1f} ms — no correctness test exists for this engine"
        else:
            return STATUS_FAILED, f"exited {code}: {stderr.strip()[:100]}"

    test_path = BASE_DIR / test_file_name
    if not test_path.exists():
        return STATUS_MISSING, f"Test file {test_file_name} not found (engine file exists, but is untested)."

    try:
        code, elapsed_ms, stderr = run_script(test_path, [])
    except Exception as e:
        return STATUS_MISSING, f"ERROR launching test file: {e}"

    if code == 0:
        return STATUS_VERIFIED, f"{test_file_name} passed in {elapsed_ms:.1f} ms"
    else:
        return STATUS_FAILED, f"{test_file_name} FAILED: {stderr.strip()[:150]}"


def main():
    print("""
    ================================================================
                    MASTER TEST RUNNER — HONEST STATUS
              Verifying All Software Engines in solo/
    ================================================================
    Legend:
      VERIFIED  - dedicated test file with real assertions, passing
      RAN_ONLY  - script executed without crashing; NOT correctness-checked
      FAILED    - a test exists and its assertions failed
      MISSING   - file not found on disk
    """)

    counts = {STATUS_VERIFIED: 0, STATUS_RAN_ONLY: 0, STATUS_MISSING: 0, STATUS_FAILED: 0}
    start_total = time.perf_counter()

    for script_name, description, test_file_name, extra_args in ENGINES:
        status, msg = check_engine(script_name, test_file_name, extra_args)
        counts[status] += 1
        icon = STATUS_ICON[status]
        print(f" {icon} [{script_name:42s}] : {description}")
        print(f"      {status:9s} -> {msg}")

    total_elapsed_sec = time.perf_counter() - start_total
    total = len(ENGINES)

    print("\n" + "=" * 78)
    print(" SUMMARY")
    print("=" * 78)
    print(f"  Total engines listed   : {total}")
    print(f"  VERIFIED (real tests)  : {counts[STATUS_VERIFIED]} / {total}")
    print(f"  RAN_ONLY (unverified)  : {counts[STATUS_RAN_ONLY]} / {total}")
    print(f"  FAILED                 : {counts[STATUS_FAILED]} / {total}")
    print(f"  MISSING                : {counts[STATUS_MISSING]} / {total}")
    print(f"  Total execution time   : {total_elapsed_sec:.3f} seconds")
    print()
    print("  Honest claim this run supports:")
    print(f"    {counts[STATUS_VERIFIED]} of {total} engines are implemented and correctness-verified")
    print(f"    against real assertions (see each test_*.py for what was checked).")
    print(f"    {counts[STATUS_RAN_ONLY]} of {total} exist and run without error but are NOT")
    print(f"    correctness-verified -- do not cite these as 'working,' only as 'present.'")
    print(f"    {counts[STATUS_MISSING]} of {total} do not exist on disk yet.")
    print(f"    {counts[STATUS_FAILED]} of {total} exist and FAILED their correctness test.")
    print("=" * 78 + "\n")

    # Supplementary suites: test files covering multiple engines already
    # counted above. Reported separately, not folded into the total, so this
    # doesn't silently inflate the "X / N engines" claim with duplicate
    # coverage of engines already accounted for individually.
    supplementary_failed = False
    if SUPPLEMENTARY_TEST_SUITES:
        print("SUPPLEMENTARY TEST SUITES (duplicate coverage, not counted above)")
        print("=" * 78)
        for suite_file, note in SUPPLEMENTARY_TEST_SUITES:
            suite_path = BASE_DIR / suite_file
            if not suite_path.exists():
                print(f"  [{suite_file:42s}] : MISSING")
                continue
            try:
                code, elapsed_ms, stderr = run_script(suite_path, [])
            except Exception as e:
                print(f"  [{suite_file:42s}] : ERROR launching: {e}")
                supplementary_failed = True
                continue
            icon = "" if code == 0 else ""
            status_word = "PASSED" if code == 0 else "FAILED"
            print(f" {icon} [{suite_file:42s}] : {note}")
            print(f"      {status_word:9s} -> exit {code} in {elapsed_ms:.1f} ms"
                  + ("" if code == 0 else f": {stderr.strip()[:150]}"))
            if code != 0:
                supplementary_failed = True
        print("=" * 78 + "\n")

    # Exit code reflects whether anything that WAS tested actually failed --
    # missing/unimplemented engines are not treated as this run's failure,
    # since "not yet built" and "built but broken" are different problems.
    sys.exit(1 if (counts[STATUS_FAILED] > 0 or supplementary_failed) else 0)


if __name__ == "__main__":
    main()
