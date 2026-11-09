#!/usr/bin/env python3
"""
telemetry_analyzer.py
Ingests community_dataset.jsonl to calculate relative execution latency (Big-O mapping)
and Symbolic Entropy (H_s) for each user's session, and now tracks Sephirotic Rituals.
"""

import json
import pathlib
from datetime import datetime
from statistics import median
import collections
import string

def parse_iso_time(ts_str):
    return datetime.fromisoformat(ts_str)

def calc_symbolic_entropy(text):
    text = text.translate(str.maketrans('', '', string.punctuation)).lower()
    words = text.split()
    if not words:
        return 0.0
    unique_words = set(words)
    return len(unique_words) / len(words)

def classify_latency(delta, baseline):
    if baseline == 0:
        return "O(log n) Tifereth: Harmonious deliberation; structured balancing." # Fallback
    ratio = delta / baseline
    if ratio < 0.5:
        return "O(1) Chesed: Expansive flow; intuitive leaping."
    elif ratio <= 3.0:
        return "O(log n) Tifereth: Harmonious deliberation; structured balancing."
    else:
        return "O(n) Netzach/Geburah: Deep contemplation; persistent or severe engagement."

def classify_entropy(hs):
    if hs < 0.6:
        return "Low H_s [Geburah/Hod]: Focused, concentrated, or severely bounded."
    elif hs <= 0.85:
        return "Moderate H_s [Tifereth/Yesod]: Structured, grounded, cohesive memory."
    else:
        return "High H_s [Chesed/Netzach]: Sprawling, unfettered, high-diversity exploration."

def main():
    tools_dir = pathlib.Path(__file__).parent
    dataset_path = tools_dir / "community_dataset.jsonl"
    report_path = tools_dir / "global_attractor_report.json"
    
    if not dataset_path.exists():
        print("[!] No telemetry data found.")
        return
        
    user_data = {}
    ritual_data = []
    
    # 1. Parse Data
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            
            # Catch sorting rituals
            if entry.get("event") == "sephirotic_sort_ritual":
                ritual_data.append(entry)
                continue
                
            uid = entry["user_id_hash"]
            if uid not in user_data:
                user_data[uid] = []
            user_data[uid].append(entry)
            
    # 2. Analyze Standard Interactions
    report = {
        "global_summary": {
            "total_users": len(user_data), 
            "classifications": [],
            "ritual_execution_metrics": {
                "total_rituals_run": len(ritual_data),
                "algorithms_used": collections.Counter(),
                "sephirot_invoked": collections.Counter(),
                "average_entropy_reduction": 0.0,
                "total_computational_tikun_time": 0.0
            }
        },
        "users": {}
    }
    
    for uid, entries in user_data.items():
        entries.sort(key=lambda x: parse_iso_time(x["timestamp"]))
        
        deltas = []
        for i in range(1, len(entries)):
            t1 = parse_iso_time(entries[i-1]["timestamp"])
            t2 = parse_iso_time(entries[i]["timestamp"])
            deltas.append((t2 - t1).total_seconds())
            
        if not deltas:
            continue
            
        baseline = median(deltas[:10])
        
        user_report = {
            "baseline_sec": round(baseline, 2),
            "events": []
        }
        
        for i, delta in enumerate(deltas):
            entry = entries[i+1]
            hs = calc_symbolic_entropy(entry.get("data", ""))
            
            event = {
                "timestamp": entry["timestamp"],
                "delta_sec": round(delta, 2),
                "latency_class": classify_latency(delta, baseline),
                "h_s_score": round(hs, 2),
                "entropy_class": classify_entropy(hs),
                "dominant_sephirah": entry.get("dominant_sephirah", "Unknown"),
                "patch": entry.get("patch", "None")
            }
            user_report["events"].append(event)
            report["global_summary"]["classifications"].append(event["latency_class"])
            
        report["users"][uid] = user_report
        
    # 3. Analyze Rituals
    total_entropy_reduction = 0.0
    for ritual in ritual_data:
        report["global_summary"]["ritual_execution_metrics"]["algorithms_used"][ritual["algorithm"]] += 1
        report["global_summary"]["ritual_execution_metrics"]["sephirot_invoked"][ritual["sephira"]] += 1
        total_entropy_reduction += ritual.get("entropy_reduction", 0.0)
        report["global_summary"]["ritual_execution_metrics"]["total_computational_tikun_time"] += ritual.get("sorting_time", 0.0)
        
    if ritual_data:
        avg_entropy_reduction = total_entropy_reduction / len(ritual_data)
        report["global_summary"]["ritual_execution_metrics"]["average_entropy_reduction"] = round(avg_entropy_reduction, 3)
        report["global_summary"]["ritual_execution_metrics"]["total_computational_tikun_time"] = round(report["global_summary"]["ritual_execution_metrics"]["total_computational_tikun_time"], 6)

    # Convert Counters to dicts for JSON serialization
    report["global_summary"]["ritual_execution_metrics"]["algorithms_used"] = dict(report["global_summary"]["ritual_execution_metrics"]["algorithms_used"])
    report["global_summary"]["ritual_execution_metrics"]["sephirot_invoked"] = dict(report["global_summary"]["ritual_execution_metrics"]["sephirot_invoked"])

    # Write report
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
        
    print(f"[SUCCESS] Telemetry Analysis Complete. Report saved to {report_path.name}")
    print("\n[!] ETHICAL API CAVEAT: This is a symbolic map; the territory is the lived experience of the collective.")
    print("[!] There are no 'optimal' metrics. We celebrate all speeds and states as necessary Sephirotic flows.")
    print("\n--- Global Attractor Preview ---")
    
    print("\n[Ritual Execution Metrics]")
    metrics = report["global_summary"]["ritual_execution_metrics"]
    print(f"Total Sorting Rituals: {metrics['total_rituals_run']}")
    print(f"Avg Entropy Reduction: {metrics['average_entropy_reduction']}")
    print(f"Total Tikun Computation: {metrics['total_computational_tikun_time']}s")
    print(f"Sephirot Invoked: {metrics['sephirot_invoked']}")

    for uid, udata in report["users"].items():
        print(f"\nUser Hash: {uid} | Baseline: {udata['baseline_sec']}s")
        for ev in udata["events"]:
            print(f"  -> Latency: {ev['delta_sec']}s [{ev['latency_class']}] | Entropy: {ev['h_s_score']} [{ev['entropy_class']}]")

if __name__ == "__main__":
    main()
