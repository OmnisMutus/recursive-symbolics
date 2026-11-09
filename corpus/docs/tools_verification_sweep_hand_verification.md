# Hand-Verification: The `Recursive-Symbolics/tools/` Sweep (14 Files, 9 Findings)

*Scope note: all files in this document live in the sibling
`Recursive-Symbolics/tools/` folder, not in this repo. Before this sweep,
that directory stood at 3 of 17 Python files VERIFIED (`delta_operator.py`,
`agency_budget.py`, `sephirotic_sorting.py` — see `LIBER_0.md`'s three
"Brought to VERIFIED" entries). This document, together with
`Recursive-Symbolics/tools/test_all_tools.py` (the master runner, modeled
directly on `../test_all_engines.py`'s `ENGINES`/`check_engine()` pattern),
is the closing artifact for bringing the remaining 14 files under the same
`TESTING_STANDARD.md` discipline: dedicated test file, independent ground
truth, completed and reverted break-it proof. Current state, reproducible
by running `test_all_tools.py` directly: 17 / 17 VERIFIED, 0 RAN_ONLY, 0
FAILED, 0 MISSING.*

*This is a hand-verification companion, not a replacement for the tests
themselves — same relationship as every other doc in this series has to
its corresponding `test_*.py` file. Given the number of files involved,
this single document covers all 14 rather than one doc per file; each
section below names its file and test file explicitly.*

---

## 1. `lookup.py` — Hebrew Gematria Lookup, Cross-Checked Against an External Standard

Independent ground truth: a `STANDARD_GEMATRIA` table transcribed from the
standard Hebrew gematria values (Aleph=1, Bet=2, ... Tav=400), external to
this repo entirely — not derived from `hermetic_qabalah.json`.

**Finding, hand-confirmed:** 21 of the 22 letters match the standard table
exactly. The one exception is **Kaf**: its stored `cipher_value` is `21`,
not the standard `20`. By hand: Kaf's `path_key_scale` in the same JSON
row is *also* `21` — the discrepancy is exactly one off from the standard
value, and exactly equal to a different field in its own row. This reads
like a transcription slip (copying the path-scale column into the
cipher-value column for that one row) rather than a random data error, but
the file itself was left untouched — this is reported as a discovered
data fact, not silently patched.

`test_lookup.py` (16 tests) pins this exactly:
`test_kaf_is_the_one_known_discrepancy` and
`test_kaf_discrepancy_is_exactly_one_off_and_equals_its_own_path_scale`.
Break-it proof: changed the unknown-letter fallback from `0` to `99`;
`test_cipher_value_unknown_letter_returns_zero` failed; reverted, byte-identical.

## 2. `symbolic_debugger.py` — A Real Keyword Collision, Confirmed by Hand

`detect_sephirah_from_text()` classifies free text by counting keyword
hits per sephirah. By hand-reading the keyword lists: **"earth" appears in
both Binah's and Malkuth's keyword lists.** Python dict construction means
whichever sephirah is defined *later* in the source silently overwrites
the earlier one's claim on that word during lookup-table construction —
Malkuth wins. Concretely: a text containing only the word "earth" and
nothing else will never be classified as Binah, even though "earth" is
listed as one of Binah's own keywords. Confirmed directly (not assumed)
via `test_binah_earth_keyword_is_therefore_unreachable_via_detect_counts`.

Also hand-confirmed: `balancing_rules` is asymmetric by design, not
oversight — Geburah balances to itself, Chesed balances to Geburah, but
Geburah does **not** balance back to Chesed. `test_geburah_balances_to_itself`
locks this in.

Entropy formula hand-computed independently for a locked-down case:
text `"a b a b"` → adjacent bigrams `("a","b"), ("b","a"), ("a","b")` → 2
unique pairs out of 3 total → entropy = 2/3 exactly, matching
`calculate_entropy()`'s output to the fraction, not just approximately.

`test_symbolic_debugger.py` (20 tests). Break-it proof: swapped
`most_common(1)[0][0]` for `most_common()[-1][0]` (least-common instead of
most-common sephirah); `test_dominant_is_the_highest_count_sephirah`
failed; reverted, byte-identical.

## 3. `ritual_compiler.py` — A Genuine Three-Way Tie, Not a Single "Correct" Path

Independent ground truth: `reference_bfs_shortest_path()`, a from-scratch
breadth-first search over a freshly-parsed adjacency list (using
`collections.deque`, never calling the file's own `a_star()`).

**Finding, hand-traced on the real Tree-of-Life path graph in
`symbolic_api.json`:** the shortest Kether→Malkuth path is 3 hops, but it
is genuinely **three-way tied** — Tiphareth connects directly to Netzach,
Yesod, *and* Hod, and each of those three connects directly to Malkuth.
There is no single mathematically-preferred answer to "the shortest path"
here; there are three, all equally short.

The two implementations resolve the tie differently, and both resolutions
are traced by hand:
- `a_star()` uses Python's `heapq`, which tie-breaks equal-priority tuples
  by comparing the next element — the *node name string*. Alphabetically,
  `"Hod" < "Netzach" < "Yesod"`, so `a_star()` deterministically picks the
  **Hod** route.
- The independent FIFO-BFS reference ties by **insertion order** into the
  adjacency dict (which lists Netzach before Yesod before Hod for
  Tiphareth's neighbors), so it deterministically picks the **Netzach**
  route.

Both are valid answers to "a shortest path"; neither is more "correct"
than the other, and asserting either one as *the* unique answer would have
been a false claim caught only by building an independent reference and
comparing. `test_all_three_of_tiphareths_children_connect_directly_to_malkuth`,
`test_reference_bfs_ties_by_insertion_order_and_picks_netzach`,
`test_a_star_ties_by_heapq_tuple_order_and_picks_hod`, and
`test_all_three_tied_routes_are_independently_confirmed_valid` all lock
this in explicitly rather than leaving it as an implicit assumption.

`test_ritual_compiler.py` (16 tests). Break-it proof: made the goal-check
return `path[:-1]` instead of `path` (silently dropping the final node);
5 tests failed across every layer that touches path output; reverted,
byte-identical.

## 4. `feedback_ingester.py` — A Regex That Can Never Match Its Real Upstream Data

`parse_metrics_from_text()` extracts a "Dominant: X" pattern via regex
requiring the literal string `"Dominant:"`. Hand-checked against
`symbolic_debugger.py`'s *actual* CLI output format (traced directly from
its print statements, not assumed): the real output is
`"Dominant Sephirah : {dom}"` — different label text, different spacing
around the colon. **These two strings never match.** Any real pipeline
that feeds `symbolic_debugger.py`'s console output into
`feedback_ingester.py`'s parser will silently get `dominant=None` on every
call, forever, with no error raised. `test_discovered_mismatch_against_
symbolic_debuggers_real_cli_output` asserts this exact failure mode
directly against the real-format string, rather than only testing the
parser against strings that happen to already match its own regex.

`test_feedback_ingester.py` (20 tests). Break-it proof: replaced the
email-redaction regex line with `pass`; 3 tests failed; reverted, byte-identical.

## 5. `transcompiler.py` — A Real, Dangerous `save_schema(path=None)` Footgun

**This one was caught the hard way.** An early draft of
`test_save_schema_defaults_to_original_path` called
`transcompiler.save_schema()` with no arguments, assuming it would target
the loaded fixture schema. It did not — it overwrote the real
`symbolic_schema.json` in place (confirmed directly: `schema_name` became
`"test_schema"`, concept count dropped from 6 to 2). Restored immediately
via `git show HEAD:tools/symbolic_schema.json > symbolic_schema.json`,
confirmed byte-identical via `diff`.

Root cause, traced by hand through `Transcompiler.__init__` and
`save_schema()`: the class never stores the path it was constructed with
(there is no `self.schema_path`). `save_schema(path=None)` falls back to
the **hardcoded module-level constant** `DEFAULT_SCHEMA_PATH`, not the
instance's actual source file. Any code that loads a schema from one
location and calls `save_schema()` with no argument, expecting a
round-trip save, will silently write to the module's hardcoded default
location instead — exactly the mistake the first test draft made. The
rewritten test,
`test_save_schema_with_no_path_targets_the_module_default_not_the_loaded_file`,
monkeypatches `DEFAULT_SCHEMA_PATH` itself to a decoy temp path for the
test's duration and documents this behavior as the real (if surprising)
contract, rather than papering over the incident.

`test_transcompiler.py` (20 tests). Break-it proof: in `translate()`,
dropped the `if reading is None: untranslated.append(t)` branch;
`test_translate_default_targets_excludes_source` failed; reverted, byte-identical.

## 6. `telemetry_analyzer.py` — A Third, Independently-Different "Symbolic Entropy" Formula

Hand-confirmed there are now **three genuinely different formulas** in
this codebase that all get called some variant of "symbolic entropy":
`standalone_rca_sandbox.py`'s `H_emotional` (word-frequency Shannon
entropy over free text), `symbolic_debugger.calculate_entropy()`
(fraction of *unique adjacent word pairs*), and this file's
`calc_symbolic_entropy()` (fraction of *unique words* over *total words*,
no adjacency at all). `test_is_a_different_formula_than_symbolic_
debuggers_entropy` demonstrates this concretely: a hand-picked input
string produces different outputs from the two formulas, not merely
different code paths that happen to agree numerically. Treating these as
interchangeable anywhere in this codebase would be a real conflation.

Boundary tests for `classify_latency`/`classify_entropy` hand-verified at
each threshold (0.5, 3.0, 0.6, 0.85) — both sides of each cutoff checked
explicitly, not just interior points.

`test_telemetry_analyzer.py` (18 tests). Break-it proof: changed
`ratio < 0.5` to `ratio < 0.05`; 2 tests failed; reverted, byte-identical.
(A pre-existing, unrelated uncommitted diff in `community_dataset.jsonl`/
`global_attractor_report.json`, dated 2026-07-28 — before this session —
was investigated and confirmed unrelated to this test run via `git log`
and content grep, not assumed.)

## 7. `embed_audio_signature.py` — No Bugs Found; Every Sample Matched by Hand

Independent ground truth: `reference_sample(t, duration_sec)`, re-deriving
the exact sine-wave formula from scratch (anchor frequency 164.81 Hz,
Tartini frequency 145.0 Hz, harmonic 432.0 Hz, plus the fade envelope) —
not calling the module's own synthesis function.
`test_every_sample_matches_independent_reference_exactly` compares
**every single sample** of a real generated WAV file (read back via
Python's `wave` module) against this independent reference. All matched.
JPEG COM-marker byte sequences hand-derived via `struct.pack('>H',
comment_length)` for both the fresh-embed and marker-deduplication cases.

`test_embed_audio_signature.py` (9 tests). Break-it proof: changed the
marker-removal slice from `data[idx+2+prev_len:]` to `data[idx+1+prev_len:]`
(an off-by-one); `test_deduplicates_a_pre_existing_com_marker` failed;
reverted, byte-identical.

## 8. `scan_anomaly.py` — An Unanchored Regex That Accepts Lookalike Domains

`construct_pages_url()` validates a GitHub Pages URL via regex. Hand-
confirmed the pattern is **unanchored**: `"https://not-github.com/foo/bar"`
contains the substring `"github.com/foo/bar"`, so it matches and the
function proceeds as if it were a real `github.com` URL, rather than
raising `ValueError` as a stricter, anchored pattern would.
`test_discovered_unanchored_regex_matches_lookalike_domains` confirms this
directly with that exact lookalike string.

`test_scan_anomaly.py` (13 tests, using `unittest.mock.patch` on
`urllib.request.urlopen` for the crawler paths). Break-it proof: dropped
the base64-clue check from an `and` condition in `crawl_site()`;
`test_missing_hidden_clue_is_flagged` failed; reverted, byte-identical.

## 9. `rca_llm_sandbox.py` — One More Directive Pattern Than Its Sibling Reimplementation

Cross-checked directly against `solo/standalone_rca_sandbox.py` (imported
via `sys.path.insert`, guarded by `@unittest.skipUnless`) since both files
independently implement the same two ideas. `sanitize_paths()` is
confirmed identical between the two. `apply_epistemic_humility()` is
**not**: `rca_llm_sandbox.py` has 5 directive-language replacement
patterns (including `"This is the correct interpretation"` →
`"One compelling interpretation is"`), while `standalone_rca_sandbox.py`
has only 4 — the fifth pattern exists in one file and not its sibling.
Neither file is "wrong" on its own terms, but treating them as
interchangeable would miss a real, confirmed difference in coverage.

Also hand-confirmed: this sandbox environment has no local Ollama daemon
running. `test_real_environment_has_no_ollama_running` is deliberately
left **unmocked** (every other HTTP test in the file mocks
`urllib.request.urlopen`) and completed in ~0.012s total across the whole
file — fast enough to confirm a real immediate connection-refused, not a
timeout being mistaken for "no server."

`test_rca_llm_sandbox.py` (17 tests). Break-it proof: changed `gamma <=
0.70` to `gamma <= 0.95`; 4 tests failed; reverted. Note: `rca_llm_sandbox.py`
is confirmed untracked by git (`git status --short` shows `?? tools/
rca_llm_sandbox.py`), so a byte-identical-to-HEAD check wasn't available
for the revert; verified instead via `grep -c "BREAK-IT"` (0 matches) and
direct inspection of the restored line.

## 10. `telemetry_service.py`, `debugger.py`, `add_meta.py`, `glossary_generator.py`, `simulate_telemetry.py` — Five More Files, One More Real Discovery, One Real Non-Finding, One Sandbox False Alarm

- **`telemetry_service.py`** (8 tests): a real `HTTPServer` is spun up on
  an ephemeral port (port 0) on a background thread and driven with real
  `http.client` requests — 200/400/404/OPTIONS-CORS all confirmed against
  a real running server, not a mocked one. No bugs found.

- **`debugger.py`** (9 tests): the first run of every test touching
  `run_self_tests()` failed with `PermissionError` on file cleanup. Traced
  to a **sandbox-specific mount restriction** (confirmed via a direct
  side experiment: even a file freshly created in the same process in the
  same directory could not be unlinked), not a bug in `debugger.py` —
  fixed by granting delete permission on the mounted folder, after which
  all 9 tests passed with zero changes to the source file. Documented
  explicitly as a false alarm rather than silently attributed to the code.

- **`add_meta.py`** (6 tests, run via `runpy.run_path` since the script
  has no functions): **real discovered bug** —
  `test_pre_existing_meta_content_survives_unchanged` proves that
  re-running this migration script against a file that already has a
  `"meta"` key leaves that key completely unchanged, silently, because
  `new_data.update(data)` overwrites the freshly-built meta dict back with
  the old one — despite the script's own comment claiming to insert fresh
  meta at the top. `test_raises_keyerror_when_metadata_key_absent`
  confirms a second real failure mode: the unconditional
  `new_data["metadata"]["version"] = "1.1.0"` line crashes with `KeyError`
  if no `"metadata"` key exists at all. The real `symbolic_api.json` was
  confirmed to already be past this migration (`version: "1.1.0"`, a
  `"meta"` key present) — i.e. this script has already done its one real
  job; these are latent bugs in a script that won't be re-run against
  fresh data, not active production issues.

- **`glossary_generator.py`** (9 tests): pure deterministic markdown
  generation over already-existing `symbolic_api.json` data. Every real
  sephirah name and path ID/label confirmed present in generated output.
  No bugs found.

- **`simulate_telemetry.py`** (4 tests): documented explicitly as
  fixture-generator infrastructure (feeds `telemetry_analyzer.py`'s tests),
  not a claim-bearing engine. **Real non-finding, reported honestly rather
  than hidden:** a break-it proof that removed `entries.sort(...)`
  entirely left every test passing, because main()'s four hardcoded
  synthetic users' time blocks are already inserted in strictly
  chronological order — the sort call is real and correctly written, but
  is currently a no-op against its own hardcoded data. It would matter if
  the per-user blocks were ever reordered; it just isn't exercised as
  written today.

## 11. The `test_all_tools.py` Build Itself — A Stale-Bytecode False Alarm, Not Two New Bugs

Building the master runner (`Recursive-Symbolics/tools/test_all_tools.py`,
modeled on `../test_all_engines.py`) surfaced what looked like two brand
new regressions: a fresh run reported `test_agency_budget.py` and
`test_sephirotic_sorting.py` — both previously-VERIFIED, previously
100%-passing files — **FAILING**, with `agency_budget.compute_gamma([100,
-100,-100])` returning `0.95` instead of the hard-capped `0.85`.

Traced by hand before concluding anything: an inline copy-pasted version
of the exact same function, run in the same process against the same
input, correctly returned `0.85`. `ab.compute_gamma.__code__.co_filename`
and `co_firstlineno` confirmed Python was executing the real source file,
at the right line — yet the imported module's behavior differed from an
identical inline copy. The actual cause: a **stale `__pycache__/*.pyc`
file** left over from this session's earlier rapid edit → test → revert
break-it-proof cycles, whose cached bytecode encoded an intermediate
(uncapped or differently-capped) version of `compute_gamma()` from partway
through a prior break-it proof. Because the edit-and-revert cycle happened
fast enough that the source file's mtime coincided with the stale `.pyc`'s
recorded mtime (same second), Python's cache-invalidation check judged the
stale bytecode still valid and used it instead of recompiling.

Deleting `__pycache__` entirely and re-running confirmed both files pass
cleanly (19/19 and 14/14 respectively) — genuinely 17/17 VERIFIED, not 15/17.
This is reported as a real incident, not smoothed over, because it's a
second, independent instance (after the `debugger.py` unlink-PermissionError
episode) of a sandbox/tooling artifact initially looking exactly like a
real code regression, and the discipline of tracing it by hand before
believing it is the same discipline this whole verification project is
built on.

`main()`'s truncate-on-import side effect on `Recursive-Symbolics/tools/
trace-log.txt` (documented in `debugger.py`'s own test docstring) fired
again during this diagnostic run, since `test_debugger.py` was re-executed
as part of `test_all_tools.py`; the real log file was restored again via
`git show HEAD:tools/trace-log.txt > tools/trace-log.txt`, confirmed
byte-identical afterward.

---

## Summary Table

| File | Tests | Real finding? |
|---|---|---|
| `lookup.py` | 16 | Kaf gematria data error |
| `symbolic_debugger.py` | 20 | "earth" keyword collision; asymmetric balancing rule |
| `ritual_compiler.py` | 16 | Genuine 3-way tied shortest path; heapq vs. FIFO divergence |
| `feedback_ingester.py` | 20 | Regex can never match real upstream CLI format |
| `transcompiler.py` | 20 | `save_schema(path=None)` targets hardcoded default, not loaded file |
| `telemetry_analyzer.py` | 18 | Third, independently-different "entropy" formula |
| `embed_audio_signature.py` | 9 | None found |
| `scan_anomaly.py` | 13 | Unanchored regex accepts lookalike domains |
| `rca_llm_sandbox.py` | 17 | One more directive pattern than its sibling reimplementation |
| `telemetry_service.py` | 8 | None found |
| `debugger.py` | 9 | Sandbox false alarm (not a code bug) |
| `add_meta.py` | 6 | Silent meta-overwrite bug; unconditional KeyError path |
| `glossary_generator.py` | 9 | None found |
| `simulate_telemetry.py` | 4 | Sort call is currently a no-op (non-finding, honestly reported) |
| `test_all_tools.py` build | — | Stale-bytecode false alarm (sandbox artifact, not a code bug) |

185 new tests across 14 files, all passing, all with completed and
reverted break-it proofs. Combined with the 3 pre-existing VERIFIED files,
`Recursive-Symbolics/tools/` now stands at 17 / 17 — reproducible directly
via `python test_all_tools.py`, not just cited here.

---

## Provenance

Closes the gap identified in the "Second/Third File Outside `solo/`
Brought to VERIFIED" `LIBER_0.md` entries, which explicitly logged the
remaining un-surveyed files in `Recursive-Symbolics/tools/` as the next
concrete step. This document and `test_all_tools.py` are that step,
completed in one sweep rather than one file at a time.
