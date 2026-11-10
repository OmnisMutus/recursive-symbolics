"""Immune memory, checked: every recorded breach names the test that now guards against it.

The Principle of Recursive Validation says a challenge should leave the system with a clearer structure, the
way an immune system keeps a memory of what it met. LIBER_0.md already records each breach. What nothing
checked, until this module, was the second half: that the record of having been wrong is tied to something
that would catch the same mistake again.

A breach is an entry in LIBER_0.md whose **Result:** line carries the status word CORRECTED or FAILED.
Each one gets a status here:

    GUARDED     it names at least one guard, and every guard it names exists
    WAIVED      it says, with a reason, that no test can guard it. Counted and shown, never hidden.
    UNGUARDED   it names nothing. This is a failure: the breach left no memory.
    BROKEN      it names a guard that is not there (the file, or the test inside it). This is a failure.

A guard is written `path/to/file.py::test_name`, or just `path/to/file` for a guard that is a whole file.
It can be given in two places:

  - in the entry itself, on a line beginning `**Guard:**` (several guards separated by commas; or
    `**Guard:** none: <reason>` for a waiver). This is the way for new entries.
  - in `architecture/guards.json`, keyed by the entry's heading. This exists because entries are never edited
    after they are written: an old entry gets its guard recorded beside the record, not inside it.

A guard recorded for a heading that is not in LIBER_0.md is BROKEN too: a memory of nothing.

"Exists" means the file is on disk and, when a test is named, the file contains `def <test_name>(`. It does
not mean the test passes: run the suite for that. It does not mean the test is the right one: that judgement
is a person's, and is why a waiver needs a reason someone can read.

Run it:  python -m symbolics.breaches
"""
import json
import os
import re

GUARDED, WAIVED, UNGUARDED, BROKEN = "GUARDED", "WAIVED", "UNGUARDED", "BROKEN"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RECORD = os.path.join(REPO, "LIBER_0.md")
SIDECAR = os.path.join(REPO, "architecture", "guards.json")

BREACH_WORDS = re.compile(r"\b(CORRECTED|FAILED)\b")       # status words, upper case only, on the Result line
_RESULT = re.compile(r"^\*\*Result:\*\*(.*)$", re.M)
_GUARD = re.compile(r"^\*\*Guard:\*\*(.*)$", re.M)
_WAIVER = re.compile(r"^\s*none\s*[:.-]\s*(.*)$", re.I | re.S)


def entries(text):
    """LIBER_0 text -> [(heading, body)], one per `### ` heading after the `## Entries` line."""
    if "## Entries" not in text:
        return []
    body = text.split("## Entries", 1)[1]
    found = []
    for chunk in re.split(r"(?m)^### ", body)[1:]:
        heading, _, rest = chunk.partition("\n")
        found.append((heading.strip(), rest))
    return found


def is_breach(body):
    result = _RESULT.search(body)
    return bool(result and BREACH_WORDS.search(result.group(1)))


def _inline(body):
    """The entry's own **Guard:** line -> (guards, waiver reason). Either may be empty."""
    line = _GUARD.search(body)
    if not line:
        return [], ""
    value = line.group(1).strip()
    waiver = _WAIVER.match(value)
    if waiver:
        return [], waiver.group(1).strip()
    return [g.strip().strip("`") for g in value.split(",") if g.strip().strip("`")], ""


def guard_exists(guard, repo=REPO):
    """'path::test' or 'path' -> (True, '') or (False, why)."""
    path, _, test = guard.partition("::")
    full = os.path.join(repo, path.strip())
    if not path.strip() or not os.path.isfile(full):
        return False, f"no such file: {path.strip() or '(empty)'}"
    if test.strip():
        with open(full, encoding="utf-8", errors="replace") as fh:
            if not re.search(r"\bdef\s+" + re.escape(test.strip()) + r"\s*\(", fh.read()):
                return False, f"{path.strip()} has no test named {test.strip()}"
    return True, ""


def check(text=None, sidecar=None, repo=REPO):
    """Every breach entry, with its status. ok is False on any UNGUARDED or BROKEN row, and False when the
    record could not be read as entries at all (a parser that finds nothing has checked nothing)."""
    if text is None:
        with open(os.path.join(repo, "LIBER_0.md"), encoding="utf-8") as fh:
            text = fh.read()
    if sidecar is None:
        path = os.path.join(repo, "architecture", "guards.json")
        sidecar = {"guards": []}
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                sidecar = json.load(fh)
    beside = {row["entry"]: row for row in sidecar.get("guards", [])}

    all_entries = entries(text)
    headings = {heading for heading, _ in all_entries}
    rows = []
    for heading, body in all_entries:
        if not is_breach(body):
            continue
        guards, reason = _inline(body)
        extra = beside.get(heading, {})
        guards = guards + [g for g in extra.get("guards", []) if g not in guards]
        reason = reason or str(extra.get("waived", "")).strip()
        problems = [why for ok, why in (guard_exists(g, repo) for g in guards) if not ok]
        if problems:
            status, detail = BROKEN, "; ".join(problems)
        elif guards:
            status, detail = GUARDED, ""
        elif reason:
            status, detail = WAIVED, reason
        else:
            status, detail = UNGUARDED, "names no guard and no reason"
        rows.append({"entry": heading, "status": status, "guards": guards, "detail": detail})
    for heading in beside:
        if heading not in headings:
            rows.append({"entry": heading, "status": BROKEN, "guards": [],
                         "detail": "architecture/guards.json names an entry that is not in LIBER_0.md"})
    count = {s: sum(1 for r in rows if r["status"] == s) for s in (GUARDED, WAIVED, UNGUARDED, BROKEN)}
    return {"entries": len(all_entries), "rows": rows, "count": count,
            "ok": bool(all_entries) and count[UNGUARDED] == 0 and count[BROKEN] == 0}


def report(result):
    lines = ["IMMUNE MEMORY: does every recorded breach name what now guards against it?", ""]
    for row in result["rows"]:
        lines.append(f"  {row['status']:<9} {row['entry']}")
        for guard in row["guards"]:
            lines.append(f"              {guard}")
        if row["detail"]:
            lines.append(f"              {'reason' if row['status'] == WAIVED else '<-'}: {row['detail']}")
    c = result["count"]
    lines += ["", f"  {result['entries']} entries read, {len(result['rows'])} breach row(s): "
                  f"{c[GUARDED]} guarded, {c[WAIVED]} waived, {c[UNGUARDED]} unguarded, {c[BROKEN]} broken."]
    if not result["entries"]:
        lines.append("  No entries could be read from the record. Nothing was checked, and that is not a pass.")
    lines += ["  Guarded means the named test exists. Whether it passes is the suite's answer, not this one's.",
              "", f"MEMORY OK: {result['ok']}"]
    return "\n".join(lines)


def main():
    result = check()
    print(report(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
