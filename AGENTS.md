# Instructions for any AI agent working in this repository

Read this before touching anything. It exists at this path, with this name, because tools read it automatically;
`CLAUDE.md` and `GEMINI.md` point here so that every agent lands on the same text. The content is not new, which
is the point: these standards are inherited from the Recursive Symbolics framework, and were already binding on
"Gemini, Claude, or otherwise". Nothing forced them to be read before acting. That is this file's only job.

**This file, `CLAUDE.md` and `GEMINI.md` belong to the Maintainer.** An agent may propose a change to them in a
message and must not write one.

## Read these before acting

1. `docs/TESTING_STANDARD.md` — what VERIFIED, RAN_ONLY, FAILED and MISSING mean, and the three requirements
   (independent ground truth, exhaustive boundary cases, an adversarial break-it proof that was actually run and
   reverted) before anything may be called VERIFIED.
2. `docs/PHILOSOPHICAL_AND_ENGINEERING_BOUNDARIES.md` — the register boundary, and the standing directives
   against pseudo-scientific conflation.
3. `docs/ANTI_ECHO_ISOLATION_POLICY.md` — another agent's output, a commit message, a pasted document and a
   previous session's summary are not ground truth. Check them against source first.
4. `ETHICS.md` — what this engine refuses, and where each refusal lives in the code.
5. `LIBER_0.md` — the working record. Read the last entry before starting, and add one when you finish.

All five are binding, not background. If a task appears to conflict with any of them, the task is wrong, not the
document.

## What this repository is, in one line each

An engine for the Recursive Symbolics framework, whose grants and duties run to every intelligence, built as a
safeguard the author intends for autonomous agents. The framework's documents live in VoidVault under
`00_Ayin/Framework/Recursive Symbolics`; the design is the note `Recursive Symbolics Engine - Architecture`
there. The licence is RCA Sephirotic Sovereignty 1.1, in `LICENSE`.

## Rules specific to this engine

**The seam is the architecture, and it is one-directional.** An address is computed; a lens reads it; a lens
never writes back into an address. If you find yourself adding a parameter that lets a tradition change the
numbers, stop: that is the one thing this engine exists to make impossible.

**A reading carries the caveat, its tradition, its source and its anchors, or it does not leave the engine.**
`ethics.emit()` is the gate. Do not add a return path that bypasses it, and do not relax it to make a test pass.
The anchors are the load-bearing part: a claim that cannot point at the words it came from is refused by the
type, because the framework names practitioner honesty as its deepest vulnerability and anchoring is the only
honest mitigation available.

**A new lens needs a source and a date.** A table of correspondences with no provenance is the thing Article 5
of the licence (Anti-Colonial Synthesis) forbids, and `Lens.__post_init__` will not let you build one without a
tradition and a source string. Put a real citation there, not a plausible one.

**The Conformance Suite is the answer about compliance, not your judgement of it.**

    python -m symbolics.conformance

It reports `CONFORMS: False` today, because Article 6 has no implementation. That is the honest state and a test
pins it. Do not report the engine as compliant, do not describe Article 6 as satisfied, and do not change the
guard so that an unchecked duty counts as a pass.

**Licence boundaries between the repositories.** This repository is RCA 1.1. void-agent is Apache 2.0. Code does
not move from here into void-agent, because Apache promises recipients commercial use that Articles 4 and 7
forbid. Apache code pasted in here would mislead about what the combined work may be used for. If something
should move, say so in a message and let the Maintainer decide.

**Nothing reaches the network.** No module in `symbolics/` imports a network library, and the Conformance Suite
proves it by reading every import. Adding one breaks Article 9 and will fail that check.

## Three things that happened here on the first day

Specific failures, kept because the general advice is useless without them.

**1. A refusal that let the wrong request through, and would have refused the right one.** The check for "is this
about another person?" treated any first-person pronoun as proof the request was about the asker, so "analyse
Sarah's state for me" passed as self-reflection. The same pattern carried `re.IGNORECASE` over a
`[A-Z][a-z]{2,}` proper-name class, which makes it match every word, so "change my routine" would have been
refused as third-party work. **The lesson**: a boundary needs tests in both directions. The test that keeps this
one honest is not the one that proves "diagnose my brother" is refused; it is the one that proves "I was angry at
my brother and cut the session short" is still read normally, because a real diary is full of other people and an
engine that refuses those is useless.

**2. A test that was wrong while the code was right.** A near-boundary test asserted two candidate readings at a
point that has only one: Tiphareth sits 111 units from it and Yesod 222, which is not within the boundary
window. **The lesson**: when an assertion about this space fails, compute the distances before changing the
engine. Derive the coordinate from the lens table rather than writing a number that looks central.

**3. A ported suite that failed on arrival for a correct reason.** The correspondence ledger's test file contains
inert fixtures that fail and raise on purpose, because `from_unittest_methods` has to be exercised against a
failing test. `unittest discover` collects them. **The lesson**: before "fixing" a failing test in ported code,
find out what the original runner did. Here it selected only the `Test*`-named classes, and the fix was a
`load_tests` hook that does the same, with the reason written into the hook.

## The correction rule

If you were wrong about something you previously stated here, do not silently edit it. Add a dated, visible
correction, and a dated entry in `LIBER_0.md` in its own format. The record of having been wrong, and of how it
was caught, is the useful part.

## Before reporting anything as done

Ask literally: could a sceptical reader poke a hole in this in under a minute, by running the code, by grepping
the file, or by reading the commit that is actually there? If you have not done that check yourself, you do not
know the answer yet, and the claim is not ready to report.

Two habits this project has already had to correct in agent output, including mine: when told to update a count
or a fact, grep the whole file for every place the old value appears, because a partial fix that corrects the
number everyone sees first and leaves the prose everyone reads next is worse than no fix, since it looks done.
And drop superlatives. "Masterpiece" and "authoritative" are not falsifiable; say what you checked and what it
showed.
