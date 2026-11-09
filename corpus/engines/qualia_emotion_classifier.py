#!/usr/bin/env python3
"""
qualia_emotion_classifier.py
Translates standalone_rca_sandbox.py's 4-dimensional qualia vector
(Phi_somatic, H_emotional, Delta_gamma, Tau_resonance) into one of the
100 named emotions in docs/glyph_correspondence_codex.md's "100-Emotion
Codex" table -- the exact mapping glyph_emotion_codex.py's own docstring
and glyph_emotion_correspondence_ledger.py explicitly registered as
UNTESTABLE, because building it would otherwise require inventing a
per-emotion qualia signature with no independent ground truth in either
source document.

This module does NOT invent one. Every number it uses to make the
mapping already existed somewhere in this repo before this file was
written:

  STAGE 1 -- which of the 7 planet-mapped sephirot (see
  SEPHIRAH_PLANET_COLOR in standalone_rca_sandbox.py) an input's qualia
  vector is closest to. The "reference" qualia signature for a sephirah
  is computed by feeding that sephirah's OWN existing centroid word list
  (SEPHIROT_CENTROIDS, already load-bearing throughout that file)
  through the SAME compute_sephirotic_vector_scores() /
  compute_qualia_vector() pipeline any real input text goes through.
  Nothing new is asserted about what a sephirah "feels like" -- it's
  this classifier's own self-description of its own centroid words, in
  its own coordinate system, compared to the input's coordinates in that
  same system.

  STAGE 2 -- which of the ~10-20 emotions assigned to that sephirah (via
  the Esoteric column's planet name, e.g. "Mars" -> Geburah) the input is
  closest to. This uses ONLY each emotion's own EXISTING gradient hex
  from the codex table, converted to HSL via the standard (not invented)
  RGB->HLS transform, compared against the input's Tau_resonance value.
  Tau_resonance is already documented elsewhere in this repo (see
  docs/rca_sandbox_gamma_kabbalistic_hand_verification.md) as measuring
  alignment with the harmonizing/resonant sephirot (Tifereth, Keter) --
  and the codex's own color choices already run light-to-dark from its
  most vital, resonant emotions (Ecstasy, #ffef8a) to its most
  annihilating ones (Annihilation, Despair, #000000). Lightness is a
  real, pre-existing property of the document's own data pressed into
  service as a proxy for resonance -- a stated design choice, not a
  proven fact about the whole table (see the hand-verification doc for
  the handful of spot values this is actually checked against).

TWO HONEST GAPS, left as gaps rather than papered over:
  - Chesed (Jupiter) has ZERO emotions in the codex -- "Jupiter" never
    appears in the Esoteric column of any of the 100 rows (confirmed by
    grep against the source document, not assumed). Chesed is therefore
    excluded from Stage 1's candidate sephirot entirely, the same
    treatment SEPHIRAH_PLANET_COLOR's own comment already gives
    Keter/Chokmah/Daath/Malkuth for lacking a planetary color.
  - 2 of the 100 emotions (#90 Madness -> Uranus, #91 Chaos -> Spirit)
    name a planet/element outside the 7 the codex maps to a sephirah.
    These stay explicitly UNCOVERED -- never classified into, on
    purpose, not silently forced into the nearest available bucket.

REGISTER DISCIPLINE (see
docs/fixed_point_closure_and_the_y_combinator.md Section 1): the
ALGORITHM here -- Euclidean distance in a 4D space, a standard RGB->HSL
transform -- is register B, real and checkable, covered by
test_qualia_emotion_classifier.py. Whether Mars "truly" governs Anger, or
whether resonance "truly" tracks color lightness, is register A --
traditional/textual/design correspondence, asserted nowhere here as more
than that. glyph_emotion_correspondence_ledger.py's existing UNTESTABLE
entry for this exact mapping is superseded by a new VERIFIED entry (see
LIBER_0.md) that names precisely what got tested: the ALGORITHM runs and
does what this docstring says, not that any emotion "truly" belongs to
any sephirah or hex value.
"""

import math
import re
import colorsys
from typing import Optional

import standalone_rca_sandbox as rca
from glyph_emotion_codex import load_emotion_codex

QUALIA_DIMS = ("Phi_somatic", "H_emotional", "Delta_gamma", "Tau_resonance")

# Reverse of standalone_rca_sandbox.SEPHIRAH_PLANET_COLOR: planet name -> sephirah.
PLANET_TO_SEPHIRAH = {info["planet"]: seph for seph, info in rca.SEPHIRAH_PLANET_COLOR.items()}

# All planet/element names that can appear in the codex's Esoteric
# column -- the 7 covered ones plus the 2 that deliberately fall outside
# SEPHIRAH_PLANET_COLOR (Uranus, Spirit).
_PLANET_RE = re.compile(r"(Sun|Moon|Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Spirit)")


def emotion_planet(esoteric: str) -> Optional[str]:
    """Extracts the planet/element name from an Esoteric column string
    like '(sun-glyph) Sun - Golden Yellow (fire-glyph)'. Returns None if
    nothing matches (a format change surfaces here rather than silently
    misclassifying)."""
    m = _PLANET_RE.search(esoteric)
    return m.group(1) if m else None


def emotion_sephirah(esoteric: str) -> Optional[str]:
    """Maps an emotion's Esoteric string to one of the 7 covered
    sephirot, or None for Uranus/Spirit/unrecognized planets -- the same
    'leave it uncovered, don't invent' rule SEPHIRAH_PLANET_COLOR already
    applies to Keter/Chokmah/Daath/Malkuth."""
    return PLANET_TO_SEPHIRAH.get(emotion_planet(esoteric))


