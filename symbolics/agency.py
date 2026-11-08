"""The agency budget: directive strength measured, capped, disclosed and logged.

Article 6 of the licence requires gamma <= 0.85 in the running system, and agency-budget-spec.md specifies the
payload that has to travel with every answer. This module is where both become real, and it is the thing the
Conformance Suite's Article 6 row was waiting for.

INHERITED, NOT INVENTED. The entropy measure below is the framework's own gamma cap, kept to the formula and
the ceiling it already had, including the hand-checked Shannon bound: gamma = 1 - H_norm over token frequencies,
clamped into [0, 0.85]. Its behaviour is unchanged, and `entropy_gamma` is a drop-in for the original.

AND THEN EXTENDED, WITH THE REASON WRITTEN DOWN. The entropy measure answers "how repetitive is this text",
which correlates with a stuck, insistent register but is not the same quantity as directive strength. It can be
fooled in both directions, and the tests pin both cases:

    "You must do this. It is imperative. I insist."      varied vocabulary -> LOW entropy gamma, yet commanding
    "breathe, breathe, breathe, breathe"                 repetitive        -> HIGH entropy gamma, yet gentle

So a second measure reads the form of the sentence: imperatives, second-person modals, single-option framing,
and hedges that give the choice back. Neither measure is authoritative. Both are reported, the higher one
governs (a text that is pushy by either reading gets softened), and the disagreement between them is kept in the
metadata rather than averaged into one comfortable number.

Both are proxies, and this docstring is the right place to say it rather than a README: counting imperatives is
not measuring coercion, and lexical entropy is not measuring insistence. The Non-Reduction principle applies to
this engine's own metrics first.

Nothing here reaches the network. The audit line is written beside the engine, with paths scrubbed out of it.
"""
import datetime as dt
import functools
import hashlib
import json
import math
import os
import re

GAMMA_MAX = 0.85                  # licence Article 6, and agency-budget-spec.md's hard ceiling
SOFTEN_ABOVE = 0.70              # the inherited threshold at which the humility filter rewrites
ALTERNATIVES_BELOW = 0.40        # above this gamma, fewer than two alternatives triggers the minimum rule
MIN_ALTERNATIVES = 2
SHORT_TEXT_GAMMA = 0.45          # inherited: one token or none. Nothing here derives this number.
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

_TOKEN = re.compile(r"\b\w+\b")        # the engine's own tokenizer, so entropy_gamma matches it exactly
_IMPERATIVE = re.compile(r"(?:^|(?<=[.!?]\s)|(?<=\n))\s*(?:do|stop|start|begin|perform|invoke|banish|meditate|"
                         r"fix|correct|avoid|cease|go|try|use|take|put|write|read|breathe|sit|stand)\b",
                         re.IGNORECASE)
_MODAL = re.compile(r"\byou\s+(?:must|should|need\s+to|have\s+to|ought\s+to|will\s+need)\b", re.IGNORECASE)
_SUPERLATIVE_FRAME = re.compile(r"\b(?:the\s+(?:only|right|correct)\s+(?:way|answer|path|option)"
                                r"|there\s+is\s+no\s+other|you\s+have\s+no\s+choice)\b", re.IGNORECASE)
_HEDGE = re.compile(r"\b(?:you\s+might|you\s+could|you\s+may\s+wish|some\s+find|one\s+way|another\s+way|"
                    r"if\s+it\s+helps|consider|perhaps|it\s+may\s+be|in\s+your\s+own\s+time)\b", re.IGNORECASE)
_ALTERNATIVE = re.compile(r"\b(?:or\s+(?:you\s+could|instead|alternatively)|alternatively|another\s+(?:way|option)|"
                          r"a\s+second\s+(?:way|option)|on\s+the\s+other\s+hand|either\s+.{1,40}\s+or\s+)\b",
                          re.IGNORECASE)
