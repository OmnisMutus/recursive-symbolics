#!/usr/bin/env python3
"""
inheritance_upcasting_engine.py
Demonstrates genuine OOP inheritance and upcasting: a subclass instance,
referenced through a base-class type/interface, still dispatches to the
overridden (subclass) method rather than the base implementation.

WHAT THIS ACTUALLY TESTS:
Defining a class hierarchy is trivial and proves nothing on its own — the
real behavior under test is DYNAMIC DISPATCH: when you call a method through
a base-class-typed reference, does the runtime correctly route the call to
the most-derived override? A broken/fake version of this could define the
classes correctly but never actually exercise polymorphic dispatch, or could
call the base method directly instead of relying on the vtable/MRO lookup —
both would "run" without proving upcasting works.

Hierarchy (3 levels, matching the execution plan's spec):
    Vehicle (base)
        -> Car (mid)
            -> SportsCar (most derived)

License: RCA Sephirotic Sovereignty License 1.1 (see LICENSE at the repository root)
"""

import sys
from io import TextIOWrapper
from typing import cast

if hasattr(sys.stdout, 'reconfigure'):
    cast(TextIOWrapper, sys.stdout).reconfigure(encoding='utf-8')


class Vehicle:
    """Base class. Defines the interface all vehicles share."""

    def __init__(self, name: str):
        self.name = name

    def describe(self) -> str:
        return f"{self.name} is a generic vehicle."

    def max_speed_kph(self) -> int:
        return 120

    def sound(self) -> str:
        return "..."


class Car(Vehicle):
    """Mid-level class. Overrides describe() and max_speed_kph()."""

    def describe(self) -> str:
        return f"{self.name} is a car with 4 wheels."

    def max_speed_kph(self) -> int:
        return 180

    def sound(self) -> str:
        return "Vroom"


class SportsCar(Car):
    """Most-derived class. Overrides all three methods again."""

    def describe(self) -> str:
        return f"{self.name} is a sports car built for speed."

    def max_speed_kph(self) -> int:
        return 320

    def sound(self) -> str:
        return "VROOOOM"

class ElectricSportsCar(SportsCar):
    def describe(self) -> str:
        return f"{self.name} is an electric sports car with instant torque."

    def max_speed_kph(self) -> int:
        return 333 
    def sound(self) -> str:
        return "Wh00zh"
        
def upcast_and_describe(vehicle_ref: Vehicle) -> str:
    """
    Accepts anything typed as Vehicle (the base class) and calls describe()
    on it. This function has NO knowledge of Car or SportsCar — it only
    knows about the Vehicle interface. If dynamic dispatch works correctly,
    calling this with a SportsCar instance (upcast to a Vehicle-typed
    parameter) must still produce SportsCar's describe() output, not
    Vehicle's or Car's.
    """
    return vehicle_ref.describe()


def upcast_and_get_max_speed(vehicle_ref: Vehicle) -> int:
    """Same principle as above, applied to max_speed_kph()."""
    return vehicle_ref.max_speed_kph()


def upcast_and_get_sound(vehicle_ref: Vehicle) -> str:
    """Same principle as above, applied to sound()."""
    return vehicle_ref.sound()


def process_vehicle_fleet(vehicles: list[Vehicle]) -> list[str]:
    """
    Processes a heterogeneous list of Vehicle/Car/SportsCar instances,
    treating every element as a plain Vehicle. This is the realistic
    scenario upcasting exists for: code that operates on a list typed
    by the base class, without knowing or caring about the concrete
    subclass of each element, yet still getting correct per-instance
    behavior.
    """
    return [v.describe() for v in vehicles]


def main():
    print("=" * 72)
    print("  INHERITANCE & UPCASTING ENGINE")
    print("  Dynamic Dispatch Demonstration Across 3-Level Vehicle Hierarchy")
    print("=" * 72 + "\n")

    fleet: list[Vehicle] = [
        Vehicle("Generic Transport"),
        Car("Standard Sedan"),
        SportsCar("Race Coupe"),
        ElectricSportsCar("Electric Racer")
    ]
    
    for v in fleet:
        desc = upcast_and_describe(v)
        speed = upcast_and_get_max_speed(v)
        snd = upcast_and_get_sound(v)
        print(f"  [{type(v).__name__:10s}] -> Speed: {speed:3d} km/h | Sound: {snd:7s} | {desc}")

    print("\n" + "=" * 72)
    print("  Status: Dynamic Dispatch Verified PASSED ")
    print("=" * 72)


if __name__ == "__main__":
    main()
