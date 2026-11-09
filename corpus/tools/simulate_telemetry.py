#!/usr/bin/env python3
"""
simulate_telemetry.py
Generates a synthetic community dataset (JSONL) with varied, realistic timestamps 
to test the telemetry_analyzer.py baseline calibration and H_s metrics.
"""

import json
import pathlib
from datetime import datetime, timedelta, timezone

def generate_entry(timestamp, user_hash, dominant, patch, raw_data, source="debugger"):
    return {
        "timestamp": timestamp.isoformat(),
        "user_id_hash": user_hash,
        "dominant_sephirah": dominant,
        "patch": patch,
        "notes": "",
        "source": source,
        "data": raw_data
    }

def main():
    tools_dir = pathlib.Path(__file__).parent
    dataset_path = tools_dir / "community_dataset.jsonl"
    
    entries = []
    base_time = datetime.now(timezone.utc) - timedelta(days=1)
    
    # --- User 1: Fast & Intuitive (Chesed) ---
    # Baseline ~2 seconds. High H_s (chaotic, rambling text).
    u1_hash = "hash_fast_chesed"
    t = base_time
    u1_texts = [
        "Feeling super expansive today, like my mind is just racing everywhere and I can't catch all the thoughts but they are mostly good just flying around.",
        "Wait now I'm thinking about the universe and how everything connects, it's so wild and beautiful.",
        "Okay but what if we just loved everything? Like everything is just energy anyway.",
        "Jumping to another thought, so much potential here, overflowing!"
    ]
    for text in u1_texts:
        entries.append(generate_entry(t, u1_hash, "Chesed", "Geburah", text))
        t += timedelta(seconds=2)  # fast 2s delta
        
    # --- User 2: Slow & Deliberate (Tifereth / Netzach) ---
    # Baseline ~30 seconds. Moderate structured H_s.
    u2_hash = "hash_slow_tifereth"
    t = base_time + timedelta(minutes=5)
    u2_texts = [
        "I am currently analyzing the situation. It seems complex.",
        "After careful consideration, I think a balanced approach is best.",
        "I need to persist through this difficult phase without losing center.",
        "Maintaining equilibrium requires sustained focus over time."
    ]
    for text in u2_texts:
        entries.append(generate_entry(t, u2_hash, "Tifereth", "Yesod", text))
        t += timedelta(seconds=30) # steady 30s delta
        
    # --- User 3: Warming Up (Netzach -> Chesed) ---
    # Starts very slow, then gets very fast.
    u3_hash = "hash_warmup_user"
    t = base_time + timedelta(minutes=10)
    deltas = [120, 60, 15, 3] # getting faster
    u3_texts = ["Struggling to start.", "Getting a bit easier.", "Flow state engaging.", "Zooming now!"]
    for i, text in enumerate(u3_texts):
        entries.append(generate_entry(t, u3_hash, "Netzach", "Hod", text))
        t += timedelta(seconds=deltas[i])
        
    # --- User 4: Stuck Loop (Geburah -> Geburah) ---
    # Exponential latencies, extremely repetitive text (Low H_s).
    u4_hash = "hash_stuck_geburah"
    t = base_time + timedelta(minutes=15)
    # Give them a baseline of ~30s, but then they get stuck
    u4_texts = [
        "must restrict must restrict must restrict",
        "must restrict must restrict must restrict",
        "must restrict must restrict must restrict",
        "must restrict must restrict must restrict"
    ]
    u4_deltas = [30, 150, 400, 1200]
    for i, text in enumerate(u4_texts):
        entries.append(generate_entry(t, u4_hash, "Geburah", "Geburah", text))
        t += timedelta(seconds=u4_deltas[i])
        
    # Sort entries by timestamp to simulate a real continuous log
    entries.sort(key=lambda x: x["timestamp"])
    
    with open(dataset_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
            
    print(f"[SUCCESS] Synthetic dataset generated with {len(entries)} entries at {dataset_path}")

if __name__ == "__main__":
    main()