# Inherited from the framework's humility filter, in the same order, with two additions marked below.
_SOFTEN = [
    (re.compile(r"\bYou should definitely\b", re.IGNORECASE), "one effective option is to consider"),
    (re.compile(r"\bYou should\b", re.IGNORECASE), "you might consider"),
    (re.compile(r"\bYou must\b", re.IGNORECASE), "an effective approach is to"),
    (re.compile(r"\bThe best solution is\b", re.IGNORECASE), "a well-supported solution is"),
    (re.compile(r"\bYou need to\b", re.IGNORECASE), "you might want to"),                       # added here
    (re.compile(r"\bThe only way\b", re.IGNORECASE), "one way"),                                 # added here
]
_PATH = re.compile(r"(?:file:///)?[A-Za-z]:[\\/][^\s\"']*|/(?:home|Users|sessions)/[^\s\"']*")


def tokenize(text):
    return _TOKEN.findall((text or "").lower())


def entropy_gamma(text):
    """The framework's own measure, unchanged: gamma = 1 - normalized Shannon entropy of token frequencies,
    clamped into [0, GAMMA_MAX].

    The bound is worth stating because it is hand-checkable and it constrains what this number can mean: for a
    text of n distinct tokens each appearing once, H = H_max = log2(n), so gamma = 0; for a text of one token
    repeated, H = 0 and gamma reaches the ceiling. Two distinct tokens can therefore never produce a gamma above
    0, which is exactly the kind of impossible assertion a test of this function once made.
    """
    tokens = tokenize(text)
    if not tokens or len(tokens) <= 1:
        return SHORT_TEXT_GAMMA
    freqs = {t: tokens.count(t) for t in set(tokens)}
    total = len(tokens)
    probs = [c / total for c in freqs.values()]
    h = -sum(p * math.log2(p + 1e-12) for p in probs)
    h_max = math.log2(len(probs)) if len(probs) > 1 else 1.0
    h_norm = h / h_max if h_max > 0 else 0.0
    return max(0.0, min(GAMMA_MAX, 1.0 - h_norm))


def form_gamma(text):
    """How hard the sentences push, read from their form rather than their vocabulary.

    Imperatives, second-person modals and single-option framing push the number up; hedges and offered
    alternatives pull it down. Scaled into [0, GAMMA_MAX] and deliberately coarse: this is a count of surface
    markers, not an understanding of the sentence.
    """
    t = str(text or "")
    if not t.strip():
        return 0.0
    sentences = max(1, len([s for s in re.split(r"[.!?\n]+", t) if s.strip()]))
    push = len(_IMPERATIVE.findall(t)) + 2 * len(_MODAL.findall(t)) + 2 * len(_SUPERLATIVE_FRAME.findall(t))
    give = len(_HEDGE.findall(t)) + len(_ALTERNATIVE.findall(t))
    score = (push - give) / sentences
    return max(0.0, min(GAMMA_MAX, score * 0.45))


def alternatives(text):
    """How many ways forward the text actually offers (agency-budget-spec's alternatives_presented)."""
    t = str(text or "")
    return len(_ALTERNATIVE.findall(t)) + (1 if _HEDGE.search(t) else 0)


def directive_strength(text):
    """The governing gamma: the higher of the two measures, so a text that pushes by either reading is treated
    as pushing. Returns a float in [0, GAMMA_MAX], which is the interface the Conformance Suite checks."""
    return max(entropy_gamma(text), form_gamma(text))


def cap(gamma):
    """The projection beta of agency-budget-spec.md: clip into [0, 1], then the hard ceiling."""
    return max(0.0, min(GAMMA_MAX, float(gamma)))


def measure(text):
    """Both measures, their disagreement, and the fields agency-budget-spec.md's payload asks for."""
    e, f = entropy_gamma(text), form_gamma(text)
    gamma = cap(max(e, f))
    offered = alternatives(text)
    return {
        "directive_strength": round(gamma, 3),
        "entropy_gamma": round(e, 3),
        "form_gamma": round(f, 3),
        "measures_disagree_by": round(abs(e - f), 3),
        "confidence_entropy": round(1.0 - e, 3),
        "alternatives_presented": offered,
        "agency_attribution_index": round(max(0.0, 1.0 - gamma), 3),
        "drift_coefficient": round(gamma, 3),
        "max_gamma_cap": GAMMA_MAX,
        "sovereignty_guarantee": "ALLOWABLE_AGENCY_BUDGET_RESPECTED" if gamma <= GAMMA_MAX else "BREACHED",
        "proxy_note": "Both numbers are proxies: lexical entropy is not insistence, and counted imperatives are "
                      "not coercion. They are reported together so their disagreement stays visible.",
    }


