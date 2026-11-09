#!/usr/bin/env python3
"""
standalone_rca_sandbox.py
LIBRA VOID: SYMBOLIC OPERATING SYSTEM VERSION 2.0
Interactive Terminal Deck with Slash Commands & Epistemic Governance Evaluator.

Slash Commands:
  /help    - Display interactive command menu
  /learn   - Launch 4-Week Software Engineering Curriculum Tutor
  /eval    - Execute Epistemic Governance Evaluation Deck (/eval <optional text>)
  /qualia  - Inspect real-time 4D Qualia Telemetry Vector (Q)
  /memory  - Inspect persistent Q-learning weights (rca_memory.json)
  /dht     - Test Kademlia P2P UDP network node
  exit     - Exit sandbox session

Usage:
    python standalone_rca_sandbox.py
    python standalone_rca_sandbox.py "Your input text"
"""

import sys
import time
import json
import re
import math
import urllib.request
import urllib.error
from pathlib import Path

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

MEMORY_FILE = Path(__file__).parent / "rca_memory.json"
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

# Import DHT Node engine if available
try:
    import dht_rca_node
    HAS_DHT = True
except ImportError:
    HAS_DHT = False

# ==============================================================================
# SEPHIROTIC STATE VECTOR CENTROIDS (R^d VECTOR SPACE)
# ==============================================================================
SEPHIROT_CENTROIDS = {
    "Keter": ["crown", "source", "will", "direction", "origin", "pure", "intent", "primary", "primal", "infinite", "monad", "purpose", "teleos", "zenith", "supreme"],
    "Chokmah": ["wisdom", "vision", "quicksort", "pivot", "idea", "flash", "intuition", "spark", "creative", "genius", "inspiration", "swift", "eureka", "breakthrough"],
    "Binah": ["understanding", "structure", "architecture", "constraint", "logic", "container", "matrix", "format", "rule", "framework", "boundary", "system", "schema"],
    "Daath": ["abyss", "cavity", "hole", "gap", "paradox", "void", "crisis", "anomaly", "lag", "exception", "trap", "mystery", "confused", "stuck", "lost", "dissonance"],
    "Chesed": ["expansion", "flow", "unbounded", "endless", "grace", "generous", "abundance", "kindness", "mercy", "growth", "freedom", "vast", "radiant", "open"],
    "Geburah": ["rigid", "stuck", "restriction", "judgment", "severe", "harsh", "paralysis", "rules", "strict", "anger", "critical", "cut", "block", "burnout", "stress"],
    "Tifereth": ["balance", "harmony", "integration", "beauty", "synthesis", "centered", "heart", "peace", "coherence", "merge", "weave", "calm", "alignment", "equilibrium"],
    "Netzach": ["grind", "persistence", "endurance", "repeat", "victory", "stubborn", "linear", "passion", "drive", "continuous", "keep", "struggle", "grit", "hustle"],
    "Hod": ["detail", "documentation", "meticulous", "process", "syntax", "craft", "precise", "specificity", "step", "code", "bug", "trace", "fix", "audit", "refactor"],
    "Yesod": ["foundation", "subconscious", "buffer", "habit", "staging", "queue", "reflection", "dream", "mirror", "memory", "latent", "psychological", "storage", "cache"],
    "Malkuth": ["hungry", "eat", "food", "body", "tired", "sleep", "physical", "manifestation", "action", "output", "hardware", "execution", "world", "sensory", "pain", "exhausted"]
}

BASE_BALANCING_RULES = {
    "Malkuth": "Yesod Subconscious Staging / Biological Nourishment Protocol",
    "Geburah": "Chesed Expansive Flow (O(1) Radix)",
    "Chesed": "Geburah Structural Constraint (O(n²) Selection)",
    "Hod": "Chokmah Visionary Spark (O(n log n) Quicksort)",
    "Netzach": "Tifereth Harmonious Integration (O(n log n) Merge)",
    "Tifereth": "Yesod Foundation Baseline Staging",
    "Daath": "Tifereth Centered Alignment",
    "Binah": "Chesed Boundless Freedom",
    "Chokmah": "Binah System Architecture Formatting",
    "Keter": "Malkuth Tangible Execution"
}

