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

### 2026-11-09 — Immune memory made checkable: every breach names its guard, and outgoing commits are read

**Attempted:** Turn the maxim of the Principle of Recursive Validation ("security is ... the immune memory of
every perturbation the system has successfully integrated") into something the repository can verify about
itself. Until now a breach became an entry here and nothing tied the entry to what would catch it again.

**Result:** VERIFIED, and CORRECTED once.

`symbolics/breaches.py` reads this file. An entry whose Result line carries CORRECTED or FAILED is a breach,
and must name a guard (`path::test_name`) or a waiver with a reason. GUARDED, WAIVED, UNGUARDED, BROKEN; the
last two fail. Entries are never edited, so the four breaches already here have their guards beside the
record, in `architecture/guards.json`: three guarded, one waived (reporting as new what the corpus's own
docstrings already said: no test can check that a docstring was read, and the waiver says so).

One of those four had no guard to name. The squash entry below records a push that would have published a
local path through history although the files were clean. `symbolics/outgoing.py` is the guard that did not
exist: it reads every commit a push would send, patches and messages, for a path into a home folder, and
skips placeholder names so this repository's own fixtures do not trip it.

Evidence: `tests/test_breaches.py` 23 tests, `tests/test_outgoing.py` 11 tests, including a real git
repository built in a temporary folder with the add-then-remove history. 18 break-its planted across the two
modules. 17 were caught by the test named in advance.

CORRECTED: the eighteenth was not caught. Limiting the scan to the newest commit still passed every test,
because the commit that removes a line shows that line, so the newest patch still held the path. The test
proved less than its name claimed. A three-commit history with an unrelated commit on top now fails under
that bug. Suite: 154 tests, OK. `python -m symbolics.breaches`: MEMORY OK True. `python -m symbolics.outgoing`
on the seven commits waiting here: clean. CONFORMS: True.

**Guard:** tests/test_outgoing.py::test_every_outgoing_commit_is_read_not_only_the_newest

**Notes:** What this does not establish. GUARDED means the named test exists in the named file. It does not
mean the test passes (the suite answers that) or that it is the right test (a person answers that). The
assignment of guards to the four old entries is mine: rank 2, falsified by any of them failing to catch a
replay of its breach. The rule is not written into the Entry Format at the top of this file or into
`AGENTS.md`, both of which are the Maintainer's; it lives in the README and in the module. Void also settled
a gap recorded in the index: the ledger is his own work, so void-agent applying its rule needs no credit
line. The gap was removed.

Correction, added the same hour, two things. (1) The counts above are wrong by one: `tests/test_breaches.py`
runs 22 tests, not 23 (a `def test_real` inside a fixture string was counted), so the two files hold 33, and
the commit message's "34" is wrong the same way. Counted this time from the runner's own "Ran N tests" line.
(2) Run on its own commit, `symbolics/outgoing.py` reported one hit: an invented name written as a literal
path inside `tests/test_outgoing.py`. A false alarm about a person, and a true statement about the file: the
scanner's own test tripped the scanner. The test now builds that path from a variable. The line remains in
the history of the commit before this one, so the check stays red until these commits are pushed or folded
together, and folding is the Maintainer's decision, not taken here.

Folded, the same evening, at Void's instruction. The two commits this entry was written across (local
`937745d` and `e939cdd`, neither pushed) are now one. The literal path is therefore in no commit, the message
that said "34" no longer exists, and `python -m symbolics.outgoing` reads clean on what is waiting. The second
sanctioned exception to the rule against rewriting history, on the same terms as the first: explicitly
approved, and limited to commits that existed on one machine only. The two paragraphs above are left as
written; they describe the state before the fold.

### 2026-11-09 — An index of where the architecture already exists, and a draft intent made only of quotations

**Attempted:** Void brought a vault note, `Sovereign Recursive Engine Architecture`, and asked whether the whole
project could be consolidated into it; then a second document proposing eight new files to fill its layers;
then asked for whatever is necessary to be built and left for his review.

