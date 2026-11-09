#!/usr/bin/env python3
"""
test_ritual_compiler.py
Independent correctness test for ritual_compiler.py's a_star()/compile_ritual()
pathfinding over the Tree of Life's 22 traditional letter-paths.

INDEPENDENT GROUND TRUTH: the 22 paths (P11-P32) are the real, traditional
Hebrew-letter paths of the Kabbalistic Tree of Life -- not invented by
this project. This file re-derives the graph from a fresh, independent
parse of symbolic_api.json's "paths" table (not ritual_compiler.py's own
module-level `adj`).

DISCOVERED, DOCUMENTED FINDING (corrects this file's own first draft):
the shortest Kether->Malkuth route is 3 hops, but it is NOT unique --
Tiphareth (reached in 1 hop from Kether via P13) has a direct edge to
ALL THREE of Netzach (P24), Yesod (P25), and Hod (P26), and each of
those three has its OWN direct edge to Malkuth (P29, P32, P31
respectively). So there are exactly three tied, equally-short 3-hop
routes:

    Kether -P13-> Tiphareth -P24-> Netzach -P29-> Malkuth
    Kether -P13-> Tiphareth -P25-> Yesod    -P32-> Malkuth
    Kether -P13-> Tiphareth -P26-> Hod      -P31-> Malkuth

ritual_compiler.py's a_star() uses a min-heap of (priority, node_name,
path) tuples; when priority ties, Python's tuple comparison falls
through to comparing `node_name` lexicographically, and -- if THAT also
ties (as it does once "Malkuth" is reached via more than one route) --
to comparing the accumulated path lists themselves. Worked out by hand
and confirmed below: this makes a_star() deterministically return the
Hod route, because "Hod" < "Netzach" < "Yesod" alphabetically among
Tiphareth's three children, so Hod is popped and its Malkuth edge
discovered before Yesod's or Netzach's are reached in the same
priority tier. A plain FIFO breadth-first search over the SAME
adjacency data (this file's own `reference_bfs_shortest_path()`, a
second, separate implementation, not a call into a_star()) ties instead
by insertion order and returns the Netzach route, since Netzach (P24) is
the first of Tiphareth's three outgoing edges in symbolic_api.json's own
listed order. Both are correct, equally-short answers to "a shortest
path" -- they differ only in WHICH one, because the underlying graph
has a genuine 3-way tie the traditional Tree-of-Life structure itself
creates, not because either algorithm is wrong.
"""

import json
import sys
import unittest
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ritual_compiler as rc  # noqa: E402

BASE_DIR = Path(__file__).parent
API_PATH = BASE_DIR / "symbolic_api.json"


def reference_bfs_shortest_path(api, start, goal):
    """Independent, from-scratch BFS over a freshly-built adjacency list
    (not ritual_compiler.py's `adj`). Returns [(node, path_id), ...] or
    None. Since every edge costs 1, BFS finds the same shortest path
    a_star() does with its zero heuristic -- a genuinely different
    algorithm and a genuinely separate parse of the source JSON, used
    here as ground truth rather than re-running a_star() against itself."""
    adjacency = {}
    for pid, pdata in api["paths"].items():
        src, dst = pdata["label"].split(" → ")
        adjacency.setdefault(src.strip(), []).append((dst.strip(), pid))

    if start == goal:
        return []
    frontier = deque([(start, [])])
    visited = {start}
    while frontier:
        node, path = frontier.popleft()
        for nxt, pid in adjacency.get(node, []):
            if nxt == goal:
                return path + [(nxt, pid)]
            if nxt not in visited:
                visited.add(nxt)
                frontier.append((nxt, path + [(nxt, pid)]))
    return None