def emotions_by_sephirah(rows=None):
    """Buckets all 100 codex rows by covered sephirah. Returns
    (buckets, uncovered) where buckets maps sephirah -> list of rows and
    uncovered is the list of rows with no covered planet. Chesed's
    bucket will be an empty list, not a missing key -- see module
    docstring: Jupiter genuinely never appears in the codex."""
    rows = rows if rows is not None else load_emotion_codex()
    buckets = {seph: [] for seph in rca.SEPHIRAH_PLANET_COLOR}
    uncovered = []
    for row in rows:
        seph = emotion_sephirah(row["esoteric"])
        if seph is None:
            uncovered.append(row)
        else:
            buckets[seph].append(row)
    return buckets, uncovered


def sephirah_reference_qualia(seph: str) -> dict:
    """The qualia vector this classifier's OWN pipeline computes for a
    sephirah's own centroid words -- e.g. what compute_qualia_vector()
    returns for the literal text built from Geburah's centroid list
    ("rigid stuck restriction judgment ..."). Not a new number: it's the
    same formula every real input goes through, run on data
    (SEPHIROT_CENTROIDS) that's already load-bearing elsewhere in this
    repo. Reads the CURRENT global rca.LEARNING_ENGINE weights, same as
    any other call to this pipeline would -- see module docstring's note
    on why that keeps Stage 1 self-consistent rather than introducing
    drift."""
    text = " ".join(rca.SEPHIROT_CENTROIDS[seph])
    scores = rca.compute_sephirotic_vector_scores(text)
    return rca.compute_qualia_vector(text, scores)


def all_sephirah_references(candidates=None) -> dict:
    candidates = candidates if candidates is not None else list(rca.SEPHIRAH_PLANET_COLOR.keys())
    return {seph: sephirah_reference_qualia(seph) for seph in candidates}


def qualia_distance(a: dict, b: dict) -> float:
    """Plain Euclidean distance across all 4 qualia dimensions. Unlike
    compute_qualia_reward() (which deliberately excludes Phi_somatic to
    avoid double-counting it into a REWARD), this is classification, not
    reward -- there's no double-counting risk in simply measuring how far
    apart two points are, so all 4 dimensions are used here."""
    return math.sqrt(sum((a[d] - b[d]) ** 2 for d in QUALIA_DIMS))


def nearest_sephirah(qualia: dict, buckets: dict, references: dict = None) -> str:
    """Nearest covered sephirah BY QUALIA DISTANCE, restricted to
    sephirot that actually have at least one emotion mapped to them in
    the codex -- Chesed is excluded here for having zero, not assigned
    the 'nearest by distance anyway' emotion of some other sephirah."""
    candidates = [seph for seph in rca.SEPHIRAH_PLANET_COLOR if buckets.get(seph)]
    if not candidates:
        raise ValueError("no sephirah has any emotions mapped to it -- codex or SEPHIRAH_PLANET_COLOR changed")
    references = references if references is not None else all_sephirah_references(candidates)
    return min(candidates, key=lambda seph: qualia_distance(qualia, references[seph]))


def hex_lightness(hex_color: str) -> float:
    """RGB -> HSL lightness, in [0, 1]. Standard colorimetric transform
    (colorsys.rgb_to_hls), applied to a hex value that already exists in
    the codex -- not a new number invented per emotion."""
    r, g, b = rca._hex_to_rgb(hex_color)
    _, l, _ = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return l


def nearest_emotion_in_bucket(tau_resonance: float, bucket: list) -> dict:
    """Within one sephirah's emotions, picks the one whose OWN existing
    hex lightness is closest to the input's Tau_resonance -- see module
    docstring (Stage 2) for why lightness stands in for resonance here."""
    if not bucket:
        raise ValueError("empty emotion bucket passed to nearest_emotion_in_bucket()")
    return min(bucket, key=lambda row: abs(hex_lightness(row["hex"]) - tau_resonance))


def classify_qualia(qualia: dict, rows=None) -> dict:
    """Full Stage 1 + Stage 2 pipeline from an already-computed qualia
    vector to one of the 100 named emotions."""
    rows = rows if rows is not None else load_emotion_codex()
    buckets, _uncovered = emotions_by_sephirah(rows)
    seph = nearest_sephirah(qualia, buckets)
    emotion = nearest_emotion_in_bucket(qualia["Tau_resonance"], buckets[seph])
    return {
        "sephirah": seph,
        "planet": rca.SEPHIRAH_PLANET_COLOR[seph]["planet"],
        "emotion": emotion["name"],
        "index": emotion["index"],
        "hex": emotion["hex"],
        "description": emotion["description"],
    }


def classify_text(text: str) -> dict:
    """End-to-end: raw text -> sephirotic scores -> qualia vector ->
    classified emotion. The full 'translation of emotions into
    algorithm, using the hex' the qualia vector was built for."""
    scores = rca.compute_sephirotic_vector_scores(text)
    qualia = rca.compute_qualia_vector(text, scores)
    result = classify_qualia(qualia)
    result["qualia"] = qualia
    result["scores"] = scores
    return result


if __name__ == "__main__":
    samples = [
        "rigid stuck restriction judgment severe harsh strict cut block",
        "expansion flow abundance grace generous kindness mercy growth open",
        "balance harmony integration beauty synthesis centered heart peace",
        "the cat sat on the mat",
    ]
    for sample in samples:
        r = classify_text(sample)
        print(f"{sample[:45]!r:48s} -> #{r['index']:>3} {r['emotion']:<16s} "
              f"({r['hex']}, {r['sephirah']}/{r['planet']})  qualia={r['qualia']}")
