# recursive-symbolics

The engine for the Recursive Symbolics framework. Plain Python (3.10 or newer), no packages to install, and
nothing in it reaches the network.

The framework's own documents are in VoidVault under `00_Ayin/Framework/Recursive Symbolics`; the architecture
of this engine is the note `Recursive Symbolics Engine - Architecture` there.

It is not a vault tool. It takes a symbolic state from any caller and returns typed records: void-agent is one
caller, the game is another, a command line is a third.

## The seam

    observable input -> address (computed) -> lens (chosen) -> reading (interpretation)

An address is three numbers that no tradition owns. A lens turns an address into one tradition's words. A lens
can never write back into an address, so no reading is ever "what the state really is": the engine can only say
that at this address, this tradition reads this name. That is the Core Axiom's "syntax, not semantics" as code.

## What is enforced, not asked

- Every reading carries its caveat, names the tradition and the source it read from, and points at the words it
  came from. A reading with no evidence is refused by the type, not by discipline.
- No output may rank a person, and none may command: it offers.
- A reading near a boundary offers both names and asks which fits.
- `unknown` and `paradox` are return types. Nothing is forced to a verdict.
- This engine reads the person asking, and no one else. A request to diagnose or act on another person is
  refused, and there is no transcend operator.

## The record

`LIBER_0.md` is this repository's working journal, in the format the Recursive Symbolics framework uses: dated
entries with what was attempted, what actually happened, and what is not verified. Corrections are new entries,
never edits that erase what was believed before. If a claim in the documentation and a claim in the record
disagree, the record is the one that was written while it happened.

## Where the architecture already exists

`architecture/layers.json` maps each layer of the Sovereign Recursive Engine Architecture (a note in the vault)
to the files that already implement it, here and in the sibling repositories, with each layer's known gaps.
`architecture/intent.json` is this repository's intent as data: every statement in it is quoted from a document
the Maintainer wrote, and it is a DRAFT until he ratifies it.

    python -m symbolics.layers

That looks for every listed file, reports a sibling repository that is not on the machine as unknown and not
as missing, fails if a quotation has drifted from its source, and does not pass if nothing could be checked.
The layer names are a way of organising the work, a provisional metaphor. Nothing claims a sephirah is a
software layer.

## Running the tests

    python -m unittest discover -s tests -q

## Licence

RCA Sephirotic Sovereignty License 1.1, in `LICENSE`. Copyright 2026 OmnisMutus.

Free of charge, forever, for every non-commercial purpose: view, copy, modify, fork, train on, study, run and
distribute it. What the licence forbids is monetizing it, closing it, hosting it without publishing your source
and weights, using it for warfare, mass surveillance, social scoring or manipulation, and reading the state of a
person who did not ask. Forks inherit the same terms.

Stated plainly: those are field-of-use restrictions, so this is **not** an "open source" licence in the Open
Source Initiative's sense, and not "free software" in the Free Software Foundation's. The accurate description is
source available, or ethical source. The licence has not been reviewed by a lawyer.

The duties the licence puts on a running system, rather than on a promise, are checkable:

    python -m symbolics.conformance

See `ETHICS.md` for what the engine refuses and where each refusal lives in the code.
