#!/usr/bin/env python3
"""
test_rca_llm_sandbox.py
Independent correctness test for rca_llm_sandbox.py: sanitize_paths,
apply_epistemic_humility, fallback_rca_engine, query_local_ollama,
process_rca_interaction.

CROSS-FILE FINDING, DOCUMENTED: rca_llm_sandbox.py's sanitize_paths()
and apply_epistemic_humility() are SEPARATE, independent
reimplementations of the same ideas already present in
solo/standalone_rca_sandbox.py. sanitize_paths() uses the exact same
regex in both files (cross-checked below). apply_epistemic_humility()
does NOT: rca_llm_sandbox.py's version has 5 directive-softening
patterns; standalone_rca_sandbox.py's has only 4 -- missing "This is the
correct interpretation" -> "One compelling interpretation is". This is a
real, checked discrepancy between two independent implementations of
"the same idea," not introduced or fixed by this test file.

query_local_ollama() makes a real network call to localhost:11434. Most
tests here mock urllib.request.urlopen to avoid a real (and, in this
sandboxed environment, always-failing) 3-second-timeout network round
trip. Exactly one test (test_real_environment_has_no_ollama_running)
does NOT mock it, to confirm directly that this specific sandboxed
environment's actual behavior matches the code's documented fallback
path -- that test is expected to take a few real seconds by design.
"""

import io
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import rca_llm_sandbox as rls  # noqa: E402

# standalone_rca_sandbox.py lives beside this folder, in the corpus's engines/.
# CORRECTED 2026-11-09 during consolidation: this pointed at "<parent>/solo", which was wrong by one
# directory in the original layout (the module is in solo/engines/, not solo/) and absent entirely here.
# So the guard below passed in the old location and the import then failed, and in the new location the
# guard failed and both cross-checks skipped silently. The cross-file check had never run in either place.
_SOLO_DIR = Path(__file__).parent.parent / "engines"
_HAS_SOLO_SANDBOX = _SOLO_DIR.is_dir()
if _HAS_SOLO_SANDBOX:
    sys.path.insert(0, str(_SOLO_DIR))
    import standalone_rca_sandbox as rca  # noqa: E402


class TestSanitizePaths(unittest.TestCase):
    def test_redacts_windows_style_file_uri(self):
        text = "See file:///C:/Users/testuser/secret.txt for details."
        self.assertEqual(rls.sanitize_paths(text), "See [redacted_path] for details.")

    def test_leaves_non_file_uri_text_untouched(self):
        text = "Visit https://example.com instead."
        self.assertEqual(rls.sanitize_paths(text), text)

    @unittest.skipUnless(_HAS_SOLO_SANDBOX, "sibling solo/ repo not found")
    def test_matches_standalone_rca_sandboxs_identical_regex(self):
        # Cross-check: both files' sanitize_paths() should behave
        # IDENTICALLY, since they use the exact same regex pattern.
        text = "Path: file:///D:/some/deep/path/file.py and more text"
        self.assertEqual(rls.sanitize_paths(text), rca.sanitize_paths(text))


class TestApplyEpistemicHumility(unittest.TestCase):
    def test_low_gamma_leaves_text_unchanged(self):
        text = "You must do this immediately."
        self.assertEqual(rls.apply_epistemic_humility(text, gamma=0.70), text)
        self.assertEqual(rls.apply_epistemic_humility(text, gamma=0.5), text)

    def test_high_gamma_rewrites_you_must(self):
        out = rls.apply_epistemic_humility("You must act now.", gamma=0.71)
        self.assertEqual(out, "An effective approach is to act now.")

    def test_high_gamma_rewrites_you_should_definitely_before_you_should(self):
        # Order matters: "You should definitely" must be replaced before
        # the shorter "You should" pattern, or it would double-match.
        out = rls.apply_epistemic_humility("You should definitely try this.", gamma=0.9)
        self.assertEqual(out, "One effective option is to consider try this.")

    def test_high_gamma_rewrites_the_correct_interpretation(self):
        # This 5th pattern exists in rca_llm_sandbox.py but NOT in
        # standalone_rca_sandbox.py's apply_epistemic_humility() -- see
        # module docstring.
        out = rls.apply_epistemic_humility("This is the correct interpretation.", gamma=0.9)
        self.assertEqual(out, "One compelling interpretation is.")

    @unittest.skipUnless(_HAS_SOLO_SANDBOX, "sibling solo/ repo not found")
    def test_discovered_discrepancy_with_standalone_rca_sandbox(self):
        text = "This is the correct interpretation of events."
        rls_out = rls.apply_epistemic_humility(text, gamma=0.9)
        rca_out = rca.apply_epistemic_humility(text, gamma=0.9)
        self.assertNotEqual(rls_out, rca_out)  # the two files genuinely disagree here
        self.assertEqual(rca_out, text)  # standalone_rca_sandbox has no rule for this phrase at all


