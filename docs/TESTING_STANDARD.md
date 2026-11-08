# TESTING STANDARD — Read This Before Marking Anything VERIFIED

This file is a standing instruction for any AI assistant (Claude, Gemini, or
otherwise) working in this `solo/` folder. If you are an AI assistant and
you are about to write a test file, run a test, or report a result to the
user, read this first.

## The problem this document exists to prevent

Early in this project, `test_all_engines.py` reported "PASSED " for 16
engines based only on `exit code == 0`. That means "the script didn't
crash." It says nothing about whether the code does what its name claims.
A file that does nothing but `print("ok"); sys.exit(0)` would have passed.

One benchmark script also compared real code against an artificially
delayed fake competitor (`time.sleep()` standing in for "the other
framework"), producing an impressive-looking speedup that measured nothing
real.

Both of these looked fine on the surface. Neither would have survived a
skeptical reader actually opening the file. That is the failure mode this
document exists to prevent, permanently, for every engine added from here on.

## The Standard

Before any engine file can be marked VERIFIED (not RAN_ONLY, not PASSED,
not "done"), its dedicated `test_<engine>.py` must satisfy all three of the
following. No exceptions, no "this one's simple enough to skip it."

### 1. Independent Ground-Truth Reference

The test must check the implementation's output against something computed
by a DIFFERENT method than the implementation itself uses. Acceptable
ground truths, in order of strength:

- **A real, independent library** (e.g. `sklearn`, `hashlib`, `numpy`'s own
  battle-tested linear algebra) — strongest, use this whenever the domain
  has one.
- **A known, published, external test vector** — e.g. the fixed SHA-1 of an
  empty Git blob (`e69de29b...`), a documented protocol constant. Strong
  because it doesn't depend on anything in this codebase at all.
- **A hand-derived reference computed a genuinely different way** — e.g. a
  plain-Python nested-loop version checked against a vectorized NumPy
  version, or manually-constructed expected bytes checked against the
  function's output. Acceptable when no library or published vector exists,
  but must NOT share code with the implementation under test (if the
  "independent" check calls the same helper function, it isn't independent).

**Not acceptable:** asserting the implementation returns whatever its own
internal computation produces. That is not a test, it's a tautology.

### 2. Exhaustive Boundary & Edge Cases

Every function must be tested at its boundaries, not just its comfortable
middle. At minimum, check:

- Empty input (empty string, empty list, zero-length array)
- Zero and negative values where the domain allows them
- The exact boundary value itself (e.g. `INT32_MAX`, not just values near it)
- One-past-the-boundary (e.g. `INT32_MAX + 1`) — this is where off-by-one
  bugs live
- Type confusion (e.g. `bool` passed where `int` expected — `bool` is a
  subclass of `int` in Python and silently slips through naive type checks)
- `None` / null input if the function could plausibly receive it

If the function's whole purpose IS a boundary condition (e.g. overflow
guards, buffer bounds), the edge case tests are not optional extras — they
are the primary test, and the "normal case" tests are the secondary ones.

### 3. Adversarial Break-It Proof

Before considering a test suite trustworthy, deliberately break the
implementation in a way that represents a real, plausible bug for that
domain, and confirm the test suite catches it. Specific examples already
used in this codebase:

- Buffer bounds: changed `>=` to `>` in a bounds check (the canonical C
  off-by-one) — caught by the test.
- Overflow guard: removed the overflow check entirely — caught.
- Lazy instantiation: made the "lazy" property eager instead — caught.
- SHA-1 hashing: changed a null byte to a space in the object header (a
  one-character change producing a completely different but equally
  plausible-looking 40-char hex hash) — caught.
- Polymorphic dispatch: hardcoded a call to the BASE class method instead
  of relying on the subclass override — caught.

**Document the specific bug you injected and confirm the specific test
that failed, in your response to the user.** Do not just say "I verified
this passes." Show the break, show the failure, then show the restored
clean pass. This is the single most important step in this whole standard
— it is the difference between a test that checks something and a test
that exists for appearances.

## What to report to the user

When you finish a test suite, report honestly using this framing:

```
Engine: <name>
Tests: <N> total, <N> passed, <N> failed
Ground truth used: <specific library/vector/independent method — name it>
Break-it check performed: <specific bug injected> -> <specific test that
  failed as a result>
Status: VERIFIED / RAN_ONLY / FAILED
```

Do NOT report just " PASSED" or "100% success" without the above detail.
A green checkmark with no supporting detail is exactly the pattern that
caused the original problem.

## The runner's status categories

`test_all_engines.py` uses four categories. Know what each one actually
means before using it:

- **VERIFIED** — a dedicated test file exists, follows the standard above
  (ground truth + edge cases + break-it proof was performed during
  development), and currently passes.
- **RAN_ONLY** — the engine executes without crashing but has NO
  dedicated correctness test. This is NOT evidence the engine works. Never
  describe a RAN_ONLY engine as "working" or "passing" to the user.
- **FAILED** — a test exists and its assertions failed.
- **MISSING** — the file doesn't exist on disk yet.

If you write an engine and do not have time to write its full test suite
in the same session, leave it as RAN_ONLY and say so plainly. Do not
imply it is more verified than it is.

## One instruction that applies regardless of which AI is reading this

If you are unsure whether a comparison, benchmark, or test is fair —
stop and flag the uncertainty to the user rather than resolving it in
whichever direction makes the result look better. Every case in this
project where something needed correcting was caught by asking "would a
skeptical reader be able to poke a hole in this claim in under a minute?"
Ask that question before reporting anything as done.