**Result:** VERIFIED for the code; the content is a proposal awaiting review.

*What was not built, and why.* The second document listed `intent.yml` and CI as existing; neither does, in
the vault or any of the three repositories (searched). It listed a component-level test registry as missing;
void-agent's `tests/registry.json` is one, with 42 components. Six of its eight proposed files duplicate
something that exists, and none came with a test. Its sample intent was invented text. None of that was built.

*What was built.* Two data files and one checker.
`architecture/layers.json`: ten rows (the note's eight layers, plus Netzach and Hod, which the note omits and
which are recorded as UNASSIGNED rather than given a meaning by guesswork). 42 components across this
repository, void-agent and the vault, each a real path, and each layer's gaps written out. The meta layer is
in it this time, under Tiphareth and Da'ath.
`architecture/intent.json`: nine statements, each quoted from `README.md` or `AGENTS.md` with its source.
Status DRAFT, `ratified: false`. No sentence in it was written for it.
`symbolics/layers.py`: looks for every listed file; a sibling repository absent from the machine is NOT_HERE
(unknown), not MISSING; a quotation no longer in its source is drift and fails; a run that checked nothing
does not pass; a draft is never reported as ratified.

Evidence: on its first run the checker reported four layers BROKEN, correctly: four evidence paths in the
index I had just written pointed at `corpus/ledgers/` for tests that live in `corpus/tests/`. Fixed in the
index, not in the checker. `tests/test_layers.py`, 21 tests against toy repositories built in a temporary
folder. Eight break-its planted in `layers.py`, each caught by the test named in advance, source restored.
Suite: 121 tests, OK. `python -m symbolics.layers`: 42 components looked for, INDEX OK True, INTENT OK True,
state DRAFT. `python -m symbolics.conformance`: CONFORMS True, so the new module imports no network library.

**Notes:** Three things are Void's and were left open on purpose. (1) The intent: the nine quotations are a
selection, and selecting is an act of interpretation even when every word is his; rank 2, falsified the
moment he says a statement does not belong or one is missing. (2) Netzach and Hod. (3) Whether Chokmah and
Binah are one layer or two. The break-its were run by hand from a script and are not yet in a registry, so
they will not re-run by themselves: this repository has no `verify --breakit` of its own.
`AGENTS.md` says the Conformance Suite "reports `CONFORMS: False` today"; it reports True. That file is the
Maintainer's and was not edited.

### 2026-11-09 — The meta layer named, its stale baseline updated, and two missing pieces ported

**Attempted:** Void asked why the meta layer had not been mentioned once in this session, pointing at
`corpus/docs/eli5_architecture_guide.md`.

**Result:** CORRECTED, then VERIFIED.

*The omission.* The meta layer (the correspondence ledgers: every claim sorted into VERIFIED, FAILED or
UNTESTABLE, and a ledger of nothing but UNTESTABLE refusing to pass) was in the repository and working the
whole time. It had been counted as "10 ledgers" in a folder inventory and never named as a layer. It was left
out of a mapping of the project's architecture drawn the same evening, where it is the central piece, and its
one failing test had been listed as a loose end. `symbolics/ledger.py` credits the ledger as its source;
void-agent's NOT_ESTABLISHED, UNCLEAR and RAN_ONLY statuses apply the same rule and credit nothing.

