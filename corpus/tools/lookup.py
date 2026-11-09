import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
JSON_PATH = BASE_DIR / "hermetic_qabalah.json"

with JSON_PATH.open("r", encoding="utf-8") as f:
    _DATA = json.load(f)["hermetic_qabalah_cipher"]

def lookup(letter: str) -> dict:
    """Return the full row for a Hebrew letter."""
    return _DATA.get(letter, {})

def cipher_value(letter: str) -> int:
    """Return the cipher value for a Hebrew letter."""
    row = lookup(letter)
    return row.get("cipher_value", 0)

def by_tarot(query: str) -> dict:
    """Search entries by Tarot trump keyword."""
    query = query.lower()
    matches = {}
    for letter, row in _DATA.items():
        if query in row.get("tarot_trump", "").lower():
            matches[letter] = row
    return matches

def by_element(query: str) -> dict:
    """Search entries by element/planet/sefirah keyword."""
    query = query.lower()
    matches = {}
    for letter, row in _DATA.items():
        if query in row.get("element_planet_sefirah", "").lower():
            matches[letter] = row
    return matches

if __name__ == "__main__":
    sample = lookup("ש")
    print("Shin Lookup:", sample)
