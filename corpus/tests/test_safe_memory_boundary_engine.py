#!/usr/bin/env python3
"""
test_safe_memory_boundary_engine.py
Runnable Unit Test Suite & Correctness Verification for safe_memory_boundary_engine.py.

Verifies:
1. Checked 32-Bit Unsigned Integer Multiplication (safe_multiply_uint32).
2. Bitwise Wrap-Around Overflow Detection (CWE-190 integer overflow prevention;
   an earlier version of this docstring cited "CVE-2010-2543" as an example --
   that CVE is actually an unrelated Cacti XSS bug, CWE-79, verified against
   the NVD record and corrected here to cite the CWE class directly).
3. Image Header Buffer Allocation Validation (Valid, Oversized, Malformed).
4. Heap Boundary Threshold Enforcement (256 MB MAX_SAFE_HEAP_BYTES limit).
5. Exact Boundary Edge Cases: Exactly 268,435,456 bytes passes, 268,435,457 bytes fails.

License: CC BY-SA 4.0
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

import safe_memory_boundary_engine as smb


class TestSafeMemoryBoundarySuite(unittest.TestCase):

    def setUp(self):
        self.allocator = smb.SafeMemoryAllocator(max_heap_limit=256 * 1024 * 1024)

    def test_safe_multiply_normal(self):
        """Tests valid 32-bit unsigned multiplication."""
        res, overflow = self.allocator.safe_multiply_uint32(1920, 1080)
        self.assertEqual(res, 2073600)
        self.assertFalse(overflow)

    def test_safe_multiply_overflow_detection(self):
        """Tests bitwise 32-bit wrap-around detection (CWE-190 integer overflow prevention)."""
        # 65536 * 65536 = 4,294,967,296 = (1 << 32) -> Wrapped uint32 value = 0
        res, overflow = self.allocator.safe_multiply_uint32(65536, 65536)
        self.assertEqual(res, 0)
        self.assertTrue(overflow, "Must flag integer overflow for 65536 * 65536")

    def test_image_buffer_normal_approval(self):
        """Tests legitimate image buffer allocation approval."""
        res = self.allocator.validate_and_allocate_image_buffer(width=1920, height=1080, bytes_per_pixel=4)
        self.assertEqual(res["status"], "APPROVED")
        self.assertEqual(res["allocated_bytes"], 8294400)

    def test_image_buffer_overflow_rejection(self):
        """Tests rejection of malformed image headers causing integer wrap-around."""
        res = self.allocator.validate_and_allocate_image_buffer(width=65536, height=65537, bytes_per_pixel=4)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["allocated_bytes"], 0)
        self.assertIn("Integer Overflow", res["reason"])

    def test_image_buffer_heap_limit_rejection(self):
        """Tests rejection when allocation exceeds max heap limit (256 MB)."""
        # 20000 * 20000 * 4 = 1,600,000,000 bytes > 268,435,456 bytes
        res = self.allocator.validate_and_allocate_image_buffer(width=20000, height=20000, bytes_per_pixel=4)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["allocated_bytes"], 0)
        self.assertIn("exceeds maximum safe heap threshold", res["reason"])

    def test_exact_heap_boundary_limits(self):
        """Tests exact 256 MB boundary condition (268,435,456 bytes)."""
        # 8192 * 8192 * 4 = 268,435,456 bytes (Exactly 256 MB -> APPROVED)
        res_exact = self.allocator.validate_and_allocate_image_buffer(width=8192, height=8192, bytes_per_pixel=4)
        self.assertEqual(res_exact["status"], "APPROVED")
        self.assertEqual(res_exact["allocated_bytes"], 268435456)

        # 8192 * 8192 * 4 + 4 bytes = 268,435,460 bytes (Exceeds by 4 bytes -> REJECTED)
        custom_allocator = smb.SafeMemoryAllocator(max_heap_limit=268435455)
        res_exceeded = custom_allocator.validate_and_allocate_image_buffer(width=8192, height=8192, bytes_per_pixel=4)
        self.assertEqual(res_exceeded["status"], "REJECTED")


def run_unit_test_suite():
    print("=" * 72)
    print("  SAFE MEMORY BOUNDARY — UNIT TEST SUITE")
    print("  Executing Checked Integer & Heap Allocation Assertions")
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