*The baseline.* `test_real_ledgers_match_current_known_baseline` asserted 15 VERIFIED / 7 UNTESTABLE; the
ledgers report 16 / 6. The cause was already written down twice in the corpus: the glyph ledger's own dated
UPDATE (its qualia-vector mapping became testable when `qualia_emotion_classifier.py` was written), and
`correspondence_ledger_meta_tool_spec.md`, which found the mismatch predates the 2026-08-02 reorg and left it
unresolved on purpose. A fourth finding the corpus had recorded before this session reported it.
The plan agreed with Void was to derive the count instead of hardcoding it. Reading the test changed that:
its docstring says the snapshot is hardcoded deliberately and must be updated consciously, and a count
derived from the ledgers could never disagree with them. So the snapshot was updated to 16/0/6 with a dated
SECOND CORRECTION in the test's docstring, and the derivable half was added as a separate test
(`test_real_ledger_totals_are_internally_consistent`: bins sum to the total, rows sum to the aggregate).
12 tests, all pass. Corpus: 830 checks, 57 files, 53 clean, 0 failed, 4 unscored. Engine: 100 tests.

*The ports.* The guide's diagram names `FUTURE_WORK.md` and links a README; neither had been carried over.
`corpus/FUTURE_WORK.md` is a verbatim copy. `corpus/README.md` is the original README adapted to this layout,
and says so in its first paragraph; it names the meta layer as a layer, and ends with a list of what the
original mentions that is not here. The largest item on that list: the original working journal. Thirty-four
corpus files say "see LIBER_0.md" and mean that journal, not this file.

*The renamed hand-written test.* `test_c_low_level_simulator.py` holds Void's own test cases. A diff against
the pre-rename file shows the module name, the class name and one banner string changed, and no assertion or
value. To show it still bites under the new name: the `abs(INT_MIN)` guard in the engine was shifted off by
one, `test_abs_edge_cases_and_int32_overflow` failed, the engine was restored byte for byte, 7 of 7 pass.

*The quadcopter question, closed.* The OPEN note in the entry below is answered by Void: no GPL code was
used. That is the author's statement about how the engine was written and it is recorded as such. The
engine's file was not compared against any outside source in this session.

**Notes:** Three runners in the corpus write to tracked files as a side effect of being run
(`ledgers/correspondence_ledger_run_history.json`, `tools/trace-log.txt`). Both were restored from HEAD
after the runs above. Worth knowing before a `git add -A`.

Correction, added the same hour: "Three runners" in the note above is a miscount. Two tracked files were
observed changing, the two named; which runs changed them was not isolated.

### 2026-11-09 — One licence across the repository, and two engines renamed

**Attempted:** A provenance review of the 41 engine files before the corpus is published, then the fixes Void
chose from it.

**Result:** VERIFIED for what was changed; OPEN for one question.

*Review.* No engine carries another party's copyright line, an "adapted from" note, or a link to an outside
repository. Imports are the standard library, NumPy, and in three benchmark files scikit-learn or PyTorch,
imported to be measured against. This was a read of headers, imports and structure. It was not a diff against
outside code, and it does not prove absence.

*Licence.* The corpus named three licences: "Universal AI & Human Sovereignty Public License v1.0" (2 engine
headers, 2 docs; no such text existed in the repository), CC BY-SA 4.0 (9 files), and RCA Sephirotic
Sovereignty 1.0 (two identical copies in `corpus/`, added earlier the same day), while the repository root is
RCA 1.1. Void's decision: the RCA licence, one version. Every header and doc now names RCA 1.1 and points at
the root `LICENSE`. The two 1.0 copies were moved out to `_to_delete/` (untracked). A doc line claiming
"protections under AGPL-3.0, CC BY-NC-SA 4.0, and OpenRAIL-M" was removed. Seven doc links that pointed at
`corpus/LICENSE` now point at the root. `AGENTS.md` still mentions Apache 2.0: that is the stated boundary
with void-agent, not a claim about this repository, and the file is locked.

*Renames.* `alx_c_low_level_simulator.py` is now `c_low_level_simulator.py`, and
`iitd_mth432_stat_learning.py` is now `stat_learning_suite.py`, with their tests and every reference (120
lines across 24 files). Each engine keeps one docstring line saying which exercise list or course its scope
follows, and that there is no affiliation: the name no longer implies one, and the origin is not hidden. The
originals outside this repository keep their old names. Five doc mentions of `alx_c_functions_nested_loops.c`
were left alone: that C file is not in this repository, so there is nothing here to rename.

