# LIBER 0

*A working record, in the tradition of the magical diary. The convention, the One Rule and the entry format are
inherited from `Thoth/solo/LIBER_0.md`, which founded them; this is the same practice applied to this repository.*

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

### 2026-11-08 — Founding: the seam, the ethical API, the ported ledger, and a licence that now says what it meant

**Attempted:** Start the engine for the Recursive Symbolics framework as its own project rather than as a mode of
void-agent, because the framework is not a vault tool and the vault is one caller among several. Specifically:
build the address/lens seam that makes the Core Axiom's "syntax, not semantics" true in code rather than in
prose; enforce `core-ethics.md` as checks instead of intentions; port the correspondence ledger from
`Thoth/solo` rather than reinvent it; and amend the licence so its ten Articles say in law what they already
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

Ledger ported (commit `e040a6b`). `correspondence_ledger.py`, its run history and its target-staleness check,
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
   test. `unittest discover` collects them; the original repo's runner selects only the `Test*` classes. Fixed
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
- `recursive_attractor_engine.py` is not ported. It is the natural Register B home for
  `Mathemathical-foundation.md`'s fixed-point formalism, and it needs numpy, which this project does not yet
  depend on. A decision, not an oversight.

**Notes:** Two things for a future entry to check back against. First, whether the three axes survive contact
with real diary text, or whether the recursive lineage C of `S = (L, N, P, C)` has to become a fourth. Second,
whether `CONFORMS: False` is still False a month from now: if Article 6 is still NOT_IMPLEMENTED then, the
licence is asking for something the reference implementation does not do, and that gap belongs in the record
rather than in a plan.
