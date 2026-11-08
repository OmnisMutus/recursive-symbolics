"""The measurement layer: observables in, an address out.

address.py defines a space; this module is the only thing that puts a point in it from something observed. The
observables are the ones Computational Kabbalah names:

    section 1   latency, read as a complexity class, relative to the person's own baseline and never absolute
    section 2   symbolic entropy H_s of the text itself
    (and)       the keyword centroids of the framework's own sandbox, which score a text against each Sephirah

INHERITED. SEPHIROT_CENTROIDS and the scoring are the framework's own, kept to the formula: cosine similarity
between token counts and centroid counts, plus 0.15 per token that shares a four-letter stem with a centroid
word, capped at 1.0. One thing is deliberately left out: the reference implementation multiplies each score by a
weight its learning engine has accumulated over past sessions. Here scores are reproducible, so the same text
always gives the same address, and a stateful weight would make an address depend on history nobody can inspect.
With the weights at their defaults, which is where a fresh engine starts, the two agree exactly.

A LIMITATION THAT HAS TO BE STATED, BECAUSE THE ARCHITECTURE CLAIMS OTHERWISE. address.py's seam says an address
is tradition-free and a lens is the interpretation. That holds for everything downstream of this module. It does
not hold for the measurement itself: the only derivation available today runs through a keyword table named
after the Sephiroth, and the pillars and levels below are the Tree's. So the axes are tradition-neutral in what
they mean, and tradition-derived in how they are currently computed, and every address this module builds says
so in its own derivation. A second, independent derivation (one that does not pass through a Kabbalistic table)
is the thing that would make the seam true at both ends.
"""
import math
import statistics

from . import address

# The framework's own centroids, unchanged.
SEPHIROT_CENTROIDS = {
    "Keter": ["crown", "source", "will", "direction", "origin", "pure", "intent", "primary", "primal", "infinite",
              "monad", "purpose", "teleos", "zenith", "supreme"],
    "Chokmah": ["wisdom", "vision", "quicksort", "pivot", "idea", "flash", "intuition", "spark", "creative",
                "genius", "inspiration", "swift", "eureka", "breakthrough"],
    "Binah": ["understanding", "structure", "architecture", "constraint", "logic", "container", "matrix", "format",
              "rule", "framework", "boundary", "system", "schema"],
    "Daath": ["abyss", "cavity", "hole", "gap", "paradox", "void", "crisis", "anomaly", "lag", "exception", "trap",
              "mystery", "confused", "stuck", "lost", "dissonance"],
    "Chesed": ["expansion", "flow", "unbounded", "endless", "grace", "generous", "abundance", "kindness", "mercy",
               "growth", "freedom", "vast", "radiant", "open"],
    "Geburah": ["rigid", "stuck", "restriction", "judgment", "severe", "harsh", "paralysis", "rules", "strict",
                "anger", "critical", "cut", "block", "burnout", "stress"],
    "Tifereth": ["balance", "harmony", "integration", "beauty", "synthesis", "centered", "heart", "peace",
                 "coherence", "merge", "weave", "calm", "alignment", "equilibrium"],
    "Netzach": ["grind", "persistence", "endurance", "repeat", "victory", "stubborn", "linear", "passion", "drive",
                "continuous", "keep", "struggle", "grit", "hustle"],
    "Hod": ["detail", "documentation", "meticulous", "process", "syntax", "craft", "precise", "specificity",
            "step", "code", "bug", "trace", "fix", "audit", "refactor"],
    "Yesod": ["foundation", "subconscious", "buffer", "habit", "staging", "queue", "reflection", "dream", "mirror",
              "memory", "latent", "psychological", "storage", "cache"],
    "Malkuth": ["hungry", "eat", "food", "body", "tired", "sleep", "physical", "manifestation", "action", "output",
                "hardware", "execution", "world", "sensory", "pain", "exhausted"],
}
STEM_HIT = 0.15
STEM = 4

# Where the measurement places each name. The Tree's own geometry: Severity on the left, Mercy on the right, and
# the numbers in order down the middle. Da'ath has no number, so it sits with Binah's level on the middle pillar.
PILLAR = {"Binah": 0, "Geburah": 0, "Hod": 0,
          "Keter": 1, "Daath": 1, "Tifereth": 1, "Yesod": 1, "Malkuth": 1,
          "Chokmah": 2, "Chesed": 2, "Netzach": 2}
PILLAR_AT = {0: 150, 1: address.MID, 2: 850}
LEVEL = {"Keter": 1, "Chokmah": 2, "Binah": 3, "Daath": 3, "Chesed": 4, "Geburah": 5, "Tifereth": 6,
         "Netzach": 7, "Hod": 8, "Yesod": 9, "Malkuth": 10}

CAVEAT_LATENCY = ("Latency is a proxy. A long pause is contemplation, an interruption, or a cat on the keyboard, "
                  "and this cannot tell them apart.")
CAVEAT_DERIVATION = ("Computed through a keyword table named after the Sephiroth, so the measurement is "
                     "tradition-derived even though the axis is not.")


