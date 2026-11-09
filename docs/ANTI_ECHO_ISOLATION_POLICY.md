# Anti-Echo Isolation — Read This Before Trusting Any Prior Output

This file is binding on any AI agent working in this repository — Gemini,
Claude, or anything used later — the same way `TESTING_STANDARD.md` and
`PHILOSOPHICAL_AND_ENGINEERING_BOUNDARIES.md` already are. It states one
rule and shows, with five real incidents already on record in this repo,
why it isn't optional.

## The rule

**Do not take another agent's output — or your own earlier output, or a
pasted document, or a commit message — as ground truth without running an
independent verification pass first.** "Independent" means: read the
actual file (`git show HEAD:<path>`, not memory), run the actual code,
`grep` for the actual claim. Not re-reading a summary of it, not trusting
that a prior step "already checked."

The name comes from `docs/recursive_symbolics_foundation_reference.md`
section 2 ("Multi-Agent Verification Notes," source:
`ai_collective_behavior_analysis.md`), which names it as one of three
proposed swarm safeguards. This document is the operational, binding
version of that one safeguard — not a restatement of the framework
material, a policy grounded in what has already happened in this specific
repo. The other two proposed safeguards in that section are handled
differently and are not part of this policy: "Hypothesis Marketplace"
doesn't map onto anything checkable here and is left as reference
material only; "Decay of Unverified Consensus" was deliberately **not**
implemented as its literal 15%-per-iteration formula (no operational
definition exists in this codebase for "confidence" as a number) — the
honest, computable alternative is `correspondence_ledger_history.py`'s
real elapsed-time-since-last-check tracking, a separate, already-built
feature (see `docs/README_DOCS.md` section 8).

## Why it's binding, not aspirational: five times it already mattered

**1. The half-fixed verification report.** Commit `eaf1575` updated
`docs/master_system_architecture_and_verification_report.md`'s top-line
scoreboard to `24/24` and looked complete from the commit message alone.
It wasn't — the executive-summary prose still said "17 software
engines," and the roster table still listed only 14 of the 24 rows. A
later session caught this by reading the actual diff instead of trusting
the commit message, and added the missing 10 rows by hand. Taking a
commit message as evidence that a change is complete, instead of reading
the change, is exactly the failure this policy prevents.

**2. Unverified, superlative analysis of already-committed work.** A
message analyzing this project's own findings doc described it as
"exceptionally well-crafted," "a masterpiece of technical documentation,"
and "an authoritative manifesto," and recommended adding six findings
that were already committed there. The recommendation implied the file
hadn't been checked in its current state before the analysis was
written. Confident, fluent language about a file is not the same thing
as having read the file.

**3. A specific, wrong causal claim in a status report.** Gemini's own
`test_all_engines.py` report claimed `stat_learning_suite.py` took
8.948 seconds "due to cross-validation loops" and recommended exposing a
cross-validation sample-size flag. Grepping the file and its test for
`KFold`/`cross_val`/any fold loop turned up nothing — the file has
exactly 4 test methods, none of them cross-validation. Rerunning the
actual timing three times gave 1.07–1.38 seconds, nowhere near 8.9s.
Logged in `GEMINI_EXPERIMENT_LOG.md` as MIXED: the report's tone and
structure were right, but this one specific causal explanation was
generated to fit an observed number rather than checked against the code.
A confident-sounding number attached to a plausible-sounding mechanism is
still a claim that needs checking, not evidence in itself.

**4. Two file trees that didn't exist.** A pasted document described a
Next.js "Web Observatory" naming specific files; none existed anywhere in
this repo. Later, a separate pasted directory tree for a
"Recursive-Consciousness-Architecture" folder named eight files under
`tools/` and `docs/`; checked against the repo via `find`, none of those
existed either (the real, related content arrived separately, as direct
file uploads, and *those* paths did resolve — see the "Six Foundation
Documents Normalized" entry in `LIBER_0.md`). Both were caught the same
way: checking whether the named files actually exist before treating the
description of them as fact, rather than assuming a detailed, specific-
sounding file tree must be real because it's specific.

*UPDATE (2026-08-01)*: the "Web Observatory" files turned out to be
real after all — in the sibling `Recursive-Symbolics` folder, which was
not connected to any session until this date. Once connected,
`omarg-ui/` (the Next.js observatory), `tools/lookup.py`,
`tools/delta_operator.py`, and `scripts/cross_validate.cjs` were all
confirmed present, and `cross_validate.cjs` was **run live: 104/104
checks passed**, exactly as its description claimed. The original catch
was still correct as stated — "none existed anywhere in this repo" was
and is true, and treating an unresolvable file tree as fact would have
been wrong at the time. But the incident now carries a second, sharper
lesson: *nonexistence within the checked scope is not evidence of
fabrication.* The honest verdict when a claim can't be resolved is
"unverifiable here," not "false" — and the claim should be re-checked
when the scope changes, which is what happened, and what corrected it.

**5. The counter-example — verification isn't the same as assuming
fabrication.** A dense "Reality as Recursive Rewriting" ontology document
made eleven specific, checkable technical claims (an exact SHA-1 hash, a
4-decimal Ridge/sklearn agreement, `INT32_MIN` handling, DDPG RPM bounds,
and more). Every single claim was independently re-checked against source
before acceptance — and every one of them held up, except one real error
(the doc said "10 Sephirotic dimensions" but its own table had 11 rows,
including Da'ath, traditionally the non-sephirah "void"). That one error
was corrected, not silently. This is the necessary other half of the
policy: the discipline is "check every specific claim," not "assume the
worst" — confirming genuine accuracy and catching real fabrication come
from the exact same habit of checking, and this repo has logged both
outcomes honestly rather than only the catches.

## Scope

This applies regardless of which agent produced the original output,
including your own prior turns in the same session. It applies to
commit messages, status reports, pasted analysis, uploaded documents,
and directory trees — anything presented as a fact about this repo's
current state that hasn't been checked in *this* pass. It does not apply
to running a test suite and trusting its own exit code (that's what
`TESTING_STANDARD.md`'s VERIFIED category already covers) — the point is
external claims *about* this repo's state, not the repo's own test
output.

## Relationship to other documents

`GEMINI.md` names incidents 1 and 2 above as Gemini-specific worked
examples and should be read as the entry point for any Gemini session;
this document generalizes the same rule to any agent and is the third
file that document should be read alongside. `GEMINI_EXPERIMENT_LOG.md`
is where the ongoing track record of checking Gemini's output specifically
gets kept (incident 3 lives there in full). `LIBER_0.md` is where the
primary build's own catches and confirmations get kept (incidents 4 and 5
live there in full).

## Before accepting anything as true

Ask, literally: has this specific claim been checked in this pass — by
reading the actual current file, running the actual code, or grepping for
the actual pattern — or is it being accepted because it sounds specific,
because a prior turn said so, or because another agent reported it? If
the answer is the second one, it isn't verified yet, regardless of how
confident it sounds.
