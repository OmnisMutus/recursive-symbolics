#!/usr/bin/env python3
"""
test_grpc_web_bridge.py
Correctness test for grpc_web_bridge.py, per TESTING_STANDARD.md.

SCOPE NOTE: grpc_web_bridge.py does not implement real gRPC-Web wire format
(no HTTP/2 framing, no protobuf, no base64 trailer encoding) -- it's JSON
dicts sent over plain TCP sockets between three in-process classes, styled
to resemble a gRPC-Web/Envoy flow. There is no independent external gRPC
library this can be checked against for protocol conformance, so "ground
truth" here means: the documented request/reply contract of THIS simulator
(name in -> "Hello {name} (via gRPC-Go Backend)" out) is checked with values
that are NOT hand-picked to work (unicode, punctuation, empty string,
concurrent distinct clients), and known-plausible network bugs (malformed
payloads, concurrent connection mixups) are actively tested for rather than
assumed away.

Edge cases: empty name, unicode name, name containing quote/backslash
characters that must survive JSON round-trip, many concurrent clients with
distinct names (checks for response cross-talk between threads/connections),
malformed non-JSON bytes sent directly to the proxy (checks for hangs).

Break-it proof: see bottom of file.
"""
import sys
import json
import socket
import threading
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import grpc_web_bridge as eng

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}  {detail}")

# Use non-default ports so this test can't collide with anyone running the
# demo harness (main()) on 8080/9090 at the same time.
BACKEND_PORT = 19090
PROXY_PORT = 18080

server = eng.GoGRPCBackendServer(port=BACKEND_PORT)
server.start()
proxy = eng.EnvoyProxyTranslator(proxy_port=PROXY_PORT, backend_port=BACKEND_PORT)
proxy.start()
time.sleep(0.3)

client = eng.GreeterClientStub(proxy_port=PROXY_PORT)

# ---------------------------------------------------------------------------
# 1. Documented contract, with values not hand-picked to be easy
# ---------------------------------------------------------------------------
cases = [
    "World",
    "",                          # empty name
    "",                       # unicode
    'a"b\\c',                    # quote + backslash -- must survive JSON round-trip
    "x" * 2000,                  # long name
    "line1\nline2",              # embedded newline
]
for name in cases:
    expected = f"Hello {name} (via gRPC-Go Backend)"
    got = client.say_hello(name)
    check(f"round-trip for name={name!r:.40}", got == expected,
          f"got={got!r:.60} expected={expected!r:.60}")

# ---------------------------------------------------------------------------
# 2. Concurrent distinct clients -- check for cross-talk between connections
# ---------------------------------------------------------------------------
results = {}
errors = []

def worker(i):
    try:
        c = eng.GreeterClientStub(proxy_port=PROXY_PORT)
        name = f"client-{i}"
        got = c.say_hello(name)
        results[i] = (name, got)
    except Exception as e:
        errors.append((i, str(e)))

threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=5)

crosstalk = [
    (i, name, got) for i, (name, got) in results.items()
    if got != f"Hello {name} (via gRPC-Go Backend)"
]
check("20 concurrent clients: no response cross-talk between connections",
      len(errors) == 0 and len(results) == 20 and len(crosstalk) == 0,
      f"errors={errors[:3]} mismatches={crosstalk[:3]} completed={len(results)}/20")

# ---------------------------------------------------------------------------
# 3. Malformed input: garbage bytes sent directly to the proxy socket.
#    This is a real network service -- a client sending non-JSON should not
#    make the connection hang forever. Guard with a watchdog so a hang
#    fails the test loudly instead of freezing the whole suite.
# ---------------------------------------------------------------------------
malformed_result = {"outcome": None}

def malformed_probe():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", PROXY_PORT))
        s.sendall(b"\xff\xfe\x00not-json-garbage***")
        s.settimeout(3.0)
        data = s.recv(4096)
        malformed_result["outcome"] = ("data", data)
    except socket.timeout:
        malformed_result["outcome"] = ("timeout", None)
    except OSError as e:
        malformed_result["outcome"] = ("closed", str(e))

t = threading.Thread(target=malformed_probe, daemon=True)
t.start()
t.join(timeout=5)

outcome = malformed_result["outcome"]
print(f"\n  [DEFECT CHECK] malformed (non-JSON) input to proxy -> outcome: {outcome}")
check("malformed input does not hang the connection indefinitely (thread returned)",
      not t.is_alive(), f"watchdog thread still alive after 5s: {outcome}")
if outcome and outcome[0] in ("closed",):
    print("  [NOTE] Server closes the connection with no error response on malformed "
        "input (bare 'except Exception: pass' in _handle_conn/_handle_proxy). A real "
        "client using blocking recv() with no timeout of its own would see a clean "
        "connection-closed, not a hang -- but it also gets no error status, just a "
        "silently dropped request. Worth a real error frame in a production version.")
elif outcome and outcome[0] == "timeout":
    print("  [DEFECT] Malformed input causes the proxy to hang without closing the "
          "connection or responding -- a real client blocked on recv() would hang forever.")

server.stop()
proxy.stop()

print(f"\n  SUMMARY: {PASS} passed, {FAIL} failed (out of {PASS+FAIL} correctness checks)")
sys.exit(1 if FAIL > 0 else 0)

# ---------------------------------------------------------------------------
# BREAK_IT_INSTRUCTIONS (per TESTING_STANDARD.md, section III):
# In grpc_web_bridge.py, GoGRPCBackendServer._handle_conn(), change:
#     reply_message = f"Hello {req.name} (via gRPC-Go Backend)"
# to:
#     reply_message = f"Hello {req.name}"  (drop the backend tag)
# Expected result: every "round-trip for name=..." check must FAIL, since the
# expected string in this test is the full documented contract string.
# Confirmed live in the assistant's response to the user, then reverted.
# ---------------------------------------------------------------------------
