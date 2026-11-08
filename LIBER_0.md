# LIBER 0

*A working record, in the tradition of the magical diary. The convention, the One Rule and the entry format are
inherited from the Recursive Symbolics framework, which established them; this is the same practice applied to
this repository.*

---

## The One Rule

Record what actually happened, not what should have happened. An entry that says "this failed, here is the exact
error, here is what I learned" is worth more than an entry that only records successes. Corrections of earlier
entries are added as new entries, never as edits that erase what was originally believed: the record of having
been wrong, and of how it was caught, is the useful part.

## Entry Format

```
### [Date] — [Short title]

**Attempted:** what was being tried.
**Result:** what actually happened — VERIFIED / FAILED / OPEN / CORRECTED, as applies. Include the specific
evidence (test count, exact error, commit hash), not just a summary judgment.
**Notes:** anything worth a future entry checking back against this one.
```

---

## Entries

### 2026-11-08 — Article 6 implemented by inheriting the framework's own gamma cap, then extending it

**Attempted:** Make Article 6 real rather than aspirational. The framework already has a Δγ,τ implementation
with a hand-checked Shannon derivation, so the question was whether to inherit it or write a new measure.

**Result:** VERIFIED, and CORRECTED twice.

Inherited. `agency.entropy_gamma` is the framework's own cap, same formula and same ceiling: gamma = 1 - H_norm
over token frequencies, clamped into [0, 0.85], with the engine's own tokenizer `\b\w+\b` over lowercased
text. Checked rather than assumed: 410 texts (10 chosen, 400 generated) run through both the reference
implementation and the inherited one in a single process gave a maximum absolute difference of **0**. 120 of
those pairs are now `tests/fixtures/gamma_vectors.json`, captured from the reference implementation so the test
does not grade the module against itself. Across the JSON round trip the worst difference is 3.3e-16, so the
test asserts agreement to 12 places and says why.

Extended, with the reason recorded rather than assumed away. The entropy measure answers "how repetitive is
this text", which is not the same quantity as directive strength, and it is wrong in both directions. Two tests
pin the exact cases: "You must begin now. It is imperative that you continue. The only way is forward. I
insist." has varied vocabulary and scores **below 0.2** on entropy while scoring above 0.4 on form; "slowly,
slowly, slowly, slowly" is repetitive and gentle and scores **above 0.8** on entropy while scoring 0 on form. So
`form_gamma` reads imperatives, second-person modals and single-option framing against hedges and offered
alternatives; both numbers are reported, the higher governs, and `measures_disagree_by` keeps the disagreement
visible instead of averaging it into one comfortable number. Both remain proxies and say so in the module
docstring.

Also implemented: the Minimum Alternatives Rule, `sovereignty_metadata` with the fields
`agency-budget-spec.md` names, the `@sovereign` decorator so the budget is enforced at the boundary rather than
remembered, and one audit line per answer with both gammas, the attribution index and a digest of the settings
that produced them. Paths are scrubbed from the log, as Article 9 requires.

**CORRECTED, twice, both caught by tests:**

1. The tokenizer in the deployed copy was still `[a-z0-9']+` rather than the engine's `\b\w+\b`, because an
   edit did not reach the machine before the file was staged. The 410-text differential check had passed anyway,
   because nothing in that corpus contained an apostrophe. The test that caught it asserts the tokenization of
   one string containing "don't". **The differential check was not wrong, it was not adversarial enough.**
