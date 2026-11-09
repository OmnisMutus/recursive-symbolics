#!/usr/bin/env python3  
# -*- coding: utf-8 -*-

"""  
Full-stack debugger for the Hermetic Qabalah / Δ-operator project.

Features  
--------  
* Auto-loads:  
    - hermetic_qabalah.json  
    - lookup.py (Python lookup module)  
    - delta_operator.py (γ / directive_strength logic)  
    - feedback_ingester.py (logging of feedback)  
* Decorates every public function with detailed logging.  
* Interactive command-line interface (REPL) for ad-hoc testing.  
* Generates a comprehensive trace log (trace-log.txt).

Usage  
-----  
$ python debugger.py           # starts REPL  
$ python debugger.py test      # runs built-in sanity test suite  
"""

import json  
import logging  
import os  
import sys  
import traceback  
from pathlib import Path  
from typing import Any, Callable, Dict, List, Tuple

# ----------------------------------------------------------------------  
# 0️⃣  Basic logger configuration  
# ----------------------------------------------------------------------  
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

LOG_FILE = Path(__file__).parent / "trace-log.txt"  
logging.basicConfig(  
    level=logging.DEBUG,  
    format="%(asctime)s | %(levelname)8s | %(message)s",  
    handlers=[  
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),  
        logging.StreamHandler(sys.stdout),  
    ],  
)  
log = logging.getLogger("debugger")

# ----------------------------------------------------------------------  
# 1️⃣  Helper: simple decorator that logs calls & results  
# ----------------------------------------------------------------------  
def logged(fn: Callable) -> Callable:  
    """Wrap a function so that entry/exit + arguments are logged."""

    def wrapper(*args, **kwargs):  
        arg_str = ", ".join(  
            [repr(a) for a in args]  
            + [f"{k}={v!r}" for k, v in kwargs.items()]  
        )  
        log.debug(f"CALL -> {fn.__name__}({arg_str})")  
        try:  
            result = fn(*args, **kwargs)  
            log.debug(f"RETURN <- {fn.__name__} -> {result!r}")  
            return result  
        except Exception as exc:  
            log.error(  
                f"EXCEPTION in {fn.__name__}: {exc!r}\n{traceback.format_exc()}"  
            )  
            raise

    wrapper.__name__ = fn.__name__  
    wrapper.__doc__ = fn.__doc__  
    return wrapper

  
# ----------------------------------------------------------------------  
# 2️⃣  Load data files (JSON + lookup module)  
# ----------------------------------------------------------------------  
BASE_DIR = Path(__file__).parent

JSON_PATH = BASE_DIR / "hermetic_qabalah.json"  
if not JSON_PATH.is_file():  
    log.error(f"Missing JSON mapping at {JSON_PATH}")  
    sys.exit(1)

with JSON_PATH.open("r", encoding="utf-8") as f:  
    QABALAH_DATA = json.load(f)

if "hermetic_qabalah_cipher" not in QABALAH_DATA:  
    log.error("JSON file malformed – missing `hermetic_qabalah_cipher` key")  
    sys.exit(1)

CIPHER = QABALAH_DATA["hermetic_qabalah_cipher"]  
log.info(f"Loaded {len(CIPHER)} cipher entries from {JSON_PATH.name}")

# ----------------------------------------------------------------------  
# 3️⃣  Import local Python helper modules  
# ----------------------------------------------------------------------  
sys.path.insert(0, str(BASE_DIR))

try:  
    import lookup as lookup_mod  
except Exception as exc:  
    log.error(f"Could not import lookup.py – {exc}")  
    sys.exit(1)

try:  
    import delta_operator as delta_mod  
except Exception as exc:  
    log.error(f"Could not import delta_operator.py – {exc}")  
    sys.exit(1)

try:  
    import feedback_ingester as feedback_mod  
except Exception as exc:  
    log.error(f"Could not import feedback_ingester.py – {exc}")  
    sys.exit(1)

# ----------------------------------------------------------------------  
# 4️⃣  Wrap public functions with the logger  
# ----------------------------------------------------------------------  
lookup = logged(lookup_mod.lookup)  
cipher_value = logged(lookup_mod.cipher_value)  
by_tarot = logged(lookup_mod.by_tarot)  
by_element = logged(lookup_mod.by_element)

compute_gamma = logged(delta_mod.compute_gamma)  
enrich_response = logged(delta_mod.enrich_response)

ingest_feedback = logged(feedback_mod.ingest_feedback)

# ----------------------------------------------------------------------  
# 5️⃣  Sanity-check utilities  
# ----------------------------------------------------------------------  
def _check_unique_letters() -> None:  
    """Ensure no duplicate Hebrew letters exist in the mapping."""  
    duplicates = [l for l, cnt in  
                  [(letter, list(CIPHER.keys()).count(letter)) for letter in CIPHER]  
                  if cnt > 1]  
    if duplicates:  
        raise ValueError(f"Duplicate letters found: {duplicates}")  
    log.debug("No duplicate letters in JSON mapping.")

  
