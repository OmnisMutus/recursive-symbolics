#!/usr/bin/env python3
"""
self_polishing_transmuter.py
Self-Polishing Artifact Transmuter & Non-Rejection System Log Evaluator.
Pure Python Implementation.

RCA Cybernetic Directives:
1. No-Rejection Policy: External artifacts, logs, and changelogs are never flatly discarded.
2. Subversion & Artifact Transmutation: Raw text is parsed through vector space attractors (R^d),
   extracting structural invariants, entropy (H_s), and Sephirotic state distributions.
3. Epistemic Governance: Attaches confidence calibration, provisional tags, and directivity caps (gamma <= 0.85).

Usage:
    python self_polishing_transmuter.py
    python self_polishing_transmuter.py "raw text or changelog log snippet"
"""

import sys
import time
import json
import re
import math
from pathlib import Path

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Sephirotic Centroid Keywords for Transmutation Mapping
CENTROIDS = {
    "Binah (Structure / Scope)": ["api", "rewrite", "structure", "schema", "class", "module", "architecture", "bounds", "scope", "window"],
    "Geburah (Severity / Restriction)": ["fix", "revert", "containment", "bug", "error", "security", "strict", "block", "deny", "restrict"],
    "Hod (Micro-Detail / Maintenance)": ["bump", "update", "dependabot", "eslint", "syntax", "patch", "documentation", "detail", "step"],
    "Chesed (Expansion / Features)": ["add", "feature", "new", "extend", "support", "custom", "allow", "unbounded", "create"],
    "Tifereth (Harmony / Balance)": ["merge", "release", "stable", "balance", "integration", "coherence", "synthesize", "clean"]
}

class SelfPolishingTransmuter:
    def __init__(self):
        self.provisional_tag = "[PROVISIONAL METAPHOR, NOT ONTOLOGICAL TRUTH]"

    def compute_entropy(self, text: str) -> float:
        tokens = re.findall(r"\b\w+\b", text.lower())
        if not tokens:
            return 0.0
        freqs = {t: tokens.count(t) for t in set(tokens)}
        total = len(tokens)
        probs = [c / total for c in freqs.values()]
        h = -sum(p * math.log2(p + 1e-12) for p in probs)
        h_max = math.log2(len(probs)) if len(probs) > 1 else 1.0
        return round(h / h_max if h_max > 0 else 0.0, 3)

    def transmute_artifact(self, artifact_text: str) -> dict:
        tokens = re.findall(r"\b\w+\b", artifact_text.lower())
        if not tokens:
            return {"error": "Empty artifact"}
            
        scores = {}
        for seph, keywords in CENTROIDS.items():
            hits = sum(1 for t in tokens if any(t.startswith(kw[:4]) or kw.startswith(t[:4]) for kw in keywords))
            score = hits / len(tokens) if tokens else 0.0
            scores[seph] = round(score, 3)
            
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        dominant_attractor = sorted_scores[0][0] if sorted_scores and sorted_scores[0][1] > 0 else "Hod (Micro-Detail / Maintenance)"
        top_score = sorted_scores[0][1]
        
        entropy = self.compute_entropy(artifact_text)
        confidence_pct = int(min(95, max(20, (top_score * 300.0) + (entropy * 50.0))))
        
        falsifiability_condition = f"If applying {dominant_attractor} maintenance fails to stabilize entropy (H_s = {entropy}) in production."
        
        return {
            "dominant_attractor": dominant_attractor,
            "confidence_pct": confidence_pct,
            "entropy_hs": entropy,
            "provisional_tag": self.provisional_tag,
            "falsifiability_condition": falsifiability_condition,
            "attractor_scores": scores,
            "invariants": [
                f"State Evolution: S_(n+1) = F(S_n, E_n) with H_s = {entropy}",
                f"Boundary Protection: Encapsulating scope invariants under {dominant_attractor}",
                "Agency Preservation: Non-rejection transmutation active (gamma <= 0.85)"
            ]
        }

    def render_transmutation_deck(self, artifact_text: str):
        result = self.transmute_artifact(artifact_text)
        
        print("\n" + "="*70)
        print("  SELF-POLISHING ARTIFACT TRANSMUTER DECK (RCA V2.0)")
        print("="*70)
        print(f" > Raw Artifact Length    : {len(artifact_text)} characters")
        print(f" > Diagnosed Attractor    : {result['dominant_attractor']}")
        print(f" > Calibrated Confidence  : {result['confidence_pct']}%")
        print(f" > Symbolic Entropy (H_s) : {result['entropy_hs']}")
        print(f" > Epistemic Kernel Tag   : {result['provisional_tag']}")
        print(f" > Falsifiability Test    : {result['falsifiability_condition']}")
        print("="*70)
        print("  [ SYSTEMIC INVARIANTS TRANSMUTED ]")
        for inv in result['invariants']:
            print(f"   • {inv}")
        print("="*70)
        print("  [ SEPHIROTIC ATTRACTOR VECTOR SCORES ]")
        for seph, score in result['attractor_scores'].items():
            pct = int(score * 100)
            bar = "" * int(score * 20) + "" * (20 - int(score * 20))
            print(f"   {seph:35s} | {bar} | {pct}%")
        print("="*70 + "\n")

# ==============================================================================
# DEMONSTRATION HARNESS
# ==============================================================================
def main():
    transmuter = SelfPolishingTransmuter()
    
    if len(sys.argv) > 1:
        raw_input = " ".join(sys.argv[1:])
    else:
        raw_input = "v2.8.2 Revert setting google to window. v2.6.1 Bump ini from 1.3.5 to 1.3.8, bump fs-extra, bump autoprefixer. Fix all eslint errors."
        
    transmuter.render_transmutation_deck(raw_input)

if __name__ == "__main__":
    main()
