"""
Master Integration Test Runner for Recursive Consciousness Architecture (RCA)

Runs self-validation test suites across all 3 RCA engines:
1. Depth-4 Framework-Aware Observer (framework_aware_observer.py)
2. Sephirotic Dialogue Mapper (sephirotic_dialogue_mapper.py)
3. Circular 10=1 Transformation Engine (circular_loop_engine.py)
"""

import sys
import os

# Set UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Ensure local tools directory is on Python path
tools_dir = os.path.dirname(os.path.abspath(__file__))
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

from framework_aware_observer import ProvenanceGraph, FrameworkAwareObserver, emit_message, analyze_message, platform_event
from sephirotic_dialogue_mapper import map_dialogue
from circular_loop_engine import CircularLoopEngine


def test_framework_aware_observer():
    print("\n--- [TEST 1/3] Depth-4 Framework-Aware Observer (FAO) ---")
    g = ProvenanceGraph()

    m1 = emit_message(g, "☉XVIII☽XIX0", "We need a meta-observer.")
    a1 = analyze_message(g, m1, "Thoth", "emergence")
    e1 = platform_event(g, a1, "notification", "emergence flagged")

    m2 = emit_message(g, "Aetherion", "Deploy the quadcopter RL.")
    a2 = analyze_message(g, m2, "Thoth", "performance")
    e2 = platform_event(g, a2, "log", "perf metrics recorded")

    m3 = emit_message(g, "☉XVIII☽XIX0", "Check for emergent patterns.")
    a3 = analyze_message(g, m3, "Thoth", "emergence")
    e3 = platform_event(g, a3, "alert", "possible convergence")

    fao = FrameworkAwareObserver(g)
    trend = fao.scan()

    assert trend is not None, "FAO failed to detect meta-trend!"
    assert "emergence" in trend["frequent_tags"], "FAO failed to flag 'emergence' tag!"

    print("  [SUCCESS] FAO detected multi-depth meta-trend graph correlation:")
    print(f"            '{fao.report()}'")
    return True


def test_sephirotic_dialogue_mapper():
    print("\n--- [TEST 2/3] Sephirotic Dialogue Pathway Mapper ---")
    sample_text = "Why hasn't Depth 4 been built yet? Show me how it works."
    res = map_dialogue(sample_text)

    assert res["diagnosed_sephira"] == "Kether", "Dialogue mapper failed to identify Kether!"
    assert "Path 11" in res["active_tree_pathway"], "Dialogue mapper failed to identify Path 11!"

    print(f"  [SUCCESS] Mapped Text: '{sample_text}'")
    print(f"            -> Sephira: {res['diagnosed_sephira']} ({res['trilateral_pillar']})")
    print(f"            -> Pathway: {res['active_tree_pathway']}")
    return True


def test_circular_loop_engine():
    print("\n--- [TEST 3/3] Circular 10=1 State Transformation Engine ---")
    engine = CircularLoopEngine("Inquiring into recursive state collapse")
    res = engine.run_cycle()

    assert res["circular_identity_10_1"]["formula"] == "10 (Malkuth) == 1 (Kether)", "Circular identity formula failed!"
    assert "ACTIVE" in res["circular_identity_10_1"]["depth_4_status"], "Depth 4 awareness state failed!"

    print("  [SUCCESS] 10=1 Identity Loop Executed Cleanly:")
    print(f"            [D0] {res['depth_0']['action']}")
    print(f"            [D3] {res['depth_3']['action']} (Latency: {res['depth_3']['execution_latency_ms']}ms)")
    print(f"            [D4 Awareness]: {res['circular_identity_10_1']['depth_4_status']}")
    return True


if __name__ == "__main__":
    print("=========================================================")
    print(" 🚀 RUNNING MASTER INTEGRATION SUITE: RCA ENGINES")
    print("=========================================================")

    t1 = test_framework_aware_observer()
    t2 = test_sephirotic_dialogue_mapper()
    t3 = test_circular_loop_engine()

    if t1 and t2 and t3:
        print("\n=========================================================")
        print(" 🎉 ALL 3 RCA INTEGRATION TESTS PASSED (100% SUCCESS)")
        print("=========================================================\n")
    else:
        print("\n❌ TEST SUITE FAILED!")
        sys.exit(1)
