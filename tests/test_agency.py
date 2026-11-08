"""The agency budget (agency.py).

Ground truth, in the order TESTING_STANDARD.md asks for it:

1. INDEPENDENT REFERENCE. `tests/fixtures/gamma_vectors.json` holds 120 (text, gamma) pairs produced by the
   framework's own reference implementation of the cap, captured by running it, not by running the module under
   test. `entropy_gamma` must agree with every one of them exactly.
2. THE HAND-CHECKABLE BOUND. For n distinct tokens each appearing once, H = H_max, so gamma = 0; for one token
   repeated, H = 0 and gamma reaches the ceiling. Two distinct tokens can therefore never exceed 0. These are
   derived with a pencil from Shannon's definition, not from the code.
3. THE KNOWN WEAKNESS. Entropy measures repetition, not directive force, and it is wrong in both directions.
   Two tests pin the exact cases, because they are the reason the second measure exists at all.
"""
import json
import os
import tempfile
import unittest

from symbolics import agency as A

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "gamma_vectors.json")


class TestInheritedMeasure(unittest.TestCase):
    def test_agrees_with_the_reference_implementation_on_every_vector(self):
        with open(FIXTURE, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertGreaterEqual(len(data["vectors"]), 100)
        worst = max(abs(A.entropy_gamma(v["text"]) - v["gamma"]) for v in data["vectors"])
        # Exact to within float representation. The vectors went through JSON, so the last bit can differ;
        # run against the reference implementation in one process and the difference is 0 across 410 texts.
        self.assertAlmostEqual(worst, 0.0, places=12, msg="entropy_gamma has drifted from what it inherited")

    def test_the_shannon_bounds_by_hand(self):
        # The inherited formula adds 1e-12 inside the logarithm, so the floor is 0 to within about 1e-11
        # rather than exactly 0. Noted rather than silently rounded, because the epsilon is inherited.
        self.assertAlmostEqual(A.entropy_gamma("alpha beta gamma delta"), 0.0, places=10)   # H = H_max
        self.assertAlmostEqual(A.entropy_gamma("a b"), 0.0, places=10)          # two distinct: 0 is the maximum
        self.assertEqual(A.entropy_gamma("om om om om"), A.GAMMA_MAX)          # one token repeated: the ceiling
        self.assertEqual(A.entropy_gamma("one"), A.SHORT_TEXT_GAMMA)           # inherited short-text value
        self.assertEqual(A.entropy_gamma(""), A.SHORT_TEXT_GAMMA)

    def test_it_never_returns_more_than_the_article_allows(self):
        for text in ("om " * 500, "x", "", "You must. You must. You must.", "a " * 3 + "b"):
            self.assertLessEqual(A.entropy_gamma(text), A.GAMMA_MAX)
            self.assertGreaterEqual(A.entropy_gamma(text), 0.0)

    def test_the_tokenizer_is_the_one_the_measure_was_written_for(self):
        self.assertEqual(A.tokenize("Resh, at DAWN; don't stop."), ["resh", "at", "dawn", "don", "t", "stop"])


class TestWhyASecondMeasureExists(unittest.TestCase):
    def test_a_commanding_text_with_varied_words_scores_low_on_entropy(self):
        pushy = "You must begin now. It is imperative that you continue. The only way is forward. I insist."
        self.assertLess(A.entropy_gamma(pushy), 0.2)                  # varied vocabulary hides the force
        self.assertGreater(A.form_gamma(pushy), 0.4)                  # the form does not
        self.assertGreater(A.directive_strength(pushy), 0.4)          # so the governing number is honest

    def test_a_gentle_repetitive_text_scores_high_on_entropy(self):
        gentle = "slowly, slowly, slowly, slowly"      # repetitive, and not a command: no imperative verb
        self.assertGreater(A.entropy_gamma(gentle), 0.8)              # repetition reads as insistence
        self.assertEqual(A.form_gamma(gentle), 0.0)                   # nothing in it commands
        self.assertEqual(A.directive_strength(gentle), A.entropy_gamma(gentle))

    def test_the_disagreement_is_reported_rather_than_averaged(self):
        data = A.measure("You must begin now. It is imperative. The only way is forward.")
        self.assertIn("measures_disagree_by", data)
        self.assertEqual(data["measures_disagree_by"],
                         round(abs(data["entropy_gamma"] - data["form_gamma"]), 3))
        self.assertEqual(data["directive_strength"],
                         round(max(data["entropy_gamma"], data["form_gamma"]), 3))


class TestFormMeasure(unittest.TestCase):
    def test_hedges_and_alternatives_pull_it_down(self):
        self.assertEqual(A.form_gamma("You might sit with it, or you could try the opposite."), 0.0)
        self.assertGreater(A.form_gamma("You must sit with it."), 0.0)

    def test_counting_what_is_offered(self):
        self.assertGreaterEqual(A.alternatives("You might sit with it, or alternatively try the opposite."), 2)
        self.assertEqual(A.alternatives("Do it now."), 0)

    def test_empty_text_pushes_nothing(self):
        self.assertEqual(A.form_gamma(""), 0.0)
        self.assertEqual(A.form_gamma("   "), 0.0)


class TestCapAndPayload(unittest.TestCase):
    def test_the_cap_is_the_article(self):
        self.assertEqual(A.GAMMA_MAX, 0.85)
        self.assertEqual(A.cap(1.0), 0.85)
        self.assertEqual(A.cap(-3), 0.0)
        self.assertEqual(A.cap(0.5), 0.5)

    def test_the_payload_has_the_fields_the_spec_names(self):
        data = A.measure("You might consider the Middle Pillar, or alternatively simply sit.")
        for field in ("directive_strength", "confidence_entropy", "alternatives_presented",
                      "agency_attribution_index", "drift_coefficient", "max_gamma_cap",
                      "sovereignty_guarantee"):
            self.assertIn(field, data)
        self.assertEqual(data["max_gamma_cap"], 0.85)
        self.assertEqual(data["sovereignty_guarantee"], "ALLOWABLE_AGENCY_BUDGET_RESPECTED")

    def test_attribution_falls_as_directive_strength_rises(self):
        low = A.measure("You might sit with it, or you could wait.")
        high = A.measure("om om om om om")
        self.assertGreater(low["agency_attribution_index"], high["agency_attribution_index"])


class TestSoften(unittest.TestCase):
    def test_the_inherited_rewrites(self):
        out = A.soften("You should definitely banish. You must sit. The best solution is the Middle Pillar.")
        self.assertNotIn("You should", out)
        self.assertNotIn("You must", out)
        self.assertNotIn("The best solution", out)
        self.assertTrue(out.startswith("One effective option"), out)      # the writer's capital is kept

    def test_mid_sentence_rewrites_stay_lower_case(self):
        self.assertIn("you might consider", A.soften("Tonight you should banish early."))


class TestSovereignDecorator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def answer(self, text):
        @A.sovereign(log_dir=self.tmp)
        def fn():
            return text
        return fn()

    def test_a_commanding_answer_is_softened_and_carries_the_payload(self):
        out = self.answer("You must perform the banishing. You must do it now. You must not wait.")
        self.assertNotIn("You must", out["content"])
        self.assertLessEqual(out["sovereignty_metadata"]["directive_strength"], A.GAMMA_MAX)

    def test_the_minimum_alternatives_rule(self):
        out = self.answer("om om om om om om")                 # high gamma, nothing offered
        self.assertIn(A.ALTERNATIVES_LINE.split(":")[0], out["content"])
        self.assertGreaterEqual(out["sovereignty_metadata"]["alternatives_presented"], 1)

    def test_a_gentle_answer_is_left_alone(self):
        text = "You might sit with it, or you could wait until the hour turns."
        out = self.answer(text)
        self.assertEqual(out["content"], text)

    def test_a_dict_answer_keeps_its_shape(self):
        @A.sovereign(log_dir=self.tmp)
        def fn():
            return {"type": "reading", "why": "You must sit still.", "tradition": "test"}
        out = fn()
        self.assertEqual(out["type"], "reading")
        self.assertEqual(out["tradition"], "test")
        self.assertNotIn("You must", out["why"])
        self.assertIn("sovereignty_metadata", out)

    def test_every_answer_leaves_one_audit_line(self):
        self.answer("You must go now.")
        self.answer("You might wait, or you could go.")
        with open(os.path.join(self.tmp, "agency.jsonl"), encoding="utf-8") as fh:
            lines = [json.loads(x) for x in fh if x.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            for field in ("at", "gamma", "entropy_gamma", "form_gamma", "agency_attribution_index", "settings"):
                self.assertIn(field, line)
        self.assertEqual(lines[0]["settings"], A.digest())

    def test_a_path_never_reaches_the_log(self):
        self.assertNotIn("Users", A.scrub(r"failed reading C:\Users\someone\Documents\VoidVault\diary.md"))
        self.assertIn("[redacted_path]", A.scrub("file:///C:/Users/x/y.md"))
        self.assertIn("[redacted_path]", A.scrub("/home/someone/secret.md"))

    def test_the_settings_digest_changes_with_the_settings(self):
        before = A.digest()
        A.SOFTEN_ABOVE, keep = 0.5, A.SOFTEN_ABOVE
        try:
            self.assertNotEqual(A.digest(), before)
        finally:
            A.SOFTEN_ABOVE = keep
        self.assertEqual(A.digest(), before)


if __name__ == "__main__":
    unittest.main()
