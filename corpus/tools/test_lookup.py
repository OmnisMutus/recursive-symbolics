#!/usr/bin/env python3
"""
test_lookup.py
Independent correctness test for lookup.py, the read-only accessor for
hermetic_qabalah.json's 22-letter Hebrew cipher table.

INDEPENDENT GROUND TRUTH: standard Hebrew gematria values are a real,
external, well-documented fact (Aleph=1 ... Yod=10, Kaf=20, Lamed=30 ...
Qof=100, Resh=200, Shin=300, Tav=400) -- not invented by this project,
not asserted by lookup.py's own code, and checkable against any
published gematria table. STANDARD_GEMATRIA below is that independent
reference, transcribed from that external standard, not copied from
hermetic_qabalah.json.

DISCOVERED, DOCUMENTED DISCREPANCY: cross-checking all 22 letters against
that independent standard turned up exactly ONE mismatch: Kaf is stored
in hermetic_qabalah.json as cipher_value=21, but the standard value is
20. Notably, 21 is also Kaf's OWN path_key_scale in the same JSON row --
consistent with a copy-paste slip when the row was authored, not a
typo in some unrelated direction. This is a data error in
hermetic_qabalah.json, not a bug in lookup.py -- lookup.py's job is
only to read the JSON faithfully, and it does that correctly (confirmed
below by re-parsing the same file independently and comparing). Per this
project's discipline (document real discrepancies, don't silently fix
someone else's uploaded reference data without being asked), this is
pinned down as an explicit, named exception rather than either silently
ignored or silently "corrected" out from under the source file.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lookup  # noqa: E402

BASE_DIR = Path(__file__).parent
JSON_PATH = BASE_DIR / "hermetic_qabalah.json"

# Independent reference: the real, external, standard Hebrew gematria
# values -- transcribed from the standard table, not from this repo.
STANDARD_GEMATRIA = {
    "Aleph": 1, "Bet": 2, "Gimel": 3, "Dalet": 4, "Heh": 5, "Vav": 6,
    "Zayin": 7, "Chet": 8, "Tet": 9, "Yod": 10, "Kaf": 20, "Lamed": 30,
    "Mem": 40, "Nun": 50, "Samekh": 60, "Ayin": 70, "Peh": 80,
    "Tzaddi": 90, "Qof": 100, "Resh": 200, "Shin": 300, "Tav": 400,
}

KNOWN_DATA_DISCREPANCIES = {"Kaf"}  # see module docstring


class TestLookupAgainstIndependentJSONReparse(unittest.TestCase):
    """Ground truth: hermetic_qabalah.json read directly and independently
    in this test file (a second, separate json.load() call), not lookup.py's
    own cached _DATA -- confirms lookup.py's parsing/access logic is a
    faithful mirror of the file, not a coincidental match against its own
    cache."""

    @classmethod
    def setUpClass(cls):
        with JSON_PATH.open("r", encoding="utf-8") as f:
            cls.raw = json.load(f)["hermetic_qabalah_cipher"]

    def test_lookup_matches_independent_reparse_for_every_letter(self):
        for letter, row in self.raw.items():
            self.assertEqual(lookup.lookup(letter), row)

    def test_cipher_value_matches_independent_reparse_for_every_letter(self):
        for letter, row in self.raw.items():
            self.assertEqual(lookup.cipher_value(letter), row["cipher_value"])

    def test_lookup_unknown_letter_returns_empty_dict(self):
        self.assertEqual(lookup.lookup("Z"), {})

    def test_cipher_value_unknown_letter_returns_zero(self):
        self.assertEqual(lookup.cipher_value("Z"), 0)


class TestCipherValuesAgainstStandardGematria(unittest.TestCase):
    """The real test: does the JSON's cipher_value data match the actual,
    external, standard Hebrew gematria table? Answer: 21 of 22 do,
    exactly. Kaf does not (21 vs the correct 20) -- pinned down as a
    named, expected exception rather than silently passing or silently
    failing."""

    @classmethod
    def setUpClass(cls):
        with JSON_PATH.open("r", encoding="utf-8") as f:
            cls.raw = json.load(f)["hermetic_qabalah_cipher"]
        cls.by_name = {row["name"]: row["cipher_value"] for row in cls.raw.values()}

    def test_all_22_standard_names_are_present(self):
        self.assertEqual(set(self.by_name.keys()), set(STANDARD_GEMATRIA.keys()))

    def test_21_of_22_letters_match_standard_gematria_exactly(self):
        matches = [name for name, val in STANDARD_GEMATRIA.items()
                   if self.by_name[name] == val]
        self.assertEqual(len(matches), 22 - len(KNOWN_DATA_DISCREPANCIES))

    def test_kaf_is_the_one_known_discrepancy(self):
        mismatches = {name for name, val in STANDARD_GEMATRIA.items()
                      if self.by_name[name] != val}
        self.assertEqual(mismatches, KNOWN_DATA_DISCREPANCIES)

    def test_kaf_discrepancy_is_exactly_one_off_and_equals_its_own_path_scale(self):
        # Hand-checkable: the stored value (21) is exactly 1 more than the
        # standard value (20), and coincides with Kaf's own path_key_scale
        # (also 21 in the same JSON row) -- consistent with a copy-paste
        # slip, not a random error.
        with JSON_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)["hermetic_qabalah_cipher"]
        kaf_row = next(row for row in raw.values() if row["name"] == "Kaf")
        self.assertEqual(kaf_row["cipher_value"], STANDARD_GEMATRIA["Kaf"] + 1)
        self.assertEqual(kaf_row["cipher_value"], kaf_row["path_key_scale"])

    def test_every_other_letter_matches_standard_gematria_exactly(self):
        for name, standard_val in STANDARD_GEMATRIA.items():
            if name in KNOWN_DATA_DISCREPANCIES:
                continue
            self.assertEqual(self.by_name[name], standard_val,
                              f"{name}: expected {standard_val}, got {self.by_name[name]}")


class TestByTarot(unittest.TestCase):
    def test_finds_shin_by_judgement(self):
        matches = lookup.by_tarot("Judgement")
        self.assertIn("ש", matches)
        self.assertEqual(matches["ש"]["name"], "Shin")

    def test_case_insensitive(self):
        matches_lower = lookup.by_tarot("judgement")
        matches_upper = lookup.by_tarot("JUDGEMENT")
        self.assertEqual(set(matches_lower.keys()), set(matches_upper.keys()))
        self.assertIn("ש", matches_lower)

    def test_no_match_returns_empty_dict(self):
        self.assertEqual(lookup.by_tarot("Nonexistent Trump Card XYZ"), {})

    def test_partial_match_on_roman_numeral(self):
        # "The Fool (0)" for Aleph -- searching "fool" should find it.
        matches = lookup.by_tarot("fool")
        self.assertIn("א", matches)


class TestByElement(unittest.TestCase):
    def test_finds_shin_by_fire(self):
        matches = lookup.by_element("Fire")
        self.assertIn("ש", matches)

    def test_finds_tav_by_saturn(self):
        matches = lookup.by_element("Saturn")
        self.assertIn("ת", matches)

    def test_no_match_returns_empty_dict(self):
        self.assertEqual(lookup.by_element("Neptune"), {})


def run_unit_test_suite():
    print("=" * 72)
    print("  LOOKUP.PY -- CORRECTNESS TEST SUITE")
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
