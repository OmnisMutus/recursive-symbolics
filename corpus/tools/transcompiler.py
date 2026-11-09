"""
Cross-World Transcompiler & Recursive Meaning Loop Engine

Purpose: Translate a symbolic reading of an input (e.g. "anger -> Geburah")
into any other registered tradition's vocabulary, without ever asserting
that one tradition's reading is the "real" one underneath the others.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).parent
DEFAULT_SCHEMA_PATH = BASE_DIR / "symbolic_schema.json"


@dataclass
class TranslationResult:
    concept: str
    source_tradition: str
    source_reading: Optional[str]
    translations: Dict[str, Optional[str]]
    untranslated_traditions: List[str]
    caveat: str


class Transcompiler:
    """
    Reads symbolic_schema.json and translates a concept's reading
    between registered traditions.

    This class deliberately has no notion of "correct" or "default"
    tradition. Every call must specify which lens produced the input.
    """

    DEFAULT_CAVEAT = (
        "This is a translation between chosen symbolic conventions, "
        "not a claim that any tradition names the 'real' underlying thing. "
        "The concept is a peg; each tradition hangs its own coat on it."
    )

    def __init__(self, schema_path: Optional[str] = None):
        target_path = schema_path or str(DEFAULT_SCHEMA_PATH)
        with open(target_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        self.mapping = self.schema["abstract_mapping"]
        self.traditions = self.schema["traditions_registered"]

    def list_concepts(self) -> List[str]:
        return list(self.mapping.keys())

    def list_traditions(self) -> List[str]:
        return list(self.traditions)

    def translate(
        self,
        concept: str,
        source_tradition: str,
        target_traditions: Optional[List[str]] = None,
    ) -> TranslationResult:
        """
        Translate `concept` (as read through `source_tradition`)
        into `target_traditions` (default: all registered traditions).
        """
        if concept not in self.mapping:
            raise KeyError(
                f"Concept '{concept}' is not in the schema. "
                f"Available concepts: {self.list_concepts()}"
            )

        if source_tradition not in self.traditions:
            raise KeyError(
                f"Tradition '{source_tradition}' is not registered. "
                f"Available traditions: {self.traditions}"
            )

        entry = self.mapping[concept]
        source_reading = entry.get(source_tradition)

        targets = target_traditions or [
            t for t in self.traditions if t != source_tradition
        ]

        translations = {}
        untranslated = []

        for t in targets:
            reading = entry.get(t)
            translations[t] = reading
            if reading is None:
                untranslated.append(t)

        return TranslationResult(
            concept=concept,
            source_tradition=source_tradition,
            source_reading=source_reading,
            translations=translations,
            untranslated_traditions=untranslated,
            caveat=self.DEFAULT_CAVEAT,
        )

    def add_user_tradition_mapping(
        self, concept: str, tradition_name: str, reading: str
    ) -> None:
        """
        Allow a user to register their own reading for a concept under
        a tradition name (could be 'User_Defined' or a new named tradition).
        This is how the schema stays a "blank canvas" rather than a closed set.
        """
        if concept not in self.mapping:
            self.mapping[concept] = {t: None for t in self.traditions}

        if tradition_name not in self.traditions:
            self.traditions.append(tradition_name)
            for c in self.mapping:
                self.mapping[c].setdefault(tradition_name, None)

        self.mapping[concept][tradition_name] = reading

    def save_schema(self, path: Optional[str] = None) -> None:
        target_path = path or str(DEFAULT_SCHEMA_PATH)
        self.schema["abstract_mapping"] = self.mapping
        self.schema["traditions_registered"] = self.traditions
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.schema, f, indent=2, ensure_ascii=False)


@dataclass
class LoopEvent:
    """
    One full cycle of: Word -> Meaning -> Action -> Experience -> New Meaning
    """
    word: str
    tradition: str
    meaning_before: Optional[str]
    action_taken: str
    experience_reported: str
    meaning_after: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RecursiveMeaningLoop:
    """
    Tracks semantic drift for a given user's vocabulary over time.
    """

    def __init__(self):
        self.events: List[LoopEvent] = []

    def log_cycle(
        self,
        word: str,
        tradition: str,
        action_taken: str,
        experience_reported: str,
        meaning_after: str,
    ) -> LoopEvent:
        meaning_before = self._current_meaning(word, tradition)

        event = LoopEvent(
            word=word,
            tradition=tradition,
            meaning_before=meaning_before,
            action_taken=action_taken,
            experience_reported=experience_reported,
            meaning_after=meaning_after,
        )
        self.events.append(event)
        return event

    def _current_meaning(self, word: str, tradition: str) -> Optional[str]:
        relevant = [
            e for e in self.events if e.word == word and e.tradition == tradition
        ]
        if not relevant:
            return None
        return relevant[-1].meaning_after

    def semantic_drift(self, word: str, tradition: str) -> Dict[str, Any]:
        relevant = [
            e for e in self.events if e.word == word and e.tradition == tradition
        ]

        if not relevant:
            return {"word": word, "tradition": tradition, "history": [], "drifted": False}

        history = [
            {
                "timestamp": e.timestamp,
                "meaning_before": e.meaning_before,
                "action": e.action_taken,
                "experience": e.experience_reported,
                "meaning_after": e.meaning_after,
            }
            for e in relevant
        ]

        first_meaning = relevant[0].meaning_after
        last_meaning = relevant[-1].meaning_after
        drifted = first_meaning != last_meaning

        return {
            "word": word,
            "tradition": tradition,
            "cycles_logged": len(relevant),
            "first_meaning": first_meaning,
            "current_meaning": last_meaning,
            "drifted": drifted,
            "history": history,
        }

    def full_report(self) -> Dict[str, Any]:
        pairs = {(e.word, e.tradition) for e in self.events}
        return {
            f"{word} [{tradition}]": self.semantic_drift(word, tradition)
            for word, tradition in pairs
        }


if __name__ == "__main__":
    tc = Transcompiler()
    print("=== Transcompiler: 'anger' as read through Kabbalah ===")
    res = tc.translate("anger", source_tradition="Kabbalah")
    print(f"Source reading (Kabbalah): {res.source_reading}")
    for trad, rd in res.translations.items():
        print(f"  {trad:20s} -> {rd or '(untranslated)'}")
    print(f"Caveat: {res.caveat}\n")

    loop = RecursiveMeaningLoop()
    loop.log_cycle(
        word="discipline",
        tradition="Kabbalah",
        action_taken="Forced rigid schedule",
        experience_reported="Burned out by day 4",
        meaning_after="Discipline = self-punishment",
    )
    loop.log_cycle(
        word="discipline",
        tradition="Kabbalah",
        action_taken="Set flexible anchor practice",
        experience_reported="Sustained for 3 weeks",
        meaning_after="Discipline = a container that flexes",
    )

    drift_report = loop.semantic_drift("discipline", "Kabbalah")
    print("=== Semantic Drift Report ===")
    print(f"Drifted: {drift_report['drifted']}")
    print(f"First meaning:   {drift_report['first_meaning']}")
    print(f"Current meaning: {drift_report['current_meaning']}")