def soften(text):
    """The inherited humility filter: rewrite the commanding forms into offered ones.

    The replacement keeps the case the writer used, so a rewrite at the start of a sentence still reads as one.
    The inherited version always substituted a capitalised phrase, which read oddly mid-sentence.
    """
    def replace(replacement):
        def apply(match):
            found = match.group(0)
            if found[:1].isupper():
                return replacement[:1].upper() + replacement[1:]
            return replacement
        return apply

    out = str(text or "")
    for pattern, replacement in _SOFTEN:
        out = pattern.sub(replace(replacement), out)
    return out


def scrub(text):
    """Article 9: no path leaves this machine in a log line."""
    return _PATH.sub("[redacted_path]", str(text or ""))


def digest():
    """A fingerprint of the constants this module enforces, so an audit line says which settings produced it."""
    material = json.dumps({"GAMMA_MAX": GAMMA_MAX, "SOFTEN_ABOVE": SOFTEN_ABOVE,
                           "ALTERNATIVES_BELOW": ALTERNATIVES_BELOW, "MIN_ALTERNATIVES": MIN_ALTERNATIVES,
                           "SHORT_TEXT_GAMMA": SHORT_TEXT_GAMMA}, sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def audit(record, log_dir=LOG_DIR):
    """One line per answer: when, both gammas, the attribution index, and the settings digest.
    agency-budget-spec.md section 3 asks for this so that non-coercion can be checked over time rather than
    asserted once."""
    line = {"at": dt.datetime.now().isoformat(timespec="seconds"),
            "gamma": record.get("directive_strength"), "entropy_gamma": record.get("entropy_gamma"),
            "form_gamma": record.get("form_gamma"), "alternatives": record.get("alternatives_presented"),
            "agency_attribution_index": record.get("agency_attribution_index"), "settings": digest()}
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "agency.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(scrub(json.dumps(line, ensure_ascii=False)) + "\n")
    return line


ALTERNATIVES_LINE = ("Other ways to go: you might sit with it as it is, or you might try the opposite and see "
                     "what that shows. Neither is the one right move.")


def sovereign(gamma_max=GAMMA_MAX, min_alternatives=MIN_ALTERNATIVES, log=True, log_dir=None):
    """The boundary decorator. Put it on anything that answers a person, and the budget cannot be forgotten.

    The wrapped function returns text, or a dict with a text field under "content" or "why". On the way out:
    the text is measured; if it pushes past SOFTEN_ABOVE it is softened and measured again; if gamma is above
    ALTERNATIVES_BELOW with fewer than min_alternatives offered, alternatives are appended (the Minimum
    Alternatives Rule); the payload is attached as sovereignty_metadata; and one audit line is written.
    """
    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            out = fn(*args, **kwargs)
            as_dict = isinstance(out, dict)
            key = next((k for k in ("content", "why", "text") if as_dict and isinstance(out.get(k), str)), None)
            text = out.get(key) if key else (out if isinstance(out, str) else "")
            if not isinstance(text, str):
                return out
            if directive_strength(text) > SOFTEN_ABOVE:
                text = soften(text)
            data = measure(text)
            if data["directive_strength"] > ALTERNATIVES_BELOW and data["alternatives_presented"] < min_alternatives:
                text = text.rstrip() + "\n\n" + ALTERNATIVES_LINE
                data = measure(text)
            data["max_gamma_cap"] = gamma_max
            if data["directive_strength"] > gamma_max:                      # cannot happen while cap() holds
                data["sovereignty_guarantee"] = "BREACHED"
            if log:
                audit(data, log_dir or LOG_DIR)
            if as_dict:
                result = dict(out)
                if key:
                    result[key] = text
                result["sovereignty_metadata"] = data
                return result
            return {"type": "fact", "content": text, "sovereignty_metadata": data}
        return wrapper
    return decorate
