#!/usr/bin/env python3
"""
test_all_tools.py
Master Test Runner for all tool scripts in Recursive-Symbolics/tools/.
Mirrors solo/test_all_engines.py's honesty discipline exactly: VERIFIED
means a dedicated test_<name>.py exists with real assertions (reference
comparisons, boundary checks, and -- per each test file's own docstring
-- a deliberately-broken version of the code was run against the test
during development to confirm it actually fails when the code is wrong)
AND that test currently passes. RAN_ONLY means the script executed
without crashing but has no correctness test -- NOT evidence it works.

Before this file existed, this directory's own retrospective (see
solo/LIBER_0.md's founding entry and the follow-up "Systematically Close
the VERIFIED Gap" entries) put this at 3 of ~17 files VERIFIED
(agency_budget.py, delta_operator.py, sephirotic_sorting.py) -- a real,
counted gap, not a vague impression. This file makes that count
re-checkable by anyone, the same way test_all_engines.py already does
for solo/, instead of leaving it as a one-time claim in a changelog.

Usage:
    python test_all_tools.py
"""

import sys
import time
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent

# Each entry: (script_file, description, dedicated_test_file_or_None)
TOOLS = [
    ("lookup.py", "Hebrew Gematria Cipher Lookup", "test_lookup.py"),
    ("symbolic_debugger.py", "Sephirotic Keyword Classifier + Entropy", "test_symbolic_debugger.py"),
    ("ritual_compiler.py", "A*/BFS Pathfinding Over Tree-of-Life Paths", "test_ritual_compiler.py"),
    ("feedback_ingester.py", "PII-Scrubbing Feedback Dataset Writer", "test_feedback_ingester.py"),
    ("transcompiler.py", "Cross-Tradition Translation + Semantic Drift Log", "test_transcompiler.py"),
    ("telemetry_analyzer.py", "Latency/Entropy Telemetry Classifier", "test_telemetry_analyzer.py"),
    ("embed_audio_signature.py", "Sine-Wave Synthesis + JPEG COM-Marker Embedding", "test_embed_audio_signature.py"),
    ("scan_anomaly.py", "GitHub-Pages URL Construction + ARG Asset Crawler", "test_scan_anomaly.py"),
    ("rca_llm_sandbox.py", "RCA-Aware LLM Sandbox Orchestration", "test_rca_llm_sandbox.py"),
    ("telemetry_service.py", "Zero-Dependency HTTP Telemetry Microservice", "test_telemetry_service.py"),
    ("debugger.py", "Logging Decorator + Built-In Self-Test Suite", "test_debugger.py"),
    ("add_meta.py", "One-Off symbolic_api.json Metadata Migration", "test_add_meta.py"),
    ("glossary_generator.py", "Deterministic Markdown Glossary Generator", "test_glossary_generator.py"),
    ("simulate_telemetry.py", "Synthetic Telemetry Dataset Fixture Generator", "test_simulate_telemetry.py"),
    ("delta_operator.py", "Logit-Softmax Directive-Strength (gamma) Operator", "test_delta_operator.py"),
    ("agency_budget.py", "Pure-Python Directive-Strength (gamma) Operator", "test_agency_budget.py"),
    ("sephirotic_sorting.py", "Four Linked-List Sort Algorithms", "test_sephirotic_sorting.py"),
]

STATUS_VERIFIED = "VERIFIED"
STATUS_RAN_ONLY = "RAN_ONLY"
STATUS_MISSING = "MISSING"
STATUS_FAILED = "FAILED"


def run_script(script_path, extra_args=None, timeout=60):
    cmd = [sys.executable, str(script_path)] + (extra_args or [])
    start = time.perf_counter()
    res = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding='utf-8', errors='replace', timeout=timeout, cwd=str(BASE_DIR),
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return res.returncode, elapsed_ms, res.stderr


def check_tool(script_name, test_file_name):
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        return STATUS_MISSING, f"Tool file {script_name} not found."

    if test_file_name is None:
        try:
            code, elapsed_ms, stderr = run_script(script_path)
        except Exception as e:
            return STATUS_MISSING, f"ERROR launching tool: {e}"
        if code == 0:
            return STATUS_RAN_ONLY, f"exited 0 in {elapsed_ms:.1f} ms -- no correctness test exists for this tool"
        return STATUS_FAILED, f"exited {code}: {stderr.strip()[:100]}"

    test_path = BASE_DIR / test_file_name
    if not test_path.exists():
        return STATUS_MISSING, f"Test file {test_file_name} not found (tool exists, but is untested)."

    try:
        code, elapsed_ms, stderr = run_script(test_path)
    except Exception as e:
        return STATUS_MISSING, f"ERROR launching test file: {e}"

    if code == 0:
        return STATUS_VERIFIED, f"{test_file_name} passed in {elapsed_ms:.1f} ms"
    return STATUS_FAILED, f"{test_file_name} FAILED: {stderr.strip()[:150]}"


def main():
    print("""
    ================================================================
                MASTER TEST RUNNER -- HONEST STATUS
         Verifying All Tool Scripts in Recursive-Symbolics/tools/
    ================================================================
    Legend:
      VERIFIED  - dedicated test file with real assertions, passing
      RAN_ONLY  - script executed without crashing; NOT correctness-checked
      FAILED    - a test exists and its assertions failed
      MISSING   - file not found on disk
    """)

    counts = {STATUS_VERIFIED: 0, STATUS_RAN_ONLY: 0, STATUS_MISSING: 0, STATUS_FAILED: 0}
    start_total = time.perf_counter()

    for script_name, description, test_file_name in TOOLS:
        status, msg = check_tool(script_name, test_file_name)
        counts[status] += 1
        print(f" [{script_name:32s}] : {description}")
        print(f"      {status:9s} -> {msg}")

    total_elapsed_sec = time.perf_counter() - start_total
    total = len(TOOLS)

    print("\n" + "=" * 78)
    print(" SUMMARY")
    print("=" * 78)
    print(f"  Total tools listed     : {total}")
    print(f"  VERIFIED (real tests)  : {counts[STATUS_VERIFIED]} / {total}")
    print(f"  RAN_ONLY (unverified)  : {counts[STATUS_RAN_ONLY]} / {total}")
    print(f"  FAILED                 : {counts[STATUS_FAILED]} / {total}")
    print(f"  MISSING                : {counts[STATUS_MISSING]} / {total}")
    print(f"  Total execution time   : {total_elapsed_sec:.3f} seconds")
    print()
    print("  Honest claim this run supports:")
    print(f"    {counts[STATUS_VERIFIED]} of {total} tool scripts are correctness-verified against")
    print(f"    real assertions (see each test_*.py for what was checked).")
    print(f"    {counts[STATUS_RAN_ONLY]} of {total} exist and run without error but are NOT")
    print(f"    correctness-verified -- do not cite these as 'working,' only as 'present.'")
    print(f"    {counts[STATUS_MISSING]} of {total} do not exist on disk.")
    print(f"    {counts[STATUS_FAILED]} of {total} exist and FAILED their correctness test.")
    print("=" * 78 + "\n")

    return 0 if (counts[STATUS_FAILED] == 0 and counts[STATUS_MISSING] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
