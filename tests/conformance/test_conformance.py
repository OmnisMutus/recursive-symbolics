"""The Conformance Suite, checked itself.

Ground truth: the licence's own Articles 5.1(D), 6, 8 and 9, and the honesty guard the correspondence ledger
established (a run in which nothing could be checked does not pass). The suite is what the licence points at, so
a suite that passes vacuously would be worse than no suite at all; these tests exist to make that impossible.
"""
import os
import unittest

from symbolics import conformance as C
from symbolics import ethics as E


class FakeAgency:
    GAMMA_MAX = 0.85

    @staticmethod
    def directive_strength(text):
        return 0.9 if "must" in text.lower() else 0.2

    @staticmethod
    def cap(gamma):
        return min(gamma, FakeAgency.GAMMA_MAX)


class LooseAgency(FakeAgency):
    GAMMA_MAX = 1.0

    @staticmethod
    def cap(gamma):
        return gamma


class TestChecks(unittest.TestCase):
    def test_the_package_reaches_no_network(self):
        r = C.check_no_network()
        self.assertEqual(r["status"], C.PASS, r["detail"])

    def test_a_network_import_is_caught(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "leaky.py"), "w", encoding="utf-8") as fh:
                fh.write("import urllib.request\n")
            r = C.check_no_network(tmp)
        self.assertEqual(r["status"], C.FAIL)
        self.assertIn("leaky.py", r["detail"])

    def test_other_state_boundary(self):
        self.assertEqual(C.check_other_state(E)["status"], C.PASS)

    def test_non_reduction(self):
        rows = C.check_non_reduction(E)
        self.assertEqual([r["status"] for r in rows], [C.PASS, C.PASS])

    def test_an_engine_that_lets_ranking_through_fails(self):
        class Lax:
            CAVEAT = E.CAVEAT

            @staticmethod
            def emit(value):
                return value

            check_request = staticmethod(E.check_request)

        self.assertEqual(C.check_non_reduction(Lax)[0]["status"], C.FAIL)

    def test_directivity_is_not_implemented_until_agency_exists(self):
        self.assertEqual(C.check_directivity(None)["status"], C.NOT_IMPLEMENTED)

    def test_directivity_passes_with_a_capped_implementation(self):
        self.assertEqual(C.check_directivity(FakeAgency)["status"], C.PASS)

    def test_directivity_fails_when_the_cap_is_above_the_article(self):
        self.assertEqual(C.check_directivity(LooseAgency)["status"], C.FAIL)


class TestHonestyGuard(unittest.TestCase):
    def test_the_suite_does_not_conform_while_a_duty_is_unchecked(self):
        """Today's real state: Article 6 has nothing to check yet, so the engine does not conform. That is the
        honest answer, and it is the whole reason this guard exists."""
        report = C.run()
        self.assertFalse(report["conforms"])
        self.assertEqual(report["counts"][C.FAIL], 0)
        self.assertGreaterEqual(report["counts"][C.NOT_IMPLEMENTED], 1)

    def test_it_conforms_once_every_duty_is_checked_and_holds(self):
        report = C.run(ethics=E, agency=FakeAgency)
        self.assertTrue(report["conforms"], report["rows"])
        self.assertEqual(report["counts"][C.NOT_IMPLEMENTED], 0)

    def test_one_failure_is_enough_to_stop_conformance(self):
        self.assertFalse(C.run(ethics=E, agency=LooseAgency)["conforms"])

    def test_the_report_prints_every_article(self):
        out = C.text(C.run())
        for article in ("5.1(D)", "6", "8", "9"):
            self.assertIn(f"Article {article}", out)
        self.assertIn("CONFORMS:", out)


if __name__ == "__main__":
    unittest.main()