# ==============================================================================
# GLYPH CORRESPONDENCE COLOR LAYER (display only)
# ==============================================================================
# Maps a dominant-sephirah classification (already computed and already
# tested elsewhere in this file) to a display color, per
# docs/glyph_correspondence_codex.md's Planet table. This is DISPLAY ONLY:
# it does not change, refine, or re-classify anything -- it decorates an
# existing, already-VERIFIED output with a color, per "Option 1" from
# LIBER_0.md's entry on this feature.
#
# Deliberately covers only the 7 sephirot the codex actually maps to a
# classical planet (Tifereth, Yesod, Hod, Netzach, Geburah, Chesed,
# Binah). Keter, Chokmah, Daath, and Malkuth have no planetary color in
# the codex and are left uncolored on purpose, rather than assigned an
# invented one -- inventing a color for them would be exactly the kind of
# fabricated correspondence this repo has caught and corrected elsewhere.
#
# Uses the codex's Queen (Briah) scale -- traditionally the "creative /
# archetypal-emotional" world of the Four Scales -- as the single default
# color per sephirah. This is a display choice, not a correctness claim;
# King, Prince, or Princess scale colors would be equally valid choices.
#
# NOTE ON SPELLING: this codebase spells the sixth sephirah "Tifereth"
# throughout (SEPHIROT_CENTROIDS, dominant_seph output); the uploaded
# docs/glyph_correspondence_codex.md transliterates it "Tiphareth" --
# both are standard transliterations of the same Hebrew word (תפארת), not
# a corruption. The key below uses THIS codebase's spelling so it
# actually matches the classification output it's meant to color; a
# dedicated test (test_exactly_seven_sephirot_are_mapped) pins this down
# so a spelling mismatch here fails loudly instead of silently never
# firing.
SEPHIRAH_PLANET_COLOR = {
    "Tifereth": {"planet": "Sun",     "glyph": "☉", "hex": "#ffbf00"},
    "Yesod":     {"planet": "Moon",    "glyph": "☽", "hex": "#b0c4de"},
    "Hod":       {"planet": "Mercury", "glyph": "☿", "hex": "#ffb347"},
    "Netzach":   {"planet": "Venus",   "glyph": "♀", "hex": "#00b3a4"},
    "Geburah":   {"planet": "Mars",    "glyph": "♂", "hex": "#ff0000"},
    "Chesed":    {"planet": "Jupiter", "glyph": "♃", "hex": "#1e90ff"},
    "Binah":     {"planet": "Saturn",  "glyph": "♄", "hex": "#191970"},
}


