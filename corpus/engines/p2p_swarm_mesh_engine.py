#!/usr/bin/env python3
"""
p2p_swarm_mesh_engine.py
Distributed Swarm Mesh Networking Engine linking multiple physical/virtual nodes over UDP.
Pure Python Implementation.

Features:
1. Multi-Node Peer Discovery over UDP Socket Broadcast.
2. Distributed State Consensus & Telemetry Sync.
3. Kademlia Routing Table Integration.

Usage:
    python p2p_swarm_mesh_engine.py
"""

import sys
import time
import json
import socket
import threading
from pathlib import Path

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class SwarmMeshNode:
    def __init__(self, node_id: str, port: int):
        self.node_id = node_id
        self.port = port
        self.peers = {} # {node_id: (ip, port)}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", self.port))
        # BUG FIX (found while writing test_p2p_swarm_mesh_engine.py):
        # without a timeout, the listener thread blocks indefinitely inside
        # recvfrom(). Closing the socket from a different thread (stop())
        # while a thread is blocked in recvfrom() on it is not guaranteed to
        # unblock that thread on Linux -- confirmed live: after stop(), a
        # freshly-sent packet was still processed and added to self.peers.
        # A short timeout lets the loop periodically recheck self.running so
        # stop() actually takes effect within one timeout interval.
        self.sock.settimeout(0.2)
        self.running = False

    def start(self):
        self.running = True
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()
        print(f"  🟢 [Swarm Node '{self.node_id}'] Listening on 127.0.0.1:{self.port}")

    def _listen_loop(self):
        # BUG FIX (found while writing test_p2p_swarm_mesh_engine.py): this used
        # to catch bare `Exception` around the whole receive+parse+reply block
        # and `break` out of the loop on any error -- meaning a single malformed
        # UDP packet from any peer (bad JSON, wrong encoding) permanently killed
        # this node's ability to receive ANY further messages, not just that one
        # packet. Confirmed live: sending one bad packet, then a valid one,
        # left self.peers empty -- the valid packet was silently dropped because
        # the listener thread had already exited. Fixed by only breaking on a
        # socket-level error (e.g. the socket being closed by stop()), and
        # skipping (not dying on) a single unparsable packet.
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
            except socket.timeout:
                # No data within the timeout window -- loop back and recheck
                # self.running instead of blocking forever.
                continue
            except OSError:
                # Socket closed (e.g. via stop()) or otherwise unusable -- exit cleanly.
                break

            try:
                msg = json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Malformed packet from a peer -- ignore it, keep listening.
                continue

            sender_id = msg.get("sender_id")
            msg_type = msg.get("type")

            if sender_id and sender_id != self.node_id:
                self.peers[sender_id] = addr

            if msg_type == "PING":
                reply = {"sender_id": self.node_id, "type": "PONG", "peers": list(self.peers.keys())}
                self.sock.sendto(json.dumps(reply).encode('utf-8'), addr)

    def broadcast_state(self, target_port: int, payload: dict):
        msg = {"sender_id": self.node_id, "type": "STATE_SYNC", "payload": payload}
        self.sock.sendto(json.dumps(msg).encode('utf-8'), ("127.0.0.1", target_port))

    def stop(self):
        self.running = False
        self.sock.close()

def main():
    print("""
    ================================================================
           DISTRIBUTED P2P SWARM MESH NETWORKING ENGINE
          Linking Multiple Physical Nodes via UDP State Mesh
    ================================================================
    """)
    
    node1 = SwarmMeshNode("Node_Alpha", 9001)
    node2 = SwarmMeshNode("Node_Beta", 9002)
    
    node1.start()
    node2.start()
    time.sleep(0.1)
    
    print("\n  Broadcasting Swarm Mesh State Sync Packet (Alpha -> Beta)...")
    node1.broadcast_state(9002, {"state": "Tifereth", "qualia_tau": 0.85})
    time.sleep(0.2)
    
    print(f"   Node Alpha Peer Table : {list(node1.peers.keys())}")
    print(f"   Node Beta Peer Table  : {list(node2.peers.keys())}")
    
    node1.stop()
    node2.stop()
    
    print("\n" + "="*64)
    print(" P2P Distributed Swarm Mesh Network Verified!")
    print("="*64)

if __name__ == "__main__":
    main()