*Also fixed.* Seven doc links left malformed by the earlier path rewrite (a parenthetical inside a link
target) are now plain text.

Evidence: 0 matches repo-wide for the two retired licence names; corpus totals identical to before the change
(829 checks, 57 files, 52 clean, 1 failed, 4 unscored); the two renamed suites pass under their new names;
engine 100 tests.

**Notes:** OPEN: `ddpg_quadcopter_rca_engine.py` says "Exact Specification Parity" without saying with what.
Void recalls github.com/tudelft/optimal_quad_control_RL as the reference. That repository is GPL-3.0 and its
root holds a racing environment (`quad_race_env.py`); its source could not be opened from this session, so
neither a match nor a mismatch is established. The engine's numbers (18-value state, rotors 0 to 900, an L1
distance reward) resemble a widely forked course project instead, from recollection and not from a diff. No
credit line was added, because a credit to an unverified source would be an invented attribution. If the
engine was written with GPL-3.0 code open as a model, that matters and should be settled before relying on
the RCA licence for this one file.

### 2026-11-09 — Five local commits squashed into one before a push, to keep a local path out of public history

**Attempted:** A pre-publish review of the five commits ahead of `origin/main`, then publishing them.

**Result:** CORRECTED, twice.

1. **The remote.** Void was told this repository had no remote and was handed a `gh repo create --private`
   command. Wrong on both counts: `origin` already existed, was public, and had been pushed earlier the same
   day. The claim was carried forward from a session summary and not checked against `git remote -v`. The
   command would have failed.
2. **The history.** The review cleaned the working tree (32 files carrying absolute local paths that included
   a Windows username, rewritten to repository-relative links) and committed the fix as a fifth commit on top.
   That left the paths readable in the history: the first of the five commits added them, the last removed
   them, and a push publishes both. The already-pushed history was checked and contained none.

Void chose to squash. The five local commits (local tip `2d9e13f`, never pushed) were folded into a single commit
with `git reset --soft origin/main`, so no published commit ever contains the paths. This is the one
sanctioned exception to the standing rule against rewriting history: explicitly approved, and limited to
commits that existed on one machine only. The five original messages are preserved in the body of the squashed
commit, with the one line that quoted the path itself redacted.

Evidence after the squash: 0 matches for the username in the tree, in the commit message, and in
`origin/main..HEAD`; corpus 829 checks, 52 files clean, 1 failure, 4 unscored; engine 100 tests.

**Notes:** A clean working tree is not a clean push. The check that matters before publishing is over
`origin/main..HEAD` (every commit that will travel, and its message), not over the files on disk. And a fact
about repository state from a summary is a claim, not an observation: `git remote -v` costs one line.

### 2026-11-09 — Three "findings" the corpus had already recorded, in its own test docstrings

**Attempted:** Nothing. This entry is a correction to the three entries above it.

**Result:** CORRECTED. Each of the following was reported to Void during this session as something found, and
each was already documented in the corpus, in the docstring of the test covering that file:

1. **The kaph cipher value.** `tools/test_lookup.py` states it exactly: cross-checking all 22 letters against
   an independently transcribed standard table turned up one mismatch, kaph stored as 21 where the standard is
   20, and "21 is also Kaf's OWN path_key_scale in the same JSON row -- consistent with a copy-paste slip when
   the row was authored." It carries `KNOWN_DATA_DISCREPANCIES = {"Kaf"}` and a stated policy of not silently
   correcting uploaded reference data. The same diagnosis was re-derived here independently, which corroborates
   it, but it was presented as new.
2. **`balancing_rules` mapping Geburah to itself.** `tools/test_symbolic_debugger.py` tests it as a fact about
   the data and says so: "a real, existing property of symbolic_api.json, tested here as a fact about the
   data, with no claim made about whether it is esoterically correct (Register A, out of scope for this test
   file)." It was known and deliberately scoped out, not missed.
