"""
test_consciousness_upgrade_groundedness.py

Independent ground truth: writes a small, throwaway dummy test module to a
temp directory with tests whose outcome is known by construction
(assertTrue(True) always passes, assertTrue(False) always fails) -- the
expected classification isn't computed by any shared code path, it's true
by definition of what was written. Also empirically confirms (rather than
assumes) that unittest's loader failure marker is stable across a
nonexistent test name AND a nonexistent module name, since check_claim's
BROKEN_REFERENCE branch depends on that string appearing in both cases.
"""

import os
import shutil
import tempfile
import unittest

import sys
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from consciousness_upgrade_groundedness import (
    Claim, check_claim, check_claims, summarize,
    GROUNDED, UNGROUNDED, BROKEN_REFERENCE, UNTESTABLE,
)


DUMMY_MODULE_SOURCE = '''
import unittest

class DummyCases(unittest.TestCase):
    def test_known_pass(self):
        self.assertTrue(True)

    def test_known_fail(self):
        self.assertTrue(False)

    def test_known_error(self):
        raise RuntimeError("deliberate non-assertion error")
'''


class GroundednessTestBase(unittest.TestCase):
    """Sets up a real temp directory containing a real dummy test module,
    so check_claim's subprocess actually has something genuine to run
    against -- not a mock."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="groundedness_test_")
        with open(os.path.join(self.tmpdir, "dummy_module.py"), "w") as f:
            f.write(DUMMY_MODULE_SOURCE)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestKnownOutcomesByConstruction(GroundednessTestBase):
    def test_a_test_that_actually_passes_is_GROUNDED(self):
        claim = Claim("known-true claim", "dummy_module.DummyCases.test_known_pass")
        result = check_claim(claim, cwd=self.tmpdir)
        self.assertEqual(result.status, GROUNDED)

    def test_a_test_that_actually_fails_an_assertion_is_UNGROUNDED(self):
        claim = Claim("known-false claim", "dummy_module.DummyCases.test_known_fail")
        result = check_claim(claim, cwd=self.tmpdir)
        self.assertEqual(result.status, UNGROUNDED)

    def test_a_test_that_raises_a_non_assertion_error_is_UNGROUNDED_not_broken_reference(self):
        # An error inside a REAL, resolvable test is still a real failure
        # of that claim, not a citation problem -- must not be misfiled
        # as BROKEN_REFERENCE just because it's an Error, not a Failure.
        claim = Claim("claim backed by a crashing test", "dummy_module.DummyCases.test_known_error")
        result = check_claim(claim, cwd=self.tmpdir)
        self.assertEqual(result.status, UNGROUNDED)

    def test_a_nonexistent_test_method_is_BROKEN_REFERENCE(self):
        claim = Claim("fabricated claim", "dummy_module.DummyCases.test_this_does_not_exist")
        result = check_claim(claim, cwd=self.tmpdir)
        self.assertEqual(result.status, BROKEN_REFERENCE)

    def test_a_nonexistent_module_is_BROKEN_REFERENCE(self):
        claim = Claim("fabricated claim, wrong module", "totally_made_up_module.X.test_y")
        result = check_claim(claim, cwd=self.tmpdir)
        self.assertEqual(result.status, BROKEN_REFERENCE)

    def test_no_cited_test_is_UNTESTABLE(self):
        claim = Claim("a value judgment, not a testable proposition", None)
        result = check_claim(claim, cwd=self.tmpdir)
        self.assertEqual(result.status, UNTESTABLE)


class TestBrokenReferenceMarkerIsDistinctFromRealFailure(GroundednessTestBase):
    """Directly confirms the empirical premise the whole BROKEN_REFERENCE
    branch depends on: that unittest's loader-failure output is
    genuinely distinguishable from a real assertion failure's output,
    not just assumed to be."""

    def test_real_failure_output_does_not_contain_the_loader_marker(self):
        import subprocess, sys
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "dummy_module.DummyCases.test_known_fail"],
            cwd=self.tmpdir, capture_output=True, text=True,
        )
        self.assertNotIn("unittest.loader._FailedTest", proc.stdout + proc.stderr)
        self.assertIn("AssertionError", proc.stdout + proc.stderr)

    def test_broken_reference_output_does_contain_the_loader_marker(self):
        import subprocess, sys
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "dummy_module.DummyCases.test_nonexistent"],
            cwd=self.tmpdir, capture_output=True, text=True,
        )
        self.assertIn("unittest.loader._FailedTest", proc.stdout + proc.stderr)


class TestCheckClaimsAndSummarize(GroundednessTestBase):
    def test_batch_of_mixed_claims_classified_correctly_and_independently(self):
        claims = [
            Claim("c1", "dummy_module.DummyCases.test_known_pass"),
            Claim("c2", "dummy_module.DummyCases.test_known_pass"),
            Claim("c3", "dummy_module.DummyCases.test_known_fail"),
            Claim("c4", "dummy_module.DummyCases.test_nonexistent"),
            Claim("c5", None),
        ]
        results = check_claims(claims, cwd=self.tmpdir)
        statuses = [r.status for r in results]
        self.assertEqual(statuses, [GROUNDED, GROUNDED, UNGROUNDED, BROKEN_REFERENCE, UNTESTABLE])

    def test_summarize_counts_match_hand_count(self):
        claims = [
            Claim("c1", "dummy_module.DummyCases.test_known_pass"),
            Claim("c2", "dummy_module.DummyCases.test_known_fail"),
            Claim("c3", None),
        ]
        results = check_claims(claims, cwd=self.tmpdir)
        report = summarize(results)
        self.assertEqual(report.grounded, 1)
        self.assertEqual(report.ungrounded, 1)
        self.assertEqual(report.broken_reference, 0)
        self.assertEqual(report.untestable, 1)

    def test_groundedness_ratio_excludes_untestable_and_broken_reference_from_denominator(self):
        claims = [
            Claim("c1", "dummy_module.DummyCases.test_known_pass"),
            Claim("c2", "dummy_module.DummyCases.test_known_pass"),
            Claim("c3", "dummy_module.DummyCases.test_known_fail"),
            Claim("c4", None),  # untestable -- must not count in denominator
            Claim("c5", "dummy_module.DummyCases.test_nonexistent"),  # broken ref -- must not count
        ]
        results = check_claims(claims, cwd=self.tmpdir)
        report = summarize(results)
        # 2 grounded, 1 ungrounded -> ratio = 2/3, NOT 2/5
        self.assertAlmostEqual(report.groundedness_ratio(), 2 / 3)

    def test_ratio_is_None_not_zero_or_one_when_nothing_is_resolvable(self):
        claims = [Claim("c1", None), Claim("c2", "dummy_module.DummyCases.test_nonexistent")]
        results = check_claims(claims, cwd=self.tmpdir)
        report = summarize(results)
        self.assertIsNone(report.groundedness_ratio())

    def test_each_claim_checked_in_its_own_subprocess_one_crash_does_not_block_others(self):
        claims = [
            Claim("crashes", "dummy_module.DummyCases.test_known_error"),
            Claim("still runs after the crash", "dummy_module.DummyCases.test_known_pass"),
        ]
        results = check_claims(claims, cwd=self.tmpdir)
        self.assertEqual(results[0].status, UNGROUNDED)
        self.assertEqual(results[1].status, GROUNDED)  # not affected by claim 0's crash


if __name__ == "__main__":
    unittest.main(verbosity=2)
