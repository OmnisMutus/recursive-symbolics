#!/usr/bin/env python3
"""
test_glyph_emotion_codex.py
Correctness verification for glyph_emotion_codex.py per TESTING_STANDARD.md.

This tests the PARSER, not any claim about emotions or classification --
see glyph_emotion_correspondence_ledger.py for the honest boundary
between what's tested here (data fidelity to the source document) and
what is explicitly UNTESTABLE (whether any of these correspondences are
"true," or whether text/qualia-vectors can be mapped onto them at all).

Ground truth: docs/glyph_correspondence_codex.md's own literal table
text, read directly -- these tests hand-verify specific rows against
what a human reading the document would see (row 1 "Ecstasy" #ffef8a,
row 41 "Anger" #ff0000, etc.), and also construct throwaway temp
documents with deliberately broken table formats to confirm the loud
failure modes actually fire.
"""

import sys
import unittest
import tempfile
import textwrap
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from glyph_emotion_codex import load_emotion_codex, DOCS_PATH


class TestParsesRealDocument(unittest.TestCase):
    """Ground truth: the actual docs/glyph_correspondence_codex.md file,
    read directly, not a copy."""

    @classmethod
    def setUpClass(cls):
        cls.rows = load_emotion_codex()

    def test_parses_exactly_100_rows(self):
        self.assertEqual(len(self.rows), 100)

    def test_rows_are_in_table_order_1_through_100(self):
        self.assertEqual([r["index"] for r in self.rows], list(range(1, 101)))

    def test_no_duplicate_emotion_names(self):
        names = [r["name"] for r in self.rows]
        self.assertEqual(len(names), len(set(names)),
            "a duplicate emotion name would mean two rows collapsed to one key elsewhere")

    def test_every_hex_value_is_well_formed(self):
        for r in self.rows:
            self.assertRegex(r["hex"], r"^#[0-9a-f]{6}$",
                f"row {r['index']} ({r['name']}) has malformed hex: {r['hex']!r}")

    def test_spot_check_first_row_matches_document_text_exactly(self):
        row = self.rows[0]
        self.assertEqual(row["name"], "Ecstasy")
        self.assertEqual(row["hex"], "#ffef8a")
        self.assertIn("Sun", row["esoteric"])

    def test_spot_check_anger_row_matches_document_text_exactly(self):
        row = next(r for r in self.rows if r["name"] == "Anger")
        self.assertEqual(row["index"], 41)
        self.assertEqual(row["hex"], "#ff0000")
        self.assertIn("Mars", row["esoteric"])

    def test_spot_check_last_row_matches_document_text_exactly(self):
        row = self.rows[-1]
        self.assertEqual(row["index"], 100)
        self.assertEqual(row["name"], "Annihilation")
        self.assertEqual(row["hex"], "#000000")

    def test_parsing_is_idempotent(self):
        rows_again = load_emotion_codex()
        self.assertEqual(self.rows, rows_again)


class TestMalformedDocumentsFailLoudly(unittest.TestCase):
    """A silent partial parse (e.g. 3 rows instead of 100) would be a
    worse failure than a loud one -- these confirm it actually raises."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _write_doc(self, body: str) -> Path:
        path = Path(self._tmpdir.name) / "toy_codex.md"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path

    def test_missing_section_raises_value_error(self):
        doc = self._write_doc("# Some other document\n\nNo emotion table here.\n")
        with self.assertRaises(ValueError):
            load_emotion_codex(doc)

    def test_too_few_rows_raises_value_error(self):
        doc = self._write_doc("""
            ## 100-Emotion Codex (Gradient + Esoteric + Tattwa)

            | # | Emotion | Gradient (Psychological) | Esoteric (Liber 777 + Tattwa) | Description |
            | --- | --- | --- | --- | --- |
            | 1 | Ecstasy | #ffef8a | Sun | Bliss. |
            | 2 | Joy | #ffd700 | Sun | Happiness. |

            ---
        """)
        with self.assertRaises(ValueError):
            load_emotion_codex(doc)

    def test_exactly_100_well_formed_rows_parses_successfully(self):
        rows_text = "\n".join(
            f"| {i} | Emotion{i} | #{i:06x} | Test | Row {i}. |" for i in range(1, 101)
        )
        doc = self._write_doc(f"""
            ## 100-Emotion Codex (Gradient + Esoteric + Tattwa)

            | # | Emotion | Gradient (Psychological) | Esoteric (Liber 777 + Tattwa) | Description |
            | --- | --- | --- | --- | --- |
            {rows_text}

            ---
        """)
        rows = load_emotion_codex(doc)
        self.assertEqual(len(rows), 100)
        self.assertEqual(rows[0]["name"], "Emotion1")
        self.assertEqual(rows[99]["name"], "Emotion100")


def run_unit_test_suite():
    print("=" * 72)
    print("  GLYPH EMOTION CODEX PARSER -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("Test") and isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
