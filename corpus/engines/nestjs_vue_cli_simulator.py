#!/usr/bin/env python3
"""
nestjs_vue_cli_simulator.py
NestJS Backend API & Vue.js Client Full-Stack CLI Architecture Simulator.
Pure Python Implementation.

Features:
1. CLI Engine Commands:
   - nestvue new <project_name>
   - nest start (Launches NestJS Controller Dependency Injection Server on :3000)
   - vue serve (Launches Vue.js Reactive SPA Client on :8080)
   - vue build (Compiles Vue.js Production Static Distribution Assets)
2. NestJS Controller & Service Dependency Injection Layer.
3. Vue.js Reactive State & Virtual DOM Renderer.

Usage:
    python nestjs_vue_cli_simulator.py
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
# 1. NESTJS BACKEND API CONTROLLER & SERVICE LAYER
# ==============================================================================
class NestJSService:
    def __init__(self):
        self.data = ["Item 1", "Item 2", "Item 3"]

    def get_all(self):
        return {"status": "success", "data": self.data}

    def add_item(self, item: str):
        self.data.append(item)
        return {"status": "created", "item": item, "total": len(self.data)}

class NestJSController:
    def __init__(self, service: NestJSService):
        self.service = service # Dependency Injection

    def handle_request(self, route: str, method: str = "GET", payload: dict = None):
        if route == "/api/items" and method == "GET":
            return self.service.get_all()
        elif route == "/api/items" and method == "POST":
            item = payload.get("item", "Default Item") if payload else "Default Item"
            return self.service.add_item(item)
        return {"error": "404 Not Found"}

class NestJSServer:
    def __init__(self, port: int = 3000):
        self.port = port
        self.service = NestJSService()
        self.controller = NestJSController(self.service)
        self.sock = None
        self.running = False

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.listen(5)
        self.running = True
        
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()
        print(f"  🟢 [NestJS Server] API Engine Running on http://127.0.0.1:{self.port} (Controller DI Active)")

    def _listen_loop(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
                t = threading.Thread(target=self._handle_req, args=(conn,), daemon=True)
                t.start()
            except Exception:
                break

    def _handle_req(self, conn):
        try:
            raw = conn.recv(4096)
            if raw:
                req_json = json.loads(raw.decode('utf-8'))
                route = req_json.get("route", "/api/items")
                method = req_json.get("method", "GET")
                payload = req_json.get("payload", {})
                
                res = self.controller.handle_request(route, method, payload)
                conn.sendall(json.dumps(res).encode('utf-8'))
        except Exception:
            pass
        finally:
            conn.close()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

# ==============================================================================
# 2. VUE.JS REACTIVE SPA CLIENT SIMULATOR
# ==============================================================================
class VueClient:
    def __init__(self, api_port: int = 3000, client_port: int = 8080):
        self.api_port = api_port
        self.client_port = client_port
        self.reactive_state = {"items": [], "loading": False}

    def fetch_items(self):
        self.reactive_state["loading"] = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", self.api_port))
        
        req = {"route": "/api/items", "method": "GET"}
        sock.sendall(json.dumps(req).encode('utf-8'))
        
        res_raw = sock.recv(4096)
        sock.close()
        
        res = json.loads(res_raw.decode('utf-8'))
        self.reactive_state["items"] = res.get("data", [])
        self.reactive_state["loading"] = False

    def render_virtual_dom(self):
        print("\n  --- [Vue.js Reactive SPA Component View] ---")
        print(f"  App Mounting Point : #app (Client Port: {self.client_port})")
        print(f"  Reactive State     : Loading = {self.reactive_state['loading']}")
        print(f"  Rendered Item List : {self.reactive_state['items']}")

    def build_production(self):
        print(f"\n   [Vue CLI Builder] Compiling Vue SPA client into /dist/ production bundle...")
        print("      app.js created (Virtual DOM Bundle)")
        print("      chunk-vendors.js created (Vue Core & Axios)")
        print("      index.html minified")
        print("   Production build successfully compiled in /dist/")

# ==============================================================================
# 3. CLI COMMAND ENGINE SIMULATOR
# ==============================================================================
class NestVueCLI:
    def __init__(self):
        self.project_name = None
        self.server = None
        self.client = None

    def new_project(self, name: str):
        self.project_name = name
        print(f"\n   [nestvue CLI] Scaffolding new full-stack project '{self.project_name}'...")
        print(f"      backend/ (NestJS TypeScript API)")
        print(f"      frontend/ (Vue.js 3 SPA Client)")
        print(f"   Project '{self.project_name}' created successfully!")

    def nest_start(self):
        print(f"\n   Executing: 'nest start'...")
        self.server = NestJSServer(port=3000)
        self.server.start()
        time.sleep(0.2)

    def vue_serve(self):
        print(f"\n   Executing: 'vue serve'...")
        print(f"  🟢 [Vue Dev Server] Serving Vue SPA client on http://127.0.0.1:8080")
        self.client = VueClient(api_port=3000, client_port=8080)
        self.client.fetch_items()
        self.client.render_virtual_dom()

    def vue_build(self):
        print(f"\n   Executing: 'vue build'...")
        if self.client:
            self.client.build_production()
        else:
            client = VueClient()
            client.build_production()

    def cleanup(self):
        if self.server:
            self.server.stop()

# ==============================================================================
# DEMONSTRATION HARNESS
# ==============================================================================
def main():
    print("""
    ================================================================
           NESTJS-VUE-CLIENT CLI FULL-STACK ARCHITECTURE
          CLI Boilerplate Generator, NestJS API, & Vue.js SPA
    ================================================================
    """)
    
    cli = NestVueCLI()
    
    # 1. npm install -g @nestjs-vue/cli & nestvue new nestvue-demo
    cli.new_project("nestvue-demo")
    
    # 2. nest start
    cli.nest_start()
    
    # 3. vue serve
    cli.vue_serve()
    
    # 4. vue build
    cli.vue_build()
    
    cli.cleanup()
    
    print("\n" + "="*70)
    print(" NestJS-Vue-Client CLI Architecture Simulator Verified!")
    print("="*70)

if __name__ == "__main__":
    main()