def _hex_to_rgb(hex_color: str):
    """'#ffbf00' -> (255, 191, 0). No error handling beyond what's needed:
    every caller in this file only ever passes the hardcoded hex values
    above, which are always well-formed 6-digit hex strings."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def colorize_sephirah(seph_name: str, text: str, *, force_color: bool = False) -> str:
    """
    Wraps `text` in a 24-bit ANSI color escape matching `seph_name`'s
    Queen-scale planetary color, IF `seph_name` is one of the 7 sephirot
    SEPHIRAH_PLANET_COLOR actually maps. Returns `text` unmodified for the
    other 4 sephirot (Keter, Chokmah, Daath, Malkuth) and whenever stdout
    isn't a real terminal (checked via sys.stdout.isatty(), since ANSI
    escapes printed to a non-terminal -- a file, a pipe, a test's captured
    stdout -- would just show up as garbage characters). `force_color`
    bypasses the isatty() check for testing.
    """
    if seph_name not in SEPHIRAH_PLANET_COLOR:
        return text
    if not force_color and not sys.stdout.isatty():
        return text
    r, g, b = _hex_to_rgb(SEPHIRAH_PLANET_COLOR[seph_name]["hex"])
    return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"


def sephirah_planet_label(seph_name: str) -> str:
    """Returns ' (Sun ☉)'-style suffix for the 7 mapped sephirot, or an
    empty string for the other 4 -- used to make the missing mapping
    visible in output rather than silently absent."""
    info = SEPHIRAH_PLANET_COLOR.get(seph_name)
    if not info:
        return ""
    return f" ({info['planet']} {info['glyph']})"

# ==============================================================================
# BEHAVIOR LEARNING ENGINE
# ==============================================================================
class RCALearningEngine:
    """
    QUALIA-AWARE LEARNING (dated addition, see LIBER_0.md): of the four
    dimensions compute_qualia_vector() computes every interaction
    (Phi_somatic, H_emotional, Delta_gamma, Tau_resonance), only
    H_emotional ever fed back into anything -- via record_state(), below.
    Phi_somatic, Delta_gamma, and Tau_resonance were computed and printed
    (see the /qualia command and process_interaction()'s telemetry deck)
    but never used. record_qualia_state() (below record_state()) closes
    that gap for two of the three: Tau_resonance and Delta_gamma now also
    feed the same weight-update mechanism, via compute_qualia_reward().

    Phi_somatic is DELIBERATELY left out, not overlooked: it's already
    an exact alias of scores["Malkuth"] (see compute_qualia_vector()),
    which is already load-bearing through the existing dominant_seph
    selection pipeline -- folding it into a reward here would be
    double-counting the same signal under a different name, and there's
    no principled reading of "more body/physical relevance is better"
    the way there is for "more lexical diversity," "closer alignment
    with Tifereth/Keter," or "less unresolved Chesed/Geburah friction."
    Forcing it in anyway would be exactly the kind of arbitrary
    correspondence this project's own discipline (SEPHIROTIC_MAPPING_
    ANALYSIS.md) flags as a risk to avoid.

    record_state() itself is UNCHANGED in observable behavior -- refactored
    to share _apply_reward_update() with the new method, but its inputs,
    outputs, and every existing test in test_standalone_rca_sandbox.py
    still pass unmodified. This is an additive extension, not a rewrite.
    """
    def __init__(self, memory_path=MEMORY_FILE):
        self.memory_path = memory_path
        self.state_counts = {}
        self.transition_weights = {}
        self.total_interactions = 0
        self.load_memory()

    def load_memory(self):
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state_counts = data.get("state_counts", {})
                    self.transition_weights = data.get("transition_weights", {})
                    self.total_interactions = data.get("total_interactions", 0)
            except Exception:
                self._init_defaults()
        else:
            self._init_defaults()

    def _init_defaults(self):
        self.state_counts = {seph: 0 for seph in SEPHIROT_CENTROIDS.keys()}
        self.transition_weights = {seph: 1.0 for seph in SEPHIROT_CENTROIDS.keys()}
        self.total_interactions = 0

    def save_memory(self):
        try:
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_interactions": self.total_interactions,
                    "state_counts": self.state_counts,
                    "transition_weights": self.transition_weights,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
        except Exception:
            pass

    def _apply_reward_update(self, seph: str, reward: float):
        """Shared EMA weight-update step (new = old + lr*(reward-old)),
        factored out so record_state() (entropy-only, existing) and
        record_qualia_state() (multi-dimensional, new) apply the exact
        same mechanism to different reward inputs, rather than
        duplicating the update arithmetic in two places."""
        self.total_interactions += 1
        self.state_counts[seph] = self.state_counts.get(seph, 0) + 1
        learning_rate = 0.05
        current_weight = self.transition_weights.get(seph, 1.0)
        self.transition_weights[seph] = round(current_weight + learning_rate * (reward - current_weight), 3)
        self.save_memory()

    def record_state(self, seph: str, entropy: float):
        reward = 1.0 if entropy >= 0.5 else 0.5
        self._apply_reward_update(seph, reward)

    def record_qualia_state(self, seph: str, qualia: dict):
        """Qualia-aware sibling of record_state() -- see the class
        docstring's 'QUALIA-AWARE LEARNING' note. Uses
        compute_qualia_reward()'s multi-dimensional reward instead of
        entropy alone, through the SAME _apply_reward_update() mechanism
        record_state() uses."""
        reward = compute_qualia_reward(qualia)
        self._apply_reward_update(seph, reward)

    def get_learned_efficacy(self, seph: str) -> float:
        return self.transition_weights.get(seph, 1.0)

LEARNING_ENGINE = RCALearningEngine()

# ==============================================================================
# SYMBOLIC OS V2.0 ENGINE & EPISTEMIC EVALUATOR
# ==============================================================================
def tokenize(text: str):
    return re.findall(r"\b\w+\b", text.lower())

def compute_sephirotic_vector_scores(text: str):
    tokens = tokenize(text)
    user_vec = {t: tokens.count(t) for t in tokens}
    scores = {}
    for seph, centroid_words in SEPHIROT_CENTROIDS.items():
        centroid_vec = {cw: centroid_words.count(cw) for cw in centroid_words}
        intersection = set(user_vec.keys()) & set(centroid_vec.keys())
        numerator = sum([user_vec[x] * centroid_vec[x] for x in intersection])
        sum1 = sum([user_vec[x]**2 for x in user_vec.keys()])
        sum2 = sum([centroid_vec[x]**2 for x in centroid_vec.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)
        cos_sim = numerator / denominator if denominator else 0.0
        
        stem_hits = 0
        for t in tokens:
            for cw in centroid_words:
                if t.startswith(cw[:4]) or cw.startswith(t[:4]):
                    stem_hits += 0.15
                    break
        total_score = min(1.0, cos_sim + stem_hits)
        learned_weight = LEARNING_ENGINE.get_learned_efficacy(seph)
        scores[seph] = round(total_score * learned_weight, 3)
    return scores

def compute_qualia_vector(text: str, scores: dict):
    tokens = tokenize(text)
    phi_somatic = round(scores.get("Malkuth", 0.0), 3)
    if not tokens:
        h_emotional = 0.0
    elif len(tokens) == 1:
        h_emotional = 0.5
    else:
        unique_pairs = len(set(f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)))
        h_emotional = round(unique_pairs / (len(tokens) - 1), 3)
    geburah_score = scores.get("Geburah", 0.0)
    chesed_score = scores.get("Chesed", 0.0)
    delta_gamma = round(abs(geburah_score - chesed_score), 3)
    tifereth_score = scores.get("Tifereth", 0.0)
    keter_score = scores.get("Keter", 0.0)
    tau_resonance = round(min(1.0, (tifereth_score + keter_score) / 2.0 + 0.30), 3)
    return {
        "Phi_somatic": phi_somatic,
        "H_emotional": h_emotional,
        "Delta_gamma": delta_gamma,
        "Tau_resonance": tau_resonance
    }


def compute_qualia_reward(qualia: dict) -> float:
    """Combines three of the four qualia dimensions into a single
    continuous reward for RCALearningEngine.record_qualia_state() --
    see that class's docstring for why Phi_somatic is deliberately
    excluded (already an alias of scores["Malkuth"], no principled
    reward direction).

        h_component        = 1.0 if H_emotional >= 0.5 else 0.5
                              (unchanged from record_state()'s existing
                              entropy reward -- reused exactly, so this
                              is a genuine EXTENSION of that signal, not
                              a replacement of it)
        resonance_component = Tau_resonance directly (already in [0,1]
                              by construction -- min(1.0, ...) -- higher
                              Tifereth/Keter alignment is rewarded)
        friction_component  = 1.0 - Delta_gamma (Delta_gamma is the
                              UNRESOLVED Chesed/Geburah gap; LOW friction
                              is rewarded, not high, consistent with how
                              sephirotic_reward_engine.py already treats
                              Tifereth as the RECONCILIATION of Chesed
                              and Geburah, not their sum)

        reward = mean(h_component, resonance_component, friction_component)
    """
    h_component = 1.0 if qualia["H_emotional"] >= 0.5 else 0.5
    resonance_component = qualia["Tau_resonance"]
    friction_component = 1.0 - qualia["Delta_gamma"]
    return round((h_component + resonance_component + friction_component) / 3.0, 3)

def evaluate_v2_governance(text: str, scores: dict):
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_score = sorted_scores[0][1] if sorted_scores else 0.0
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
    
    total_energy = sum(scores.values()) or 1.0
    raw_confidence = (top_score / (total_energy + 1e-5)) * (top_score - second_score + 0.2) * 100.0
    confidence_pct = int(max(20, min(95, raw_confidence * 2.5)))
    
    tokens = tokenize(text)
    code_words = {"code", "bug", "refactor", "build", "memory", "leak", "speed", "test", "function", "fix", "syntax"}
    creative_words = {"idea", "art", "music", "write", "story", "image", "creative", "novel", "vision"}
    body_words = {"hungry", "eat", "tired", "sleep", "pain", "body", "food", "exhausted"}
    
    if any(w in code_words for w in tokens):
        teleology_mode = "Technical (Optimize for Performance & Reliability)"
    elif any(w in body_words for w in tokens):
        teleology_mode = "Physical (Optimize for Biological Homeostasis)"
    elif any(w in creative_words for w in tokens):
        teleology_mode = "Creative (Optimize for Expression & Novelty)"
    else:
        teleology_mode = "Exploratory (Optimize for Consciousness Alignment)"
        
    top_seph = sorted_scores[0][0] if sorted_scores and top_score > 0 else "Tifereth"
    falsifiability_condition = f"If taking an alternative action stabilizes entropy faster than {top_seph} integration."
    
    return {
        "dominant_seph": top_seph,
        "confidence_pct": confidence_pct,
        "teleology_mode": teleology_mode,
        "falsifiability_condition": falsifiability_condition,
        "alternatives": [s[0] for s in sorted_scores[1:3] if s[1] > 0.05]
    }

def compute_gamma(text: str) -> float:
    tokens = tokenize(text)
    if not tokens or len(tokens) <= 1:
        return 0.45
    freqs = {t: tokens.count(t) for t in set(tokens)}
    total = len(tokens)
    probs = [c / total for c in freqs.values()]
    h = -sum(p * math.log2(p + 1e-12) for p in probs)
    h_max = math.log2(len(probs)) if len(probs) > 1 else 1.0
    h_norm = h / h_max if h_max > 0 else 0.0
    return max(0.0, min(0.85, 1.0 - h_norm))

def apply_epistemic_humility(text: str, gamma: float) -> str:
    if gamma <= 0.70:
        return text
    rewritten = text
    directives = [
        (r'\bYou should definitely\b', 'One effective option is to consider'),
        (r'\bYou should\b', 'You might consider'),
        (r'\bYou must\b', 'An effective approach is to'),
        (r'\bThe best solution is\b', 'A well-supported solution is')
    ]
    for pattern, replacement in directives:
        rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
    return rewritten

def sanitize_paths(text: str) -> str:
    return re.sub(r'file:///[A-Za-z]:/[^\s]*', '[redacted_path]', text)

def synthesize_natural_conversational_response(prompt: str, seph: str, bal: str) -> str:
    conversational_voices = {
        "Malkuth": "I hear you. When your body sends a physical signal like that, it's Malkuth reminding us that hardware comes first. Before diving back into deep analytical work, consider grabbing something to eat or taking a rest.",
        "Geburah": "I completely understand how frustrating that feels. When things feel rigid or overwhelmed by constraints, you're experiencing a high-friction Geburah state. Opening up breathing room with Chesed expansion helps break this into simpler steps.",
        "Chesed": "It sounds like you're in an expansive, wide-open mindset right now with endless possibilities! Introducing a little Geburah structure can help pick the core priorities first.",
        "Daath": "That sounds like you're standing at a paradox or facing an unexpected gap—a Da'at abyss transition. Let's return to your central Tifereth grounding: what is the core goal you want to achieve right now?",
        "Hod": "You're diving deep into micro-details and precise craftsmanship—classic Hod focus. Getting the step-by-step details right is crucial.",
        "Netzach": "I see your persistence and drive pushing through the grind—that endurance is pure Netzach energy. Keep that momentum going!",
        "Chokmah": "That sounds like a brilliant creative spark flashing through—a pure Chokmah moment! While the intuition is fresh, let's capture it in a clear Binah structure.",
        "Binah": "You're building out a solid, logical system architecture and setting clear boundaries—great Binah structural thinking.",
        "Tifereth": "I love the clarity and balance in what you're sharing. You're in a centered, integrated Tifereth state where intuition and structure work together smoothly.",
        "Keter": "You're focusing right at the root intention and overarching True Will of what you want to create—a clear Keter direction."
    }
    return conversational_voices.get(seph, f"I hear what you're sharing. You seem to be working through a {seph} state. Applying {bal} helps balance your momentum.")

# ==============================================================================
# SLASH COMMAND HANDLER
# ==============================================================================
def handle_slash_command(cmd: str):
    parts = cmd.strip().split(maxsplit=1)
    base_cmd = parts[0].lower()
    extra_text = parts[1] if len(parts) > 1 else "I am analyzing code structure and system architecture"
    
    if base_cmd == "/help":
        print("""
        ============================================================
               SYMBOLIC OS V2.0 INTERACTIVE SLASH COMMAND MENU
        ============================================================
          /help    - Print this command menu
          /learn   - Launch 4-Week Software Engineering Curriculum Tutor
          /eval    - Run Epistemic Governance Evaluation Deck (/eval <text>)
          /qualia  - Inspect real-time 4D Qualia Telemetry Vector (Q)
          /memory  - Inspect persistent Q-learning weights (rca_memory.json)
          /dht     - Test Kademlia P2P UDP network node
          exit     - Exit sandbox session
        ============================================================
        """)
    elif base_cmd == "/eval":
        scores = compute_sephirotic_vector_scores(extra_text)
        gov = evaluate_v2_governance(extra_text, scores)
        print("\n" + "="*70)
        print("  EPISTEMIC GOVERNANCE V2.0 EVALUATION DECK")
        print("="*70)
        print(f" > Evaluated Target Text : \"{extra_text}\"")
        _seph = gov['dominant_seph']
        _colored_seph = colorize_sephirah(_seph, _seph)
        print(f" > Diagnosed Pattern (D2): {_colored_seph}{sephirah_planet_label(_seph)} [Confidence: {gov['confidence_pct']}%]")
        print(f" > Provisional Tag       : [PROVISIONAL METAPHOR, NOT ONTOLOGICAL TRUTH]")
        print(f" > Context Teleology     : {gov['teleology_mode']}")
        print(f" > Falsifiability Test   : {gov['falsifiability_condition']}")
        if gov['alternatives']:
            print(f" > Alternatives          : {', '.join(gov['alternatives'])}")
        print("="*70 + "\n")
    elif base_cmd == "/learn":
        print("""
        ============================================================
                4-WEEK SOFTWARE ENGINEERING CURRICULUM TUTOR
        ============================================================
          Week 1: OOP & Clean Code Design
                  Target File: inheritance_upcasting_engine.py
          Week 2: Machine Learning & Data Science
                  Target File: knn_project.py & iitd_mth432_stat_learning.py
          Week 3: Networks & Distributed Systems
                  Target File: dht_rca_node.py & grpc_web_bridge.py
          Week 4: 3D Graphics & Security Engineering
                  Target File: opengl_3d_scene_simulator.py & safe_memory_boundary_engine.py
        ============================================================
        """)
    elif base_cmd == "/memory":
        print("\n  --- [RCA PERSISTENT Q-LEARNING WEIGHTS] ---")
        print(f"  Total Interactions : {LEARNING_ENGINE.total_interactions}")
        print("  State Weights      :")
        for seph, weight in LEARNING_ENGINE.transition_weights.items():
            print(f"    {seph:10s} : {weight:.3f}")
        print()
    elif base_cmd == "/qualia":
        q = compute_qualia_vector(extra_text, compute_sephirotic_vector_scores(extra_text))
        print(f"\n  --- [4D QUALIA VECTOR TELEMETRY (Q)] ---")
        print(f"  Φ_somatic   (Body Baseline) : {q['Phi_somatic']:.3f}")
        print(f"  H_emotional (Entropy)       : {q['H_emotional']:.3f}")
        print(f"  Δγ_teleos   (Friction)      : {q['Delta_gamma']:.3f}")
        print(f"  τ_resonance (Awe Alignment) : {q['Tau_resonance']:.3f}\n")
    elif base_cmd == "/dht":
        if HAS_DHT:
            print("\n   Launching Kademlia DHT Node test on 127.0.0.1:8001...")
            dht_rca_node.main()
        else:
            print("   dht_rca_node.py not found in directory.")
    else:
        print(f"  Unknown command '{base_cmd}'. Type '/help' for options.")

# ==============================================================================
# MAIN RCA INTERACTION PIPELINE
# ==============================================================================
def process_interaction(user_input: str):
    if user_input.startswith("/"):
        handle_slash_command(user_input)
        return
        
    start_time = time.perf_counter()
    scores = compute_sephirotic_vector_scores(user_input)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    dominant_seph = sorted_scores[0][0] if sorted_scores and sorted_scores[0][1] > 0 else "Tifereth (Balanced)"
    bal_patch = BASE_BALANCING_RULES.get(dominant_seph, "Tifereth Integration")
    
    qualia = compute_qualia_vector(user_input, scores)
    LEARNING_ENGINE.record_qualia_state(dominant_seph, qualia)
    
    raw_output = synthesize_natural_conversational_response(user_input, dominant_seph, bal_patch)
    gamma = compute_gamma(raw_output)
    agency_response = apply_epistemic_humility(raw_output, gamma)
    final_output = sanitize_paths(agency_response)
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    
    print("\n" + "="*70)
    print("  SYMBOLIC OPERATING SYSTEM V2.0 - TELEMETRY DECK")
    print("="*70)
    print(f" > Input Utterance (D0)    : \"{user_input}\"")
    print(f" > Diagnosed Pattern (D2)  : {colorize_sephirah(dominant_seph, dominant_seph)}{sephirah_planet_label(dominant_seph)}")
    print(f" > Provisional Tag (Kernel): [PROVISIONAL METAPHOR, NOT ONTOLOGICAL TRUTH]")
    print(f" > QUALIA VECTOR (Q)      : Φ_somatic={qualia['Phi_somatic']:.2f} | H_emotional={qualia['H_emotional']:.2f} | Δγ_teleos={qualia['Delta_gamma']:.2f} | τ_resonance={qualia['Tau_resonance']:.2f}")
    print(f" > Directivity (gamma / D4): {gamma:.3f} (Max Cap: 0.85)")
    print(f" > Execution Latency       : {elapsed_ms:.3f} ms [Budget: <=30ms]")
    
    print("\n  [ TIKUN VISUAL ARENA - SEPHIROTIC ENERGY DISTRIBUTION ]")
    print("  " + "-"*60)
    max_len = 15
    for seph, score in scores.items():
        bar_count = int(score * max_len)
        bar = "" * bar_count + "" * (max_len - bar_count)
        pct = int(score * 100)
        marker = "  [DOMINANT]" if seph == dominant_seph and score > 0 else ""
        print(f"  {seph:10s} | {bar} | {pct:3d}%{marker}")
    print("  " + "-"*60)
    
    print("-" * 70)
    print("  CONVERSATIONAL ASSISTANT RESPONSE:")
    print("-" * 70)
    print(final_output)
    print("="*70 + "\n")

def main():
    print("""
    ================================================================
           LIBRA VOID: SYMBOLIC OPERATING SYSTEM VERSION 2.0
          Interactive Terminal Deck with Slash Commands
          Type '/help' for command menu, '/eval' for evaluation, or 'exit'
    ================================================================
    """)
    
    if len(sys.argv) > 1:
        process_interaction(" ".join(sys.argv[1:]))
        return
        
    print("Type your message below. Type '/help' for command menu or 'exit' to quit.\n")
    while True:
        try:
            user_input = input("SymbolicOS-V2 > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Closing Symbolic OS V2.0. State collapsed safely.")
                break
            process_interaction(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Symbolic OS V2.0.")
            break

if __name__ == "__main__":
    main()
