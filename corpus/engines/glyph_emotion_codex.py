#!/usr/bin/env python3
"""
glyph_emotion_codex.py
Read-only accessor for the 100-Emotion Codex table in
docs/glyph_correspondence_codex.md.

This is deliberately NOT a classifier. It does not detect which emotion
a piece of text expresses -- see glyph_emotion_correspondence_ledger.py's
still-UNTESTABLE "Emotion Detection From Text" entry for why: doing that
would require inventing ~100 keyword lists with no independent ground
truth to check them against.

UPDATE (2026-08-01): the OTHER claim this docstring used to make here --
that nothing maps the qualia vector's 4 continuous values onto any of
these 100 emotions -- is no longer true project-wide, though it remains
true of THIS file specifically. That mapping is now built in
qualia_emotion_classifier.py, WITHOUT inventing a per-emotion signature
(see that module's docstring and docs/qualia_emotion_classifier_hand_
verification.md for exactly how). This file's job stays unchanged: parse
the table, nothing more.

What this module DOES do: parse the canonical markdown table directly
out of docs/glyph_correspondence_codex.md, rather than maintaining a
separate hand-copied Python literal of the same 100 rows. That's a
deliberate choice, not laziness -- a hand-transcribed copy is exactly
the kind of thing that silently drifts from its source over time (the
same failure mode this repo's other correspondence work already guards
against by cross-testing hardcoded hex values against document text,
e.g. test_standalone_rca_sandbox.py's
test_hex_values_match_uploaded_codex_document_exactly). Parsing the
document directly at call time makes that drift structurally
impossible here instead of merely caught by a test.
"""

import re
from pathlib import Path

DOCS_PATH = Path(__file__).parent.parent / "docs" / "glyph_correspondence_codex.md"

_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(#[0-9a-fA-F]{6})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$"
)


def load_emotion_codex(docs_path: Path = DOCS_PATH) -> list:
    """Parses the '100-Emotion Codex' table out of the given markdown
    file. Returns a list of dicts (index, name, hex, esoteric,
    description), one per row, in table order.

    Raises ValueError if the section can't be found, or if parsing
    doesn't yield exactly 100 rows -- a silent partial parse would be
    a worse failure mode than a loud one, since a caller iterating over
    a wrong-length list would never notice on its own."""
    text = docs_path.read_text(encoding="utf-8")
    if "100-Emotion Codex" not in text:
        raise ValueError(f"'100-Emotion Codex' section not found in {docs_path}")

    section = text.split("100-Emotion Codex", 1)[1]
    rows = []
    for line in section.splitlines():
        stripped = line.strip()
        m = _ROW_RE.match(stripped)
        if m:
            index, name, hex_color, esoteric, description = m.groups()
            rows.append({
                "index": int(index),
                "name": name,
                "hex": hex_color.lower(),
                "esoteric": esoteric,
                "description": description,
            })
        elif rows and stripped.startswith("---"):
            break  # end of this table's section

    if len(rows) != 100:
        raise ValueError(
            f"Expected exactly 100 emotion rows, parsed {len(rows)} from "
            f"{docs_path} -- the table format may have changed."
        )
    return rows


if __name__ == "__main__":
    rows = load_emotion_codex()
    print(f"Parsed {len(rows)} emotion rows from {DOCS_PATH}")
    print(f"  First : #{rows[0]['index']} {rows[0]['name']} ({rows[0]['hex']})")
    print(f"  Last  : #{rows[-1]['index']} {rows[-1]['name']} ({rows[-1]['hex']})")
