"""What is about to be published, read before it is.

On 2026-11-09 this repository's working tree was cleaned of absolute local paths (they carried a Windows
username) and the fix was committed on top. The tree was clean and the push was not: the commit that added the
paths and the commit that removed them would both have travelled, and the paths would have stayed readable in
public history. See LIBER_0.md for that day.

The lesson was that the thing to check before a push is not the files on disk. It is every commit that will
travel: its patch, removed lines included, and its message. This module is that check.

    python -m symbolics.outgoing

It reads `git log -p` for the commits ahead of the upstream branch (or the whole history if there is no
upstream yet) and reports any absolute path into a user's home folder. It reads local git only and reaches no
network.

A name is not flagged when it is an obvious placeholder (`testuser`, `<name>`, `user`, ...): the test fixtures
here use such paths on purpose, to prove a sanitiser redacts them.
"""
import re
import subprocess

# Names that are placeholders, not people. Lower case.
NEUTRAL = {"testuser", "user", "username", "name", "you", "me", "example", "someuser", "somebody",
           "public", "default", "shared", "runner"}

_NAME = r"([^\\/\s\"'`<>()\[\]{},;:*?|]+)"
PATTERNS = [
    # C:\Users\name, C:/Users/name, c:/Users/name (also inside file:///c:/Users/name)
    re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+" + _NAME),
    # file:///Users/name, file:///home/name
    re.compile(r"file:/+(?:Users|home)/" + _NAME),
    # /Users/name or /home/name standing by itself, not the tail of a URL or of a longer path
    re.compile(r"(?<![\w.:/\\-])/(?:Users|home)/" + _NAME),
]


def scan(text):
    """Every home-folder path in the text, as (line number, name, the line). Placeholders are skipped."""
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        seen = set()
        for pattern in PATTERNS:
            for match in pattern.finditer(line):
                name = match.group(1).replace("%20", " ").strip(".")
                if not name or name.lower() in NEUTRAL or name in seen:
                    continue
                seen.add(name)
                hits.append((number, name, line.strip()))
    return hits


def _git(args, cwd):
    done = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return done.returncode, done.stdout


def outgoing_range(cwd="."):
    """The commits that a push would send: upstream..HEAD, or everything when no upstream is set."""
    code, upstream = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd)
    if code == 0 and upstream.strip():
        return upstream.strip() + "..HEAD", f"commits ahead of {upstream.strip()}"
    return "HEAD", "no upstream branch: the whole history"


def check(cwd="."):
    """Scan what would be pushed. ok is False on any hit, and False if git could not be read at all."""
    rng, described = outgoing_range(cwd)
    code, count = _git(["rev-list", "--count", rng], cwd)
    if code != 0:
        return {"ok": False, "readable": False, "scope": described, "commits": 0, "hits": []}
    code, log = _git(["log", "-p", "--format=commit %h%n%B", rng], cwd)
    if code != 0:
        return {"ok": False, "readable": False, "scope": described, "commits": 0, "hits": []}
    hits = scan(log)
    return {"ok": not hits, "readable": True, "scope": described, "commits": int(count.strip() or 0),
            "hits": hits}


def report(result):
    if not result["readable"]:
        return "OUTGOING: git could not be read here. Nothing was checked, and that is not a pass."
    lines = [f"OUTGOING: {result['commits']} commit(s), {result['scope']}."]
    if result["commits"] == 0:
        lines.append("  Nothing is waiting to be pushed.")
    for number, name, line in result["hits"]:
        lines.append(f"  HOME PATH  name '{name}'  (log line {number}): {line[:110]}")
    lines.append("  CLEAN: no home-folder path in any patch or message." if result["ok"]
                 else f"  {len(result['hits'])} hit(s). Do not push until these are out of the HISTORY, not only the files.")
    return "\n".join(lines)


def main():
    result = check()
    print(report(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
