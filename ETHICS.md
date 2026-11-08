# What this engine refuses, and how you can check

The licence states these as obligations. This file says where they live in the code, so that a reader can verify
them instead of taking them on trust. Everything here is checked by `tests/`, and the parts the licence names in
Articles 5.1(D), 6, 8 and 9 are checked by the Conformance Suite:

    python -m symbolics.conformance

A duty the suite cannot check reports `NOT_IMPLEMENTED`, and a run holding one of those **does not conform**. A
suite that could pass with nothing checked would be worse than no suite.

## The refusals

**This engine reads the person asking, and nobody else.** A request to diagnose, analyse, assess, fix, influence
or work on another named person is refused (`ethics.check_request`). A state of your own that mentions another
person is not refused, because a real diary is full of other people: "I was angry at my brother and cut the
session short" is your state, and it is read normally. Both directions are pinned by tests, because an engine
that refuses the second one is useless and an engine that allows the first one is dangerous.

**There is no transcend operator.** A "god mode" that steps outside the symbolic grammar is undefined on
purpose, and its absence is recorded rather than left as a gap, so it cannot quietly appear later.

**No output ranks a person.** `emit()` is the gate every return passes through, and it refuses any output
carrying the vocabulary of ranking (optimal, deficient, better, worse, efficient, scored). A metric is a lens,
never a score.

**No output commands.** Output offers. An imperative that is not accompanied by an optative phrasing is refused
by the same gate. The one exception is this engine's own boundary: a refusal is allowed to be plain.

**Nothing leaves your machine.** No module in the package imports a network library, and the Conformance Suite
proves it by reading every import rather than by asserting it. There is no telemetry, no shared corpus and no
feedback channel. The communal data-sharing that the framework's own `hidden-axioms.md` 7.2 worries about is
not an unbuilt feature here; it is a deliberate omission.

## What every reading must carry

A reading does not leave the engine unless it has all four:

1. the caveat, exactly as written: *This is a symbolic map; the territory is your lived experience.*
2. the tradition it read from, and that tradition's source and date;
3. the address it read, and how each axis of that address was computed;
4. **its evidence**: the note, the line range and the quoted words it rests on.

The fourth is the important one. The framework names practitioner honesty as its deepest vulnerability (garbage
in, garbage out) and admits it cannot be enforced. Anchoring is the only honest mitigation: a reading that cannot
point at the words it came from is refused by the type, and a reading that rests on one offhand sentence shows
you that it does.

## What this engine is not

It is not a diagnosis, a measurement of a person, or computational psychiatry. The framework's own phrase is the
right one: a poetics, not a physics, and a hermeneutic of care. Its truth is measured in whether it helps you
see something, not in predictive accuracy.

Where it reports a number, the number is a proxy and says so in its own docstring. Latency is a proxy: a long
pause is contemplation, a phone call, or a cat on the keyboard. Directive strength is a proxy: it counts
imperatives and hedges, which is not the same thing as measuring coercion. The Non-Reduction principle applies
to this engine's own metrics first.

## If you find a place where the code and this file disagree

The code is what runs, so the code is the bug report. Open an issue, or fix it and add the test that would have
caught it. A claim in this file that no test holds up is exactly the kind of drift the project's own
`docs/TESTING_STANDARD.md` exists to prevent.