def tokenize(text):
    return address_tokens(text)


def address_tokens(text):
    import re
    return re.findall(r"\b\w+\b", (text or "").lower())


def scores(text):
    """Each Sephirah's score for a text: the framework's own measure, without the learning weight."""
    tokens = address_tokens(text)
    counts = {t: tokens.count(t) for t in tokens}
    out = {}
    for name, centroid in SEPHIROT_CENTROIDS.items():
        centroid_counts = {w: centroid.count(w) for w in centroid}
        shared = set(counts) & set(centroid_counts)
        numerator = sum(counts[x] * centroid_counts[x] for x in shared)
        left = math.sqrt(sum(v ** 2 for v in counts.values()))
        right = math.sqrt(sum(v ** 2 for v in centroid_counts.values()))
        cosine = numerator / (left * right) if left and right else 0.0
        stems = 0.0
        for t in tokens:
            if any(t.startswith(w[:STEM]) or w.startswith(t[:STEM]) for w in centroid):
                stems += STEM_HIT
        out[name] = round(min(1.0, cosine + stems), 3)
    return out


def entropy(text):
    """Symbolic entropy H_s, normalized to 0-1000 for the address space.

    0 is one token repeated (nothing new); 1000 is every token distinct. This is the quantity agency.py's
    inherited gamma is one minus, except that gamma is clamped at 0.85 and this is not, because an axis should
    not inherit a ceiling meant for a directivity budget.
    """
    tokens = address_tokens(text)
    if len(tokens) <= 1:
        return address.MID            # nothing to measure; the middle says so without pretending
    counts = {t: tokens.count(t) for t in set(tokens)}
    total = len(tokens)
    probs = [c / total for c in counts.values()]
    h = -sum(p * math.log2(p) for p in probs)
    h_max = math.log2(len(probs)) if len(probs) > 1 else 0.0
    return address.clamp((h / h_max if h_max > 0 else 0.0) * address.HIGH)


def severity_mercy(score_map):
    """Where the scored names sit across the pillars, weighted by their scores."""
    weighted = [(PILLAR_AT[PILLAR[n]], s) for n, s in score_map.items() if s > 0]
    if not weighted:
        return address.MID
    total = sum(s for _, s in weighted)
    return address.clamp(sum(p * s for p, s in weighted) / total)


def descent(score_map):
    """How far down the Tree the scored names sit, weighted by their scores: origin at 0, manifest at 1000."""
    weighted = [((LEVEL[n] - 1) / 9 * address.HIGH, s) for n, s in score_map.items() if s > 0]
    if not weighted:
        return address.MID
    total = sum(s for _, s in weighted)
    return address.clamp(sum(d * s for d, s in weighted) / total)


def address_of(text, anchors=()):
    """An address for a piece of text, with how every axis was derived and the words it rests on."""
    s = scores(text)
    named = sorted(((v, k) for k, v in s.items() if v > 0), reverse=True)
    top = ", ".join(f"{k} {v}" for v, k in named[:3]) or "nothing scored"
    return address.at(
        severity_mercy=severity_mercy(s),
        descent=descent(s),
        entropy=entropy(text),
        derivation={
            "severity_mercy": f"scores across the pillars ({top}). {CAVEAT_DERIVATION}",
            "descent": f"scores down the levels ({top}). {CAVEAT_DERIVATION}",
            "entropy": f"symbolic entropy of {len(address_tokens(text))} tokens",
        },
        anchors=anchors,
    )


# ---------------------------------------------------------------- latency, as Computational Kabbalah reads it
CLASSES = (("O(1)", "Chesed", "instant, unimpeded"),
           ("O(log n)", "Tifereth", "balanced deliberation"),
           ("O(n)", "Netzach", "a linear slog, deep processing or saturation"),
           ("O(n^2)", "Geburah", "stalling or repeating; a stuck state"))


def latency(seconds, baseline=None):
    """A pause, read as a complexity class relative to the person's OWN baseline, never in absolute seconds.

    `baseline` is the median of their earlier pauses; given a list of pauses, the median of those. Returns the
    class, the Sephirotic reading Computational Kabbalah section 1 gives it, and the caveat, which travels with
    it because the number means much less than it looks like it does.
    """
    if isinstance(seconds, (list, tuple)):
        if not seconds:
            raise ValueError("Give at least one pause, in seconds.")
        baseline = baseline if baseline is not None else statistics.median(seconds)
        seconds = seconds[-1]
    if baseline in (None, 0):
        raise ValueError("A latency reading needs the person's own baseline; absolute seconds mean nothing here.")
    ratio = float(seconds) / float(baseline)
    index = 0 if ratio <= 1.2 else 1 if ratio <= 2.0 else 2 if ratio <= 4.0 else 3
    name, reading, what = CLASSES[index]
    return {"type": "fact", "class": name, "ratio": round(ratio, 2), "reads_as": reading, "means": what,
            "method": "the person's own median pause, not absolute seconds", "caveat": CAVEAT_LATENCY}
