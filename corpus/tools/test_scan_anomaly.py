#!/usr/bin/env python3
"""
test_scan_anomaly.py
Independent correctness test for scan_anomaly.py: construct_pages_url()
(regex-based GitHub-repo-URL -> GitHub-Pages-URL conversion) and
crawl_site() (HTTP fetch + asset-verification logic).

crawl_site() makes a real network call via urllib.request.urlopen() --
this test suite never hits the network. `urllib.request.urlopen` is
patched (via unittest.mock.patch, which patches the single shared
module object, so it takes effect for scan_anomaly.py's own
`import urllib.request` too) to return hand-constructed fake HTTP
responses covering each of the three asset checks and each error path,
so every branch of crawl_site()'s logic is exercised deterministically
rather than depending on a real, changeable, external website.
"""

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent))
import scan_anomaly as sa  # noqa: E402


class TestConstructPagesUrl(unittest.TestCase):
    def test_standard_github_url_with_dot_git(self):
        url = sa.construct_pages_url(
            "https://github.com/OmnisMutus/OMARG-PHIRERA-Open-Source-Anomalous-Phenomena-Methods.git"
        )
        self.assertEqual(
            url,
            "https://OmnisMutus.github.io/OMARG-PHIRERA-Open-Source-Anomalous-Phenomena-Methods/games/web_arg/index.html",
        )

    def test_github_url_without_dot_git(self):
        url = sa.construct_pages_url("https://github.com/someuser/somerepo")
        self.assertEqual(url, "https://someuser.github.io/somerepo/games/web_arg/index.html")

    def test_username_case_is_preserved_not_lowercased(self):
        # A real, checkable property of the regex/f-string as written:
        # it does not call .lower() anywhere on the captured username.
        url = sa.construct_pages_url("https://github.com/MixedCase/Repo")
        self.assertIn("MixedCase.github.io", url)

    def test_completely_malformed_url_raises_value_error(self):
        with self.assertRaises(ValueError):
            sa.construct_pages_url("not a url at all")

    def test_url_missing_a_path_segment_raises_value_error(self):
        with self.assertRaises(ValueError):
            sa.construct_pages_url("https://github.com/onlyusername")

    def test_discovered_unanchored_regex_matches_lookalike_domains(self):
        # DISCOVERED, DOCUMENTED FINDING: the regex is
        # r'github\.com/([^/]+)/([^/.]+)(?:\.git)?' with no anchor and
        # no required scheme/host boundary -- re.search() finds it
        # anywhere in the string. "https://not-github.com/foo/bar"
        # literally contains the substring "github.com/foo/bar" (since
        # "not-github.com" ends in "github.com"), so this does NOT raise
        # ValueError the way a naive reader might expect a "not a real
        # github.com host" input to. This is a real property of the
        # regex as written, not a bug this test introduces or fixes --
        # pinned down explicitly rather than silently assumed away.
        url = sa.construct_pages_url("https://not-github.com/foo/bar")
        self.assertEqual(url, "https://foo.github.io/bar/games/web_arg/index.html")


def _fake_response(html: str, status: int = 200):
    resp = MagicMock()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.return_value = html.encode("utf-8")
    resp.status = status
    return resp


class TestCrawlSite(unittest.TestCase):
    GOOD_HTML = (
        '<html><head><link rel="stylesheet" href="style.css"></head>'
        '<body><pre class="hidden-clue">UEFUSF9JRDogUDEx</pre>'
        '<img src="anomaly_scan.jpg"></body></html>'
    )

    @patch("urllib.request.urlopen")
    def test_all_assets_verified_no_anomalies(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response(self.GOOD_HTML)
        report = sa.crawl_site("https://example.github.io/repo/games/web_arg/index.html")
        self.assertEqual(report["status"], "HTTP 200 OK")
        self.assertTrue(report["assets_verified"]["hidden_pre_block"])
        self.assertTrue(report["assets_verified"]["glitch_css_linked"])
        self.assertTrue(report["assets_verified"]["anomaly_image_linked"])
        self.assertEqual(report["anomalies"], [])

    @patch("urllib.request.urlopen")
    def test_missing_hidden_clue_is_flagged(self, mock_urlopen):
        html = self.GOOD_HTML.replace("UEFUSF9JRDogUDEx", "wrong_content")
        mock_urlopen.return_value = _fake_response(html)
        report = sa.crawl_site("https://example.github.io/repo/games/web_arg/index.html")
        self.assertFalse(report["assets_verified"]["hidden_pre_block"])
        self.assertIn("Steganographic Base64 clue is missing or malformed.", report["anomalies"])

    @patch("urllib.request.urlopen")
    def test_missing_css_is_flagged(self, mock_urlopen):
        html = self.GOOD_HTML.replace("style.css", "other.css")
        mock_urlopen.return_value = _fake_response(html)
        report = sa.crawl_site("https://example.github.io/repo/games/web_arg/index.html")
        self.assertFalse(report["assets_verified"]["glitch_css_linked"])
        self.assertIn("Glitch CSS stylesheet is not linked.", report["anomalies"])

    @patch("urllib.request.urlopen")
    def test_missing_image_is_flagged(self, mock_urlopen):
        html = self.GOOD_HTML.replace("anomaly_scan.jpg", "other.jpg")
        mock_urlopen.return_value = _fake_response(html)
        report = sa.crawl_site("https://example.github.io/repo/games/web_arg/index.html")
        self.assertFalse(report["assets_verified"]["anomaly_image_linked"])
        self.assertIn("Anomaly scan image is missing from DOM.", report["anomalies"])

    @patch("urllib.request.urlopen")
    def test_http_error_sets_error_status(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://x", code=404, msg="Not Found", hdrs=None, fp=None
        )
        report = sa.crawl_site("https://example.github.io/repo/games/web_arg/index.html")
        self.assertEqual(report["status"], "HTTP 404 Error")
        self.assertEqual(len(report["anomalies"]), 1)

    @patch("urllib.request.urlopen")
    def test_connection_error_sets_generic_error_status(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Name or service not known")
        report = sa.crawl_site("https://example.github.io/repo/games/web_arg/index.html")
        self.assertEqual(report["status"], "CONNECTION ERROR")

    @patch("urllib.request.urlopen")
    def test_report_always_includes_timestamp_and_target_url(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response(self.GOOD_HTML)
        url = "https://example.github.io/repo/games/web_arg/index.html"
        report = sa.crawl_site(url)
        self.assertEqual(report["target_url"], url)
        self.assertIn("timestamp", report)


def run_unit_test_suite():
    print("=" * 72)
    print("  SCAN_ANOMALY.PY -- CORRECTNESS TEST SUITE")
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
