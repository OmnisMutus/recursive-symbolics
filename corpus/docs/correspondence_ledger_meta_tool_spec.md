# The Correspondence Ledger: A Meta-Tool, Precisely Defined

This document exists to answer one question carefully: what is
`correspondence_ledger.py`, actually, and why does it sit outside
`test_all_engines.py`'s main engine count instead of being its own entry?

The short answer is that it's a **meta-tool** — a tool that operates on
other tools' results, not on the thing those tools were built to check.
The rest of this document is that claim made precise, layer by layer,
with the actual mechanics of what runs when you invoke it, the two
break-it proofs that back its own correctness, and a worked path for
extending the pattern to other engines in this repo.

---

## The Three Layers

There are three genuinely distinct layers of code involved here, and
conflating any two of them is where confusion (and, worse, false
confidence) creeps in.

### Layer 0 — the engine

`sephirotic_reward_engine.py`. Real math: velocity in, a float out. This
is the only layer that actually computes anything a quadcopter controller
would use. `SephiroticRewardComponents.chesed_expansion_term()` takes a
velocity vector and an altitude gain and returns a number. Nothing about
this layer knows or cares what "Chesed" means outside of being a method
name.

### Layer 1 — the test

`test_sephirotic_reward_engine.py`. This calls Layer 0's functions with
controlled inputs and asserts on the outputs — "higher speed must
increase Chesed," "a crash must add a fixed penalty to Geburah," and so
on. **This is where all the actual correctness knowledge about the
engine lives.** If every other file discussed in this document were
deleted, this one test file would still be the complete, sufficient proof
that the reward engine behaves as claimed. It has its own documented
ground truth and its own confirmed break-it proof (dropping the Geburah
term from `tifereth_reconciliation()`, which failed 5 of its 16 tests
before being reverted) — see that file's own docstring for the details.

### Layer 2 — the ledger

