# Hand-Verifying `qualia_emotion_classifier.py`

This closes the gap `glyph_emotion_correspondence_ledger.py` registered
as UNTESTABLE since the 100-Emotion Codex was first uploaded: mapping
`standalone_rca_sandbox.py`'s 4-dimensional qualia vector (`Phi_somatic`,
`H_emotional`, `Delta_gamma`, `Tau_resonance`) onto one of the codex's
100 named emotions. The original refusal to build this was correct at
the time -- doing it honestly requires NOT inventing a per-emotion
signature. This module doesn't invent one; every number it uses already
existed in this repo (`SEPHIROT_CENTROIDS`, `SEPHIRAH_PLANET_COLOR`, each
emotion's own gradient hex) or is a standard transform (RGB->HSL).

This file takes `compute_sephirotic_vector_scores()` and
`compute_qualia_vector()`'s own correctness as given -- both are
pre-existing and already covered by `test_standalone_rca_sandbox.py`.
What's hand-verified here is the NEW logic layered on top: the
Esoteric-column parser, the sephirah bucketing, the two distance
measures, and the two nearest-neighbor selections.

---

## 1. Stage 1 — Reference Signatures Are Self-Description, Not Invention

`sephirah_reference_qualia(seph)` runs `SEPHIROT_CENTROIDS[seph]`'s own
words through the exact same scoring pipeline any real input text goes
through. With `LEARNING_ENGINE` weights at their default (1.0 — true for
a fresh engine, and true of this repo's actual `rca_memory.json` as of
this writing), direct computation gives:

```
Tifereth -> Phi_somatic=0.0  H_emotional=1.0  Delta_gamma=0.0   Tau_resonance=0.875
Yesod    -> Phi_somatic=0.0  H_emotional=1.0  Delta_gamma=0.0   Tau_resonance=0.3
Hod      -> Phi_somatic=0.0  H_emotional=1.0  Delta_gamma=0.0   Tau_resonance=0.375
Netzach  -> Phi_somatic=0.0  H_emotional=1.0  Delta_gamma=0.0   Tau_resonance=0.3
Geburah  -> Phi_somatic=0.0  H_emotional=1.0  Delta_gamma=1.0   Tau_resonance=0.3
Chesed   -> Phi_somatic=0.0  H_emotional=1.0  Delta_gamma=1.0   Tau_resonance=0.3
Binah    -> Phi_somatic=0.0  H_emotional=1.0  Delta_gamma=0.15  Tau_resonance=0.3
```

**A discovered limitation, documented rather than hidden**: Geburah's
and Chesed's reference vectors are *exactly identical*. `Delta_gamma` is
defined as `abs(Geburah_score - Chesed_score)` — an absolute value, so
it throws away *which side* the imbalance is on. Geburah's own text
scores `(Geburah=1.0, Chesed=0.0)`; Chesed's own text scores the mirror
image, `(Geburah=0.0, Chesed=1.0)`. Both produce `Delta_gamma = 1.0`.
Combined with `H_emotional=1.0` (both centroid lists are all-distinct
words) and `Tau_resonance=0.3` (neither list touches Tifereth/Keter
words), the two full vectors collide. `Phi_somatic=0.0` for all seven
listed above for the same reason — none of these six centroid lists
touch Malkuth vocabulary either.

This collision is harmless in practice only because Chesed's bucket is
independently empty (see Section 3) and therefore never a candidate —
but it is a real, checked property of `compute_qualia_vector()`'s
existing `Delta_gamma` formula, not something introduced or fixed by
this module. `test_geburah_and_chesed_self_references_collide` locks
this in explicitly rather than letting a future reader discover it as a
surprise.

## 2. Stage 1 — Distance, By Hand

`qualia_distance(a, b)` is plain Euclidean distance over the 4
dimensions. For `a = {Phi:0, H:1, Delta:1, Tau:0.3}` (Geburah's/Chesed's
reference) and `b = {Phi:0, H:1, Delta:0, Tau:0.875}` (Tifereth's):

```
diff = (0-0, 1-1, 1-0, 0.3-0.875) = (0, 0, 1.0, -0.575)
d = sqrt(0^2 + 0^2 + 1.0^2 + 0.575^2)
  = sqrt(1 + 0.330625)
  = sqrt(1.330625)
  ≈ 1.15353
```

Checkable on any calculator with a square-root key. `test_hand_computed_distance` locks this exact value in.

## 3. Stage 1 — The Empty Bucket, Confirmed Not Assumed

`grep -c "Jupiter" docs/glyph_correspondence_codex.md` inside the
100-Emotion Codex table returns zero matches in the Esoteric column —
confirmed directly against the document, not assumed from the Planets
table's existence. `emotions_by_sephirah()` therefore produces an empty
list for Chesed, and `nearest_sephirah()` explicitly excludes any
sephirah with an empty bucket from its candidate set — the same
discipline `SEPHIRAH_PLANET_COLOR`'s own comment already applies to
Keter/Chokmah/Daath/Malkuth for lacking a planetary color. Text whose
qualia vector is closest to Chesed's reference (an inherently
Chesed-shaped input, e.g. `"expansion flow abundance grace generous
kindness mercy growth open"`) is *not* invented an emotion — it routes
to whichever covered sephirah is nearest among the six real candidates
(in practice, Geburah, per the collision in Section 1).

Two emotions (#90 Madness, #91 Chaos) name Uranus/Spirit — outside the 7
planets `SEPHIRAH_PLANET_COLOR` covers — and are likewise left
`uncovered`, confirmed by `test_madness_and_chaos_are_uncovered`.

## 4. Stage 2 — HSL Lightness, By Hand

`hex_lightness()` uses the standard RGB→HSL transform:
`L = (max(r,g,b) + min(r,g,b)) / 2`, on channels normalized to `[0,1]`.

- `#ffffff` → r=g=b=1.0 → `L = (1.0+1.0)/2 = 1.0`
- `#000000` → r=g=b=0.0 → `L = (0.0+0.0)/2 = 0.0`
- `#ff0000` → r=1.0, g=b=0.0 → `L = (1.0+0.0)/2 = 0.5`
- `#808080` → r=g=b=128/255 ≈ 0.50196 → since max=min, `L = 128/255` exactly

All four are checkable by hand or calculator; `test_hex_lightness`
confirms Python's `colorsys.rgb_to_hls()` agrees with each.

**Why Tau_resonance, specifically, drives Stage 2**:
`Tau_resonance` is already documented (see
`docs/rca_sandbox_gamma_kabbalistic_hand_verification.md`) as measuring
alignment with the harmonizing/resonant sephirot (Tifereth, Keter). The
codex's own color choices independently run light-to-dark from its most
vital emotion (#1 Ecstasy, `#ffef8a`, `L≈0.90`) to its most annihilating
one (#100 Annihilation, `#000000`, `L=0.0`) — a real, pre-existing
property of the document's own data (confirmed directly:
`test_ecstasy_is_lighter_than_annihilation`), not a new judgment
invented per emotion. Treating lightness as a resonance proxy is a
**stated design choice** built on that existing property, not a claim
that this correlation holds perfectly across all 100 rows (it wasn't
exhaustively checked row-by-row, only anchored at these spot values).

## 5. Break-It Proofs Performed

Two deliberate bugs were introduced, run against the full 35-test suite,
confirmed to fail for the stated reason, and reverted (confirmed
byte-identical via a `grep -c "BREAK-IT"` check returning 0 afterward):

1. **Dropped the empty-bucket filter** in `nearest_sephirah()`
   (`candidates = [seph for seph in rca.SEPHIRAH_PLANET_COLOR]`, no
   `.get(seph)` check). Result: `test_raises_if_no_candidates_have_emotions`
   failed as expected (no candidates ever raises `ValueError` again,
   since `SEPHIRAH_PLANET_COLOR` itself is never empty). Notably,
   `test_excludes_chesed_even_when_it_would_be_the_exact_match` did
   **not** fail under this bug — because Section 1's Geburah/Chesed
   collision means Python's `min()` still picks Geburah first on a tie
   (dict iteration order: Geburah precedes Chesed in
   `SEPHIRAH_PLANET_COLOR`). This is itself an honest finding, not a
   test-suite gap: the guard clause IS still needed (a qualia vector
   that's closer to Chesed's reference than to any other real
   candidate's would misroute without it), it's just that this
   particular constructed test case couldn't distinguish the two paths
   due to the same collision documented above.
2. **Swapped `min` for `max`** in `nearest_emotion_in_bucket()`.
   Result: `test_hand_constructed_bucket` failed exactly as expected
   (`'Dark One' != 'Light One'`), confirming the nearest-neighbor
   selection is real and load-bearing, not a no-op.

## 6. What This Does NOT Claim

Per `docs/fixed_point_closure_and_the_y_combinator.md` §1's three-register
distinction: this file's algorithm — Euclidean distance, RGB→HSL,
bucket-then-refine — is Register B, checked above and by
`test_qualia_emotion_classifier.py`'s 35 tests. Whether Mars "truly"
governs Anger, whether Geburah "truly" opposes Chesed, or whether
resonance "truly" tracks color lightness for a human reader, is Register
A — traditional/textual/design correspondence, exactly as
`glyph_emotion_correspondence_ledger.py`'s separate "Esoteric / Planetary
Correspondence Validity" entry already states and continues to leave
UNTESTABLE. Nothing in this module claims to detect what emotion a piece
of text "really" expresses (that harder claim — a keyword classifier —
remains the separate, still-UNTESTABLE "Emotion Detection From Text"
entry in the same ledger).

---

## Provenance

Built in response to the explicit request to wire the qualia vector's
"translation of emotions into algorithm" through to the 100-Emotion
Codex's existing hex data, after clarifying that this required a new,
principled design (not a keyword classifier, and not silently forcing a
per-emotion signature) — see `LIBER_0.md`'s entry on this feature for
the fuller design discussion.
