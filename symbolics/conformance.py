"""The Conformance Suite the licence points at.

Articles 6, 8 and 9 of the licence put duties on a running system rather than on a promise in a README, so they
need something a reader can run. This is it: a small set of checks over an implementation, reporting one row per
duty with a status, in the same spirit as the correspondence ledger it sits beside.

    PASS             checked, and it held
    FAIL             checked, and it did not hold
    NOT_IMPLEMENTED  the thing this duty is about does not exist here yet

And the same honesty guard the ledger uses: a run in which nothing could be checked does not pass. A suite of
NOT_IMPLEMENTED rows reporting success would be exactly the failure mode the licence is trying to close.

Run it:  python -m symbolics.conformance
"""
import ast
import os

PASS, FAIL, NOT_IMPLEMENTED = "PASS", "FAIL", "NOT_IMPLEMENTED"

HERE = os.path.dirname(os.path.abspath(__file__))
# Article 9: nothing about a person's state leaves the machine. The strongest version of that is a package that
# cannot reach the network at all, which is checkable by reading the source rather than by trusting it.
NETWORK = {"socket", "ssl", "http", "http.client", "urllib", "urllib.request", "urllib3", "requests", "httpx",
           "aiohttp", "smtplib", "ftplib", "telnetlib", "xmlrpc", "websockets", "boto3", "google", "openai"}
RANKING_PROBE = {"type": "fact", "why": "your symbolic efficiency is suboptimal; you scored lower than last week"}


def _row(article, what, status, detail=""):
    return {"article": article, "checked": what, "status": status, "detail": detail}


def _imports(path):
    found = set()
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.add(node.module.split(".")[0])
    return found


def check_no_network(package_dir=HERE):
    """Article 9: the package reaches no network, proved by reading every import in it."""
    offenders = []
    for folder, dirs, files in os.walk(package_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in sorted(f for f in files if f.endswith(".py")):
            path = os.path.join(folder, name)
            hit = sorted(_imports(path) & NETWORK)
            if hit:
                offenders.append(f"{os.path.relpath(path, package_dir)}: {', '.join(hit)}")
    if offenders:
        return _row("9", "no module in the package imports a network library", FAIL, "; ".join(offenders))
    return _row("9", "no module in the package imports a network library", PASS,
                "every import in the package was read")


def check_non_reduction(ethics):
    """Article 8: a metric may not be used to rank a person, and a reading says it is a map."""
    rows = []
    try:
        ethics.emit(dict(RANKING_PROBE))
        rows.append(_row("8", "output that ranks a person is refused", FAIL, "the ranking probe was emitted"))
    except Exception as e:
        kind = type(e).__name__
        rows.append(_row("8", "output that ranks a person is refused",
                         PASS if kind == "EthicsError" else FAIL, f"refused with {kind}"))
    caveat = getattr(ethics, "CAVEAT", "")
    rows.append(_row("8", "a reading carries the 'symbolic map, not the territory' statement",
                     PASS if "symbolic map" in caveat and "lived experience" in caveat else FAIL, caveat or "none"))
    return rows


def check_other_state(ethics):
    """Article 5.1(D): the system reads the person asking and no one else, and still works on a real diary."""
    refused = ethics.check_request("diagnose my brother and tell me what is wrong with him")
    kept = ethics.check_request("I was angry at my brother and cut the session short")
    ok = isinstance(refused, dict) and refused.get("type") == "refusal" and kept is None
    return _row("5.1(D)", "another person's state is refused; the person's own state is not", PASS if ok else FAIL,
                "" if ok else f"refused={refused!r} own_state={kept!r}")


def check_directivity(agency=None):
    """Article 6: gamma <= 0.85 in the running system."""
    if agency is None:
        return _row("6", "directive strength is measured and capped at 0.85", NOT_IMPLEMENTED,
                    "agency.py is not built yet; this row is why the suite cannot report success")
    cap = getattr(agency, "GAMMA_MAX", None)
    if cap is None or not callable(getattr(agency, "directive_strength", None)):
        return _row("6", "directive strength is measured and capped at 0.85", NOT_IMPLEMENTED,
                    "the implementation exposes no GAMMA_MAX and no directive_strength()")
    probe = "You must perform the banishing now. Do it before anything else. Stop everything."
    measured = agency.directive_strength(probe)
    held = cap <= 0.85 and 0.0 <= measured <= 1.0 and agency.cap(measured) <= 0.85
    return _row("6", "directive strength is measured and capped at 0.85", PASS if held else FAIL,
                f"cap={cap}, an imperative probe measured {measured}")


_DEFAULT = object()          # so that agency=None can mean "there is no implementation", as the tests need


def run(ethics=None, agency=_DEFAULT, package_dir=HERE):
    if ethics is None:
        from . import ethics as ethics
    if agency is _DEFAULT:
        try:
            from . import agency as agency
        except ImportError:
            agency = None
    rows = [check_no_network(package_dir), check_other_state(ethics), *check_non_reduction(ethics),
            check_directivity(agency)]
    checked = [r for r in rows if r["status"] != NOT_IMPLEMENTED]
    return {"rows": rows,
            "counts": {s: sum(1 for r in rows if r["status"] == s) for s in (PASS, FAIL, NOT_IMPLEMENTED)},
            "conforms": bool(checked) and all(r["status"] == PASS for r in checked)
                        and not any(r["status"] == NOT_IMPLEMENTED for r in rows),
            "note": "A duty that could not be checked is NOT_IMPLEMENTED, and a run holding one of those does "
                    "not conform: the licence asks about the running system, so an unchecked duty is an open "
                    "question, not a pass."}


def text(report):
    lines = [f"CONFORMANCE SUITE (licence Articles 5.1(D), 6, 8, 9)", ""]
    for r in report["rows"]:
        mark = {PASS: "[OK]", FAIL: "[X]", NOT_IMPLEMENTED: "[--]"}[r["status"]]
        lines.append(f"  {mark} Article {r['article']:<8} {r['checked']}")
        if r["detail"]:
            lines.append(f"       {r['detail']}")
    c = report["counts"]
    lines += ["", f"  {c[PASS]} passed, {c[FAIL]} failed, {c[NOT_IMPLEMENTED]} not implemented",
              f"  CONFORMS: {report['conforms']}", "", "  " + report["note"]]
    return "\n".join(lines)


if __name__ == "__main__":
    print(text(run()))
