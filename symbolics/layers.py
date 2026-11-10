"""The architecture index, checked.

`architecture/layers.json` says where each layer of the Sovereign Recursive Engine Architecture already
exists: which file, in which repository, and which test stands behind it. A list like that goes stale the day
after it is written, so this module reads it and looks. It is the same idea as the correspondence ledger, one
level up: a claim ("this layer is implemented by that file") either has something behind it or says that it
does not.

Each component gets one status:

    PRESENT     the file is there (and so is its evidence file, if it names one)
    MISSING     the index names a file that is not there. This is the failure.
    NOT_HERE    the file belongs to a sibling repository that is not on this machine, so nothing was checked

Each layer gets one status:

    COVERED     at least one component was found, and none is missing
    BROKEN      at least one component is MISSING
    GAP         the layer lists no components. A declared gap is honest and is not a failure.
    UNCHECKED   every component is NOT_HERE

And the guard the ledger uses: a run in which nothing could be checked does not pass.

`architecture/intent.json` is checked the same way. Every statement in it is a quotation with a source, and a
quotation that no longer appears in its source is a failure: the intent may not drift away from the words it
was taken from.

Run it:  python -m symbolics.layers
"""
import json
import os

PRESENT, MISSING, NOT_HERE = "PRESENT", "MISSING", "NOT_HERE"
COVERED, BROKEN, GAP, UNCHECKED = "COVERED", "BROKEN", "GAP", "UNCHECKED"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                      # this repository
THIS_REPO = "recursive-symbolics"
INDEX = os.path.join(REPO, "architecture", "layers.json")
INTENT = os.path.join(REPO, "architecture", "intent.json")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def repo_root(name, repo=REPO):
    """Where a named repository should be: this one, or a folder beside it with that name."""
    if name == THIS_REPO:
        return repo
    return os.path.join(os.path.dirname(repo), name)


def check_component(component, repo=REPO):
    """One component -> a row with a status. Looks at the disk and at nothing else."""
    root = repo_root(component["repo"], repo)
    row = dict(component)
    if not os.path.isdir(root):
        row["status"] = NOT_HERE
        row["detail"] = f"repository {component['repo']} is not on this machine"
        return row
    absent = [p for p in (component["path"], component.get("evidence"))
              if p and not os.path.exists(os.path.join(root, p))]
    if absent:
        row["status"] = MISSING
        row["detail"] = "not found: " + ", ".join(absent)
    else:
        row["status"] = PRESENT
        row["detail"] = ""
    return row


def check_layer(layer, repo=REPO):
    rows = [check_component(c, repo) for c in layer.get("components", [])]
    statuses = [r["status"] for r in rows]
    if not rows:
        status = GAP
    elif MISSING in statuses:
        status = BROKEN
    elif PRESENT in statuses:
        status = COVERED
    else:
        status = UNCHECKED
    return {"layer": layer["layer"], "role": layer.get("role", ""), "status": status,
            "components": rows, "gaps": list(layer.get("gaps", []))}


def check(index=None, repo=REPO):
    """The whole index. ok is False if anything is BROKEN, and False if nothing at all could be checked."""
    index = load(INDEX) if index is None else index
    layers = [check_layer(layer, repo) for layer in index.get("layers", [])]
    checked = sum(1 for layer in layers for r in layer["components"] if r["status"] in (PRESENT, MISSING))
    broken = [layer["layer"] for layer in layers if layer["status"] == BROKEN]
    return {"layers": layers, "checked": checked, "broken": broken,
            "ok": checked > 0 and not broken}


def _squash(text):
    """Collapse runs of whitespace, so a quotation still matches where its source wraps a line."""
    return " ".join(text.split())


def _quotations(intent):
    found = []
    if isinstance(intent.get("purpose"), dict):
        found.append(intent["purpose"])
    found.extend(q for q in intent.get("principles", []) if isinstance(q, dict))
    return found


def check_intent(intent=None, repo=REPO):
    """Every statement must still appear, word for word, in the document it names.

    Returns the state (RATIFIED or DRAFT), the quotations that drifted, and ok. A draft is reported as a
    draft and never as ratified; an intent with no statements in it is not ok.
    """
    intent = load(INTENT) if intent is None else intent
    drifted = []
    quotes = _quotations(intent)
    for q in quotes:
        source = os.path.join(repo, q.get("source", ""))
        try:
            with open(source, encoding="utf-8") as fh:
                body = _squash(fh.read())
        except OSError:
            drifted.append({"text": q.get("text", ""), "source": q.get("source", ""), "why": "source not found"})
            continue
        if not q.get("text") or _squash(q["text"]) not in body:
            drifted.append({"text": q.get("text", ""), "source": q.get("source", ""),
                            "why": "these words are no longer in the source"})
    ratified = (intent.get("ratified") is True and bool(intent.get("ratified_by"))
                and bool(intent.get("ratified_on")))
    return {"state": "RATIFIED" if ratified else "DRAFT", "statements": len(quotes),
            "drifted": drifted, "ok": bool(quotes) and not drifted}


def report(result, intent_result):
    lines = ["ARCHITECTURE INDEX", ""]
    for layer in result["layers"]:
        lines.append(f"  {layer['status']:<10} {layer['layer']}  ({layer['role']})")
        for r in layer["components"]:
            where = "" if r["repo"] == THIS_REPO else f"{r['repo']}: "
            note = f"   <- {r['detail']}" if r["detail"] else ""
            lines.append(f"      {r['status']:<9} {where}{r['path']}{note}")
        for gap in layer["gaps"]:
            lines.append(f"      gap       {gap}")
    lines += ["", f"  {result['checked']} component(s) looked for on disk."]
    if result["broken"]:
        lines.append("  BROKEN: " + ", ".join(result["broken"]))
    if result["checked"] == 0:
        lines.append("  Nothing could be checked. That is not a pass.")
    lines += ["", f"INTENT: {intent_result['state']}, {intent_result['statements']} statement(s) quoted from source."]
    for d in intent_result["drifted"]:
        lines.append(f"  DRIFTED  {d['source']}: \"{d['text']}\"  ({d['why']})")
    if intent_result["state"] == "DRAFT":
        lines.append("  Not ratified. Only the Maintainer ratifies: see how_to_ratify in architecture/intent.json.")
    lines += ["", f"INDEX OK: {result['ok']}    INTENT OK: {intent_result['ok']}"]
    return "\n".join(lines)


def main():
    result, intent_result = check(), check_intent()
    print(report(result, intent_result))
    return 0 if (result["ok"] and intent_result["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
