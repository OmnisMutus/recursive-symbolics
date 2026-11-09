#!/usr/bin/env python3
"""
test_dht_rca_node.py
Correctness test for dht_rca_node.py, per TESTING_STANDARD.md.

Ground truth:
  - xor_distance: checked against Python's own bin()/int XOR on independently
    constructed test vectors, plus a published-style known value (SHA-1 of
    the empty string, a documented external constant, XORed with itself -> 0).
  - _get_bucket_index: checked against dist.bit_length() - 1, the standard
    Kademlia bucket-index formula, computed via pure integer arithmetic
    (no float conversion -- a genuinely different code path than the
    engine's int(math.log2(dist))).

Edge cases: distance 0 (self), distance 1 (adjacent IDs), every power-of-two
boundary up to 2^159, max possible 160-bit distance, K-bucket capacity limit,
duplicate-contact update.

Break-it proof: see bottom of file.
"""
import sys
import math
import hashlib
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import dht_rca_node as eng

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
# 1. xor_distance -- ground truth via known SHA-1 vector + raw int XOR
# ---------------------------------------------------------------------------
sha1_empty = hashlib.sha1(b"").hexdigest()   # published constant: da39a3ee...
check("known SHA-1(empty) constant is what we expect",
      sha1_empty == "da39a3ee5e6b4b0d3255bfef95601890afd80709")

check("xor_distance(x, x) == 0 for a real SHA-1 id",
      eng.xor_distance(sha1_empty, sha1_empty) == 0)

id_a = hashlib.sha1(b"node-a").hexdigest()
id_b = hashlib.sha1(b"node-b").hexdigest()
expected_xor = int(id_a, 16) ^ int(id_b, 16)   # independent raw computation
check("xor_distance matches raw int XOR on real node ids",
      eng.xor_distance(id_a, id_b) == expected_xor)

check("XOR distance is symmetric",
      eng.xor_distance(id_a, id_b) == eng.xor_distance(id_b, id_a))

# ---------------------------------------------------------------------------
# 2. _get_bucket_index -- ground truth via dist.bit_length() - 1 (integer-only)
# ---------------------------------------------------------------------------
rt = eng.KademliaRoutingTable(local_node_id=hashlib.sha1(b"local").hexdigest())

def ground_truth_bucket(local_id_hex, other_id_hex):
    dist = int(local_id_hex, 16) ^ int(other_id_hex, 16)
    if dist == 0:
        return 0
    return min(159, dist.bit_length() - 1)

mismatches = 0
tested = 0
mismatch_examples = []
for shift in range(1, 160):
    # Test both the exact power-of-two AND one-less-than-it (the largest value
    # in the bucket below). Exact powers of two are float-exact and won't
    # reproduce the bug; the "-1" values have multiple bits set and are where
    # float(int) precision loss actually bites once dist exceeds 2**53.
    for dist in ((1 << shift), (1 << shift) - 1):
        other_id_int = int(rt.local_node_id, 16) ^ dist
        other_id_hex = format(other_id_int, '040x')
        got = rt._get_bucket_index(other_id_hex)
        expected = ground_truth_bucket(rt.local_node_id, other_id_hex)
        tested += 1
        if got != expected:
            mismatches += 1
            if len(mismatch_examples) < 5:
                mismatch_examples.append((shift, dist.bit_length(), expected, got))

check(f"_get_bucket_index matches bit_length()-1 ground truth near power-of-two distances",
      mismatches == 0,
      f"{mismatches}/{tested} boundary cases disagreed with the correct integer formula; examples (shift, bit_length, expected, got): {mismatch_examples}")

check("_get_bucket_index(self) == 0 (distance 0 edge case)",
      rt._get_bucket_index(rt.local_node_id) == 0)

max_dist_id = format(int(rt.local_node_id, 16) ^ ((1 << 160) - 1), '040x')
check("_get_bucket_index at max possible 160-bit distance == 159",
      rt._get_bucket_index(max_dist_id) == 159)

# ---------------------------------------------------------------------------
# 3. KBucket capacity + dedup
# ---------------------------------------------------------------------------
kb = eng.KBucket()
for i in range(25):
    kb.add_contact(f"node-{i}", "127.0.0.1", 9000 + i)
check("KBucket caps at K_BUCKET_SIZE (20), doesn't grow past capacity",
      len(kb.contacts) == eng.K_BUCKET_SIZE, f"got {len(kb.contacts)}")

kb2 = eng.KBucket()
kb2.add_contact("node-x", "1.1.1.1", 1000)
kb2.add_contact("node-x", "2.2.2.2", 2000)   # same id, different addr -> update not duplicate
check("KBucket updates existing contact instead of duplicating",
      len(kb2.contacts) == 1 and kb2.contacts[0] == ("node-x", "2.2.2.2", 2000),
      f"got {kb2.contacts}")

# ---------------------------------------------------------------------------
# 4. find_closest_nodes ordering -- ground truth via independent sort
# ---------------------------------------------------------------------------
rt2 = eng.KademliaRoutingTable(local_node_id=hashlib.sha1(b"root").hexdigest())
node_ids = [hashlib.sha1(f"peer-{i}".encode()).hexdigest() for i in range(30)]
for nid in node_ids:
    rt2.add_node(nid, "127.0.0.1", 9000)

target = hashlib.sha1(b"target-key").hexdigest()
got_closest = rt2.find_closest_nodes(target, k=5)
got_ids = [c[0] for c in got_closest]

all_contacts = []
for b in rt2.buckets:
    all_contacts.extend(b.contacts)
expected_closest = sorted(all_contacts, key=lambda c: int(c[0], 16) ^ int(target, 16))[:5]
expected_ids = [c[0] for c in expected_closest]

check("find_closest_nodes returns same top-5 order as independent sort",
      got_ids == expected_ids, f"got {got_ids} expected {expected_ids}")

print(f"\n  SUMMARY: {PASS} passed, {FAIL} failed (out of {PASS+FAIL} correctness checks)")
sys.exit(1 if FAIL > 0 else 0)

# ---------------------------------------------------------------------------
# BREAK_IT_INSTRUCTIONS (per TESTING_STANDARD.md, section III):
# In dht_rca_node.py, KademliaRoutingTable._get_bucket_index(), change:
#     return min(ID_BIT_LENGTH - 1, int(math.log2(dist)))
# to:
#     return min(ID_BIT_LENGTH - 1, dist.bit_length() - 1)
# (i.e. FIX the real bug found above) and confirm the
# "_get_bucket_index matches bit_length()-1 ground truth" check flips to PASS
# with 0 mismatches. Conversely, injecting a fresh off-by-one
# (dist.bit_length()) into a hypothetical fixed version should make that
# same check FAIL again. Confirmed live in the assistant's response.
# ---------------------------------------------------------------------------
