#!/usr/bin/env python3
"""
test_add_meta.py
Independent correctness test for add_meta.py, a one-off JSON migration
script (already run for real against symbolic_api.json -- its version
is already "1.1.0" and it already has a "meta" key, confirmed by
directly reading the file). Lighter-weight treatment than the other
tools/ files, per this being a already-executed, one-shot migration
rather than an ongoing engine.

add_meta.py hardcodes its target paths as RELATIVE strings
("symbolic_api.json", "../omarg-ui/src/lib/symbolic_api.json"), resolved
against the process's current working directory, not `__file__`. This
test runs add_meta.py's logic against temp fixture copies by `os.chdir`-
ing into a temp directory for the duration of each test (restored via
addCleanup), rather than ever touching the real symbolic_api.json.
add_meta.py has no functions to import (it's a bare top-level script),
so this test re-executes it via `runpy.run_path()` against fixtures.

DISCOVERED, DOCUMENTED FINDING: `add_meta.py`'s own inline comment says
it "Insert[s] meta at the top by creating a new dict", but
`new_data.update(data)` OVERWRITES `new_data["meta"]` with `data["meta"]`
whenever the target file ALREADY HAS a "meta" key -- meaning re-running
this script against a file that already has one (exactly symbolic_api.json's
current real state) has NO EFFECT on the meta content at all, despite
looking like it's inserting a fresh one. It only positions "meta" first
if the file doesn't have one already. This is a real property of the
script as written, confirmed against a fixture below, not a bug this
test introduces or silently patches.
"""

import json
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
ADD_META_SCRIPT = TOOLS_DIR / "add_meta.py"


class ChdirTestCase(unittest.TestCase):
    """Runs each test with CWD set to a fresh temp directory (add_meta.py's
    relative paths resolve against CWD, not __file__), restoring the
    original CWD afterward regardless of outcome."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._old_cwd = os.getcwd()
        os.chdir(self._tmpdir)

    def tearDown(self):
        os.chdir(self._old_cwd)
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _run_add_meta(self):
        # Fresh run every time (runpy re-executes the module from
        # scratch, run_name="__main__" so its `if __name__ == ...` guard
        # -- there isn't one here, it's bare top-level code -- runs).
        runpy.run_path(str(ADD_META_SCRIPT), run_name="__not_main__")


class TestAddMetaOnFileWithoutExistingMeta(ChdirTestCase):
    def test_inserts_meta_first_and_bumps_version(self):
        fixture = {
            "sephirot": {"Kether": {"node_id": "S1"}},
            "metadata": {"version": "1.0.0", "generated_by": "test"},
        }
        Path("symbolic_api.json").write_text(json.dumps(fixture), encoding="utf-8")

        self._run_add_meta()

        result = json.loads(Path("symbolic_api.json").read_text(encoding="utf-8"))
        self.assertEqual(list(result.keys())[0], "meta")
        self.assertIn("mapping_principle", result["meta"])
        self.assertEqual(result["metadata"]["version"], "1.1.0")
        self.assertEqual(result["sephirot"], fixture["sephirot"])  # untouched


class TestAddMetaOnFileWithPreExistingMeta(ChdirTestCase):
    def test_pre_existing_meta_content_survives_unchanged(self):
        # DISCOVERED FINDING (see module docstring): re-running against
        # a file that already has ANY "meta" key leaves that key's
        # CONTENT exactly as it was -- new_data.update(data) overwrites
        # the freshly-built meta dict right back with the old one.
        old_meta = {"custom_note": "this is the pre-existing meta, untouched"}
        fixture = {
            "meta": old_meta,
            "sephirot": {"Kether": {"node_id": "S1"}},
            "metadata": {"version": "1.0.0", "generated_by": "test"},
        }
        Path("symbolic_api.json").write_text(json.dumps(fixture), encoding="utf-8")

        self._run_add_meta()

        result = json.loads(Path("symbolic_api.json").read_text(encoding="utf-8"))
        self.assertEqual(result["meta"], old_meta)  # NOT the freshly-constructed meta
        self.assertNotIn("mapping_principle", result["meta"])
        self.assertEqual(result["metadata"]["version"], "1.1.0")  # version bump still happens


class TestAddMetaOnFileMissingMetadataKey(ChdirTestCase):
    def test_raises_keyerror_when_metadata_key_absent(self):
        # DISCOVERED, DOCUMENTED FRAGILITY: add_meta.py unconditionally
        # does new_data["metadata"]["version"] = "1.1.0" -- a file with
        # no "metadata" key at all crashes the whole script with a
        # KeyError rather than failing gracefully or skipping that step.
        fixture = {"sephirot": {"Kether": {"node_id": "S1"}}}
        Path("symbolic_api.json").write_text(json.dumps(fixture), encoding="utf-8")

        with self.assertRaises(KeyError):
            self._run_add_meta()


class TestAddMetaProcessesBothTargetPaths(ChdirTestCase):
    def test_updates_both_files_when_both_exist(self):
        fixture = {
            "sephirot": {"Kether": {"node_id": "S1"}},
            "metadata": {"version": "1.0.0"},
        }
        Path("symbolic_api.json").write_text(json.dumps(fixture), encoding="utf-8")
        ui_dir = Path("../omarg-ui/src/lib")
        ui_dir.mkdir(parents=True, exist_ok=True)
        (ui_dir / "symbolic_api.json").write_text(json.dumps(fixture), encoding="utf-8")

        self._run_add_meta()

        main_result = json.loads(Path("symbolic_api.json").read_text(encoding="utf-8"))
        ui_result = json.loads((ui_dir / "symbolic_api.json").read_text(encoding="utf-8"))
        self.assertEqual(main_result["metadata"]["version"], "1.1.0")
        self.assertEqual(ui_result["metadata"]["version"], "1.1.0")

    def test_skips_missing_ui_path_without_error(self):
        # Only the primary file exists -- os.path.exists() guard means
        # the missing UI path is silently skipped, not an error.
        fixture = {"sephirot": {}, "metadata": {"version": "1.0.0"}}
        Path("symbolic_api.json").write_text(json.dumps(fixture), encoding="utf-8")
        self._run_add_meta()  # should not raise
        result = json.loads(Path("symbolic_api.json").read_text(encoding="utf-8"))
        self.assertEqual(result["metadata"]["version"], "1.1.0")


class TestRealFileAlreadyMigrated(unittest.TestCase):
    """Read-only sanity check against the REAL symbolic_api.json --
    confirms it's already been migrated (has "meta" and version 1.1.0),
    consistent with add_meta.py being a one-off script that already ran."""

    def test_real_symbolic_api_json_already_has_meta_and_version(self):
        real_path = TOOLS_DIR / "symbolic_api.json"
        data = json.loads(real_path.read_text(encoding="utf-8"))
        self.assertIn("meta", data)
        self.assertEqual(data["metadata"]["version"], "1.1.0")


def run_unit_test_suite():
    print("=" * 72)
    print("  ADD_META.PY -- CORRECTNESS TEST SUITE")
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