class TestGraphStructure(unittest.TestCase):
    """Confirms the traditional Tree-of-Life path structure itself,
    against a fresh, independent re-parse of symbolic_api.json."""

    @classmethod
    def setUpClass(cls):
        with API_PATH.open("r", encoding="utf-8") as f:
            cls.api = json.load(f)

    def test_exactly_22_paths(self):
        self.assertEqual(len(self.api["paths"]), 22)

    def test_kethers_direct_neighbors_are_chokmah_binah_tiphareth(self):
        neighbors = {pdata["label"].split(" → ")[1].strip()
                     for pid, pdata in self.api["paths"].items()
                     if pdata["label"].split(" → ")[0].strip() == "Kether"}
        self.assertEqual(neighbors, {"Chokmah", "Binah", "Tiphareth"})

    def test_no_direct_edge_from_any_kether_neighbor_to_malkuth(self):
        # Confirms the shortest path cannot be 2 hops.
        kether_neighbors = {"Chokmah", "Binah", "Tiphareth"}
        direct_to_malkuth = {pdata["label"].split(" → ")[0].strip()
                              for pid, pdata in self.api["paths"].items()
                              if pdata["label"].split(" → ")[1].strip() == "Malkuth"}
        self.assertEqual(kether_neighbors & direct_to_malkuth, set())

    def test_all_three_of_tiphareths_children_connect_directly_to_malkuth(self):
        # The genuine 3-way tie behind the shortest-path ambiguity
        # documented in the module docstring.
        tiphareth_children = {pdata["label"].split(" → ")[1].strip()
                               for pid, pdata in self.api["paths"].items()
                               if pdata["label"].split(" → ")[0].strip() == "Tiphareth"}
        self.assertEqual(tiphareth_children, {"Netzach", "Yesod", "Hod"})
        direct_to_malkuth = {pdata["label"].split(" → ")[0].strip()
                              for pid, pdata in self.api["paths"].items()
                              if pdata["label"].split(" → ")[1].strip() == "Malkuth"}
        self.assertEqual(tiphareth_children, direct_to_malkuth)


class TestAStarAgainstIndependentBFS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with API_PATH.open("r", encoding="utf-8") as f:
            cls.api = json.load(f)

    def test_kether_to_malkuth_matches_independent_bfs_in_length_not_necessarily_route(self):
        # Both algorithms find A shortest path; per the module docstring,
        # a genuine 3-way tie means they don't have to agree on WHICH one.
        expected = reference_bfs_shortest_path(self.api, "Kether", "Malkuth")
        actual = rc.a_star("Kether", "Malkuth")
        self.assertEqual(len(actual), len(expected))
        self.assertEqual(len(actual), 3)

    def test_reference_bfs_ties_by_insertion_order_and_picks_netzach(self):
        expected = reference_bfs_shortest_path(self.api, "Kether", "Malkuth")
        self.assertEqual(expected, [("Tiphareth", "P13"), ("Netzach", "P24"), ("Malkuth", "P29")])

    def test_a_star_ties_by_heapq_tuple_order_and_picks_hod(self):
        # The specific, hand-worked-out tie-break from the module
        # docstring: "Hod" sorts before "Netzach" and "Yesod"
        # alphabetically, so a_star()'s min-heap pops it first among
        # Tiphareth's three equally-short children.
        route = rc.a_star("Kether", "Malkuth")
        self.assertEqual(route, [("Tiphareth", "P13"), ("Hod", "P26"), ("Malkuth", "P31")])

    def test_all_three_tied_routes_are_independently_confirmed_valid(self):
        # Not a claim about what a_star() or BFS return -- just that all
        # three really are legitimate 3-hop Kether->Malkuth routes in the
        # graph itself, checked directly against the path data.
        pid_by_edge = {(pdata["label"].split(" → ")[0].strip(), pdata["label"].split(" → ")[1].strip()): pid
                       for pid, pdata in self.api["paths"].items()}
        for middle, first_pid, second_pid in [
            ("Netzach", "P24", "P29"), ("Yesod", "P25", "P32"), ("Hod", "P26", "P31"),
        ]:
            self.assertEqual(pid_by_edge[("Tiphareth", middle)], first_pid)
            self.assertEqual(pid_by_edge[(middle, "Malkuth")], second_pid)

    def test_same_node_returns_empty_path(self):
        self.assertEqual(rc.a_star("Kether", "Kether"), [])

    def test_unreachable_goal_returns_none(self):
        self.assertIsNone(rc.a_star("Malkuth", "Kether"))  # paths are directed top-down only

    def test_shorter_route_from_geburah_to_hod(self):
        # Geburah -[P23]-> Hod is a direct, single-hop edge.
        expected = reference_bfs_shortest_path(self.api, "Geburah", "Hod")
        actual = rc.a_star("Geburah", "Hod")
        self.assertEqual(actual, expected)
        self.assertEqual(actual, [("Hod", "P23")])


