"""One runner for the whole corpus, reporting what the suites actually said.

It replaces reading either `test_all_engines.py` or `test_all_tools.py` as the suite's result. Those are
per-component rollups: useful for seeing which engine is which, wrong as a count. `test_all_engines.py` covers
24 engines out of 57 test files, and it scores a missing-dependency skip as a correctness failure, so a real
failure elsewhere in the corpus never appears in its summary. Both of those happened, in that order, on
2026-11-09.

Two formats are read, because the corpus has two:

- unittest's own summary ("Ran N tests", then OK or FAILED with its counts);
- the hand-rolled scripts that print "SUMMARY: N passed, M failed". Seven files use this, and a reader that
  knows only unittest silently omits them. A format not understood is an omission, not a safe refusal.

A verdict is withheld unless it is unambiguous. GREEN needs checks that ran and nothing else at all, including
no skips, because a skip is not a verification and this project's own standard says so. UNCLEAR is a result:
nothing collected, any skip, any expected failure, any unexpected success, a missing dependency, a clean count
with a nonzero exit, or output in neither known format. Expected failures matter most, since a registered known
gap is not a regression, and treating one as breakage is how working code gets "fixed".

    python corpus/run_corpus.py [--quiet]
"""
import glob
import os
import re
import subprocess
import sys

GREEN, RED, UNCLEAR = "GREEN", "RED", "UNCLEAR"
RAN = re.compile(r"^Ran (\d+) tests? in ", re.M)
OK = re.compile(r"^OK(?:\s*\((.*)\))?\s*$", re.M)
FAILED = re.compile(r"^FAILED\s*\((.*)\)\s*$", re.M)
COUNT = re.compile(r"(failures|errors|skipped|expected failures|unexpected successes)=(\d+)")
OWN = re.compile(r"^\s*SUMMARY:\s*(\d+)\s+passed,\s*(\d+)\s+failed", re.M)
MISSING = re.compile(r"ModuleNotFoundError: No module named '([^']+)'")
NO_TESTS = re.compile(r"^NO TESTS RAN", re.M)
# The environment refusing an operation is not the code failing. tools/debugger.py's self-test calls
# Path.unlink() on its own temporary file; a mount that denies deletion makes it report three failures, and
# the same files in a writable directory pass. Scoring that RED blames working code for where it was run.
DENIED = re.compile(r"(?:PermissionError|OSError).{0,80}?(?:Operation not permitted|Permission denied|"
                    r"Read-only file system)|\[Errno (?:1|13|30)\]", re.S)
FIELDS = ("failures", "errors", "skipped", "expected failures", "unexpected successes")

# (glob, the directory to run from). Each group runs the way its own tests expect to be run.
GROUPS = (("tests/test_*.py", "."), ("tools/test_*.py", "tools"), ("arch/test_*.py", "arch"))
ROLLUPS = {"test_all_tools.py", "test_all_engines.py"}


def read(text, exit_code):
    out = {k: 0 for k in FIELDS}
    out["ran"] = 0
    ran, own = RAN.search(text), OWN.search(text)
    tail = FAILED.search(text) or OK.search(text)
    if ran:
        out["ran"] = int(ran.group(1))
        if tail and tail.group(1):
            for name, number in COUNT.findall(tail.group(1)):
                out[name] = int(number)
    elif own:
        out["ran"] = int(own.group(1)) + int(own.group(2))
        out["failures"] = int(own.group(2))
    out["exit_code"] = exit_code
    out["deps"] = sorted(set(MISSING.findall(text)))
    out["denied"] = bool(DENIED.search(text))
    out["format"] = "unittest" if ran else ("own summary" if own else "unreadable")
    out["no_tests"] = bool(NO_TESTS.search(text))
    return out


def verdict(p):
    if p["no_tests"]:
        return UNCLEAR, "collected no tests"
    if p["format"] == "unreadable":
        return UNCLEAR, "output in neither known format, so its own verdict is unknown"
    if p["ran"] == 0:
        return UNCLEAR, "zero checks ran"
    if p["expected failures"]:
        return UNCLEAR, f"{p['expected failures']} expected failure(s): a registered gap is not a regression"
    if p["unexpected successes"]:
        return UNCLEAR, f"{p['unexpected successes']} unexpected success(es): a recorded gap may have closed"
    if p["denied"]:
        return UNCLEAR, ("the environment refused an operation (permission, read-only or no-delete), so this "
                         "describes where it ran, not the code")
    if p["deps"]:
        return UNCLEAR, "absent here, so this describes the machine: " + ", ".join(p["deps"])
    if p["skipped"]:
        return UNCLEAR, f"{p['skipped']} skipped, and a skip is not a verification"
    if p["failures"] or p["errors"]:
        return RED, f"{p['failures']} failure(s), {p['errors']} error(s)"
    if p["exit_code"]:
        return UNCLEAR, f"every count clean but exited {p['exit_code']}, so the runner has a rule of its own"
    return GREEN, f"{p['ran']} check(s), nothing failed, nothing skipped"


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    quiet = "--quiet" in argv
    here = os.path.dirname(os.path.abspath(__file__))
    totals = {k: 0 for k in FIELDS}
    totals["ran"] = 0
    counts, rows = {}, []
    for pattern, cwd in GROUPS:
        for path in sorted(glob.glob(os.path.join(here, pattern))):
            if os.path.basename(path) in ROLLUPS:
                continue
            run_in = os.path.join(here, cwd)
            try:
                done = subprocess.run([sys.executable, os.path.relpath(path, run_in)], cwd=run_in,
                                      capture_output=True, text=True, timeout=900)
                text, code = (done.stderr or "") + (done.stdout or ""), done.returncode
            except subprocess.TimeoutExpired:
                text, code = "", 1
            p = read(text, code)
            kind, why = verdict(p)
            for k in totals:
                totals[k] += p.get(k, 0)
            counts[kind] = counts.get(kind, 0) + 1
            rows.append((kind, os.path.relpath(path, here), why, p["format"]))
    print("=" * 78)
    print("CORPUS", " ".join(f"{k}={v}" for k, v in totals.items()))
    print("files:", " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("=" * 78)
    for kind, name, why, fmt in rows:
        if kind != GREEN or not quiet:
            print(f"  {kind:8} {name[:52]:<54} {why}")
    print("=" * 78)
    print("The honest claim this run supports:")
    print(f"  {totals['ran']} check(s) ran across {len(rows)} file(s). {counts.get(GREEN, 0)} file(s) are")
    print(f"  unambiguously clean. {counts.get(RED, 0)} failed. {counts.get(UNCLEAR, 0)} did not say enough")
    print("  to score, which is a result and not a pass: read those before concluding anything.")
    return 1 if counts.get(RED) else 0


if __name__ == "__main__":
    sys.exit(main())
