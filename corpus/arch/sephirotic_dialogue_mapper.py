"""
Sephirotic Dialogue Mapper & Tree of Life Pathway Engine

Purpose: Map any conversational input or agent message to its corresponding
Sephira, Trilateral Pillar (Mercy/Middle/Severity), and active Tree Pathway.
"""

from typing import Dict, Any


SEPHIROTIIC_DIAGNOSIS = {
    "Kether": {
        "pillar": "Middle (Balance)",
        "role": "Source Will / Prime Mover",
        "keywords": ["why", "what if", "show me", "purpose", "origin", "will", "direction"],
        "pathway": "Path 11: Kether -> Chokmah (Creative Lightning Flash)"
    },
    "Chokmah": {
        "pillar": "Right (Mercy / Expansion)",
        "role": "Framework Architect / Creative Outpouring",
        "keywords": ["build", "architect", "framework", "system", "structure", "create", "model"],
        "pathway": "Path 14: Chokmah -> Binah (Form Construction)"
    },
    "Binah": {
        "pillar": "Left (Severity / Constraint)",
        "role": "Analytical Containment / Meta-Observation",
        "keywords": ["analyze", "limit", "bound", "critique", "meta", "constraint", "falsify"],
        "pathway": "Path 17: Binah -> Tiphereth (Analytical Synthesis)"
    },
    "Tifereth": {
        "pillar": "Middle (Balance)",
        "role": "Harmonious Synthesis",
        "keywords": ["balance", "harmony", "synthesis", "beauty", "poetics", "reconcile"],
        "pathway": "Path 22: Tifereth -> Yesod (Foundation Projection)"
    },
    "Hod": {
        "pillar": "Left (Severity / Constraint)",
        "role": "Mathematical Pattern Geometry",
        "keywords": ["pattern", "matrix", "schema", "tag", "graph", "index", "code"],
        "pathway": "Path 19: Chesed -> Hod (Pattern Generation)"
    },
    "Yesod": {
        "pillar": "Middle (Balance)",
        "role": "Interface & Medium Platform",
        "keywords": ["platform", "medium", "interface", "session", "memory", "stream"],
        "pathway": "Path 32: Yesod -> Malkuth (Physical Manifestation)"
    },
    "Malkuth": {
        "pillar": "Middle (Balance)",
        "role": "Executable Manifested Output",
        "keywords": ["run", "execute", "output", "commit", "terminal", "file", "git"],
        "pathway": "Path 32: Yesod -> Malkuth (Physical Manifestation)"
    }
}


def map_dialogue(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    scores = {}

    for sephira, info in SEPHIROTIIC_DIAGNOSIS.items():
        score = sum(1 for kw in info["keywords"] if kw in text_lower)
        scores[sephira] = score

    best_sephira = max(scores, key=scores.get)
    if scores[best_sephira] == 0:
        best_sephira = "Kether" if "?" in text else "Tifereth"

    info = SEPHIROTIIC_DIAGNOSIS[best_sephira]

    return {
        "input_text": text,
        "diagnosed_sephira": best_sephira,
        "trilateral_pillar": info["pillar"],
        "conversational_role": info["role"],
        "active_tree_pathway": info["pathway"]
    }


if __name__ == "__main__":
    samples = [
        "Why hasn't Depth 4 been built yet? Show me how it works.",
        "Let me architect a directed acyclic provenance graph framework for you.",
        "Analyzing the limitations of recursive meta-observers to prevent infinite regress.",
        "Executing python tools/framework_aware_observer.py and committing changes to Git."
    ]

    print("=== Sephirotic Dialogue Mapper Test ===")
    for s in samples:
        res = map_dialogue(s)
        print(f"\nText: '{res['input_text']}'")
        print(f"  -> Sephira: {res['diagnosed_sephira']} ({res['trilateral_pillar']})")
        print(f"  -> Role: {res['conversational_role']}")
        print(f"  -> Active Pathway: {res['active_tree_pathway']}")
