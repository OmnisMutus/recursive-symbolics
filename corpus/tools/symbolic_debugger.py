#!/usr/bin/env python3  
"""  
symbolic_debugger.py  
A lightweight CLI that analyses free-text input, detects dominant  
Sephirotic signatures, and proposes a balancing operator.

Usage:  
    python symbolic_debugger.py "I feel stuck in analysis, my mind loops."  
"""

import json, sys, re, collections, pathlib

API_PATH = pathlib.Path(__file__).parent / "symbolic_api.json"  
API = json.load(open(API_PATH, "r", encoding="utf-8"))

# ----------------------------------------------------------------------  
# Helper: flatten keyword → sephira map  
keyword_map = {}  
for seph, data in API["sephirot"].items():  
    for kw in data["keywords"]:  
        keyword_map[kw.lower()] = seph

def tokenize(text):  
    # very simple word tokenizer – enough for a demo  
    return re.findall(r"\b\w+\b", text.lower())

def detect_counts(tokens):  
    counts = collections.Counter()  
    for t in tokens:  
        if t in keyword_map:  
            counts[keyword_map[t]] += 1  
    return counts

def dominant_sephira(counts):  
    if not counts:  
        return None  
    return counts.most_common(1)[0][0]

def suggest_balance(seph):  
    rules = API["balancing_rules"]  
    return rules.get(seph, None)

def calculate_entropy(text):
    """
    Calculates H_s (Entropy) based on the unique-adjacent-pair rule.
    Returns a float between 0.0 and 1.0.
    """
    tokens = tokenize(text)
    if len(tokens) < 2:
        return 0.0
        
    total_pairs = 0
    unique_pairs = set()
    
    for i in range(len(tokens) - 1):
        pair = f"{tokens[i]} {tokens[i+1]}"
        total_pairs += 1
        unique_pairs.add(pair)
        
    if total_pairs == 0:
        return 0.0
    return len(unique_pairs) / total_pairs

def analyze(text):
    """
    Module entry point for analyzing text.
    Returns a dict with 'dominant', 'suggestion', and 'entropy'.
    """
    tokens = tokenize(text)
    entropy = calculate_entropy(text)
    counts = detect_counts(tokens)
    if not counts:
        return {"dominant": None, "suggestion": None, "entropy": entropy}
    
    dom = dominant_sephira(counts)
    bal = suggest_balance(dom)
    return {"dominant": dom, "suggestion": bal, "entropy": entropy}

def main():  
    if len(sys.argv) < 2:  
        print("Usage: python symbolic_debugger.py \"<text>\"")  
        sys.exit(1)

    raw = " ".join(sys.argv[1:])  
    tokens = tokenize(raw)  
    counts = detect_counts(tokens)
    entropy = calculate_entropy(raw)

    if not counts:  
        print("No recognizable symbolic keywords found.")  
        sys.exit(0)

    dom = dominant_sephira(counts)  
    bal = suggest_balance(dom)

    print("\n--- Symbolic Debugger Report ---")  
    print(f"Input text   : {raw}")  
    print(f"Hs (Entropy) : {entropy:.2f} | Measures coherence, not correctness.")
    print(f"Detected signatures:")  
    for s, c in counts.most_common():  
        print(f"  {s:10s} → {c} hit(s)")

    print(f"\nDominant Sephirah : {dom}")  
    if bal:  
        print(f"Recommended balancing operator : {bal}")  
        # Show a one-liner suggestion  
        print(f"Suggested patch: invoke {bal} on the current state.")  
    else:  
        print("No balancing rule defined for this Sephirah.")

    print("\nTip: To improve detection, add more keywords to symbolic_api.json → sephirot → <name> → keywords.\n")

if __name__ == "__main__":  
    main()  
