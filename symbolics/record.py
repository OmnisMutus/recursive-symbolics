"""The record is only added to. Checked, not promised.

LIBER_0.md is the record, and nothing here writes to it: entries are added by Void alone, and once written they
are not edited. This module checks the first half of that from the outside - that the file's git history only
ever adds lines, never changes or deletes one.

The intent says: "Corrections to the record are new entries, never edits that erase what was believed before.
The one exception is removing what must not be kept, such as a key or a private path, and the removal is itself
recorded as an entry." On 2026-11-08, before anything checked this, six lines of older entries were reworded in
place (commit fc60f51).

Because the record is never edited, a historical edit cannot be excused by a line written inside it. It is named
from the outside, in architecture/guards.json, under "record_edits":

    "record_edits": {"accepted": [{"commit": "fc60f51", "why": "..."}]}

An edit the history shows is accepted only when its commit is named there (7 to 40 hex characters, matched by
prefix). Every other changed or deleted line, committed or not, is a breach the check reports. This is the same
way symbolics/breaches.py records a guard for an entry that can no longer be edited: beside the record, never
inside it.

    python -m symbolics.record

It reads local git and architecture/guards.json only, and reaches no network.
"""
import difflib
import json
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = "LIBER_0.md"
GUARDS = os.path.join("architecture", "guards.json")


def _lines(text):
    return [l.rstrip() for l in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def erased(old, new):
    """Lines of `old` that `new` changed or deleted, in order. Pure additions return []."""
    a, b = _lines(old), _lines(new)
    out = []
    for op, i1, i2, _j1, _j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("replace", "delete"):
            out += [l for l in a[i1:i2] if l.strip()] or ["(blank lines)"]
    return out


def accepted(repo=REPO):
    """Commits named as accepted in-place edits in architecture/guards.json, under record_edits.accepted.
    The record is never edited, so a historical edit is named here, beside the record, never inside it."""
    try:
        with open(os.path.join(repo, GUARDS), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return set()
    out = set()
    for e in data.get("record_edits", {}).get("accepted", []):
        sha = e.get("commit", "") if isinstance(e, dict) else str(e)
        if sha:
            out.add(sha.strip())
    return out


def _covered(sha, names):
    return any(len(n) >= 7 and sha.startswith(n) for n in names)


def _git(args, cwd):
    done = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return done.returncode, done.stdout


class Unreadable(Exception):
    pass


def _show(cwd, rev, path):
    """The file as it was at `rev`. A failure to read is an error, never an empty file: an empty read would
    compare as "nothing changed" and pass. (cat-file, not show: show fails on some mounted drives.)"""
    code, listed = _git(["ls-tree", rev, "--", path], cwd)
    if code != 0:
        raise Unreadable(f"git could not read the tree at {rev[:7]}")
    if not listed.strip():
        return ""                                     # the file did not exist yet: everything after is added
    code, out = _git(["cat-file", "-p", f"{rev}:{path}"], cwd)
    if code != 0:
        raise Unreadable(f"git could not read {path} at {rev[:7]}")
    return out


def check(repo=REPO, path=RECORD):
    """{ok, edits: [{commit, subject, lines, recorded}], uncommitted: [lines]}. ok is False on any edit
    the guards do not name, or on any uncommitted edit (it has no commit to name yet)."""
    code, out = _git(["log", "--format=%H%x09%s", "--", path], repo)
    if code != 0:
        return {"ok": False, "edits": [], "uncommitted": [], "error": "not a git repository, or git failed"}
    try:
        with open(os.path.join(repo, path), encoding="utf-8") as fh:
            current = fh.read()
    except OSError:
        return {"ok": False, "edits": [], "uncommitted": [], "error": f"{path} not found"}
    names = accepted(repo)
    edits = []
    try:
        return _walk(repo, path, out, current, names, edits)
    except Unreadable as e:
        return {"ok": False, "edits": edits, "uncommitted": [], "error": str(e)}


def _walk(repo, path, out, current, names, edits):
    for row in out.splitlines():
        sha, _, subject = row.partition("\t")
        code, parents = _git(["rev-list", "--parents", "-n", "1", sha], repo)
        parent = parents.split()[1] if len(parents.split()) > 1 else None
        if not parent:
            continue                                  # the commit that created the file only added
        lines = erased(_show(repo, parent, path), _show(repo, sha, path))
        if lines:
            edits.append({"commit": sha[:7], "subject": subject, "lines": lines, "recorded": _covered(sha, names)})
    uncommitted = erased(_show(repo, "HEAD", path), current) if out.strip() else []
    ok = all(e["recorded"] for e in edits) and not uncommitted
    return {"ok": ok, "edits": edits, "uncommitted": uncommitted}


def report(result):
    lines = [f"RECORD: is {RECORD} only ever added to?", ""]
    if result.get("error"):
        lines.append(f"  {result['error']}")
    for e in result["edits"]:
        lines.append(f"  {'RECORDED' if e['recorded'] else 'ERASED  '}  {e['commit']}  {e['subject']}"
                     f"  ({len(e['lines'])} line(s) changed or removed)")
    if result["uncommitted"]:
        lines.append(f"  ERASED    (uncommitted)  {len(result['uncommitted'])} line(s) changed or removed")
    if not result["edits"] and not result["uncommitted"] and not result.get("error"):
        lines.append("  Every commit only added lines.")
    lines += ["", f"RECORD OK: {result['ok']}"]
    if not result["ok"]:
        lines.append('  An edit is accepted only when its commit is named in architecture/guards.json'
                     ' under record_edits.accepted.')
    return "\n".join(lines)


def main():
    result = check()
    print(report(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