def _check_value_ranges() -> None:  
    """Validate that numeric fields are within expected bounds."""  
    for letter, info in CIPHER.items():  
        cv = info["cipher_value"]  
        if not (1 <= cv <= 400):  
            raise ValueError(f"Cipher value out of range for {letter}: {cv}")  
        path = info["path_key_scale"]  
        if not (11 <= path <= 32):  
            raise ValueError(f"Path key scale out of range for {letter}: {path}")  
    log.debug("All numeric ranges look healthy.")

  
def run_self_tests() -> bool:  
    """Run a quick end-to-end sanity suite."""  
    try:  
        log.info("[START] Running self-test suite...")  
        _check_unique_letters()  
        _check_value_ranges()

        # 1. Test lookup round-trip  
        sample_letter = "ש"  
        row = lookup(sample_letter)  
        assert row["name"] == "Shin"  
        assert row["cipher_value"] == 300

        # 2. Test gamma calculation  
        logits = [2.0, 1.0, 0.5]  
        gamma = compute_gamma(logits)  
        assert 0.0 <= gamma <= 1.0

        # 3. Test enrich_response integration  
        payload = enrich_response(  
            content="Demo response",  
            logits=logits,  
            alternatives=3,  
            confidence_entropy=0.23,  
            agency_attribution_index=0.7,  
            post_dialogue_score=0.85,  
        )  
        assert "directive_strength" in payload["sovereignty_metadata"]  
        assert payload["sovereignty_metadata"]["directive_strength"] == gamma

        # 4. Test feedback ingestion  
        tmp_log = BASE_DIR / "temp_feedback_log.jsonl"  
        if tmp_log.exists():  
            tmp_log.unlink()  
            
        feedback_mod.DATASET_PATH = tmp_log  
        ingest_feedback(  
            content="Test feedback prompt payload",  
            source_type="self_test",  
            dry_run=False  
        )  
        assert tmp_log.is_file() and tmp_log.stat().st_size > 0  
        tmp_log.unlink()  
        log.info("[SUCCESS] Self-test suite passed.")  
        return True  
    except Exception as exc:  
        log.error(f"Self-test failure: {exc}\n{traceback.format_exc()}")  
        return False

  
# ----------------------------------------------------------------------  
# 6️⃣  Interactive REPL  
# ----------------------------------------------------------------------  
def repl() -> None:  
    """Very small REPL that forwards commands to the wrapped functions."""  
    banner = """  
🦑  🐙  Karen-Plankton Debug REPL  
Commands (type `help` for details):  
  lookup <letter>                 → full row for a Hebrew letter  
  cipher <letter>                 → numeric cipher value  
  tarot <search-term>             → letters whose Tarot trump matches  
  element <search-term>           → letters whose element/planet matches  
  gamma <logit1,logit2,…>         → compute directive_strength (γ)  
  enrich <content> <logits> …     → run enrich_response (comma-separated logits)  
  test                            → run built-in sanity suite  
  quit / exit                     → leave REPL  
"""  
    print(banner)  
    while True:  
        try:  
            raw = input("debug> ").strip()  
        except (EOFError, KeyboardInterrupt):  
            print("\nBye.")  
            break

        if not raw:  
            continue  
        cmd, *args = raw.split()  
        cmd = cmd.lower()

        if cmd in ("quit", "exit"):  
            break  
        elif cmd == "help":  
            print(banner)  
        elif cmd == "lookup" and args:  
            print(lookup(args[0]))  
        elif cmd == "cipher" and args:  
            print(cipher_value(args[0]))  
        elif cmd == "tarot" and args:  
            print(by_tarot(" ".join(args)))  
        elif cmd == "element" and args:  
            print(by_element(" ".join(args)))  
        elif cmd == "gamma" and args:  
            try:  
                logits = [float(x) for x in " ".join(args).split(",")]  
                print(compute_gamma(logits))  
            except ValueError:  
                print("Invalid logits – use comma-separated numbers")  
        elif cmd == "enrich" and len(args) >= 2:  
            content = args[0]  
            logits = [float(x) for x in args[1].split(",")]  
            print(  
                enrich_response(  
                    content=content,  
                    logits=logits,  
                    alternatives=3,  
                    confidence_entropy=0.0,  
                    agency_attribution_index=0.5,  
                )  
            )  
        elif cmd == "test":  
            run_self_tests()  
        else:  
            print(f"Unknown / malformed command: {raw}")

# ----------------------------------------------------------------------  
# 7️⃣  Main entry point  
# ----------------------------------------------------------------------  
if __name__ == "__main__":  
    if len(sys.argv) > 1 and sys.argv[1] == "test":  
        success = run_self_tests()  
        sys.exit(0 if success else 1)  
    else:  
        repl()  
