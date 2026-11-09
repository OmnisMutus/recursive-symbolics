#!/usr/bin/env python3
"""
test_telemetry_service.py
Independent correctness test for telemetry_service.py's TelemetryHandler,
a zero-dependency http.server-based microservice.

Spins up a REAL HTTPServer on an OS-assigned ephemeral port (port 0) on
a background thread, and sends REAL HTTP requests to it via
http.client -- not calling do_POST()/do_OPTIONS() directly, so the
actual socket/threading/request-parsing wiring is exercised, not just
the handler logic in isolation.

`telemetry_service.LOG_FILE` is monkeypatched to a temp file for every
test -- the real LOG_FILE (Recursive-Symbolics/logs/community_dataset.jsonl)
already contains real accumulated data and must never be touched here.
"""

import http.client
import json
import sys
import tempfile
import threading
import time
import unittest
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import telemetry_service as ts  # noqa: E402


class TestTelemetryHandler(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._real_log_file = ts.LOG_FILE
        ts.LOG_FILE = Path(self._tmpdir) / "logs" / "community_dataset.jsonl"

        self.server = HTTPServer(("127.0.0.1", 0), ts.TelemetryHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)  # give the server a moment to actually start listening

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        ts.LOG_FILE = self._real_log_file
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _post(self, path, body: dict):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        payload = json.dumps(body).encode("utf-8")
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, data

    def test_valid_post_returns_200_and_logged_status(self):
        status, data = self._post("/log", {"event": "test_event", "value": 42})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data), {"status": "logged"})

    def test_valid_post_appends_real_entry_to_log_file_with_timestamp_and_source(self):
        self._post("/log", {"event": "test_event", "value": 42})
        self.assertTrue(ts.LOG_FILE.is_file())
        lines = ts.LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["event"], "test_event")
        self.assertEqual(record["value"], 42)
        self.assertEqual(record["source"], "web_observatory")
        self.assertIn("timestamp", record)

    def test_multiple_posts_append_rather_than_overwrite(self):
        self._post("/log", {"n": 1})
        self._post("/log", {"n": 2})
        lines = ts.LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["n"], 1)
        self.assertEqual(json.loads(lines[1])["n"], 2)

    def test_creates_logs_directory_if_missing(self):
        self.assertFalse(ts.LOG_FILE.parent.exists())
        self._post("/log", {"n": 1})
        self.assertTrue(ts.LOG_FILE.parent.is_dir())

    def test_invalid_json_returns_400(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/log", body=b"not valid json {{{",
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        status = resp.status
        data = resp.read()
        conn.close()
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(data)["status"], "error")
        # Invalid payload must not be written to the log at all.
        self.assertFalse(ts.LOG_FILE.exists())

    def test_unknown_path_returns_404(self):
        status, _ = self._post("/nonexistent", {"n": 1})
        self.assertEqual(status, 404)

    def test_options_returns_cors_headers(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("OPTIONS", "/log")
        resp = conn.getresponse()
        status = resp.status
        allow_origin = resp.getheader("Access-Control-Allow-Origin")
        allow_methods = resp.getheader("Access-Control-Allow-Methods")
        conn.close()
        self.assertEqual(status, 200)
        self.assertEqual(allow_origin, "*")
        self.assertIn("POST", allow_methods)

    def test_log_response_includes_cors_header(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/log", body=json.dumps({"n": 1}).encode("utf-8"))
        resp = conn.getresponse()
        allow_origin = resp.getheader("Access-Control-Allow-Origin")
        resp.read()
        conn.close()
        self.assertEqual(allow_origin, "*")


def run_unit_test_suite():
    print("=" * 72)
    print("  TELEMETRY_SERVICE.PY -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("Test") and isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
