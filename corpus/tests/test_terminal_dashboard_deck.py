#!/usr/bin/env python3
"""
test_terminal_dashboard_deck.py
Correctness verification for terminal_dashboard_deck.py per TESTING_STANDARD.md.

HONEST SCOPE NOTE: unlike most engines in this repo, this file has almost no
computational logic to verify -- render_squeeze_dashboard() is a sequence of
print() calls with hardcoded, static values (e.g. "DIRECTIVITY (gamma): 0.450",
"[127.0.0.1:8001] Kademlia DHT Node : ACTIVE"). None of these numbers or
"ACTIVE" statuses are computed from, or checked against, any real running
process, socket, or measurement in this function -- they are string literals.
This test suite does NOT claim those values are true; it only verifies the
one genuine structural invariant the rendering code has: that its box-drawing
border rows are internally consistent widths (a real, currently-true property
that a careless edit could silently break). If you are looking for evidence
that "DIRECTIVITY: 0.450" reflects anything real, it doesn't -- there's
nothing in this file that measures directivity.

Ground truth used: the border rows are all constructed from the pattern
corner + ("─" * 78) + corner (or the ├/┤ middle-separator equivalent).
This test independently reconstructs that expected string and compares it
character-for-character against the actual rendered output, rather than
just checking "did it run."
"""

import sys
import io
import contextlib
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from terminal_dashboard_deck import render_squeeze_dashboard


def capture_dashboard_output() -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        render_squeeze_dashboard()
    return buf.getvalue()


class TestDashboardRendersWithoutCrashing(unittest.TestCase):
    def test_runs_and_produces_output(self):
        output = capture_dashboard_output()
        self.assertGreater(len(output), 0)

    def test_output_is_multiple_lines(self):
        output = capture_dashboard_output()
        lines = output.split("\n")
        self.assertGreater(len(lines), 10, "Dashboard should render more than a trivial single line.")


class TestBoxDrawingStructuralInvariants(unittest.TestCase):
    """The one real, checkable property of a static ASCII dashboard: its
    border rows must actually be well-formed and consistent, independent
    of what text is inside them."""

    def setUp(self):
        self.lines = capture_dashboard_output().split("\n")

    def test_top_border_is_well_formed(self):
        # Ground truth: corner + 78 horizontal-rule characters + corner,
        # reconstructed independently rather than copy-pasted from the source.
        expected_top = "┌" + "─" * 78 + "┐"
        self.assertEqual(self.lines[0], expected_top)

    def test_bottom_border_is_well_formed(self):
        expected_bottom = "└" + "─" * 78 + "┘"
        self.assertEqual(self.lines[-2], expected_bottom)  # last line is the trailing "" from print's \n

    def test_top_and_bottom_borders_are_equal_length(self):
        # If someone edits one border's dash count without the other, the
        # box visually breaks -- this is a real regression this check catches.
        top = self.lines[0]
        bottom = [l for l in self.lines if l.startswith("└")][0]
        self.assertEqual(len(top), len(bottom))

    def test_all_middle_separator_rows_match_top_border_width(self):
        # Every "├───┤" separator row must be the same total width as the
        # top/bottom borders for the box to render as a rectangle.
        top_width = len(self.lines[0])
        separator_rows = [l for l in self.lines if l.startswith("├")]
        self.assertGreater(len(separator_rows), 0, "Expected at least one middle separator row.")
        for row in separator_rows:
            self.assertEqual(len(row), top_width,
                f"Separator row {row!r} does not match border width {top_width}")

    def test_content_rows_start_and_could_end_with_vertical_bar(self):
        content_rows = [l for l in self.lines if l.startswith("│")]
        self.assertGreater(len(content_rows), 0)
        for row in content_rows:
            self.assertTrue(row.startswith("│"))


def run_unit_test_suite():
    print("=" * 72)
    print("  TERMINAL DASHBOARD DECK — RENDERING STRUCTURE TEST SUITE")
    print("  (verifies box-drawing structure only -- displayed telemetry")
    print("   values are static literals, not measured; not claimed here)")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
