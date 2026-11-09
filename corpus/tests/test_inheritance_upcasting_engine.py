#!/usr/bin/env python3
"""
test_inheritance_upcasting_engine.py
Runnable unit test suite for inheritance_upcasting_engine.py.

The core thing under test is NOT "do these classes exist" — it's
"does calling a method through a base-class-typed reference correctly
dispatch to the most-derived override." Every test here calls the
upcast_and_*() functions, which only know about Vehicle, and checks
that SportsCar/Car behavior still surfaces correctly.
"""

import sys
import unittest
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from inheritance_upcasting_engine import (
    Vehicle, Car, SportsCar,
    upcast_and_describe, upcast_and_get_max_speed, upcast_and_get_sound,
    process_vehicle_fleet,
)


class TestInheritanceUpcasting(unittest.TestCase):

    def test_base_class_behavior_directly(self):
        v = Vehicle("Generic")
        self.assertEqual(v.describe(), "Generic is a generic vehicle.")
        self.assertEqual(v.max_speed_kph(), 120)
        self.assertEqual(v.sound(), "...")

    def test_upcast_dispatches_to_most_derived_describe(self):
        # The critical test: pass a SportsCar into a function that only
        # knows about the Vehicle interface, and confirm SportsCar's
        # OWN describe() ran -- not Vehicle's, not Car's.
        sc = SportsCar("Ferrari")
        result = upcast_and_describe(sc)
        self.assertEqual(result, "Ferrari is a sports car built for speed.")
        self.assertNotEqual(result, Vehicle.describe(sc))  # not base behavior
        self.assertNotEqual(result, Car.describe(sc))       # not mid behavior

    def test_upcast_dispatches_to_most_derived_max_speed(self):
        sc = SportsCar("Lamborghini")
        self.assertEqual(upcast_and_get_max_speed(sc), 320)

    def test_upcast_dispatches_to_most_derived_sound(self):
        sc = SportsCar("Bugatti")
        self.assertEqual(upcast_and_get_sound(sc), "VROOOOM")

    def test_mid_level_car_dispatch_not_confused_with_base_or_derived(self):
        # A plain Car (not a SportsCar) upcast to Vehicle must get
        # Car's overrides, not Vehicle's defaults and not SportsCar's.
        c = Car("Sedan")
        self.assertEqual(upcast_and_describe(c), "Sedan is a car with 4 wheels.")
        self.assertEqual(upcast_and_get_max_speed(c), 180)
        self.assertEqual(upcast_and_get_sound(c), "Vroom")

    def test_heterogeneous_fleet_each_dispatches_independently(self):
        # This is the realistic use case: a list typed/treated as
        # list[Vehicle], containing a mix of concrete subclasses.
        # Each element must independently resolve to ITS OWN override,
        # proving dispatch is per-instance, not fixed by declared type.
        fleet = [
            Vehicle("Base"),
            Car("Sedan"),
            SportsCar("Ferrari"),
        ]
        results = process_vehicle_fleet(fleet)
        self.assertEqual(results, [
            "Base is a generic vehicle.",
            "Sedan is a car with 4 wheels.",
            "Ferrari is a sports car built for speed.",
        ])

    def test_isinstance_relationships_hold_for_upcasting(self):
        # A SportsCar must genuinely BE a Car and a Vehicle (not just
        # duck-typed similarly) for "upcasting" to be a meaningful claim
        # rather than coincidental method-name overlap.
        sc = SportsCar("Ferrari")
        self.assertIsInstance(sc, SportsCar)
        self.assertIsInstance(sc, Car)
        self.assertIsInstance(sc, Vehicle)

    def test_downcast_incompatible_type_is_not_silently_accepted(self):
        # A bare Vehicle is NOT a Car or SportsCar. If someone tried to
        # treat it as one, that should be detectably false -- this guards
        # against a "fake" upcasting demo where the type hierarchy is
        # cosmetic and isinstance checks would silently lie.
        v = Vehicle("Generic")
        self.assertNotIsInstance(v, Car)
        self.assertNotIsInstance(v, SportsCar)


def run_unit_test_suite():
    print("=" * 72)
    print("  INHERITANCE & UPCASTING ENGINE — UNIT TEST SUITE")
    print("  Verifying Dynamic Dispatch Through Base-Class References")
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
    status = "ALL PASSED (dispatch behavior verified per-assertion above)" if result.wasSuccessful() else "FAILED — see output above"
    print(f"  Result               : {status}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_unit_test_suite()
    sys.exit(0 if success else 1)
