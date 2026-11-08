"""The measurement layer (metrics.py).

Ground truth:

1. INDEPENDENT REFERENCE. `tests/fixtures/sephirot_scores.json`, produced by running the framework's own
   reference implementation of the centroid scoring over a set of texts and recording what it returned. The
   module under test did not produce these numbers.
2. BY HAND. The entropy bounds (one token repeated is 0, all distinct is 1000) and the pillar and level
   weightings, which are an average that can be computed on paper for a single scored name.
3. THE STATED LIMITATION. Every address this module builds must say in its own derivation that the measurement
   runs through a Kabbalistic keyword table, because the architecture's claim of a tradition-free address holds
   downstream of here and not inside it. A test asserts the caveat is present, so the honesty cannot be dropped
   by accident.
"""
import json
import os
import unittest

from symbolics import address as A
from symbolics import metrics as M

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sephirot_scores.json")


class TestInheritedScoring(unittest.TestCase):
    def test_agrees_with_the_reference_on_every_text(self):
        with open(FIXTURE, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertGreaterEqual(len(data["vectors"]), 20)
        for v in data["vectors"]:
            self.assertEqual(M.scores(v["text"]), v["scores"], v["text"][:60])

    def test_the_centroids_are_the_frameworks_own(self):
        self.assertEqual(len(M.SEPHIROT_CENTROIDS), 11)              # the ten and Da'ath
        self.assertIn("Daath", M.SEPHIROT_CENTROIDS)
        self.assertIn("abyss", M.SEPHIROT_CENTROIDS["Daath"])
        self.assertIn("cut", M.SEPHIROT_CENTROIDS["Geburah"])

    def test_scores_are_reproducible(self):
        """The reference multiplies by a weight its learning engine accumulates; this does not, so the same text
        always gives the same address rather than one that depends on history nobody can inspect."""
        text = "I cut the practice short, angry and rigid"
        self.assertEqual(M.scores(text), M.scores(text))
        self.assertGreater(M.scores(text)["Geburah"], 0)

    def test_nothing_scored_is_a_real_answer(self):
        self.assertEqual(set(M.scores("")), set(M.SEPHIROT_CENTROIDS))
        self.assertEqual(sum(M.scores("").values()), 0)


class TestEntropy(unittest.TestCase):
    def test_the_bounds_by_hand(self):
        self.assertEqual(M.entropy("om om om om"), 0)                     # one token repeated: nothing new
        self.assertEqual(M.entropy("alpha beta gamma delta"), 1000)       # all distinct: H = H_max
        self.assertEqual(M.entropy("one"), A.MID)                         # nothing to measure
        self.assertEqual(M.entropy(""), A.MID)

    def test_it_is_not_capped_like_the_directivity_budget(self):
        """agency.entropy_gamma clamps at 0.85 because a budget needs a ceiling. An axis must not inherit it."""
        from symbolics import agency
        self.assertEqual(agency.entropy_gamma("om om om om"), agency.GAMMA_MAX)
        self.assertEqual(M.entropy("om om om om"), 0)                     # the same text, uncapped, at the floor

    def test_in_between(self):
        middling = M.entropy("resh at dawn resh at noon resh at sunset")
        self.assertGreater(middling, 0)
        self.assertLess(middling, 1000)


class TestAxes(unittest.TestCase):
    def test_one_scored_name_lands_where_the_tree_puts_it(self):
        only = {"Geburah": 0.5}
        self.assertEqual(M.severity_mercy(only), 150)                     # the pillar of Severity
        self.assertEqual(M.descent(only), A.clamp((5 - 1) / 9 * 1000))    # fifth of ten
        self.assertEqual(M.severity_mercy({"Chesed": 0.5}), 850)          # the pillar of Mercy
        self.assertEqual(M.severity_mercy({"Tifereth": 0.5}), A.MID)      # the middle pillar

    def test_two_opposed_names_average_to_the_middle(self):
        self.assertEqual(M.severity_mercy({"Geburah": 0.5, "Chesed": 0.5}), A.MID)

    def test_nothing_scored_sits_in_the_middle_rather_than_at_zero(self):
        self.assertEqual(M.severity_mercy({}), A.MID)
        self.assertEqual(M.descent({}), A.MID)


class TestAddressOf(unittest.TestCase):
    def test_a_real_sentence_reads_toward_severity(self):
        a = M.address_of("I cut the practice short, angry and rigid, could not settle at all")
        self.assertLess(a.severity_mercy, A.MID)
        self.assertEqual(sorted(a.derivation), sorted(list(A.AXES)))

    def test_every_derivation_states_the_limitation(self):
        a = M.address_of("expansion and grace, abundance, open and vast")
        for axis in ("severity_mercy", "descent"):
            self.assertIn("tradition-derived", a.derivation[axis], axis)
        self.assertGreater(a.severity_mercy, A.MID)

    def test_the_words_it_rests_on_travel_with_it(self):
        anchor = A.Anchor("journal/2026-01-02.md", "cut the session short", (22, 24))
        a = M.address_of("I cut the practice short", anchors=[anchor])
        self.assertEqual(a.anchors[0].quote, "cut the session short")

    def test_what_it_produces_can_be_read_and_emitted(self):
        from symbolics import ethics as E
        a = M.address_of("rigid and stuck, could not move", anchors=[A.Anchor("x.md", "rigid and stuck")])
        reading = E.emit(A.read(a, "kabbalistic", caveat=E.CAVEAT))
        self.assertEqual(reading["type"], "reading")
        self.assertTrue(reading["anchors"])


class TestLatency(unittest.TestCase):
    def test_the_classes_are_relative_to_the_persons_own_baseline(self):
        self.assertEqual(M.latency(10, baseline=10)["class"], "O(1)")
        self.assertEqual(M.latency(18, baseline=10)["class"], "O(log n)")
        self.assertEqual(M.latency(35, baseline=10)["class"], "O(n)")
        self.assertEqual(M.latency(200, baseline=10)["class"], "O(n^2)")

    def test_the_readings_are_the_ones_the_note_gives(self):
        self.assertEqual(M.latency(10, baseline=10)["reads_as"], "Chesed")
        self.assertEqual(M.latency(200, baseline=10)["reads_as"], "Geburah")

    def test_a_list_uses_its_own_median(self):
        out = M.latency([5, 5, 5, 40])
        self.assertEqual(out["class"], "O(n^2)")
        self.assertEqual(out["ratio"], 8.0)

    def test_absolute_seconds_are_refused(self):
        with self.assertRaises(ValueError):
            M.latency(30)
        with self.assertRaises(ValueError):
            M.latency([])

    def test_the_caveat_travels_with_the_number(self):
        self.assertIn("proxy", M.latency(10, baseline=10)["caveat"])
        self.assertIn("cat on the keyboard", M.latency(10, baseline=10)["caveat"])


if __name__ == "__main__":
    unittest.main()