`sephirotic_correspondence_ledger.py`, built on top of the generic
`correspondence_ledger.py`. This is where "meta" applies literally: it
does not call `chesed_expansion_term()` itself, does not know what a
velocity vector is, and adds **zero new facts** about whether the engine
works. What it does is take Layer 1's existing test methods as raw
material and re-index them along a different axis — not "which test
class does this method belong to," but "which named metaphor claim does
this cluster of tests actually back." Then it adds one thing Layer 1 has
no place to put: an explicit row for the claim that has *no* tests
(Binah/Malkuth/Keter's exclusion from the reward function), sitting in
the same table, at the same visual weight, as the claims that do.

A useful way to hold the boundary between Layer 1 and Layer 2: Layer 1
answers *"does the code do what it says?"* Layer 2 answers *"for this
specific named claim about the code, which tests actually back it, and
is there a claim floating around with nothing backing it at all?"* Those
are different questions, and only the first one is about the engine.

---

## The nearest existing analogy: code coverage

The closest existing analogy is a code-coverage tool. `coverage.py`
doesn't test your code either — it re-runs your existing test suite and
reports which lines got touched versus which didn't, so an untouched
branch can't hide silently. It adds no new assertions; it adds
*visibility* into what your existing assertions actually reached.

`correspondence_ledger.py` is that same idea applied to a different unit
than lines-of-code. Instead of "which lines did the tests exercise," it
asks "which specific natural-language claims did the tests exercise,"
and it forces every claim registered in the ledger to declare itself
either backed-by-a-validator or explicitly-untestable. There is no third
option where a claim just quietly exists in a docstring paragraph with
nobody ever checking whether it's still true after the next refactor.

---

## What Actually Runs, Mechanically

When you execute `python sephirotic_correspondence_ledger.py`, here is
the literal call chain, with no hand-waving:

1. `build_ledger()` constructs a `CorrespondenceLedger` and calls
   `.register()` five times — once each for Chesed, Geburah, Tifereth,
   the end-to-end integration wiring, and the untested Binah/Malkuth/Keter
   exclusion. Each `.register()` call is a plain dataclass construction;
   nothing executes yet.

2. For four of the five, the `validator` argument is built by
   `from_unittest_methods(test_case_cls, method_names)`, which returns a
   closure — not a result. Calling `from_unittest_methods(...)` does not
   run any tests; it just remembers which `TestCase` class and which
   method names to run later.

3. `ledger.run()` is what actually executes anything. For each entry, if
   `validator` is `None`, the entry is marked `UNTESTABLE` and nothing
   runs. Otherwise, the validator closure is called, which does this for
   every named method:

   ```python
   suite = unittest.TestSuite([test_case_cls(name)])
   result = unittest.TestResult()
   suite.run(result)
   ```

   That is a real, live `unittest` invocation of one specific test method
   from `test_sephirotic_reward_engine.py`, run in complete isolation
   from the others. If every named method's suite reports
   `wasSuccessful()`, the correspondence is marked `VERIFIED`. If any
   fail, it's marked `FAILED`, and the detail string names exactly which
   method names failed — not just "something in this group broke."

4. `ledger.report()` formats the results; `ledger.all_testable_passed()`
   is the honesty guard described below, and is what the exit code is
   actually gated on.

So when the break-it proof (next section) showed `Tifereth: FAILED,
4/5 sub-checks`, that was not the ledger discovering a new bug through
some novel mechanism — it was `TestTiferethReconciliation`'s own five
methods running exactly as they always do, just reported through a lens
that names *which claim* they collectively support, instead of just "5
tests, 4 passed, here's a traceback."

---

## The Honesty Guard

The one piece of genuinely new logic in this whole exercise —
**the only place where something new is actually being claimed and
checked, rather than re-displayed** — is `CorrespondenceLedger.all_testable_passed()`:

```python
def all_testable_passed(self) -> bool:
    testable = [c for c in self.entries if c.status != STATUS_UNTESTABLE]
    if not testable:
        return False
    return all(c.status == STATUS_VERIFIED for c in testable)
```

The `if not testable: return False` line is the entire point of the
guard. Without it, a ledger consisting *entirely* of `UNTESTABLE` entries
— i.e., a metaphor with zero actual validators wired up anywhere — would
have `all(...)` vacuously evaluate to `True` over an empty list, and the
ledger would report overall success while having checked literally
nothing. That is the exact same failure shape as `unittest`'s own
`TestResult.wasSuccessful()` returning `True` when every test in a run
was skipped (the reason `test_reconstructed_frameworks_comparison.py`
needed its own explicit "nothing_actually_ran" guard earlier in this
project), and the same shape as `test_all_engines.py` refusing to let
`RAN_ONLY` (script executed, nothing checked) be reported as equivalent
to `VERIFIED`.

Because this is the one place with real, novel logic, it is the one
place with its own dedicated correctness test: `test_correspondence_ledger.py`
(16 tests), using hand-constructed toy `TestCase` fixtures with
known, deliberately-controlled outcomes as ground truth — not anything
derived from the Sephirotic engine.

---

## Two Break-It Proofs, Both Confirmed and Reverted

**Proof 1 — the honesty guard itself.** The guard's `if not testable:
return False` line was changed to fall through to the bare `all(...)`
call, so an empty testable list would vacuously return `True`. Running
`test_correspondence_ledger.py` against this broken version failed 2 of
16 tests (`test_all_untestable_ledger_does_not_report_success` and
`test_empty_ledger_does_not_report_success`), exactly the two tests
written specifically to catch this. Reverted; clean 16/16 pass confirmed
restored.

**Proof 2 — the real, previously-documented engine bug.**
`tifereth_reconciliation()` in `sephirotic_reward_engine.py` was changed
from `(chesed_weight * chesed_value) - (geburah_weight * geburah_value)`
to just `(chesed_weight * chesed_value)`, dropping the Geburah term
entirely — the exact bug already documented in
`test_sephirotic_reward_engine.py`'s own docstring as a
previously-performed break-it check. Running
`sephirotic_correspondence_ledger.py` against the broken engine produced:

```
[X] Tifereth  ->  SephiroticRewardComponents.tifereth_reconciliation()
    Status : FAILED
    Detail : failed sub-checks (4/5): test_low_chesed_high_geburah_gives_negative_reward,
             test_severe_geburah_dominates_large_chesed,
             test_reconciliation_is_sensitive_to_both_terms_independently,
             test_weights_control_relative_influence

[X] Chesed + Geburah -> Tifereth (integration)  ->  SephiroticRewardComponents.compute_reward()
    Status : FAILED
    Detail : failed sub-checks (1/3): test_crash_gives_negative_reward_regardless_of_prior_speed
```

Exit code `1`. Chesed and Geburah, whose validators don't touch
`tifereth_reconciliation()` at all, correctly stayed `VERIFIED` — the
break confined itself to exactly the correspondences whose underlying
tests actually exercise the broken function, which is itself a small
confirmation that the ledger's per-claim attribution is doing real work
rather than just reporting a single repo-wide pass/fail. Reverted; clean
4/5 VERIFIED, 1/5 UNTESTABLE, 0 FAILED, exit `0` confirmed restored.

---

## Why It Stays Out of `test_all_engines.py`'s Count

`test_all_engines.py` answers one specific question per entry: *does
this engine have a dedicated test that actually verifies it?* The answer
for `sephirotic_reward_engine.py` was already **yes**, independent of
whether the ledger exists — `test_sephirotic_reward_engine.py` was
written, break-it-proofed, and passing before the ledger was ever
conceived. Registering `sephirotic_correspondence_ledger.py` as a 24th
entry would make it look like a 24th *thing got verified*, when what
actually happened is that the same, already-complete verification got a
second, differently-organized presentation layered on top. Counting it
would be double-counting coverage the same way `test_production_engine_unit_tests.py`
already isn't folded into the main 23 for re-testing engines covered
individually elsewhere — same principle, applied one level deeper.

---

## A Second Validator Constructor: `from_script_exit_code()`

Everything above describes `from_unittest_methods()`, which requires the
underlying test file to be a `unittest.TestCase` with named methods to
select individually. Not every test file in this repo is written that
way — `test_ddpg_quadcopter_rca_engine.py` and `test_dht_rca_node.py` use
a simpler module-level `check()` / `PASS:` / `FAIL:` script style, run
top-to-bottom, exiting nonzero on any failure. There is no `TestCase`
class to instantiate a method on, so `from_unittest_methods()` cannot
wrap them.

`from_script_exit_code(script_path, args=None)` is the second validator
constructor, built for exactly this case:

```python
def validator() -> ValidationResult:
    cmd = [sys.executable, str(script_path)] + list(args or [])
    result = subprocess.run(cmd, capture_output=True, text=True,
                             cwd=str(script_path.parent), timeout=120)
    if result.returncode != 0:
        tail_lines = (result.stdout + result.stderr).strip().splitlines()[-5:]
        return ValidationResult(False, ...)
    return ValidationResult(True, f"{script_path.name} exited 0 (full script passed)")
```

It re-runs the whole script as a real subprocess — the same mechanism
`test_all_engines.py` already uses to invoke every engine's test file —
and treats the real exit code as ground truth. This is deliberately
**coarser than `from_unittest_methods()`**: a script like this has no
named sub-checks to select individually, so one `VERIFIED` here speaks
for everything the script's `check()` function tests (8 checks, in
`test_ddpg_quadcopter_rca_engine.py`'s case), not one isolated claim. The
worked example, `ddpg_correspondence_ledger.py`, says so explicitly in
its first entry's `claim` text rather than implying a granularity that
doesn't exist for this style of test.

That worked example was also, for a while, the first ledger in this
series to register a claim the evidence actually contradicted, on
purpose. Its second entry claims "the actor and critic networks are
genuinely trained end-to-end," backed by a custom validator (not
`from_script_exit_code`, since this particular claim needed a
snapshot-before/train/compare-after check that neither existing
constructor performs) that mirrors `test_ddpg_quadcopter_rca_engine.py`'s
own weight-change check. At the time this section was first written, only
`critic_out.W` ever received a gradient in `DDPGAgent.step()`, and
running the ledger reported that entry as `FAILED`, correctly, because
the claim was false — the point being that a correspondence ledger's job
is to say so plainly rather than only quietly in a code comment. That gap
is now fixed (real backprop through every layer of both networks; dated
correction in the module's own docstring and in `LIBER_0.md`), so the
entry now reports `VERIFIED` — the FAILED result isn't deleted from
history, it's on record in both of those places, precisely so a fixed gap
doesn't quietly read, to a later reader, as if it had never been real.

### Where the Discipline Bends

This validator is also the one place in the whole framework that breaks
this document's own opening rule — "Layer 2... does not call
`chesed_expansion_term()` itself... adds zero new facts." Every other
worked ledger's validator is built from `from_unittest_methods()`, which
only ever re-runs Layer 1's *existing* test methods; it never imports or
calls the engine (Layer 0) directly. `_validate_actor_critic_is_genuinely_trained()`
does exactly that: it constructs a real `DDPGAgent` and `QuadcopterTakeoffEnv`
and runs 40 real training steps, computing genuinely new evidence rather
than re-displaying Layer 1's. That's a deliberate, acknowledged exception
(no `from_unittest_methods()`-compatible method existed to reuse), not an
oversight — but it's worth naming plainly, because it's exactly the shape
of thing this document's own discipline exists to prevent: a Layer 2 that
can reach around Layer 1 and generate its own evidence is a Layer 2 that
could, in principle, rubber-stamp a claim `VERIFIED` without any
independent test ever having checked it.

It didn't, here — the claim it computed was true (backed independently by
`test_ddpg_quadcopter_rca_engine.py`'s own section 7). But until
2026-08-02, the one piece of *this validator's own logic* — the part that
decides whether a given weight snapshot counts as "changed" or
"unchanged" — had no dedicated correctness test of its own, unlike every
other piece of novel Layer 2 logic in this framework (`all_testable_passed()`
and `from_script_exit_code()` both have ground-truth tests in
`test_correspondence_ledger.py`). The comparison logic was pulled out into
its own function, `_classify_weight_changes(snapshot, agent)`, specifically
so it could be tested against hand-constructed fake agent objects with a
known-in-advance answer, independent of whether the real DDPGAgent's
training dynamics happen to be correct that day.
`test_ddpg_correspondence_ledger.py` (8 tests) is that test: exact-match,
clearly-different, multiple-independent-names, both sides of
`np.allclose`'s default tolerance boundary, a two-level dotted-path
resolution check, and one integration test against the real engine.
Break-it proof: the `unchanged`/`changed` branches of the classifier were
swapped; 7 of 8 tests failed for exactly that reason; reverted, confirmed
byte-identical via `diff`, full suite re-confirmed passing.

`from_script_exit_code()` has its own dedicated tests in
`test_correspondence_ledger.py`'s `TestFromScriptExitCode` class (4
tests, using hand-written throwaway scripts with known exit codes as
ground truth — not real repo scripts, so the expected outcome is
unambiguous by construction). Break-it proof performed: the
`!= 0` check was inverted to `== 0`; exactly those 4 new tests failed
and no others; reverted, confirmed byte-identical via `diff`, re-ran to
confirm the full suite passing again.

---

## Extending the Pattern to Other Engines

The framework in `correspondence_ledger.py` is generic and not wired to
anything Sephirotic-specific. The same four-step shape — external
pattern meets technical system, translation, adversarial validation,
explicit boundary clarification — has already been applied by hand
(without ledger code) in two other places in this repo, and both are
natural candidates for the same treatment if it's ever worth doing:

- **`standalone_rca_sandbox.py`** — its own test suite
  (`test_standalone_rca_sandbox.py`, 49 tests) already separates
  mechanically-tested claims (the cosine-similarity scoring formula, the
  Shannon-entropy directivity calculation, the regex rewriting rules, the
  learning engine's EMA weight update) from the one claim that has no
  validator and cannot have one: whether "Qualia vector" or "Sephirotic
  state" describe anything real about a user's actual mental state. A
  ledger here would look almost identical in shape to the reward-engine
  one: several `VERIFIED` rows wired to existing test methods, one
  `UNTESTABLE` row for the philosophical claim, registered with
  `validator=None` on purpose rather than omitted.
- **`studies/EXERCISES.md`'s Kabbalistic Lens** — this is prose, not
  code, so a ledger entry here would look different: the "validator"
  for something like "1.2 severs Yesod, the dispatch mechanism" is
  really `test_inheritance_upcasting_engine.py`'s existing dynamic-dispatch
  tests, which is the same reuse pattern `from_unittest_methods()` already
  supports. This one hasn't been built, since the workbook's `<details>`
  toggles already perform a lighter version of the same boundary-labeling
  job (every Kabbalistic Lens section is explicitly marked "optional,
  provisional metaphor") — but the ledger structure would be a strict
  upgrade if that boundary ever needed to be machine-checked rather than
  just visually flagged.

Building either of those is a genuine follow-up task, not something this
document is claiming has already happened.

---

## Files Referenced

- `correspondence_ledger.py` — the generic framework (`Correspondence`,
  `CorrespondenceLedger`, `from_unittest_methods`, `from_script_exit_code`,
  the honesty guard).
- `sephirotic_correspondence_ledger.py` — the worked example against
  `sephirotic_reward_engine.py`. 4 VERIFIED, 1 UNTESTABLE.
- `attractor_correspondence_ledger.py` — the worked example against
  `recursive_attractor_engine.py`. 6 VERIFIED, 1 UNTESTABLE (the Register
  C reading that consciousness itself is such a system).
- `rca_sandbox_gamma_correspondence_ledger.py` — the worked example
  against `standalone_rca_sandbox.py`'s `compute_gamma()`. 2 VERIFIED,
  1 UNTESTABLE (a cross-document identity claim against
  `agency-budget-spec.md`).
- `ddpg_correspondence_ledger.py` — the worked example against
  `ddpg_quadcopter_rca_engine.py`, and the `from_script_exit_code()`
  worked example. Its second entry was previously the first ledger in
  this series with a genuine `FAILED` entry (the actor-critic
  reconciliation gap); now VERIFIED, since that gradient-flow bug is
  fixed (dated correction in the module's own docstring, and in
  `LIBER_0.md`). Currently 2 VERIFIED, 1 UNTESTABLE. Its second entry's
  validator, `_validate_actor_critic_is_genuinely_trained()`, is also the
  one documented exception to this whole document's "Layer 2 never
  touches Layer 0 directly, adds zero new facts" rule (see
  **Where the Discipline Bends** above) — as of 2026-08-02, its
  comparison logic has its own dedicated ground-truth test,
  `test_ddpg_correspondence_ledger.py` (8 tests), closing what had been
  the one piece of novel Layer 2 logic in this framework without an
  independent correctness check of its own.
- `glyph_emotion_correspondence_ledger.py` — the worked example against
  the 100-Emotion Codex in `docs/glyph_correspondence_codex.md`, via
  `glyph_emotion_codex.py`'s parser. 1 VERIFIED (data fidelity to the
  source document), 3 UNTESTABLE (emotion detection from text, the
  qualia-vector mapping, and esoteric/planetary correspondence
  validity).
- `test_correspondence_ledger.py` — 20 tests of the framework itself
  (16 original + 4 for `from_script_exit_code()`), independent of any
  specific engine.
- `test_ddpg_correspondence_ledger.py` — 8 tests of
  `ddpg_correspondence_ledger.py`'s own custom validator logic
  (`_classify_weight_changes()`, hand-constructed fake-agent ground truth,
  plus one integration check against the real engine), independent of the
  generic framework tested above.
- `sephirotic_reward_engine.py` / `test_sephirotic_reward_engine.py`,
  `recursive_attractor_engine.py` / `test_recursive_attractor_engine.py`,
  `standalone_rca_sandbox.py` / `test_standalone_rca_sandbox.py`,
  `ddpg_quadcopter_rca_engine.py` / `test_ddpg_quadcopter_rca_engine.py`,
  `glyph_emotion_codex.py` / `test_glyph_emotion_codex.py` — Layer 0 and
  Layer 1 for each of the five worked examples above, unchanged by any
  of the ledger code itself.
- `run_all_correspondence_ledgers.py` — a Layer 3, not a sixth worked
  example: it doesn't add any new correspondence claims, it aggregates
  the five ledgers above into one command, the same relationship
  `test_all_engines.py` has to the individual engine tests. Its one
  piece of real logic (`KNOWN_EXPECTED_FAILURES`, distinguishing
  ddpg_correspondence_ledger.py's deliberate FAILED entry from a
  genuine regression) is covered by `test_run_all_correspondence_ledgers.py`
  (7 tests: hand-built toy ledgers for the classification logic, plus
  one integration test snapshotting the real ledgers' current baseline —
  22 total correspondences, currently 16 VERIFIED, 0 FAILED, 6 UNTESTABLE
  now that the DDPG actor-critic gap is fixed; see the note below on a
  separate, pre-existing, unrelated stale baseline assertion in that
  test file itself).

**VERIFIED per `TESTING_STANDARD.md` on 2026-07-30 (original framework),
2026-07-31 (`from_script_exit_code()` addition and the two additional
worked examples), 2026-07-31 (`run_all_correspondence_ledgers.py`), and
2026-08-02 (`_classify_weight_changes()` extracted and independently
tested — see **Where the Discipline Bends** above).**
Ground truth: the framework's own `test_correspondence_ledger.py` uses
hand-constructed toy `TestCase` fixtures and throwaway scripts with
known, deliberately-controlled pass/fail outcomes, and
`test_run_all_correspondence_ledgers.py` does the same with toy ledger
objects. Break-it checks performed: all five described in full above
(four in this document, one in `run_all_correspondence_ledgers.py`'s own
inverted-condition test), all reverted, all confirmed restored to a clean
state before this document was written/updated.

**A separate, pre-existing note, unrelated to this section's fix**:
`test_run_all_correspondence_ledgers.py`'s own
`test_real_ledgers_match_current_known_baseline` hardcodes
`total_verified == 15`; the real, current count is 16 (one correspondence
became VERIFIED sometime after that baseline was written, and the test
was never updated). Confirmed, via a clean clone of the commit before the
2026-08-02 `engines/`/`protocols`/`ledgers`/`tests` reorg, that this exact
mismatch already existed before that reorg — not a regression from it,
and out of scope for this document's fix to resolve quietly.

**Resolved 2026-11-09**: that baseline is now 16/0/6, updated deliberately with a
dated SECOND CORRECTION in the test's own docstring, which names the
correspondence that moved (the glyph ledger's qualia-vector mapping). The
note above is kept as written.
