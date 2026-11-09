#!/usr/bin/env python3
"""
glyph_emotion_correspondence_ledger.py
Worked example / proof of concept for correspondence_ledger.py, applied
to the 100-Emotion Codex in docs/glyph_correspondence_codex.md.

This is the closing item from LIBER_0.md's founding retrospective: the
100-emotion side of the glyph codex was deliberately left unwired,
because a real emotion-detection classifier or a qualia-vector-to-
emotion mapping would each require inventing ~100 keyword lists or a
per-emotion signature with no independent ground truth in either source
document to check them against -- exactly the fabrication pattern this
project's own documentation audits have caught multiple times elsewhere.

Rather than inventing either of those, or leaving the topic as
unstructured prose, this ledger does the honest middle thing: it
registers claims that ARE genuinely testable, testing them via real
code, and registers the claims that are NOT testable as explicit
UNTESTABLE rows, each with the specific reason it can't be tested,
rather than silently omitting them.

UPDATE (dated addition, see LIBER_0.md): what started as ONE testable
claim (codex data fidelity) is now TWO. The "Qualia Vector to Discrete
Emotion Mapping" entry below used to be UNTESTABLE for the reason still
given in the "Emotion Detection From Text" entry right above it: no
mapping existed, and building one would require inventing a per-emotion
signature with no ground truth anywhere. qualia_emotion_classifier.py
closes that specific gap WITHOUT inventing one -- see that module's
docstring and this ledger's updated entry for exactly how. The
"Emotion Detection From Text" claim (detecting an emotion from raw text
by keyword classification) remains untouched and still UNTESTABLE for
the reason originally stated; it is a genuinely different, harder claim
than the qualia-vector mapping, not solved by this addition.

Every entry below is expected to either VERIFY or land UNTESTABLE by
design -- this ledger has no FAILED entry, unlike ddpg_correspondence_ledger.py,
because nothing here claims something the evidence contradicts.
"""

import sys
import unittest
from pathlib import Path
from typing import List, Type

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from correspondence_ledger import CorrespondenceLedger, from_unittest_methods, ValidationResult
from test_glyph_emotion_codex import TestParsesRealDocument, TestMalformedDocumentsFailLoudly
from test_qualia_emotion_classifier import (
    TestEmotionsBySephirah,
    TestSephirahReferenceQualia,
    TestNearestSephirah,
    TestNearestEmotionInBucket,
    TestClassifyPipeline,
)


def _from_unittest_classes(test_case_classes: List[Type[unittest.TestCase]]):
    """Like correspondence_ledger.from_unittest_methods(), but re-runs
    EVERY test method on EVERY listed TestCase class -- needed here
    because the qualia-to-emotion claim is backed by several test
    classes (bucketing, reference vectors, nearest-neighbor selection,
    end-to-end classification), not one."""
    def validator() -> ValidationResult:
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        for cls in test_case_classes:
            suite.addTests(loader.loadTestsFromTestCase(cls))
        result = unittest.TestResult()
        suite.run(result)
        total = result.testsRun
        failed = len(result.failures) + len(result.errors)
        if failed:
            names = [t[0].id() for t in (result.failures + result.errors)]
            return ValidationResult(False, f"{failed}/{total} sub-checks failed: {', '.join(names)}")
        return ValidationResult(True, f"{total}/{total} sub-checks passed across {len(test_case_classes)} test classes")
    return validator


def _qualia_classifier_validator():
    return _from_unittest_classes([
        TestEmotionsBySephirah,
        TestSephirahReferenceQualia,
        TestNearestSephirah,
        TestNearestEmotionInBucket,
        TestClassifyPipeline,
    ])


