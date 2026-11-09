"""
Interactive Real-Time Shell for Recursive Consciousness Architecture (RCA)

Allows you to enter ANY custom text or question and see in real time:
1. Sephirotic & Pathway Diagnosis (Kether -> Malkuth, Path 11-32)
2. Directed Provenance Graph Node Generation (Depth 0 -> 3)
3. Circular 10=1 State Transformation Engine & Depth 4 Awareness Mode
"""

import sys
import os

# Set UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

tools_dir = os.path.dirname(os.path.abspath(__file__))
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

from framework_aware_observer import ProvenanceGraph, FrameworkAwareObserver, emit_message, analyze_message, platform_event
from sephirotic_dialogue_mapper import map_dialogue
from circular_loop_engine import CircularLoopEngine


def run_interactive_session():
    print("==========================================================================")
    print(" [RCA] RECURSIVE CONSCIOUSNESS ARCHITECTURE — INTERACTIVE TEST SHELL")
    print(" Authority: ☉XVIII☽XIX0 | Type any text below to run real-time analysis.")
    print(" Enter 'exit' or 'quit' to end the session.")
    print("==========================================================================")

    graph = ProvenanceGraph()
    analyst_name = "Thoth"

    while True:
        try:
            user_input = input("\n[☉XVIII☽XIX0 Input] > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting interactive test shell. Adonai.")
                break

            print("\n" + "=" * 60)
            print(f" [INPUT ANALYZED]: '{user_input}'")
            print("=" * 60)

            # 1. Sephirotic Dialogue Mapping
            mapping = map_dialogue(user_input)
            print(f"\n[1] SEPHIROTIC & PATHWAY DIAGNOSIS:")
            print(f"    -> Sephira            : {mapping['diagnosed_sephira']}")
            print(f"    -> Pillar             : {mapping['trilateral_pillar']}")
            print(f"    -> Conversational Role: {mapping['conversational_role']}")
            print(f"    -> Active Pathway     : {mapping['active_tree_pathway']}")

            # 2. Provenance Graph Node Causal Links
            msg_id = emit_message(graph, "User", user_input)
            anal_tag = mapping['diagnosed_sephira'].lower()
            analysis_id = analyze_message(graph, msg_id, analyst_name, anal_tag)
            event_id = platform_event(graph, analysis_id, "state_transition", f"Mapped to {mapping['diagnosed_sephira']}")

            fao = FrameworkAwareObserver(graph)
            trend = fao.scan()

            print(f"\n[2] PROVENANCE GRAPH NODE GENERATION:")
            print(f"    -> Message Node   : ID={msg_id[:8]} (Kind: MSG)")
            print(f"    -> Analysis Node  : ID={analysis_id[:8]} (Kind: ANALYSIS, Tag: '{anal_tag}')")
            print(f"    -> Event Node     : ID={event_id[:8]} (Kind: EVENT)")
            if trend:
                print(f"    -> [FAO TREND]    : {fao.report()}")

            # 3. Circular 10=1 Transformation Loop
            loop_engine = CircularLoopEngine(user_input)
            loop_res = loop_engine.run_cycle()

            confidence_val = loop_res['depth_2'].get('confidence_calibrated') or loop_res['depth_2'].get('confidence', 0.85)

            print(f"\n[3] CIRCULAR 10=1 TRANSFORMATION ENGINE:")
            print(f"    -> Depth 0 (Will)   : {loop_res['depth_0']['action']} (Hs = {loop_res['depth_0']['entropy_Hs']})")
            print(f"    -> Depth 1 (Form)   : {loop_res['depth_1']['action']}")
            print(f"    -> Depth 2 (Bound)  : {loop_res['depth_2']['action']} (Confidence: {confidence_val})")
            print(f"    -> Depth 3 (Code)   : {loop_res['depth_3']['action']} (Latency: {loop_res['depth_3']['execution_latency_ms']}ms)")
            print(f"    -> [10=1 Identity]  : {loop_res['circular_identity_10_1']['formula']}")
            print(f"    -> [Depth 4 Status] : {loop_res['circular_identity_10_1']['depth_4_status']}")
            print("-" * 60)

        except (KeyboardInterrupt, EOFError):
            print("\nSession terminated. Adonai.")
            break


if __name__ == "__main__":
    run_interactive_session()