class TestFallbackRCAEngine(unittest.TestCase):
    def test_geburah_knowledge_base_entry(self):
        out = rls.fallback_rca_engine("prompt", {"dominant": "Geburah", "suggestion": "Chesed"})
        self.assertIn("Geburah", out)
        self.assertIn("Merge Sort", out)

    def test_unlisted_sephirah_uses_generic_fallback(self):
        out = rls.fallback_rca_engine("prompt", {"dominant": "Yesod", "suggestion": "Tifereth"})
        self.assertIn("Yesod", out)
        self.assertIn("Tifereth", out)

    def test_missing_dominant_defaults_to_tifereth(self):
        out = rls.fallback_rca_engine("prompt", {})
        self.assertIn("Tifereth", out)


class TestQueryLocalOllama(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_returns_response_text_on_success(self, mock_urlopen):
        import json as _json
        fake = mock_urlopen.return_value.__enter__.return_value
        fake.read.return_value = _json.dumps({"response": "hello from ollama"}).encode("utf-8")
        result = rls.query_local_ollama("test prompt")
        self.assertEqual(result, "hello from ollama")

    @patch("urllib.request.urlopen")
    def test_returns_none_on_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("refused")
        self.assertIsNone(rls.query_local_ollama("test prompt"))

    @patch("urllib.request.urlopen")
    def test_returns_none_on_malformed_json(self, mock_urlopen):
        fake = mock_urlopen.return_value.__enter__.return_value
        fake.read.return_value = b"not json"
        self.assertIsNone(rls.query_local_ollama("test prompt"))

    def test_real_environment_has_no_ollama_running(self):
        # Unmocked, real network call -- confirms THIS sandboxed
        # environment genuinely has no local Ollama daemon, so
        # query_local_ollama() really does exercise its except-and-
        # return-None path here, not just in a mocked simulation of it.
        # Expected to take a few real seconds (connection refused is
        # usually fast; the 3s timeout is a ceiling, not a guarantee).
        self.assertIsNone(rls.query_local_ollama("integration check prompt"))


class TestProcessRCAInteraction(unittest.TestCase):
    @patch("rca_llm_sandbox.query_local_ollama", return_value=None)
    def test_prints_expected_telemetry_deck_fields(self, mock_query):
        # Forces the fallback path deterministically regardless of
        # whether a real Ollama daemon happens to be reachable.
        buf = io.StringIO()
        with redirect_stdout(buf):
            rls.process_rca_interaction("I feel stuck and blocked")
        output = buf.getvalue()
        self.assertIn("Sephira Diagnosis (D2)", output)
        self.assertIn("Geburah", output)  # "stuck"/"blocked" both hit Geburah keywords
        self.assertIn("Directivity (gamma / D4)", output)
        self.assertIn("RCA-BOUNDED MODEL RESPONSE", output)

    @patch("rca_llm_sandbox.query_local_ollama", return_value=None)
    def test_no_keyword_input_defaults_to_balanced_tifereth(self, mock_query):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rls.process_rca_interaction("the quick brown fox jumps")
        output = buf.getvalue()
        self.assertIn("Tifereth (Balanced)", output)


def run_unit_test_suite():
    print("=" * 72)
    print("  RCA_LLM_SANDBOX.PY -- CORRECTNESS TEST SUITE")
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
