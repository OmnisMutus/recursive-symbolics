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

## Running the tests

    python -m unittest discover -s tests -q

## Licence

Not yet decided. `Thoth/solo`, whose correspondence ledger this engine will port, is under the RCA Sephirotic
Sovereignty License; void-agent is Apache 2.0. Until that is settled, this folder is unlicensed and unpublished:
all rights reserved, OmnisMutus, 2026.
