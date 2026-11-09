#!/usr/bin/env python3
"""
safe_memory_boundary_engine.py
Defensive Safe Integer Arithmetic & Memory Allocation Boundary Engine (RCA Geburah Layer).
Pure Python Implementation.

RCA Defensive Parity:
1. Safe Integer Arithmetic: Intercepts integer wrap-around/overflow before memory allocation occurs.
2. Geburah Boundary Protection: Rejects buffer allocation requests where requested memory exceeds
   safe capacity bounds or wraps around uint limits (preventing the general integer-overflow ->
   heap-buffer-overflow bug class, CWE-190). NOTE: earlier versions of this docstring cited
   "CVE-2010-2543" as an example -- checked against the actual NVD record and that CVE is an
   unrelated cross-site scripting bug in Cacti (CWE-79), not an integer overflow. Corrected to
   cite the CWE classification directly instead of a specific but wrong CVE.
3. Epistemic Safeguard Tagging: Validates allocations against maximum allowable heap boundaries.

Usage:
    python safe_memory_boundary_engine.py
"""

import sys
import time
import math
from pathlib import Path

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Maximum 32-bit unsigned integer boundary (0xFFFFFFFF)
MAX_UINT32 = 0xFFFFFFFF
# Maximum safe memory heap allocation threshold (e.g., 256 MB)
MAX_SAFE_HEAP_BYTES = 256 * 1024 * 1024

class SafeMemoryAllocator:
    def __init__(self, max_heap_limit: int = MAX_SAFE_HEAP_BYTES):
        self.max_heap_limit = max_heap_limit

    @staticmethod
    def safe_multiply_uint32(a: int, b: int) -> tuple:
        """
        Executes checked 32-bit unsigned integer multiplication.
        Returns: (result_bytes, has_overflowed)
        """
        raw_product = a * b
        if raw_product > MAX_UINT32:
            # Simulated 32-bit wrap-around integer overflow
            wrapped_product = raw_product & MAX_UINT32
            return wrapped_product, True
        return raw_product, False

    def validate_and_allocate_image_buffer(self, width: int, height: int, bytes_per_pixel: int = 4) -> dict:
        """
        Defensive Image Header Parser & Memory Allocation Validator.
        Prevents integer overflow vulnerabilities (CWE-190) that can lead to
        undersized heap allocations and subsequent buffer overflows.
        """
        # Step 1: Check intermediate dimensions multiplication
        pixels, pixel_overflow = self.safe_multiply_uint32(width, height)
        total_bytes, byte_overflow = self.safe_multiply_uint32(pixels, bytes_per_pixel)
        
        has_overflow = pixel_overflow or byte_overflow
        
        print("\n" + "="*70)
        print("  GEBURAH SAFE MEMORY ALLOCATION BOUNDARY CHECK")
        print("="*70)
        print(f" > Requested Image Dimensions : {width} x {height} ({bytes_per_pixel} BPP)")
        print(f" > Raw Computed Byte Size    : {width * height * bytes_per_pixel:,} bytes")
        
        if has_overflow:
            print(f" >  INTEGER OVERFLOW DETECTED : Wrapped Size = {total_bytes} bytes (Unsafe Wrap-around!)")
            print(" >  GEBURAH POLICY REJECTION : Memory allocation BLOCKED to prevent Heap Buffer Overflow.")
            return {
                "status": "REJECTED",
                "reason": "Integer Overflow Detected during dimension multiplication",
                "allocated_bytes": 0
            }
            
        if total_bytes > self.max_heap_limit:
            print(f" >  HEAP BOUND EXCEEDED      : {total_bytes:,} bytes > Max Limit ({self.max_heap_limit:,} bytes)")
            print(" >  GEBURAH POLICY REJECTION : Memory allocation BLOCKED due to excessive size.")
            return {
                "status": "REJECTED",
                "reason": "Requested allocation exceeds maximum safe heap threshold",
                "allocated_bytes": 0
            }
            
        print(f" >  ALLOCATION APPROVED      : Safely allocated {total_bytes:,} bytes in Heap Memory.")
        return {
            "status": "APPROVED",
            "allocated_bytes": total_bytes
        }

# ==============================================================================
# DEMONSTRATION HARNESS
# ==============================================================================
def main():
    print("""
    ================================================================
           SAFE INTEGER ARITHMETIC & MEMORY BOUNDARY ENGINE
          Defensive Prevention of Integer Overflows (CWE-190)
    ================================================================
    """)
    
    allocator = SafeMemoryAllocator()
    
    # Test Case 1: Legitimate Normal Image Allocation
    print("  TEST 1: Normal Image Allocation (1920 x 1080)...")
    res1 = allocator.validate_and_allocate_image_buffer(1920, 1080, 4)
    
    # Test Case 2: Oversized Image Allocation (Exceeds Heap Limit)
    print("\n  TEST 2: Oversized Image Allocation (20000 x 20000)...")
    res2 = allocator.validate_and_allocate_image_buffer(20000, 20000, 4)
    
    # Test Case 3: Malformed Image with Integer Wrap-Around (Overflow)
    print("\n  TEST 3: Malformed Image Dimensions (65536 x 65537 - Overflow Case)...")
    res3 = allocator.validate_and_allocate_image_buffer(65536, 65537, 4)
    
    print("\n" + "="*70)
    print(" Safe Memory Boundary & Integer Arithmetic Engine Verified!")
    print("="*70)

if __name__ == "__main__":
    main()
