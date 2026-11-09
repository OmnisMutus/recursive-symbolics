#!/usr/bin/env python3
"""
test_briah_composition_engine.py
Runnable unit test suite for briah_composition_engine.py.

Verifies:
1. Null Initial State: BriahSprinklerSystem initializes with _water_source and _soap_container as None (0 memory overhead).
2. On-Demand Lazy Instantiation: Accessing property .water_source or .soap_container triggers instantiation only on first access.
3. Instance Caching: Subsequent accesses return the exact same instance until collapsed.
4. Ephemeral Security Collapse: collapse_ephemeral_state() explicitly resets fields back to None.
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

import briah_composition_engine as briah


class TestBriahCompositionSuite(unittest.TestCase):

    def test_uninitialized_lazy_fields(self):
        """Assures system initializes with NULL references (zero memory overhead)."""
        sys_obj = briah.BriahSprinklerSystem("Test System")
        self.assertIsNone(sys_obj._water_source)
        self.assertIsNone(sys_obj._soap_container)

    def test_lazy_instantiation_on_access(self):
        """Assures fields are instantiated on-demand ONLY when accessed via property."""
        sys_obj = briah.BriahSprinklerSystem("Test System")
        
        # Access water_source property
        water = sys_obj.water_source
        self.assertIsNotNone(sys_obj._water_source)
        self.assertIsInstance(water, briah.WaterSource)
        self.assertEqual(water.source_name, "Malkuth Flow Baseline")

        # Access soap_container property
        soap = sys_obj.soap_container
        self.assertIsNotNone(sys_obj._soap_container)
        self.assertIsInstance(soap, briah.SoapContainer)
        self.assertEqual(soap.formula, "Chesed Purification")

    def test_repeated_access_returns_cached_instance(self):
        """Assures repeated access returns the existing instance rather than re-instantiating."""
        sys_obj = briah.BriahSprinklerSystem("Test System")
        w1 = sys_obj.water_source
        w2 = sys_obj.water_source
        self.assertIs(w1, w2, "Property access must return the cached instance")

    def test_ephemeral_state_collapse(self):
        """Assures ephemeral state collapse resets instantiated fields back to None."""
        sys_obj = briah.BriahSprinklerSystem("Test System")
        _ = sys_obj.water_source
        _ = sys_obj.soap_container
        self.assertIsNotNone(sys_obj._water_source)

        sys_obj.collapse_ephemeral_state()
        self.assertIsNone(sys_obj._water_source, "Collapse must reset _water_source to None")
        self.assertIsNone(sys_obj._soap_container, "Collapse must reset _soap_container to None")


def run_unit_test_suite():
    print("=" * 72)
    print("  BRIAH LAYER OBJECT COMPOSITION — UNIT TEST SUITE")
    print("  Verifying Lazy Ephemeral Instantiation & State Collapse")
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
