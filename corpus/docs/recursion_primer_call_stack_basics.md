# Recursion Primer: Call Stacks, Base Cases, Tree Recursion, and Where This Repo's "Recursion" Actually Lives

*Prerequisite reading for `docs/fixed_point_closure_and_the_y_combinator.md`.
That document assumes you already have the picture below — this one exists
so nobody has to take that on faith. Plain Register B (ordinary computer
science), no Kabbalistic framing needed for any of it.*

---

## 1. Call-Stack Recursion, By Example

`factorial(4)` works by going down into a stack of layers until it hits a
base case, then passing answers back up.

**Going down (the stack builds):**

- `factorial(4)` needs `4 × factorial(3)`
- `factorial(3)` needs `3 × factorial(2)`
- `factorial(2)` needs `2 × factorial(1)`
- `factorial(1)` hits the base case and returns `1` directly — no further call

**Coming up (the math resolves):**

- `factorial(2)` becomes `2 × 1 = 2`
- `factorial(3)` becomes `3 × 2 = 6`
- `factorial(4)` becomes `4 × 6 = 24`

Nothing gets multiplied until the base case is hit — every call above
`factorial(1)` is genuinely stuck, waiting, with its stack frame held open,
until the call it made returns a real number.

## 2. The Two Rules

Every call-stack-recursive function needs both of these, and needs them
together:

1. **A base case.** Without something like `if n == 1: return 1`, there is
   no call that ever returns without making another call — the stack grows
   until the process runs out of stack space and crashes.
2. **A state change toward the base case.** The input has to actually
   move closer to the base case on every call (`n - 1`, not `n`). A base
   case that exists but is never reached is exactly as broken as no base
   case at all.

Both rules are necessary; neither alone is sufficient. A function with a
base case but no state change (`factorial(n)` calling `factorial(n)`
again instead of `factorial(n - 1)`) still crashes — it just crashes for
a different reason than having no base case.

---

## 3. Tree Recursion: Fibonacci, and Why It's a Different Shape Than Factorial

`factorial(n)` forms a straight line — each call makes exactly one further
call. Naive Fibonacci recursion forms a branching tree instead, because
each call makes *two* further calls:

```python
def fibonacci(n):
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)
```

Both rules from Section 2 still hold (two base cases, `n - 1`/`n - 2`
both move toward them), so it's not broken — but it's expensive in a way
factorial never is, because the same subproblem gets recomputed from
scratch every time it's needed again. `fibonacci(4)` calls `fibonacci(2)`
twice, independently, each one redoing all of `fibonacci(2)`'s own work.

