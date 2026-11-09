#!/usr/bin/env python3
"""
telemetry_service.py
A zero-dependency Python microservice that receives telemetry POST requests
from the Web UI and appends them to logs/community_dataset.jsonl.
This keeps file I/O operations centralized in Python.
"""

import json
import time
import pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

PORT = 5001
LOG_FILE = pathlib.Path(__file__).parent.parent / "logs" / "community_dataset.jsonl"

class TelemetryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/log':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"status":"error","message":"Invalid JSON"}')
                return

            # Append timestamp
            data['timestamp'] = time.time()
            data['source'] = 'web_observatory'

            # Ensure logs dir exists
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data) + '\n')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            # Add CORS for local testing if needed
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status":"logged"}')
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run(server_class=HTTPServer, handler_class=TelemetryHandler, port=PORT):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"OMARG Telemetry Bridge running on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Telemetry Bridge stopped.")

if __name__ == '__main__':
    run()
