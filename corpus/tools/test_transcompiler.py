#!/usr/bin/env python3
"""
test_transcompiler.py
Independent correctness test for transcompiler.py's Transcompiler and
RecursiveMeaningLoop classes.

Most tests run against a small, hand-constructed temp schema fixture
(not the real symbolic_schema.json) so expected values are simple enough
to state directly in each test, and so save_schema() tests never touch
the real file. A separate, smaller TestAgainstRealSchema class sanity-
checks the actual symbolic_schema.json loads and behaves as documented.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import transcompiler as tc  # noqa: E402

REAL_SCHEMA_PATH = Path(__file__).parent / "symbolic_schema.json"

FIXTURE_SCHEMA = {
    "schema_name": "test_schema",
    "version": "1.0",
    "traditions_registered": ["Kabbalah", "Zen", "CBT"],
    "abstract_mapping": {
        "anger": {"Kabbalah": "Geburah", "Zen": "Attachment", "CBT": None},
        "focus": {"Kabbalah": "Hod", "Zen": "Samadhi", "CBT": "Attention"},
    },
}


class TestTranscompilerAgainstFixture(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.schema_path = Path(self._tmpdir) / "test_schema.json"
        self.schema_path.write_text(json.dumps(FIXTURE_SCHEMA), encoding="utf-8")
        self.tc = tc.Transcompiler(schema_path=str(self.schema_path))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_list_concepts(self):
        self.assertEqual(self.tc.list_concepts(), ["anger", "focus"])

    def test_list_traditions(self):
        self.assertEqual(self.tc.list_traditions(), ["Kabbalah", "Zen", "CBT"])

    def test_translate_default_targets_excludes_source(self):
        result = self.tc.translate("anger", source_tradition="Kabbalah")
        self.assertEqual(result.source_reading, "Geburah")
        self.assertEqual(result.translations, {"Zen": "Attachment", "CBT": None})
        self.assertEqual(result.untranslated_traditions, ["CBT"])
        self.assertEqual(result.caveat, tc.Transcompiler.DEFAULT_CAVEAT)

    def test_translate_explicit_targets(self):
        result = self.tc.translate("focus", source_tradition="Zen", target_traditions=["CBT"])
        self.assertEqual(result.translations, {"CBT": "Attention"})
        self.assertEqual(result.untranslated_traditions, [])

    def test_translate_unknown_concept_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.tc.translate("nonexistent_concept", source_tradition="Kabbalah")

    def test_translate_unknown_tradition_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.tc.translate("anger", source_tradition="Nonexistent_Tradition")

    def test_add_mapping_to_existing_concept_new_tradition(self):
        self.tc.add_user_tradition_mapping("anger", "Stoic", "An impression, not a harm")
        self.assertIn("Stoic", self.tc.list_traditions())
        result = self.tc.translate("anger", source_tradition="Kabbalah", target_traditions=["Stoic"])
        self.assertEqual(result.translations["Stoic"], "An impression, not a harm")
        # Existing concepts not yet given a Stoic reading get None, not KeyError.
        result2 = self.tc.translate("focus", source_tradition="Kabbalah", target_traditions=["Stoic"])
        self.assertIsNone(result2.translations["Stoic"])

    def test_add_mapping_creates_brand_new_concept(self):
        self.tc.add_user_tradition_mapping("envy", "Kabbalah", "Netzach")
        self.assertIn("envy", self.tc.list_concepts())
        result = self.tc.translate("envy", source_tradition="Kabbalah")
        self.assertEqual(result.source_reading, "Netzach")
        # Other traditions default to None for the brand-new concept.
        self.assertIsNone(result.translations["Zen"])

    def test_save_schema_round_trips_added_mapping(self):
        self.tc.add_user_tradition_mapping("anger", "Stoic", "An impression, not a harm")
        out_path = Path(self._tmpdir) / "saved.json"
        self.tc.save_schema(str(out_path))
        reloaded = tc.Transcompiler(schema_path=str(out_path))
        self.assertIn("Stoic", reloaded.list_traditions())
        result = reloaded.translate("anger", source_tradition="Kabbalah", target_traditions=["Stoic"])
        self.assertEqual(result.translations["Stoic"], "An impression, not a harm")

    def test_save_schema_with_no_path_targets_the_module_default_not_the_loaded_file(self):
        # DISCOVERED, DOCUMENTED FINDING (caught by this test file's first
        # draft actually overwriting the real symbolic_schema.json --
        # immediately restored from git afterward; see LIBER_0.md):
        # save_schema(path=None) does NOT save back to whatever file this
        # Transcompiler instance was constructed from. Transcompiler
        # never stores the path it was loaded from -- __init__ uses a
        # local `target_path` variable, not `self.schema_path` -- so
        # save_schema()'s own `target_path = path or str(DEFAULT_SCHEMA_PATH)`
        # falls back to the hardcoded MODULE-LEVEL constant every time,
        # regardless of which file .schema was actually loaded from.
        # Concretely: a Transcompiler loaded from a custom/temp schema,
        # then saved with no explicit path, silently writes to the real
        # default symbolic_schema.json instead of back to its own source
        # file. This test proves that danger safely, by monkeypatching
        # DEFAULT_SCHEMA_PATH itself to a throwaway temp file for its
        # duration -- it must NEVER be run in a way that lets the real
        # module-level default get written to.
        real_default = tc.DEFAULT_SCHEMA_PATH
        decoy_default_path = Path(self._tmpdir) / "decoy_default.json"
        try:
            tc.DEFAULT_SCHEMA_PATH = decoy_default_path
            self.tc.add_user_tradition_mapping("anger", "Stoic", "test reading")
            self.tc.save_schema()  # no path -> targets tc.DEFAULT_SCHEMA_PATH, NOT self.schema_path
            self.assertTrue(decoy_default_path.is_file())
            self.assertFalse(self.schema_path.read_text(encoding="utf-8").count("Stoic"),
                              "save_schema() with no path must NOT have touched the originally-loaded file")
            reloaded = json.loads(decoy_default_path.read_text(encoding="utf-8"))
            self.assertIn("Stoic", reloaded["traditions_registered"])
        finally:
            tc.DEFAULT_SCHEMA_PATH = real_default


class TestAgainstRealSchema(unittest.TestCase):
    """Sanity checks against the actual symbolic_schema.json -- read-only,
    never calls save_schema() against the real file."""

    @classmethod
    def setUpClass(cls):
        cls.tc = tc.Transcompiler()

    def test_real_schema_has_anger_concept(self):
        self.assertIn("anger", self.tc.list_concepts())

    def test_real_schema_has_kabbalah_tradition(self):
        self.assertIn("Kabbalah", self.tc.list_traditions())

    def test_real_translate_anger_from_kabbalah(self):
        result = self.tc.translate("anger", source_tradition="Kabbalah")
        self.assertIn("Geburah", result.source_reading)
        self.assertIn("Zen", result.translations)


class TestRecursiveMeaningLoop(unittest.TestCase):
    def setUp(self):
        self.loop = tc.RecursiveMeaningLoop()

    def test_first_cycle_has_no_prior_meaning(self):
        event = self.loop.log_cycle(
            word="discipline", tradition="Kabbalah",
            action_taken="Forced rigid schedule",
            experience_reported="Burned out",
            meaning_after="Discipline = self-punishment",
        )
        self.assertIsNone(event.meaning_before)
        self.assertEqual(event.meaning_after, "Discipline = self-punishment")

    def test_second_cycle_carries_forward_prior_meaning(self):
        self.loop.log_cycle(
            word="discipline", tradition="Kabbalah", action_taken="A",
            experience_reported="B", meaning_after="Meaning 1",
        )
        event2 = self.loop.log_cycle(
            word="discipline", tradition="Kabbalah", action_taken="C",
            experience_reported="D", meaning_after="Meaning 2",
        )
        self.assertEqual(event2.meaning_before, "Meaning 1")

    def test_different_tradition_is_independent_history(self):
        self.loop.log_cycle(word="discipline", tradition="Kabbalah", action_taken="A",
                             experience_reported="B", meaning_after="K-meaning")
        event = self.loop.log_cycle(word="discipline", tradition="Zen", action_taken="A",
                                     experience_reported="B", meaning_after="Z-meaning")
        self.assertIsNone(event.meaning_before)  # Zen history is separate from Kabbalah's

    def test_semantic_drift_true_when_meaning_changes(self):
        self.loop.log_cycle(word="discipline", tradition="Kabbalah", action_taken="A",
                             experience_reported="B", meaning_after="Meaning 1")
        self.loop.log_cycle(word="discipline", tradition="Kabbalah", action_taken="C",
                             experience_reported="D", meaning_after="Meaning 2")
        drift = self.loop.semantic_drift("discipline", "Kabbalah")
        self.assertTrue(drift["drifted"])
        self.assertEqual(drift["first_meaning"], "Meaning 1")
        self.assertEqual(drift["current_meaning"], "Meaning 2")
        self.assertEqual(drift["cycles_logged"], 2)

    def test_semantic_drift_false_when_meaning_unchanged(self):
        self.loop.log_cycle(word="focus", tradition="Zen", action_taken="A",
                             experience_reported="B", meaning_after="Same meaning")
        self.loop.log_cycle(word="focus", tradition="Zen", action_taken="C",
                             experience_reported="D", meaning_after="Same meaning")
        drift = self.loop.semantic_drift("focus", "Zen")
        self.assertFalse(drift["drifted"])

    def test_semantic_drift_no_history_returns_empty_shape(self):
        drift = self.loop.semantic_drift("nonexistent", "Kabbalah")
        self.assertEqual(drift, {"word": "nonexistent", "tradition": "Kabbalah",
                                  "history": [], "drifted": False})

    def test_full_report_covers_every_logged_word_tradition_pair(self):
        self.loop.log_cycle(word="discipline", tradition="Kabbalah", action_taken="A",
                             experience_reported="B", meaning_after="M1")
        self.loop.log_cycle(word="focus", tradition="Zen", action_taken="A",
                             experience_reported="B", meaning_after="M2")
        report = self.loop.full_report()
        self.assertEqual(set(report.keys()), {"discipline [Kabbalah]", "focus [Zen]"})
        self.assertEqual(report["discipline [Kabbalah]"]["current_meaning"], "M1")


def run_unit_test_suite():
    print("=" * 72)
    print("  TRANSCOMPILER.PY -- CORRECTNESS TEST SUITE")
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