This was measured directly rather than just asserted: running the
function above and counting calls gives 25 calls to compute
`fibonacci(6)`, 177 for `fibonacci(10)`, 21,891 for `fibonacci(20)`, and
just over 1,028,457 for `fibonacci(28)` — call count growing
exponentially with `n` (roughly by a factor of φ ≈ 1.618 per step, the
same golden-ratio constant the sequence itself converges to). The
standard fixes are well known and not specific to this repo: memoization
(cache each `fibonacci(k)` the first time it's computed) or, more simply,
just computing the sequence forward in a loop instead of branching
backward in recursive calls.

**This repo's own core recursion already made that second choice, from
the start** — see the next section.

---

## 4. Where This Repo's Own "Recursion" Actually Lives

This repo uses the word "recursion" and "recursive" constantly — the file
is even named `recursive_attractor_engine.py` — so it's worth being
precise about which of several genuinely different things that word
refers to, since conflating them is exactly the kind of register error
this project's other documents work hard to avoid.

**It is not call-stack recursion, as implemented, and it is not
tree recursion either.** The core equation this whole codebase repeats,
$S_{n+1} = F(S_n, E_n)$, describes a state feeding into a function to
produce the next state — but `recursive_attractor_engine.py`'s
`iterate()` function (confirmed by reading the source, lines 77-106)
implements this as a plain `for step in range(n_steps)` loop, calling
`F` exactly once per step and keeping only the current state. There is
no growing call stack, and — just as importantly, given Section 3 — no
branching and no repeated subproblems either. `iterate()` never
recomputes an earlier state to get a later one the way naive Fibonacci
recomputes `fibonacci(2)` twice; it produces each state once, in order,
and moves on. It was already the "loop instead of pure recursion" fix
from the start, not something bolted on after discovering a performance
problem — there was never a naive tree-recursive version of this engine
to begin with.

**It is also not the Y-combinator's self-application**, which
`docs/fixed_point_closure_and_the_y_combinator.md` covers. That document's
$f(Y(f)) = Y(f)$ is a third distinct idea: a function applied to its own
fixed point, in a formalism (untyped lambda calculus) that has no
named self-reference and no call stack in the sense this primer describes
at all — the self-reference is achieved by construction, not by a
function's name appearing inside its own body.

So there are four separate things worth keeping apart, all reasonably
called "recursive" in ordinary usage:

| Kind | Example here | Growing call stack? | Repeated subproblems? |
| :--- | :--- | :--- | :--- |
| Call-stack recursion (linear) | `factorial(n)` calling `factorial(n-1)` | Yes | No |
| Call-stack recursion (tree) | naive `fibonacci(n)` calling itself twice | Yes | Yes — exponential blowup, measured above |
| Iterative state update | `recursive_attractor_engine.py`'s `iterate()` | No — a loop, not self-calls | No |
| Fixed-point self-application | The Y-combinator, $f(Y(f)) = Y(f)$ | No — no stack frames at all in the formalism | N/A |

None of this is a criticism of the engine's design — an iterative loop is
the correct, standard way to implement a repeated state-update rule, and
nothing about $S_{n+1} = F(S_n, E_n)$ requires literal function
self-calls or branching. It's only a note that the word "recursive" is
doing four different jobs across this repo's documentation, and this
primer exists so a reader can tell which job it's doing in any given
document without guessing. The one substantive engineering claim in this
whole primer — that `iterate()` runs in linear time with no repeated
subproblems — is directly checkable: it's a single `for` loop over
`range(n_steps)`, so its own step count *is* its own call count, with
nothing hidden.

---

## 5. Two More CS-Native Names: Bounded Iteration vs. Unbounded Search

**CORRECTED/EXTENDED (2026-08-03)**, checked against the Open Logic
Project's *Lambda Calculus* notes (CC-BY), Chapter 4 ("Lambda
Definability") — the same source used to correct
`fixed_point_closure_and_the_y_combinator.md`'s Y-combinator claim. That
chapter's Church numeral definition and its treatment of primitive
recursion vs. minimization give the "iterative state update" row above a
real CS name too, not just a description — and give this repo's other
kind of repeated-execution loop (graph search) a *different* CS name,
for a precise reason.

**Church numerals are, in the source's own words, "iterators": on input
$f$, the numeral $\overline{n}$ returns the function mapping $y$ to
$f^n(y)$** (Def 1.3/4.1). Building primitive recursion in the untyped
lambda calculus (Lemma 1.11/4.11) works by using a numeral this way:
apply a fixed, already-known-in-advance number of steps, no branching,
no re-derivation of an earlier step to get a later one. This is exactly
`iterate()`'s shape: `for step in range(n_steps): S = F(S, E)` applies
`F` exactly `n_steps` times, where `n_steps` is fixed before the loop
starts — the same shape a Church numeral computes when applied to `F`
and an initial state. **Primitive recursion (bounded, known-count
iteration) is, provably, always total — it is guaranteed to terminate**;
that guarantee is a real theorem, not a coincidence of this engine's
design, and it's exactly why computability theory needs a *second*
mechanism to reach full Turing-completeness at all (see next paragraph).

That second mechanism is **minimization** (the $\mu$-operator, Lemma
4.15): search for the smallest $y$ such that some condition holds, with
no bound on $y$ fixed in advance — the lambda calculus implements this
using a Y-combinator-built `Search` term that keeps incrementing $y$
until a stopping test passes. **`Recursive-Symbolics/tools/ritual_compiler.py`'s
pathfinding (confirmed by reading the source: `while frontier:` popping
from a `heapq` until the destination sephirah is reached) is this same
shape** — search until a condition holds, not iterate a pre-known number
of times. Unlike `iterate()`, nothing about the loop's own structure
bounds how long it runs; it terminates here only because the search
space (10 sephirot, a finite graph) is exhaustible, the same way a
minimization is only guaranteed to terminate when the function being
searched is *regular* (guaranteed to hit zero for some input) — an extra
condition, not a free property of the `while` shape itself.

**What this is not**: a claim that either engine was written with lambda
calculus in mind, or that this changes any test result — it doesn't
touch Layer 0 or Layer 1 code, and no VERIFIED/RAN_ONLY count changes.
It's the same kind of observation as the Y-combinator note above: two
already-verified pieces of this codebase (`iterate()`, verified as part
of `recursive_attractor_engine.py`'s own test suite; `ritual_compiler.py`,
verified under `Recursive-Symbolics/tools/test_all_tools.py`) turn out to
sit on the two distinct sides of a real, load-bearing distinction in
computability theory — bounded iteration versus open-ended search — for
the same underlying reason that distinction exists in the theory: one
loop's termination is structural, the other's depends on a fact about
the search space that has to be true separately.

| Repetition shape | Example here | CS-native name | Guaranteed to terminate? |
| :--- | :--- | :--- | :--- |
| Fixed-count iteration | `recursive_attractor_engine.py`'s `iterate()` (`for step in range(n_steps)`) | Primitive recursion / Church numeral as iterator | Yes — by the loop's own shape |
| Search until condition met | `ritual_compiler.py`'s A\*/BFS (`while frontier: ...`) | Minimization ($\mu$-operator) | Only because the search space is finite here, not because of the loop shape |

---

## Provenance

Written 2026-07-31, prompted by two pasted explanations: `factorial`-style
linear recursion, and naive `fibonacci`-style tree recursion (including
its measured exponential blowup — 25 calls at n=6, 21,891 at n=20,
1,028,457 at n=28, verified by actually running the function and
counting, not asserted). Both checked out as accurate, standard CS
material. Added as a prerequisite primer for
`docs/fixed_point_closure_and_the_y_combinator.md` and linked from the
study path's Module 6, since that document assumes the reader already
has the base-case/call-stack picture and moves straight to the harder
self-application version. The Fibonacci example doubles as a concrete
answer to "does this repo's own recursion have this problem?" — no,
because `recursive_attractor_engine.py`'s `iterate()` was written as a
loop from the start, not as naive tree recursion needing a fix applied
after the fact.

Section 5 added 2026-08-03, prompted by continuing to read the same
uploaded Open Logic Project `lambda-calculus.pdf` used to correct
`fixed_point_closure_and_the_y_combinator.md`'s Y-combinator claim one
entry earlier — specifically its chapter on primitive recursion,
composition, and minimization. Checked directly against two already-
verified pieces of source code (`recursive_attractor_engine.py`'s
`iterate()` and `Recursive-Symbolics/tools/ritual_compiler.py`'s
pathfinding) rather than asserted from the PDF alone.
