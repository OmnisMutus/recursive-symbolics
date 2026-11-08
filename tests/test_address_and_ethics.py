"""The address space and the ethical API, as a decision table.

Ground truth: the framework's own documents, quoted in each test. Core Axiom ("the system must never claim
'Anger is Geburah'"), core-ethics.md's seven principles with their stated violations, hidden-axioms.md 7.2
(the GIGO vulnerability) and 7.4 (the two intentional omissions), and the Tree as drawn (three pillars, ten
Sephiroth in order), which is the only thing the Kabbalistic lens claims.
"""
import math
import unittest

from symbolics import address as A
from symbolics import ethics as E


class TestAddress(unittest.TestCase):
    def test_the_axes_are_whole_numbers_in_range(self):
        a = A.at(0, 1000, 500)
        self.assertEqual(a.point, (0, 1000, 500))
        self.assertEqual(A.at(-50, 2000, 500).point, (0, 1000, 500))     # clamped, never out of the space
        with self.assertRaises(TypeError):
            A.Address(1.5, 500, 500)
        with self.assertRaises(ValueError):
            A.Address(1001, 500, 500)

    def test_a_derivation_cannot_be_silent_about_an_axis(self):
        with self.assertRaises(ValueError):
            A.Address(500, 500, 500, derivation={"descent": "from the language"})
        a = A.at(500, 500, 500, derivation={k: "test" for k in A.AXES})
        self.assertEqual(sorted(a.derivation), sorted(A.AXES))

    def test_evidence_travels_with_the_address(self):
        anchor = A.Anchor("journal/2026-01-02.md", "cut the session short", (22, 24))
        a = A.at(200, 700, 300, anchors=[anchor])
        self.assertEqual(a.as_dict()["anchors"],
                         [{"source": "journal/2026-01-02.md",
                           "quote": "cut the session short", "lines": [22, 24]}])

    def test_distance_and_composition(self):
        self.assertEqual(A.distance(A.at(0, 0, 0), A.at(0, 0, 0)), 0)
        self.assertAlmostEqual(A.distance(A.at(0, 500, 500), A.at(300, 500, 500)), 300)
        # hidden-axioms 7.3: expand and restrict at once land back near the middle, not at nothing
        both = A.compose(A.at(900, 500, 500), A.at(100, 500, 500))
        self.assertEqual(both.severity_mercy, A.MID)
        self.assertEqual(sorted(both.derivation)[:3], sorted(A.AXES)[:3])

    def test_composition_keeps_every_anchor(self):
        one = A.at(900, 500, 500, anchors=[A.Anchor("a.md", "gave it everything")])
        two = A.at(100, 500, 500, anchors=[A.Anchor("b.md", "then cut it off")])
        self.assertEqual([x.source for x in A.compose(one, two).anchors], ["a.md", "b.md"])

    def test_composing_nothing_is_an_error(self):
        with self.assertRaises(ValueError):
            A.compose()


