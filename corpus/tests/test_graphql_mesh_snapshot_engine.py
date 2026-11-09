#!/usr/bin/env python3
"""
test_graphql_mesh_snapshot_engine.py
Runnable Unit Test Suite for graphql_mesh_snapshot_engine.py.

WHAT THIS TESTS:
1. Ground-Truth Schema Hashing: Verifies compute_schema_snapshot_hash against independent
   hashlib blob header construction and the universal empty-file blob SHA-1 vector
   (e69de29bb2d1d6434b8b29ae775ad8c2e48c5391).
2. Checked Integer Math & DoS Safety Guard: Verifies validate_graphql_query_safety
   blocks integer wrap-around (65536 x 65536) and allocations > 256 MB.
3. Ephemeral Resolver State Collapse: Verifies resolver pool resets upstream references
   back to None after every query execution.
4. Ground-Truth Match: Verifies query execution returns expected data structures and extensions.
"""

import sys
import hashlib
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import graphql_mesh_snapshot_engine as mesh_engine


class TestGraphQLMeshSnapshotSuite(unittest.TestCase):

    def test_schema_snapshot_hash_known_empty_vector(self):
        """Verifies schema snapshot hash for empty string matches universal Git empty blob vector."""
        actual_hash = mesh_engine.compute_schema_snapshot_hash("")
        self.assertEqual(
            actual_hash,
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
            "Empty schema snapshot must match fixed Git blob SHA-1 vector"
        )

    def test_schema_snapshot_hash_against_independent_hashlib(self):
        """Verifies schema hashing against independent byte header construction in test."""
        schema_sdl = "type Query { ping: String! }"
        schema_bytes = schema_sdl.encode("utf-8")
        ref_header = f"blob {len(schema_bytes)}\0".encode("utf-8")
        expected_hash = hashlib.sha1(ref_header + schema_bytes).hexdigest()

        actual_hash = mesh_engine.compute_schema_snapshot_hash(schema_sdl)
        self.assertEqual(actual_hash, expected_hash)

    def test_query_safety_guard_blocks_overflow(self):
        """Verifies 32-bit integer wrap-around (65536 * 65536) is rejected."""
        res = mesh_engine.validate_graphql_query_safety(query_depth=65536, field_count=65536)
        self.assertEqual(res["status"], "REJECTED")
        self.assertIn("Integer overflow", res["reason"])

    def test_query_safety_guard_blocks_excessive_heap(self):
        """Verifies query complexity exceeding 256 MB is rejected."""
        # 1000 depth * 5000 fields * 64 B/field = 320,000,000 B > 268,435,456 B
        res = mesh_engine.validate_graphql_query_safety(query_depth=1000, field_count=5000)
        self.assertEqual(res["status"], "REJECTED")
        self.assertIn("exceeds 256 MB safety limit", res["reason"])

    def test_ephemeral_resolver_collapse(self):
        """Verifies resolver pool executes resolution, returns valid data, and resets references to None after execution."""
        sdl = "type Query { users: [User!]! }"
        gw = mesh_engine.GraphQLMeshGateway(sdl)

        # Before query execution, fields are None
        self.assertIsNone(gw.resolver_pool._rest_service)

        # Execute query
        res = gw.execute_query("{ users { id } }", depth=2, fields=2)
        self.assertIsNotNone(res["data"], "Query response data must not be None")
        self.assertIn("users", res["data"], "Query response must contain resolved 'users' field")
        self.assertEqual(len(res["data"]["users"]), 2, "Resolver must fetch 2 user records")
        self.assertEqual(res["data"]["users"][0]["id"], "usr_1", "Resolver must return valid user record data")

        # After query execution, fields must collapse back to None
        self.assertIsNone(gw.resolver_pool._rest_service, "Resolver pool must collapse to None post-execution")

    def test_adversarial_break_it_missing_null_header_fails(self):
        """
        Adversarial Break-It Proof: Verifies that changing 'blob <len>\\0' to 'blob <len> '
        diverges from expected SHA-1 digest.
        """
        schema_sdl = "type Query { test: Int }"
        schema_bytes = schema_sdl.encode("utf-8")
        
        # Malformed header using space instead of null byte \0
        broken_header = f"blob {len(schema_bytes)} ".encode("utf-8")
        broken_hash = hashlib.sha1(broken_header + schema_bytes).hexdigest()

        correct_hash = mesh_engine.compute_schema_snapshot_hash(schema_sdl)
        self.assertNotEqual(correct_hash, broken_hash, "Header without null byte MUST fail comparison")


def run_unit_test_suite():
    print("=" * 72)
    print("  GRAPHQL MESH SNAPSHOT ENGINE — UNIT TEST SUITE")
    print("  Executing Cryptographic Hashing, DoS Safety & Ephemeral Assertions")
    print("=" * 72 + "\n")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 72)
    print("  UNIT TEST SUITE SUMMARY")
    print("=" * 72)
    print(f"  Total Tests Executed : {result.testsRun}")
    print(f"  Total Failures       : {len(result.failures)}")
    print(f"  Total Errors         : {len(result.errors)}")
    status = "ALL PASSED  (correctness verified per-assertion above)" if result.wasSuccessful() else "FAILED  — see output above"
    print(f"  Result               : {status}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_unit_test_suite()
    sys.exit(0 if success else 1)