3. **The debugger's three failures being the environment.** `tools/test_debugger.py` has a section headed "A
   NOTE ON A FALSE ALARM" describing the identical PermissionError from `tmp_log.unlink()`, identifying it as
   a sandbox mount restriction rather than a code regression, and ending: "Recorded here so a future reader
   who sees this exact failure mode again knows to check the environment first, not assume the code
   regressed." That note was written for exactly the reader this session was, and it was not read.

**What was actually new**, stated narrowly so the distinction survives: that `tools/test_rca_llm_sandbox.py`'s
cross-file checks had never executed in either layout, which is different from the discrepancy they check and
which its docstring documents; the ledger baseline asserting 15 where the ledgers now report 16; and the
corpus total being 829 checks rather than 463.

**Also found by the corpus and not by this session:** the "earth" keyword collides between Binah and Malkuth
in `symbolic_api.json`, and because `keyword_map` is built by plain dict assignment in JSON order, Malkuth
wins and Binah's "earth" is unreachable through `detect_counts()`. And `transcompiler.save_schema(path=None)`
writes to the module-level default rather than the file the instance was loaded from, caught when the test's
own first draft overwrote the real `symbolic_schema.json`.

**Notes:** The lesson is narrower than "read more carefully". These test files are the project's findings log,
not only its verification: the discoveries live in the docstrings, above the code. Reading a suite's results
while skipping its docstrings is the same error as reading a wrapper's summary while skipping the suite, which
this session also made twice. A reader that wants to know what is wrong with this corpus should read the test
docstrings first and run the tests second.

### 2026-11-09 — A cross-file check that had never run, and a failure that was the environment

**Attempted:** Resolve the two things the consolidated corpus reported as not-clean, rather than leaving them
located but undiagnosed as the previous entry did.

**Result:** VERIFIED. The corpus now reads 829 checks across 57 files, 52 files unambiguously clean, **1
failure**, 4 unscored on absent dependencies.

**`tools/test_rca_llm_sandbox.py` had never executed its cross-file checks, in either location.** It guards
them on `_SOLO_DIR = Path(__file__).parent.parent.parent / "solo"`. In the original layout that directory
exists, so the guard passed and `import standalone_rca_sandbox` then failed, because the module is in
`solo/engines/` and the path was wrong by one level: the whole file errored. In the consolidated copy the
directory does not exist, so the guard failed and both checks **skipped silently**, which is the worse of the
two failures because nothing looks wrong. Repointed in the copy to `../engines`, where the module actually
is. The file now runs 17 tests with nothing skipped, and both cross-checks hold: `sanitize_paths` is
identical across the two implementations, and `apply_epistemic_humility` genuinely differs, with
`standalone_rca_sandbox` having no rule for "This is the correct interpretation". That discrepancy was
documented by hand in the test's own docstring and is now verified by a running test for the first time.

**`tools/test_debugger.py`'s three failures were this environment, not the code.** `run_self_tests` calls
`Path.unlink()` on its own temporary file, and the mount this ran in denies deletion. The same files in a
writable directory pass. `run_corpus.py` now treats a refused operation as UNCLEAR rather than RED, matching
the rule already in void-agent's `suitecheck`, so the two readers agree.

**Not verified, and not claimed:**

- The remaining failure is the ledger baseline: the ledgers report 16 verified claims and
  `test_real_ledgers_match_current_known_baseline` asserts 15. A claim was added and the baseline was never
  updated. The ledgers themselves pass. A hardcoded count is a number that goes stale the moment the thing it
  describes improves, so the fix is to derive it or assert a floor, and that is not done.
- Only the consolidated copy was repointed. The desktop original keeps its broken path, deliberately: it is
  reference material and not mine to edit.
- `apply_epistemic_humility` having five patterns in one file and four in the other is now a proved
  difference, not a decided one. Which count is correct is a question for Void.