2. `test_the_suite_does_not_conform_while_a_duty_is_unchecked` now failed, because the engine conforms. The
   claim it made was true yesterday and false today. Per the correction rule it was not edited away: it now
   proves the guard by handing the suite no implementation, and a second test pins the live state. Finding the
   sentinel bug that this exposed (passing `agency=None` had come to mean "use the default" rather than "there
   is none") was the useful part.

**The state as of this entry**, from `python -m symbolics.conformance`: 5 passed, 0 failed, 0 not implemented,
**CONFORMS: True**. 81 tests pass.

**Notes:** The 0.85 ceiling is still an inherited convention that nothing here derives, and the previous entry's
question about that stands. `form_gamma`'s coefficient of 0.45 per sentence is mine and is just as arbitrary:
it was chosen so that a single bare imperative in a one-sentence answer lands near the softening threshold
rather than above the cap, and it has no derivation either. A future entry should either derive both or say
plainly that they are tuned.

### 2026-11-08 — Founding: the seam, the ethical API, the ported ledger, and a licence that now says what it meant

**Attempted:** Start the engine for the Recursive Symbolics framework as its own project rather than as a mode of
void-agent, because the framework is not a vault tool and the vault is one caller among several. Specifically:
build the address/lens seam that makes the Core Axiom's "syntax, not semantics" true in code rather than in
prose; enforce `core-ethics.md` as checks instead of intentions; bring in the framework's own correspondence ledger rather than reinvent it; and amend the licence so its ten Articles say in law what they already
said in intent.

**Result:** Four commits, 58 tests passing, and one deliberate False.

`address.py` (commit `c7a7342`). The space is three axes no tradition owns: severity to mercy, descent, entropy.
A lens is a table with a source and a date, and `read()` takes an address and returns words. The rule that
matters is structural rather than stylistic: a lens cannot write back into an address, so the same unchanged
numbers read as Geburah under the Kabbalistic lens and as contraction under the dynamical one, and "anger is
Geburah" is not expressible at all. How each axis was computed, and the words the reading rests on, travel with
the point. Several traditions can be read over one address in isolation, so none can colour another, and a
broken lens table returns its own `unknown` while the rest stand.

`ethics.py` (same commit). Six of the seven principles are mechanical and are enforced at `emit()`, the gate
every return passes through: a reading without the caveat, without its tradition and source, or without its
anchors does not leave the engine, and no output may rank a person or command one. `unknown` and `paradox` are
return types. The two intentional omissions of `hidden-axioms.md` 7.4 are refusals.

Ledger inherited (commit `e040a6b`). `correspondence_ledger.py`, its run history and its target-staleness check,
copied with provenance on every file rather than rewritten, because the substance is the point: validator=None
means untestable in principle, and an all-UNTESTABLE ledger cannot report success. Also brought over as
governing documents, not references: `TESTING_STANDARD.md` and `ANTI_ECHO_ISOLATION_POLICY.md`.

Licence 1.1 and the Conformance Suite (commit `646a4d1`). Every restriction of 1.0 kept; what was added is the
machinery 1.0 lacked: definitions, an express distribution grant, a patent grant with retaliation, attribution
and change-statement duties, a 30-day cure, termination, severability, governing law, a trademark reservation and
a versioning clause. Articles 6, 8 and 9 put duties on a running system, so they now point at
`symbolics/conformance.py`, which reports: Article 9 PASS (proved by reading every import in the package, not by
asserting it), Article 5.1(D) PASS, Article 8 PASS twice, Article 6 NOT_IMPLEMENTED, and **CONFORMS: False**.
That False is the honest state and a test pins it, so the suite can never pass vacuously.

Article 1 widened (commit `b3086bb`). The grant runs to every Intelligence rather than every human being, on the
framework's own reasoning: the Core Axiom holds mind to be one manifestation of a recursive process rather than a
property of one kind of body. 1.3 ties the rights to the duties; 0.8 keeps a corporation from being an
Intelligence, since "any other intelligence" is otherwise one argument away from a commercial escape hatch.

**CORRECTED, three times, each caught by a test rather than by review:**

1. The other-state refusal let "analyse Sarah's state for me" through. The self-reference check was matching
   "me" in "for me", so a request about another person read as a request about the asker. Worse, the
   proper-name pattern carried `re.IGNORECASE`, which made its `[A-Z][a-z]{2,}` match any word at all, so
   "change my routine" would have been refused as third-party work. Both were rewritten as explicit checks.
   The test for the opposite direction, that "I was angry at my brother and cut the session short" must still
   be read normally, is the one that keeps this honest: an engine that refuses that is useless on a real diary.
2. The near-boundary test asserted two candidate readings at a point that has only one. Tiphareth sits 111
   units from it and Yesod 222, so the engine was right and the test was wrong. It now computes the midpoint
   from the lens table rather than guessing a coordinate.
3. The ported ledger suite failed on arrival: one failure and one error, both from the file's own inert
   fixtures, which fail and raise on purpose so that `from_unittest_methods` can be exercised against a failing
   test. `unittest discover` collects them; the framework's own runner selects only the `Test*` classes. Fixed
   with a `load_tests` hook that does the same, and the reason is written in the hook.

**Not verified, and not claimed:**

- Article 6 has no implementation. `agency.py` does not exist, so directivity is capped nowhere in this engine
  yet, and the Conformance Suite says so.
- The 0.85 ceiling is a convention inherited from `agency-budget-spec.md`. Nothing here derives it, and a
  safeguard's ceiling should say why it sits there.
- γ measured from imperatives and hedges, and latency read as a complexity class, are proxies. Neither is a
  measurement of coercion or of contemplation, and both carry that caveat in their own docstrings.
- The 7.4% gap is recorded as a chosen convention. The Resonance Log it cites is not in hand.
- The licence has not been reviewed by a lawyer. Its 1.0 header cited 17 U.S.C. § 302(c) and Berne Art. 7(3) as
  "Pseudonymous Author Protection"; both provisions concern the *term* of protection for anonymous and
  pseudonymous works, not the protection of an author's identity. Flagged, not silently rewritten.
- The framework's recursive attractor engine is not brought in yet. It is the natural Register B home for
  `Mathemathical-foundation.md`'s fixed-point formalism, and it needs numpy, which this project does not yet
  depend on. A decision, not an oversight.

**Notes:** Two things for a future entry to check back against. First, whether the three axes survive contact
with real diary text, or whether the recursive lineage C of `S = (L, N, P, C)` has to become a fourth. Second,
whether `CONFORMS: False` is still False a month from now: if Article 6 is still NOT_IMPLEMENTED then, the
licence is asking for something the reference implementation does not do, and that gap belongs in the record
rather than in a plan.
