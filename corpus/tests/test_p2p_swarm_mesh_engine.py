#!/usr/bin/env python3
"""
test_p2p_swarm_mesh_engine.py
Correctness & resilience verification for p2p_swarm_mesh_engine.py per
TESTING_STANDARD.md.

Ground truth used: real UDP sockets on 127.0.0.1 (loopback), independent
test-side sockets sending raw bytes/JSON rather than going through the
engine's own SwarmMeshNode class on the sending side -- so the test isn't
just calling the engine and checking the engine agrees with itself.

Break-it proof documented in-line: this test suite was written after finding
a real bug live (see p2p_swarm_mesh_engine.py's _listen_loop docstring/comment
for the fix). Before the fix, `test_survives_malformed_packet` below failed
(a single bad packet permanently killed the listener thread); after the fix
it passes. That fix is already applied in the engine file -- this test
guards against it regressing.
"""

import sys
import time
import json
import socket
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from p2p_swarm_mesh_engine import SwarmMeshNode


def free_port(offset):
    # Deterministic-ish port assignment per test to avoid cross-test collisions
    return 9200 + offset


class TestStateSyncBroadcast(unittest.TestCase):
    def test_peer_learned_from_state_sync(self):
        node_a = SwarmMeshNode("Alpha", free_port(1))
        node_b = SwarmMeshNode("Beta", free_port(2))
        node_a.start()
        node_b.start()
        time.sleep(0.05)
        try:
            node_a.broadcast_state(free_port(2), {"state": "test"})
            time.sleep(0.15)
            self.assertIn("Alpha", node_b.peers)
            # Address recorded should be loopback with SOME port (the sender's
            # ephemeral or bound port) -- ground truth: it's a real socket addr tuple.
            ip, port = node_b.peers["Alpha"]
            self.assertEqual(ip, "127.0.0.1")
            self.assertIsInstance(port, int)
        finally:
            node_a.stop()
            node_b.stop()

    def test_self_sent_message_not_added_as_peer(self):
        # A node must never add itself to its own peer table, even if it
        # somehow receives a message bearing its own sender_id.
        node = SwarmMeshNode("SelfNode", free_port(3))
        node.start()
        time.sleep(0.05)
        try:
            raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            raw.sendto(json.dumps({"sender_id": "SelfNode", "type": "STATE_SYNC", "payload": {}}).encode(),
                       ("127.0.0.1", free_port(3)))
            time.sleep(0.1)
            self.assertNotIn("SelfNode", node.peers)
        finally:
            node.stop()

    def test_multiple_distinct_peers_tracked(self):
        node = SwarmMeshNode("Hub", free_port(4))
        node.start()
        time.sleep(0.05)
        try:
            for sender in ["PeerX", "PeerY", "PeerZ"]:
                raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                raw.sendto(json.dumps({"sender_id": sender, "type": "STATE_SYNC", "payload": {}}).encode(),
                           ("127.0.0.1", free_port(4)))
            time.sleep(0.15)
            self.assertEqual(set(node.peers.keys()), {"PeerX", "PeerY", "PeerZ"})
        finally:
            node.stop()


class TestPingPong(unittest.TestCase):
    def test_ping_gets_pong_reply_with_peer_list(self):
        node = SwarmMeshNode("Responder", free_port(5))
        node.start()
        time.sleep(0.05)
        try:
            requester = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            requester.bind(("127.0.0.1", 0))
            requester.settimeout(2.0)
            requester.sendto(json.dumps({"sender_id": "Requester", "type": "PING"}).encode(),
                              ("127.0.0.1", free_port(5)))
            data, _ = requester.recvfrom(4096)
            reply = json.loads(data.decode())
            self.assertEqual(reply["sender_id"], "Responder")
            self.assertEqual(reply["type"], "PONG")
            self.assertIn("Requester", reply["peers"])
        finally:
            node.stop()


class TestResilienceAndLifecycle(unittest.TestCase):
    def test_survives_malformed_packet(self):
        # THE BREAK-IT-FOUND-BUG TEST: a single malformed (non-JSON) packet
        # must not kill the listener's ability to process subsequent valid
        # packets. This failed before the fix in p2p_swarm_mesh_engine.py
        # (bare `except Exception: break` around the whole receive block).
        node = SwarmMeshNode("Resilient", free_port(6))
        node.start()
        time.sleep(0.05)
        try:
            bad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            bad_sock.sendto(b"not valid json {{{", ("127.0.0.1", free_port(6)))
            time.sleep(0.1)

            good_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            good_sock.sendto(json.dumps({"sender_id": "SurvivorPeer", "type": "STATE_SYNC", "payload": {}}).encode(),
                              ("127.0.0.1", free_port(6)))
            time.sleep(0.15)

            self.assertIn("SurvivorPeer", node.peers,
                "Listener must survive a malformed packet and keep processing valid ones afterward.")
        finally:
            node.stop()

    def test_survives_undecodable_bytes(self):
        # Non-UTF-8 bytes must also not kill the listener (UnicodeDecodeError case).
        node = SwarmMeshNode("Resilient2", free_port(7))
        node.start()
        time.sleep(0.05)
        try:
            bad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            bad_sock.sendto(b"\xff\xfe\x00\x01invalid-utf8", ("127.0.0.1", free_port(7)))
            time.sleep(0.1)

            good_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            good_sock.sendto(json.dumps({"sender_id": "SurvivorPeer2", "type": "STATE_SYNC", "payload": {}}).encode(),
                              ("127.0.0.1", free_port(7)))
            time.sleep(0.15)

            self.assertIn("SurvivorPeer2", node.peers)
        finally:
            node.stop()

    def test_stop_closes_socket_and_halts_processing(self):
        # NOTE: the listener uses a 0.2s socket timeout so it can periodically
        # recheck self.running (see p2p_swarm_mesh_engine.py's fix comment on
        # why a bare blocking recvfrom() + close()-from-another-thread isn't
        # reliable). Give it slightly more than one timeout window to actually
        # exit before asserting shutdown took effect.
        node = SwarmMeshNode("Stoppable", free_port(8))
        node.start()
        time.sleep(0.05)
        node.stop()
        self.assertFalse(node.running)
        time.sleep(0.35)  # > one 0.2s timeout window, so the loop has exited
        try:
            raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            raw.sendto(json.dumps({"sender_id": "TooLate", "type": "STATE_SYNC", "payload": {}}).encode(),
                       ("127.0.0.1", free_port(8)))
        except OSError:
            pass  # connection refused is also an acceptable outcome of a closed socket
        time.sleep(0.1)
        self.assertNotIn("TooLate", node.peers)


def run_unit_test_suite():
    print("=" * 72)
    print("  P2P SWARM MESH ENGINE — CORRECTNESS & RESILIENCE TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