**Notes:** This is the consolidation earning itself. The cross-file check was written to compare two
implementations that lived in different repositories, and it could not work from either. Putting them in one
tree is what made it runnable, and what it found on its first run was that the human-written docstring was
right all along.

### 2026-11-09 — The corpus consolidated here, and a count that had been wrong all along

**Attempted:** Bring the framework's prior implementation into this repository as one body of work, instead of
a new engine beside an older one on a desktop. Void chose the full corpus rather than a framework-relevant
subset, on the ground that the CS-to-Kabbalah mapping is the thesis and the ML and systems engines are its
evidence rather than exercises.

**Result:** VERIFIED, with a correction to a number this record would otherwise have inherited.

Copied, never moved: 42 engine files, 10 ledgers, 8 protocols, 48 tools, 7 architecture tools, 41 test files,
45 docs, 5 studies and 2 data files, into `corpus/`. The originals on the desktop are untouched and were
re-counted afterwards to prove it.

`corpus/run_corpus.py` replaces reading `test_all_engines.py` or `test_all_tools.py` as the suite's result.
Those are per-component rollups: `test_all_engines.py` covers 24 engines out of 57 test files, and it scores a
missing-dependency skip as a correctness failure, so a real failure elsewhere never reaches its summary. Both
of those misreadings happened in this session, in that order, before the tests were run directly.

**CORRECTED:** the corpus is **829 checks across 57 files**, not the 463 reported earlier the same day. The
463 counted only files that print unittest's "Ran N tests" line. Seven files are hand-rolled scripts that
print their own "SUMMARY: N passed, M failed" instead, and a reader that knows one format silently omits the
other. That is an omission rather than a misread, and it is the more dangerous of the two, because nothing
looks wrong.

Current state: 51 files unambiguously clean, 2 failed, 4 did not say enough to score. The two failures are a
stale baseline in `test_run_all_correspondence_ledgers.py` (the ledgers report 16 verified claims; the test
asserts 15) and three failures in `tools/test_debugger.py` around `run_self_tests` not cleaning up its own
temporary file. The four unscored are all absent dependencies: scikit-learn and PyTorch.

**Not verified, and not claimed:**

- The two failures are not diagnosed, only located. The debugger one in particular loads
  `hermetic_qabalah.json` and I have not established whether its self-test fails on the data or on the temp
  file.
- A verdict of GREEN here means a file's own runner said so and nothing was skipped. It does not mean the
  tests are good ones. The break-it registry is what would say that, and the corpus does not have one yet:
  its discipline lives in prose and in each test's own assertions.
- `symbolic_api.json`'s `balancing_rules` was copied as it stands, unaltered. Void states that Chesed and
  Geburah balance in the middle pillar at the corresponding level, which makes all eight of its entries wrong
  in relation rather than in value: the block maps side-pillar pairs to each other instead of to the apex of
  their triad. The port does not silently fix doctrine, so the data is here as it was and the correction is
  recorded as pending.
- `data/hermetic_qabalah.json` carries the kaph error: `cipher_value: 21` beside `path_key_scale: 21`, where
  kaph is 20. It is the same error corrected in the vault note this morning, and it is still live in the data
  that `tools/lookup.py` reads. Copied unaltered for the same reason.

**Notes:** The three triads are doctrine, not geometry. Deriving them from the path graph was tried and fails:
16 triangles have a middle-pillar vertex, and narrowing to the three horizontal paths still leaves Chokmah and
Binah connected to both Kether and Tiphareth, and Netzach and Hod to Yesod, Malkuth and Tiphareth, with Yesod
and Tiphareth tying exactly on distance. So the balance pairs must be stored with a source and checked against
the graph, which is what hidden-axioms 7.2 asks for anyway. Worth a future entry: whether the corpus gets a
break-it registry of its own, since 829 passing checks with no planted-bug proof is precisely the state this
project's standard was written to distrust.

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
