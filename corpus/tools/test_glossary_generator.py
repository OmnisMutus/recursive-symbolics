#!/usr/bin/env python3
"""
test_glossary_generator.py
Independent correctness test for glossary_generator.py: make_entry(),
generate(), and main(). Lighter treatment than the other tools/ files --
this is pure deterministic markdown formatting over already-existing
data, not a novel algorithm.

main()'s hardcoded output path (Recursive-Symbolics/docs/glossary.md)
is redirected to a temp directory via the same `__file__` monkeypatch
technique used in test_ritual_compiler.py / test_telemetry_analyzer.py
-- the real docs/glossary.md already exists and must not be touched.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import glossary_generator as gg  # noqa: E402

API_PATH = Path(__file__).parent / "symbolic_api.json"


class TestMakeEntry(unittest.TestCase):
    def test_six_or_fewer_keywords_no_ellipsis(self):
        data = {"node_id": "S1", "keywords": ["a", "b", "c"], "function": "f(x) => x"}
        entry = gg.make_entry("Test", data)
        self.assertIn("a, b, c", entry)
        self.assertNotIn("…", entry)

    def test_more_than_six_keywords_truncated_with_ellipsis(self):
        data = {"node_id": "S1", "keywords": ["a", "b", "c", "d", "e", "f", "g", "h"], "function": "f(x)"}
        entry = gg.make_entry("Test", data)
        self.assertIn("a, b, c, d, e, f…", entry)
        self.assertNotIn(", g", entry)

    def test_missing_function_shows_na(self):
        data = {"node_id": "CAVITY", "keywords": ["void"], "function": None}
        entry = gg.make_entry("Daath", data)
        self.assertIn("N/A", entry)

    def test_includes_node_id_and_name_header(self):
        data = {"node_id": "S5", "keywords": ["restriction"], "function": "restrict(x)"}
        entry = gg.make_entry("Geburah", data)
        self.assertIn("### Geburah", entry)
        self.assertIn("**Node ID:** S5", entry)


class TestGenerateAgainstRealSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = json.loads(API_PATH.read_text(encoding="utf-8"))
        cls.output = gg.generate()

    def test_starts_with_title(self):
        self.assertTrue(self.output.startswith("# Recursive Symbolics"))

    def test_contains_every_real_sephirah_name(self):
        for name in self.api["sephirot"]:
            self.assertIn(f"### {name}", self.output)

    def test_contains_every_real_path_id_and_label(self):
        for pid, pdata in self.api["paths"].items():
            self.assertIn(f"### {pid}", self.output)
            self.assertIn(pdata["label"], self.output)

    def test_daath_shows_na_function_in_real_output(self):
        # Daath's real "function" value is null in symbolic_api.json.
        self.assertIsNone(self.api["sephirot"]["Daath"]["function"])
        # Confirmed indirectly: make_entry() on the real Daath data
        # produces "N/A" (checked directly, not just assumed from the
        # generate() blob where multiple "N/A" entries could appear).
        entry = gg.make_entry("Daath", self.api["sephirot"]["Daath"])
        self.assertIn("N/A", entry)


class TestMainWritesFile(unittest.TestCase):
    def test_main_writes_glossary_to_docs_dir_relative_to_parent(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmpdir, ignore_errors=True))
        fake_file = str(Path(tmpdir) / "tools" / "glossary_generator.py")
        Path(fake_file).parent.mkdir(parents=True, exist_ok=True)

        old_file = gg.__file__
        try:
            gg.__file__ = fake_file
            gg.main()
        finally:
            gg.__file__ = old_file

        out_path = Path(tmpdir) / "docs" / "glossary.md"
        self.assertTrue(out_path.is_file())
        content = out_path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("# Recursive Symbolics"))


def run_unit_test_suite():
    print("=" * 72)
    print("  GLOSSARY_GENERATOR.PY -- CORRECTNESS TEST SUITE")
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
