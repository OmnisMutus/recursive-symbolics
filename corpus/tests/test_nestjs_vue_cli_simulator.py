#!/usr/bin/env python3
"""
test_nestjs_vue_cli_simulator.py
Correctness test for nestjs_vue_cli_simulator.py, per TESTING_STANDARD.md.

SCOPE NOTE: like grpc_web_bridge.py, this is JSON-over-TCP styled to resemble
a NestJS/Vue stack -- there's no real NestJS or Vue involved, so there's no
external library to check protocol conformance against. Ground truth here is
the documented routing contract (checked directly against NestJSController,
not just through the paired VueClient, so the test doesn't just confirm the
two halves agree with each other), plus a raw-socket client built
independently in this file (not reusing VueClient.fetch_items) to verify the
actual wire format, plus a genuine concurrency stress test since add_item()
mutates shared state from multiple connection threads.

Edge cases: missing payload, missing "item" key, unknown route, wrong method
case (exact-match check), and 20-way concurrent POST for lost-update races.

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
import nestjs_vue_cli_simulator as eng

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

# ---------------------------------------------------------------------------
# 1. Direct controller/service contract (no network) -- documented behavior
# ---------------------------------------------------------------------------
service = eng.NestJSService()
controller = eng.NestJSController(service)

r = controller.handle_request("/api/items", "GET")
check("GET /api/items returns initial 3 seed items",
      r == {"status": "success", "data": ["Item 1", "Item 2", "Item 3"]}, f"got {r}")

r = controller.handle_request("/api/items", "POST", {"item": "Widget"})
check("POST /api/items with item creates it and reports total=4",
      r == {"status": "created", "item": "Widget", "total": 4}, f"got {r}")

r = controller.handle_request("/api/items", "POST", None)
check("POST /api/items with no payload defaults to 'Default Item'",
      r == {"status": "created", "item": "Default Item", "total": 5}, f"got {r}")

r = controller.handle_request("/api/items", "POST", {})
check("POST /api/items with empty payload dict defaults to 'Default Item'",
      r == {"status": "created", "item": "Default Item", "total": 6}, f"got {r}")

r = controller.handle_request("/api/unknown", "GET")
check("unknown route returns 404", r == {"error": "404 Not Found"}, f"got {r}")

r = controller.handle_request("/api/items", "get")  # lowercase, not "GET"
check("method match is case-sensitive: lowercase 'get' does NOT match 'GET', returns 404",
      r == {"error": "404 Not Found"}, f"got {r}")

# ---------------------------------------------------------------------------
# 2. Real network integration -- raw socket client built independently here,
#    not reusing VueClient.fetch_items, to check the actual wire contract.
# ---------------------------------------------------------------------------
PORT = 13000
server = eng.NestJSServer(port=PORT)
server.start()
time.sleep(0.3)

def raw_request(route, method="GET", payload=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", PORT))
    req = {"route": route, "method": method}
    if payload is not None:
        req["payload"] = payload
    s.sendall(json.dumps(req).encode("utf-8"))
    data = s.recv(4096)
    s.close()
    return json.loads(data.decode("utf-8"))

resp = raw_request("/api/items", "GET")
check("raw socket GET matches direct-call contract (fresh server, seed data)",
      resp == {"status": "success", "data": ["Item 1", "Item 2", "Item 3"]}, f"got {resp}")

resp = raw_request("/api/items", "POST", {"item": "Gadget"})
check("raw socket POST creates item over real TCP connection",
      resp == {"status": "created", "item": "Gadget", "total": 4}, f"got {resp}")

resp = raw_request("/api/items", "GET")
check("state persists across separate TCP connections (server-side, not client-side)",
      resp == {"status": "success", "data": ["Item 1", "Item 2", "Item 3", "Gadget"]}, f"got {resp}")

# ---------------------------------------------------------------------------
# 3. Concurrency: 20 simultaneous POSTs from separate threads/connections.
#    add_item() does self.data.append(item) then returns len(self.data) with
#    no lock. Check for lost updates: final count must be exactly
#    starting_count + 20, and the 20 returned "total" values must be a
#    complete, gap-free, duplicate-free set (a race would show up as
#    duplicate or skipped totals).
# ---------------------------------------------------------------------------
before = raw_request("/api/items", "GET")
start_count = len(before["data"])

totals = []
lock = threading.Lock()

def post_worker(i):
    resp = raw_request("/api/items", "POST", {"item": f"concurrent-{i}"})
    with lock:
        totals.append(resp.get("total"))

threads = [threading.Thread(target=post_worker, args=(i,)) for i in range(20)]
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=5)

after = raw_request("/api/items", "GET")
end_count = len(after["data"])
expected_totals = set(range(start_count + 1, start_count + 21))
got_totals = set(totals)

check("concurrent POSTs: no lost updates (final count == start + 20)",
      end_count == start_count + 20, f"start={start_count} end={end_count}")
check("concurrent POSTs: all 20 'total' values are unique and gap-free (no race)",
      got_totals == expected_totals,
      f"missing={expected_totals - got_totals} unexpected_dupes_or_extra={got_totals - expected_totals}")

server.stop()

print(f"\n  SUMMARY: {PASS} passed, {FAIL} failed (out of {PASS+FAIL} correctness checks)")
sys.exit(1 if FAIL > 0 else 0)

# ---------------------------------------------------------------------------
# BREAK_IT_INSTRUCTIONS (per TESTING_STANDARD.md, section III):
# In nestjs_vue_cli_simulator.py, NestJSController.handle_request(), change:
#     elif route == "/api/items" and method == "POST":
# to:
#     elif route == "/api/items" and method == "GET":   (duplicate the GET
#     branch instead of checking POST, so POST requests fall through to 404)
# Expected result: every "POST" check must FAIL (all of them, direct and
# over-the-wire, plus the concurrency section since no items get created at
# all). Confirmed live in the assistant's response to the user, then reverted.
# ---------------------------------------------------------------------------