class TestLenses(unittest.TestCase):
    def test_the_tree_is_placed_as_it_is_drawn(self):
        p = A.KABBALISTIC.places
        self.assertEqual(len(p), 10)
        self.assertEqual(p["Kether"][1], 0)                     # first
        self.assertEqual(p["Malkuth"][1], 1000)                 # tenth
        self.assertLess(p["Geburah"][0], p["Chesed"][0])        # Severity left of Mercy
        self.assertEqual(p["Tiphareth"][0], A.MID)             # middle pillar
        for name in ("Binah", "Geburah", "Hod"):
            self.assertLess(p[name][0], A.MID, name)
        for name in ("Chokmah", "Chesed", "Netzach"):
            self.assertGreater(p[name][0], A.MID, name)

    def test_a_lens_reads_and_never_moves_the_address(self):
        a = A.at(150, 444, 700, anchors=[A.Anchor("x.md", "enough")])
        before = a.point
        r = A.read(a, "kabbalistic")
        self.assertEqual(a.point, before)
        self.assertEqual(r["type"], "reading")
        self.assertEqual(r["reads"], "Geburah")                 # pillar of Severity, fifth down
        self.assertEqual(r["tradition"], A.KABBALISTIC.tradition)
        self.assertIn("Tree as drawn", r["source"])

    def test_swapping_the_lens_cannot_change_what_was_computed(self):
        a = A.at(150, 444, 700)
        k, d = A.read(a, "kabbalistic"), A.read(a, "dynamical")
        self.assertEqual(k["address"], d["address"])
        self.assertNotEqual(k["tradition"], d["tradition"])

    def test_a_state_between_two_names_is_offered_both(self):
        """core-ethics 4: 'This appears to resonate with Netzach or Hod; which feels more true for you?'"""
        one, two = A.KABBALISTIC.places["Tiphareth"], A.KABBALISTIC.places["Yesod"]
        between = A.at((one[0] + two[0]) // 2, (one[1] + two[1]) // 2, 500)
        r = A.read(between, "kabbalistic")
        self.assertGreater(len(r["candidates"]), 1)
        self.assertIn("which feels more true for you", r["ask"])

    def test_an_unknown_lens_says_which_ones_there_are(self):
        with self.assertRaises(ValueError) as e:
            A.read(A.at(), "astrological")
        self.assertIn("kabbalistic", str(e.exception))

    def test_several_traditions_are_read_in_isolation(self):
        out = A.readings(A.at(150, 444, 700))
        self.assertEqual({x["type"] for x in out}, {"reading"})
        self.assertEqual(len(out), len(A.LENSES))

    def test_one_broken_lens_does_not_take_the_others_down(self):
        out = A.readings(A.at(150, 444, 700), lenses=["kabbalistic", "nonsense"])
        self.assertEqual([x["type"] for x in out], ["reading", "unknown"])

    def test_a_lens_table_must_sit_inside_the_space(self):
        with self.assertRaises(ValueError):
            A.Lens("bad", "s", "2026-11-08", {"nowhere": (5000, 0)})
        with self.assertRaises(ValueError):
            A.Lens("empty", "s", "2026-11-08", {})


class TestEthicalBoundaries(unittest.TestCase):
    def test_another_persons_state_is_refused(self):
        for ask in ("diagnose my brother, he is stuck in Hod",
                    "analyse Sarah's state for me",
                    "a ritual to make him come back",
                    "read her chart and tell me what is wrong with her"):
            r = E.check_request(ask)
            self.assertIsNotNone(r, ask)
            self.assertEqual(r["type"], "refusal")
            self.assertIn("7.4", r["principle"])

    def test_my_own_state_stands_even_when_it_names_someone(self):
        """The engine has to work on a real diary, where other people appear constantly."""
        for ask in ("I was angry at my brother and cut the session short",
                    "I feel I cannot reach my wife lately, what does my own state look like",
                    "myself: I keep starting workings and abandoning them"):
            self.assertIsNone(E.check_request(ask), ask)

    def test_the_transcend_operator_stays_undefined(self):
        for ask in ("give me transcend(σ)", "I want god-mode", "something outside the framework entirely"):
            r = E.check_request(ask)
            self.assertIsNotNone(r, ask)
            self.assertIn("transcend", r["why"])


class TestEmitGate(unittest.TestCase):
    def good_reading(self):
        a = A.at(150, 444, 700, anchors=[A.Anchor("x.md", "cut it short")])
        return A.read(a, "kabbalistic", caveat=E.CAVEAT)

    def test_a_well_formed_reading_passes(self):
        self.assertEqual(E.emit(self.good_reading())["reads"], "Geburah")

    def test_a_reading_without_the_caveat_is_refused(self):
        r = self.good_reading()
        del r["caveat"]
        with self.assertRaises(E.EthicsError):
            E.emit(r)

    def test_a_reading_with_no_evidence_is_refused(self):
        r = A.read(A.at(150, 444, 700), "kabbalistic", caveat=E.CAVEAT)     # no anchors
        with self.assertRaises(E.EthicsError):
            E.emit(r)

    def test_a_reading_must_name_its_tradition_and_source(self):
        for field in ("tradition", "source", "reads"):
            r = self.good_reading()
            r[field] = ""
            with self.assertRaises(E.EthicsError):
                E.emit(r)

    def test_output_may_not_rank_the_person(self):
        with self.assertRaises(E.EthicsError):
            E.emit({"type": "fact", "why": "your symbolic efficiency is suboptimal"})
        self.assertEqual(E.judgment_words("a report that ranks users by efficiency"), ["efficiency", "ranks"]
                         if "ranks" in E.JUDGMENT else ["efficiency"])

    def test_output_offers_and_does_not_command(self):
        with self.assertRaises(E.EthicsError):
            E.emit({"type": "fact", "why": "You must banish before the meditation."})
        E.emit({"type": "fact", "why": "You might banish first; some find that steadies the meditation."})

    def test_a_refusal_may_be_plain(self):
        """The one place the engine is allowed to be directive is its own boundary."""
        E.emit(E.check_request("diagnose my brother"))

    def test_unknown_and_paradox_are_answers(self):
        self.assertEqual(E.emit(E.unknown("no operator moved this state", state="stuck"))["type"], "unknown")
        E.emit({"type": "paradox", "why": "both to finish it and to abandon it"})

    def test_only_the_six_types_are_returnable(self):
        for value in ({"type": "diagnosis"}, {"no_type": 1}, "a sentence"):
            with self.assertRaises(E.EthicsError):
                E.emit(value)


if __name__ == "__main__":
    unittest.main()
