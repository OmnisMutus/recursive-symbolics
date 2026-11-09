#!/usr/bin/env python3
"""
test_feedback_ingester.py
Independent correctness test for feedback_ingester.py: scrub_pii,
generate_user_hash, parse_metrics_from_text, ingest_feedback.

INDEPENDENT GROUND TRUTH: scrub_pii()'s regexes are checked against
hand-constructed strings where the expected redaction is obvious by
inspection (a literal email address, a literal phone number, a literal
IP, a literal "#User:" line) -- not against feedback_ingester.py's own
assumptions about what counts as PII. generate_user_hash()'s determinism
is checked against a SEPARATE, independent `hashlib.sha256()` call in
this test file computed the same way the function's own docstring says
it should be (hash of this file's own resolved path), not by calling
generate_user_hash() twice and comparing it to itself.

`feedback_ingester.DATASET_PATH` is monkeypatched to a temp file for
every test that calls ingest_feedback() with dry_run=False, so this
suite never touches the real community_dataset.jsonl.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import feedback_ingester as fi  # noqa: E402


class TestScrubPII(unittest.TestCase):
    def test_redacts_email(self):
        out = fi.scrub_pii("Contact me at foo.bar@example.com for details.")
        self.assertNotIn("foo.bar@example.com", out)
        self.assertIn("[EMAIL_REDACTED]", out)

    def test_redacts_phone_number(self):
        out = fi.scrub_pii("Call me at 555-123-4567 tomorrow.")
        self.assertNotIn("555-123-4567", out)
        self.assertIn("[PHONE_REDACTED]", out)

    def test_redacts_ip_address(self):
        out = fi.scrub_pii("The server lives at 192.168.1.1 internally.")
        self.assertNotIn("192.168.1.1", out)
        self.assertIn("[IP_REDACTED]", out)

    def test_redacts_user_tag_line(self):
        out = fi.scrub_pii("Some text\n#User: John Doe\nMore text")
        self.assertNotIn("John Doe", out)
        self.assertIn("#User: [REDACTED]", out)

    def test_user_tag_case_insensitive(self):
        out = fi.scrub_pii("#user: Jane Roe")
        self.assertNotIn("Jane Roe", out)

    def test_leaves_ordinary_text_untouched(self):
        text = "I feel stuck in analysis, my mind loops."
        self.assertEqual(fi.scrub_pii(text), text)

    def test_all_four_patterns_together(self):
        text = "Email a@b.com or call 555-867-5309, server 10.0.0.1.\n#User: Alice"
        out = fi.scrub_pii(text)
        self.assertNotIn("a@b.com", out)
        self.assertNotIn("555-867-5309", out)
        self.assertNotIn("10.0.0.1", out)
        self.assertNotIn("Alice", out)


class TestGenerateUserHash(unittest.TestCase):
    def test_matches_independent_sha256_of_own_resolved_path(self):
        # Ground truth per generate_user_hash()'s own documented
        # behavior: sha256 of str(Path(feedback_ingester.py).resolve()),
        # first 16 hex chars. Computed here independently, not by calling
        # generate_user_hash() a second time.
        fi_path = str(Path(fi.__file__).resolve())
        expected = hashlib.sha256(fi_path.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(fi.generate_user_hash(), expected)

    def test_is_deterministic_across_calls(self):
        self.assertEqual(fi.generate_user_hash(), fi.generate_user_hash())

    def test_is_16_hex_characters(self):
        h = fi.generate_user_hash()
        self.assertEqual(len(h), 16)
        int(h, 16)  # raises ValueError if not valid hex


class TestParseMetricsFromText(unittest.TestCase):
    def test_extracts_dominant_and_patch_in_the_literal_format_the_regex_expects(self):
        # parse_metrics_from_text()'s own regex is r'Dominant:\s*([A-Za-z]+)'
        # -- it requires the literal substring "Dominant:" (colon
        # immediately after the word), not "Dominant Sephirah :".
        dominant, patch = fi.parse_metrics_from_text(
            "Dominant: Geburah\nSuggested patch: invoke Chesed on the current state."
        )
        self.assertEqual(dominant, "Geburah")
        self.assertEqual(patch, "Chesed")

    def test_missing_fields_return_none(self):
        dominant, patch = fi.parse_metrics_from_text("Nothing relevant here.")
        self.assertIsNone(dominant)
        self.assertIsNone(patch)

    def test_case_insensitive_matching(self):
        dominant, patch = fi.parse_metrics_from_text("dominant: Tifereth ... invoke yesod")
        self.assertEqual(dominant, "Tifereth")
        self.assertEqual(patch, "yesod")

    def test_discovered_mismatch_against_symbolic_debuggers_real_cli_output(self):
        # DISCOVERED, DOCUMENTED FINDING: symbolic_debugger.py's actual
        # CLI prints f"\nDominant Sephirah : {dom}" (see its main()) --
        # "Dominant Sephirah :" with a space before the colon and an
        # extra word -- NOT "Dominant:". parse_metrics_from_text()'s
        # regex therefore never matches real symbolic_debugger.py output,
        # so ingest_feedback()'s "auto-extract dominant/patch from raw
        # debugger text" feature silently returns None for both fields
        # whenever fed the real debugger's actual report text, not just
        # in some edge case. This is a real integration gap between two
        # existing files, not something introduced or fixed by this test
        # -- documented here rather than silently patched, since fixing
        # it requires a judgment call this test file isn't positioned to
        # make (loosen the regex, or change the debugger's print format).
        real_debugger_style_text = "\nDominant Sephirah : Geburah\n"
        dominant, patch = fi.parse_metrics_from_text(real_debugger_style_text)
        self.assertIsNone(dominant)  # NOT "Geburah" -- the mismatch, confirmed


class TestIngestFeedback(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._real_path = fi.DATASET_PATH
        fi.DATASET_PATH = Path(self._tmpdir) / "test_dataset.jsonl"

    def tearDown(self):
        fi.DATASET_PATH = self._real_path
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_dry_run_does_not_write_file(self):
        payload = fi.ingest_feedback("Test content", source_type="unit_test", dry_run=True)
        self.assertFalse(fi.DATASET_PATH.exists())
        self.assertEqual(payload["source"], "unit_test")
        self.assertEqual(payload["data"], "Test content")

    def test_real_run_appends_valid_json_line(self):
        fi.ingest_feedback("Some feedback", source_type="unit_test", dry_run=False)
        self.assertTrue(fi.DATASET_PATH.is_file())
        lines = fi.DATASET_PATH.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["data"], "Some feedback")
        self.assertEqual(record["source"], "unit_test")

    def test_multiple_calls_append_rather_than_overwrite(self):
        fi.ingest_feedback("First", dry_run=False)
        fi.ingest_feedback("Second", dry_run=False)
        lines = fi.DATASET_PATH.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["data"], "First")
        self.assertEqual(json.loads(lines[1])["data"], "Second")

    def test_pii_is_scrubbed_before_storage(self):
        fi.ingest_feedback("My email is a@b.com", dry_run=False)
        stored = json.loads(fi.DATASET_PATH.read_text(encoding="utf-8").strip())
        self.assertNotIn("a@b.com", stored["data"])

    def test_directive_strength_and_confidence_metrics_pass_through(self):
        payload = fi.ingest_feedback(
            "content", dry_run=True, directive_strength=0.42,
            confidence_entropy=0.31, agency_attribution_index=0.9,
        )
        self.assertEqual(payload["directive_strength_gamma"], 0.42)
        self.assertEqual(payload["confidence_entropy_hc"], 0.31)
        self.assertEqual(payload["agency_attribution_index"], 0.9)
        self.assertEqual(payload["max_gamma_cap"], 0.85)

    def test_auto_extracts_dominant_and_patch_when_text_matches_the_expected_format(self):
        payload = fi.ingest_feedback(
            "Dominant: Netzach\nSuggested patch: invoke Hod on the current state.",
            dry_run=True,
        )
        self.assertEqual(payload["dominant_sephira"], "Netzach")
        self.assertEqual(payload["patch"], "Hod")


def run_unit_test_suite():
    print("=" * 72)
    print("  FEEDBACK_INGESTER.PY -- CORRECTNESS TEST SUITE")
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
