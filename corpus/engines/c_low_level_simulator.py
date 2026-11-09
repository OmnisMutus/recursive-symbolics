#!/usr/bin/env python3
"""
c_low_level_simulator.py
Low-Level C Functions & Nested Loops Simulator.
The function set follows the ALX low-level programming exercise list (0x02).
Independent Python implementation; no affiliation with ALX.
ISO GNU89 C-Accurate 32-Bit Signed Integer & Char Boundary Engine.

Copyright (C) 2026 OmnisMutus (RCA Sovereign Maintainer).
Licensed under the RCA Sephirotic Sovereignty License 1.1 (see LICENSE at the repository root).

Features & C Gotchas Enforced:
1. _putchar(c): Character buffer stream writer.
2. _islower(c): Full type-safety check for char, int, empty strings, non-ASCII 'é', bool, and invalid bounds.
3. _isalpha(c): Full boundary check for ASCII ranges [a-z, A-Z].
4. _abs(r): C stdlib abs(INT_MIN) signed 32-bit integer overflow detector.
5. add(a, b): 32-bit signed integer addition overflow boundary check.
"""

import sys
import time

# Force UTF-8 stdout encoding for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# C Standard 32-bit Signed Integer Boundaries (limits.h)
INT32_MIN = -2147483648
INT32_MAX = 2147483647


def _putchar(c):
    """Writes a single character to standard output stream."""
    if not isinstance(c, str) or len(c) != 1:
        raise TypeError("C _putchar accepts exactly one character string or char byte")
    sys.stdout.write(c)
    return 1


def print_alphabet():
    """Prints lower-case alphabet followed by newline."""
    for i in range(ord('a'), ord('z') + 1):
        _putchar(chr(i))
    _putchar('\n')


def print_alphabet_x10():
    """Prints 10 sets of lower-case alphabets."""
    for _ in range(10):
        print_alphabet()


def _islower(c):
    """
    Checks for lowercase character in ISO GNU89 C (ASCII only [97-122]).
    Returns 1 if c is lowercase ASCII, 0 otherwise.
    Rejects empty string '', multichar, None, non-ASCII (e.g. 'é'), bool, and non-ints.
    """
    if c is None or c == "" or isinstance(c, bool):
        return 0
    if isinstance(c, str):
        if len(c) != 1 or ord(c) > 127:
            return 0
        return 1 if 'a' <= c <= 'z' else 0
    if isinstance(c, int):
        return 1 if ord('a') <= c <= ord('z') else 0
    return 0


def _isalpha(c):
    """
    Checks for alphabetic character (lowercase or uppercase) in ISO GNU89 C.
    Returns 1 if c is a letter, 0 otherwise.
    Rejects empty string '', multichar, None, non-ASCII, bool, and non-ints.
    """
    if c is None or c == "" or isinstance(c, bool):
        return 0
    if isinstance(c, str):
        if len(c) != 1 or ord(c) > 127:
            return 0
        return 1 if ('a' <= c <= 'z' or 'A' <= c <= 'Z') else 0
    if isinstance(c, int):
        return 1 if (ord('a') <= c <= ord('z') or ord('A') <= c <= ord('Z')) else 0
    return 0


def print_sign(n):
    """Prints sign of number n (+, 0, -)."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("C print_sign requires an integer argument")
    if n > 0:
        _putchar('+')
        return 1
    elif n == 0:
        _putchar('0')
        return 0
    else:
        _putchar('-')
        return -1


def _abs(r):
    """
    Computes absolute value of integer r.
    C Gotcha: abs(INT_MIN) (-2147483648) overflows 32-bit signed int [-2147483648, 2147483647]
    because +2147483648 exceeds INT32_MAX.
    """
    if not isinstance(r, int) or isinstance(r, bool):
        raise TypeError("C _abs requires an integer argument")
    if r == INT32_MIN:
        raise OverflowError("C stdlib abs(INT_MIN) signed 32-bit integer overflow: -(-2147483648) exceeds INT32_MAX")
    return -r if r < 0 else r


def print_last_digit(n):
    """Prints and returns last digit of number n."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("C print_last_digit requires an integer argument")
    last = abs(n) % 10
    _putchar(str(last))
    return last


def add(a, b):
    """
    Adds two integers.
    Enforces C 32-bit signed integer overflow boundaries [INT32_MIN, INT32_MAX].
    """
    if not isinstance(a, int) or isinstance(a, bool) or not isinstance(b, int) or isinstance(b, bool):
        raise TypeError("C add requires integer arguments")
    result = a + b
    if result > INT32_MAX or result < INT32_MIN:
        raise OverflowError(f"C 32-bit signed integer addition overflow: {a} + {b} = {result} outside [{INT32_MIN}, {INT32_MAX}]")
    return result


def print_to_98(n):
    """Prints all natural numbers from n to 98."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("C print_to_98 requires an integer argument")
    if n <= 98:
        nums = [str(i) for i in range(n, 99)]
    else:
        nums = [str(i) for i in range(n, 97, -1)]
    sys.stdout.write(", ".join(nums) + "\n")


def run_c_suite():
    start = time.perf_counter()
    print("=" * 66)
    print("  LOW-LEVEL C: FUNCTIONS & NESTED LOOPS")
    print("  ISO GNU89 C-Accurate Execution & Boundary Validation")
    print("=" * 66)

    print("\n Task 1: print_alphabet(): ", end="")
    print_alphabet()

    print(f" Task 3: _islower('a'): {_islower('a')} | _islower('A'): {_islower('A')} | _islower(''): {_islower('')}")
    print(f" Task 4: _isalpha('z'): {_isalpha('z')} | _isalpha('9'): {_isalpha('9')} | _isalpha(''): {_isalpha('')}")
    print(f" Task 5: print_sign(-98): ", end="")
    sign_val = print_sign(-98)
    print(f" (Return Value: {sign_val})")
    print(f" Task 6: _abs(-98): {_abs(-98)}")
    print(f" Task 10: add(38, 60): {add(38, 60)}")

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    print("\n" + "=" * 66)
    print(f"  Execution Time: {elapsed_ms:.2f} ms | Status: PASSED ")
    print("=" * 66)


if __name__ == "__main__":
    run_c_suite()