class TestCompileRitual(unittest.TestCase):
    def test_default_route_matches_a_star(self):
        # Per the a_star() tie-break documented above: Tiphareth -> Hod -> Malkuth.
        steps = rc.compile_ritual("Test Intent")
        self.assertEqual([s["to_node"] for s in steps], ["Tiphareth", "Hod", "Malkuth"])
        self.assertEqual([s["path_id"] for s in steps], ["P13", "P26", "P31"])

    def test_each_step_description_matches_the_real_path_data(self):
        with API_PATH.open("r", encoding="utf-8") as f:
            api = json.load(f)
        steps = rc.compile_ritual("Test Intent")
        for step in steps:
            path_info = api["paths"][step["path_id"]]
            expected_desc = f"{path_info['label']} – {path_info['alchemy']} – {path_info['pattern']}"
            self.assertEqual(step["description"], expected_desc)

    def test_raises_for_unreachable_route(self):
        with self.assertRaises(RuntimeError):
            rc.compile_ritual("Impossible", origin="Malkuth", destination="Kether")


class TestFormatMarkdown(unittest.TestCase):
    def test_produces_one_table_row_per_step(self):
        steps = rc.compile_ritual("Launch New Project")
        md = rc.format_markdown(steps, "Launch New Project")
        self.assertIn('# Ritual Compilation – "Launch New Project"', md)
        # header + separator + 3 rows = 5 lines of table content
        table_lines = [l for l in md.splitlines() if l.startswith("|")]
        self.assertEqual(len(table_lines), 2 + len(steps))
        for step in steps:
            self.assertIn(step["to_node"], md)
            self.assertIn(step["path_id"], md)


class TestMainCLIWritesExpectedFile(unittest.TestCase):
    """Exercises main()'s real argv-parsing/file-output wiring directly
    (not just compile_ritual()/format_markdown() in isolation), with
    `ritual_compiler.__file__` monkeypatched to a temp directory so the
    output file lands somewhere a plain tempdir cleanup can remove it --
    this repo's mounted filesystem does not permit unlinking real files
    inside the tracked tools/ directory (confirmed elsewhere this
    session: `rm`/`Path.unlink()` fail with PermissionError there even
    though the same operations work fine in a real temp directory), so
    a subprocess writing directly into tools/ would leave an
    un-cleanable artifact behind."""

    def test_cli_writes_a_ritual_markdown_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_module_file = str(Path(tmpdir) / "ritual_compiler.py")
            old_argv = sys.argv
            old_file = rc.__file__
            try:
                rc.__file__ = fake_module_file
                sys.argv = ["ritual_compiler.py", "Zzz", "Test", "Ritual"]
                rc.main()
            finally:
                sys.argv = old_argv
                rc.__file__ = old_file

            out_path = Path(tmpdir) / "ritual_zzz_test_ritual.md"
            self.assertTrue(out_path.is_file())
            content = out_path.read_text(encoding="utf-8")
            self.assertIn("Tiphareth", content)
            self.assertIn("Malkuth", content)


def run_unit_test_suite():
    print("=" * 72)
    print("  RITUAL_COMPILER.PY -- CORRECTNESS TEST SUITE")
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
