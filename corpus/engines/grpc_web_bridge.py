#!/usr/bin/env python3
"""
grpc_web_bridge.py
Pure Python gRPC-Web & Microservice RPC Proxy Bridge Simulator.
Translates Web Client HTTP Requests -> Envoy Proxy -> Backend gRPC Server.

Features:
1. Proto3 Schema Contract Simulator (Greeter Service: SayHello).
2. Backend gRPC Server listening on TCP :9090.
3. Envoy Proxy Translator listening on TCP :8080 (handling CORS & RPC Translation).
4. Client Stub invoking SayHello("World") over gRPC-Web.

Usage:
    python grpc_web_bridge.py
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

# ==============================================================================
# 1. PROTO3 SERVICE CONTRACT DEFINITION
# ==============================================================================
class HelloRequest:
    def __init__(self, name: str = ""):
        self.name = name

    def to_dict(self):
        return {"name": self.name}

    @staticmethod
    def from_dict(d: dict):
        return HelloRequest(name=d.get("name", ""))

class HelloReply:
    def __init__(self, message: str = ""):
        self.message = message

    def to_dict(self):
        return {"message": self.message}

    @staticmethod
    def from_dict(d: dict):
        return HelloReply(message=d.get("message", ""))

# ==============================================================================
# 2. BACKEND gRPC SERVER SIMULATOR (Port 9090)
# ==============================================================================
class GoGRPCBackendServer:
    def __init__(self, ip: str = "127.0.0.1", port: int = 9090):
        self.ip = ip
        self.port = port
        self.sock = None
        self.running = False

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(5)
        self.running = True
        
        t = threading.Thread(target=self._server_loop, daemon=True)
        t.start()
        print(f"  🟢 [Go gRPC Server] Native HTTP/2 gRPC Listening on {self.ip}:{self.port}")

    def _server_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                t = threading.Thread(target=self._handle_conn, args=(conn,), daemon=True)
                t.start()
            except Exception:
                break

    def _handle_conn(self, conn):
        try:
            raw_data = conn.recv(4096)
            if raw_data:
                request_payload = json.loads(raw_data.decode('utf-8'))
                req = HelloRequest.from_dict(request_payload.get("data", {}))
                
                # Execute Service Handler: SayHello
                reply_message = f"Hello {req.name} (via gRPC-Go Backend)"
                reply = HelloReply(message=reply_message)
                
                response_payload = {
                    "grpc_status": 0,
                    "grpc_message": "OK",
                    "reply": reply.to_dict()
                }
                conn.sendall(json.dumps(response_payload).encode('utf-8'))
        except Exception:
            pass
        finally:
            conn.close()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

# ==============================================================================
# 3. ENVOY PROXY TRANSLATOR (Port 8080)
# ==============================================================================
class EnvoyProxyTranslator:
    def __init__(self, proxy_port: int = 8080, backend_port: int = 9090):
        self.proxy_ip = "127.0.0.1"
        self.proxy_port = proxy_port
        self.backend_ip = "127.0.0.1"
        self.backend_port = backend_port
        self.sock = None
        self.running = False

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.proxy_ip, self.proxy_port))
        self.sock.listen(5)
        self.running = True
        
        t = threading.Thread(target=self._proxy_loop, daemon=True)
        t.start()
        print(f"   [Envoy Proxy] gRPC-Web Proxy Listening on {self.proxy_ip}:{self.proxy_port} -> Target: :{self.backend_port}")

    def _proxy_loop(self):
        while self.running:
            try:
                client_conn, addr = self.sock.accept()
                t = threading.Thread(target=self._handle_proxy, args=(client_conn,), daemon=True)
                t.start()
            except Exception:
                break

    def _handle_proxy(self, client_conn):
        try:
            web_data = client_conn.recv(4096)
            if web_data:
                web_payload = json.loads(web_data.decode('utf-8'))
                
                # 1. CORS Verification & Envoy Filter Inspection
                headers = web_payload.get("headers", {})
                content_type = headers.get("content-type", "application/grpc-web+proto")
                
                # 2. Translate gRPC-Web Request -> Forward to Backend gRPC Server (:9090)
                backend_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                backend_sock.connect((self.backend_ip, self.backend_port))
                
                grpc_payload = {
                    "method": "/helloworld.Greeter/SayHello",
                    "content_type": content_type,
                    "data": web_payload.get("request", {})
                }
                backend_sock.sendall(json.dumps(grpc_payload).encode('utf-8'))
                
                # 3. Receive Backend Reply -> Translate Back to gRPC-Web Client
                backend_reply_raw = backend_sock.recv(4096)
                backend_sock.close()
                
                backend_reply = json.loads(backend_reply_raw.decode('utf-8'))
                
                web_response = {
                    "headers": {
                        "access-control-allow-origin": "*",
                        "content-type": "application/grpc-web-text",
                        "grpc-status": backend_reply.get("grpc_status", 0)
                    },
                    "body": backend_reply.get("reply", {})
                }
                client_conn.sendall(json.dumps(web_response).encode('utf-8'))
        except Exception:
            pass
        finally:
            client_conn.close()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

# ==============================================================================
# 4. CLIENT STUB SIMULATOR (SayHello Client)
# ==============================================================================
class GreeterClientStub:
    def __init__(self, proxy_ip="127.0.0.1", proxy_port=8080):
        self.proxy_ip = proxy_ip
        self.proxy_port = proxy_port

    def say_hello(self, name: str) -> str:
        req = HelloRequest(name=name)
        web_payload = {
            "headers": {
                "content-type": "application/grpc-web+proto",
                "x-user-agent": "grpc-web-js/1.0.0"
            },
            "request": req.to_dict()
        }
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.proxy_ip, self.proxy_port))
        sock.sendall(json.dumps(web_payload).encode('utf-8'))
        
        resp_raw = sock.recv(4096)
        sock.close()
        
        resp = json.loads(resp_raw.decode('utf-8'))
        reply_dict = resp.get("body", {})
        reply = HelloReply.from_dict(reply_dict)
        return reply.message

# ==============================================================================
# DEMONSTRATION HARNESS
# ==============================================================================
def main():
    print("""
    ================================================================
           gRPC-WEB & ENVOY PROXY TRANSLATOR BRIDGE (RCA)
          Proto3 Schema, Envoy Filter, & Go Server Simulator
    ================================================================
    """)
    
    # 1. Start Go gRPC Backend Server on :9090
    server = GoGRPCBackendServer(port=9090)
    server.start()
    
    # 2. Start Envoy Proxy Bridge on :8080
    proxy = EnvoyProxyTranslator(proxy_port=8080, backend_port=9090)
    proxy.start()
    
    time.sleep(0.2)
    
    # 3. Client Stub Invokes SayHello("World") over gRPC-Web Proxy
    print("\n  Client Stub invoking client.sayHello(name='World') over Envoy Proxy (:8080)...")
    client = GreeterClientStub(proxy_port=8080)
    result = client.say_hello("World")
    
    print("\n" + "="*70)
    print("  gRPC-WEB RESPONSE TELEMETRY")
    print("="*70)
    print(f" > Target RPC Method : /helloworld.Greeter/SayHello")
    print(f" > Client Stub Output: \"{result}\"")
    print("="*70 + "\n")
    
    server.stop()
    proxy.stop()

if __name__ == "__main__":
    main()