def build_ledger() -> CorrespondenceLedger:
    ledger = CorrespondenceLedger("100-Emotion Codex")

    ledger.register(
        pattern="Codex Data Fidelity",
        target="glyph_emotion_codex.py's load_emotion_codex()",
        claim="The code's view of the 100-emotion table (name, gradient "
              "hex, esoteric label, description for all 100 rows) "
              "matches docs/glyph_correspondence_codex.md exactly, "
              "because it is parsed directly from that document rather "
              "than hand-copied into a separate literal that could "
              "silently drift. Verified by re-running the parser's own "
              "test suite: exact row count, in-order indices, no "
              "duplicate names, well-formed hex on every row, and three "
              "hand-verified spot checks (row 1 Ecstasy, row 41 Anger, "
              "row 100 Annihilation) against the document's literal "
              "text.",
        validator=from_unittest_methods(TestParsesRealDocument, [
            "test_parses_exactly_100_rows",
            "test_rows_are_in_table_order_1_through_100",
            "test_no_duplicate_emotion_names",
            "test_every_hex_value_is_well_formed",
            "test_spot_check_first_row_matches_document_text_exactly",
            "test_spot_check_anger_row_matches_document_text_exactly",
            "test_spot_check_last_row_matches_document_text_exactly",
            "test_parsing_is_idempotent",
        ]),
    )

    ledger.register(
        pattern="Emotion Detection From Text",
        target="(no classifier exists anywhere in this repo)",
        claim="That this system can determine which of the 100 named "
              "emotions a given piece of text expresses. No such "
              "classifier exists. Building one honestly would require "
              "inventing roughly 100 new keyword lists, one per "
              "emotion, with no independent ground truth anywhere in "
              "this repo or its source documents to check them "
              "against -- exactly the fabrication risk flagged when "
              "this codex was first uploaded, and left unbuilt for "
              "that reason.",
        validator=None,
    )

    ledger.register(
        pattern="Qualia Vector to Discrete Emotion Mapping",
        target="qualia_emotion_classifier.py's classify_qualia()/classify_text()",
        claim="UPDATED (dated addition, see LIBER_0.md): this claim used "
              "to be UNTESTABLE because no such mapping existed and "
              "building one would have required inventing a per-emotion "
              "signature with no ground truth anywhere. That gap is now "
              "closed WITHOUT inventing one: qualia_emotion_classifier.py "
              "buckets each of the 100 emotions by the covered sephirah "
              "its own Esoteric column already names (Stage 1), computes "
              "each covered sephirah's OWN reference qualia signature by "
              "running its existing SEPHIROT_CENTROIDS words through the "
              "same tested pipeline any input goes through (no new "
              "number), routes an input to its nearest such reference by "
              "plain Euclidean distance, and within that bucket picks the "
              "emotion whose OWN existing gradient hex (converted to HSL "
              "lightness, a standard transform) is closest to the "
              "input's Tau_resonance. Chesed (zero emotions in the "
              "codex -- 'Jupiter' never appears) and 2 of 100 emotions "
              "(Madness/Uranus, Chaos/Spirit) are left explicitly "
              "uncovered, not forced. What's VERIFIED here is the "
              "ALGORITHM runs and does exactly this, every time, "
              "deterministically -- NOT that any given emotion 'truly' "
              "belongs to any sephirah or hex value (that remains "
              "Register A, same as the separate correspondence-validity "
              "entry below).",
        validator=_qualia_classifier_validator(),
    )

    ledger.register(
        pattern="Esoteric / Planetary Correspondence Validity",
        target="(traditional/textual claim, Register A)",
        claim="That each emotion's Liber 777 planetary and Tattwa "
              "assignment in the codex is esoterically correct or "
              "meaningful. This is a Register A claim (see "
              "docs/fixed_point_closure_and_the_y_combinator.md §1) -- "
              "no test in this repo could validate or falsify whether "
              "a given emotion 'truly' corresponds to a given planet; "
              "that question isn't computable, it's traditional and "
              "textual.",
        validator=None,
    )

    return ledger


if __name__ == "__main__":
    ledger = build_ledger()
    ledger.run()
    print(ledger.report())
    sys.exit(0 if ledger.all_testable_passed() else 1)
