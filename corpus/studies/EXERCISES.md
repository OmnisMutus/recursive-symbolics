# Exercise Workbook: 5 Modules, With Actual Things To Do

This is the missing piece the other study docs didn't have: concrete tasks per
module, each with a way to check your own answer before you look at what the
code does. Same spirit as `TESTING_STANDARD.md` — don't trust that something
works, check it.

Do these in the `solo/` directory so imports resolve:
```powershell
cd "`this corpus`"
```

## How To Use This Workbook

Three habits make the difference between "did the exercises" and actually
learning something:

1. **Predict before you run.** Every exercise below asks you to commit to an
   answer *before* checking it. Write your prediction down somewhere (even a
   scratch comment) before running anything. Guessing wrong and then seeing
   why is where the real learning happens — reading the answer first skips
   that step entirely.
2. **Explain it in one sentence before you check it.** For the "break it on
   purpose" exercises, write one sentence for *why* the break should cause
   the effect described. If you can't, that's a sign to reread the code
   before running it — not a failure.
3. **Worked answers are hidden behind a toggle**, not printed inline. Try the
   problem first; click to reveal only after you've committed to an answer.
   <details><summary>Like this — try not to peek before you've made a guess.</summary>
   This one's just a demo. The real ones are below.
   </details>

Each module ends with an optional ** Stretch** exercise (harder, for if the
base exercises felt easy) and every couple of modules there's a
**Checkpoint** that makes you recall something from an earlier module before
moving on — mixing old and new material back together is proven to help
retention more than doing everything once in a strict sequence.

Each module also ends with a collapsed **Kabbalistic Lens** — an optional
mnemonic reading of that module's exercises against the Tree of Life, using
the actual `SEPHIROT_CENTROIDS` and `BASE_BALANCING_RULES` keyword
associations already defined in `standalone_rca_sandbox.py` (not invented
fresh per exercise). Same status as everything else with this framing
elsewhere in `solo/`: a provisional metaphor and memory aid, not a claim
that inheritance or gradient descent *is* Kabbalistic in any deeper sense.
Skip it entirely if it's not useful to you — nothing else in the workbook
depends on it.

## Before You Start: Safe Revert Setup (Do This Once)

Several exercises below (1.2, 2.4, 4.3) tell you to break something on purpose,
observe it, then revert. Doing that by hand — retyping the original line back
from memory — is exactly the kind of thing that quietly leaves a half-reverted
file behind. `solo/` is now under a **local, private git repository** (no
remote configured — nothing pushes anywhere, `git remote -v` returns empty).
Use it:

1. **Before starting any exercise**, confirm you're starting clean:
   ```powershell
   git status
   ```
   It should say `nothing to commit, working tree clean`. If it doesn't,
   commit or stash whatever's pending first — don't start an exercise on top
   of unrelated uncommitted changes.

2. **Make the exercise edit, run/test it** as the exercise describes.

3. **Revert with git, not memory.** In Visual Studio: open the *Git Changes*
   panel (View → Git Changes), right-click the modified file, and choose
   **Discard Changes**. From a terminal instead:
   ```powershell
   git restore <filename>
   ```
   Either way, this restores the file byte-for-byte to the last commit — no
   risk of a typo, a stray comment, or a half-reverted line surviving.

4. **After finishing real (non-exercise) changes you want to keep** — e.g.
   you extended the fleet in 1.1 and want to keep that — commit them:
   ```powershell
   git add -A
   git commit -m "Module 1: added ElectricSportsCar"
   ```
   Do this *before* starting the next "break it" exercise, so a later
   `git restore` can't accidentally wipe out real progress along with the
   intentional breakage.

5. **Turn wrong predictions into a mistake log.** Whenever your prediction
   doesn't match what actually happened, commit anyway and put both numbers
   in the message:
   ```powershell
   git commit --allow-empty -m "Ex 2.2: predicted k=11 acc ~80%, actual was lower -- underestimated how much the local cluster still dominates"
   ```
   Later, `git log --grep="predicted"` surfaces every place your intuition
   was wrong — a free, personal record of exactly where you learned
   something, more useful than any generic answer key.

Rule of thumb: **exercises that say "revert" → discard/restore with git.
Exercises that say "add" or "extend" (1.1) → commit when you're happy with it.
Wrong prediction → commit the lesson, don't just move on.**

---

## Module 1 (Week 1): OOP & Dynamic Dispatch
**File**: `inheritance_upcasting_engine.py`

**1.1 — Extend the hierarchy.**
Add a fourth class, `ElectricSportsCar(SportsCar)`, overriding all three
methods (pick your own speed/sound, e.g. speed `350`, sound `"WHIRRR"`).
Add an instance to the `fleet` list in `main()`.
*Predict first*: which values should show up in the new row — yours, or
`SportsCar`'s inherited ones?
*Check yourself*: run the script. The new row must show your overridden
values, not `SportsCar`'s (320, "VROOOOM"). If it shows `SportsCar`'s values,
the override didn't take — check your method names match exactly.

**1.2 — Break dispatch on purpose, then find your own bug.**
In `upcast_and_describe()`, temporarily change `vehicle_ref.describe()` to
`Vehicle.describe(vehicle_ref)` (calling the base method directly instead of
letting the object route the call).
*Before running*, write one sentence: why would this make every row print
"is a generic vehicle," even for the `SportsCar`?
*Predict first*, then run and compare against your sentence.
<details><summary>Reveal expected result</summary>
Every row prints "is a generic vehicle" — the reference type stops mattering
because you bypassed dynamic dispatch and called the base implementation
directly, instead of letting Python route the call to the actual object's
class.
</details>
Revert the change before moving on (`git restore inheritance_upcasting_engine.py`
or Discard Changes in VS — see "Safe Revert Setup" above).

**1.3 — Write one assertion, and notice what it does and doesn't protect.**
Add to the bottom of the file (under `if __name__`, before calling `main()`,
or in a scratch script): `assert upcast_and_get_max_speed(SportsCar("x")) == 320`.
*Predict*: will this raise an error or pass silently?
Run it — no output means it passed.

Now reintroduce the bug from 1.2 (`vehicle_ref.describe()` →
`Vehicle.describe(vehicle_ref)`, inside `upcast_and_describe()`) and rerun
*this same speed assertion*. *Predict first*: will it now raise, or still
pass silently?
<details><summary>Reveal what actually happens (and why)</summary>
It still passes silently. `upcast_and_get_max_speed()` calls
`vehicle_ref.max_speed_kph()` — a completely separate method from
`describe()`. The 1.2 bug only breaks dispatch on `describe()`, inside
`upcast_and_describe()`; it never touches `max_speed_kph()` at all. A test
only protects the exact code path it exercises — this assertion protects
speed dispatch, not describe dispatch, even though both are "dynamic
dispatch" in the abstract.
</details>
Confirm this yourself (don't just take the reveal's word for it): with the
1.2 bug still in place, add and run
`assert upcast_and_describe(SportsCar("x")) == "x is a sports car built for speed."`
instead. *This* one raises `AssertionError` — because it actually calls
through the broken code path. Revert the 1.2 bug when you're done
(`git restore inheritance_upcasting_engine.py`).

The lesson here is arguably bigger than either bug: a passing assertion
only tells you the specific path it exercised is fine, not that the
general thing it's named after ("dynamic dispatch works") is fine
everywhere. Match the assertion to the code path you actually care about.

** Stretch 1.4 — Partial overrides.**
Add a class that overrides only 2 of the 3 base methods. *Predict*: for the
method you didn't override, does it use your class's inherited version or
fall back to `Vehicle`'s? Verify by adding it to `fleet` and checking that
one method's output specifically.

<details><summary>Kabbalistic Lens (optional, provisional metaphor)</summary>

- **1.1 (add `ElectricSportsCar`)** is Netzach — persistence and extension.
  You're not modifying `Vehicle`, `Car`, or `SportsCar` at all; you're
  proving the pattern survives being extended by a fourth branch nobody who
  wrote `Vehicle` anticipated. This isn't a loose analogy — it's the Open/
  Closed Principle in different words ("open for extension, closed for
  modification"), and Netzach's "victory" here is specifically that the
  original design wins by *not* needing to be touched. The same root idea
  recurs twice more in the workbook, each time asking something to endure a
  different kind of pressure without reverting to a simpler baseline: 3.3
  asks code to endure repetition (run the concurrency test 20 times, then
  100, then a few more), and 5.4 asks state to endure across time (the
  physics output of one step has to survive as the true input to the next).
  One caution worth carrying forward: your own sandbox pairs Netzach not
  with more Netzach but with Tifereth ("Netzach: Tifereth Harmonious
  Integration") — persistence without an integrating check eventually turns
  a clean hierarchy into a brittle one. Adding a fourth branch cleanly is
  1.1. Adding a tenth without ever stepping back to refactor is the failure
  mode Tifereth exists to catch.
- **1.2 (force `Vehicle.describe(vehicle_ref)`)** severs Yesod, the dispatch
  mechanism connecting the abstract reference to the concrete vessel. Cut
  it, and every branch is forced to speak only in Keter's original tongue —
  every row prints "is a generic vehicle" regardless of which leaf you're
  holding.
- **1.3 (the assertion that doesn't protect what you think it protects)** is
  Gevurah — a contract that only binds the channel it's written on. The
  speed assertion is a real boundary, but it's a boundary on the
  Netzach→Malkuth channel for *speed*, not the Hod→Malkuth channel for
  *description*. Breaking Yesod for `describe()` alone leaves that other
  contract intact and silently passing, because Gevurah's judgment doesn't
  automatically extend across sephirot just because both sit under
  "dynamic dispatch" in the abstract.
- **1.4 (partial override)** is Chesed and Gevurah in direct tension: the
  method you override is Gevurah, a new boundary; the method you leave alone
  is pure Chesed, unrestricted inherited flow straight down from `Vehicle`.

</details>

---

## Module 2 (Week 2): ML & Statistical Math
**Files**: `knn_project.py`, `stat_learning_suite.py`

**2.1 — Hand-compute a distance.**
By hand, before looking below: what's the Euclidean distance between
`[1, 1]` and `[4, 5]`?
<details><summary>Reveal the hand-computation</summary>
$\sqrt{(4-1)^2 + (5-1)^2} = \sqrt{9+16} = \sqrt{25} = 5.0$
</details>
*Check*: `python3 -c "from knn_project import euclidean_distance; print(euclidean_distance([1,1],[4,5]))"` → must print `5.0`.

**2.2 — See what k actually does.**
*Predict first*: will `k=1` or `k=11` give higher training accuracy, and why?
In `run_benchmarks()`, change `KNNClassifier(k=3, ...)` to `k=1`, rerun.
Training accuracy should hit 100% — with k=1, every training point's nearest
neighbor (at distance 0) is itself. Now try `k=11` (all 12 training points
minus one) — accuracy should drop, since each point now votes with almost
the whole dataset instead of its local cluster. This is the bias/variance
tradeoff, seen directly instead of described. If your prediction was wrong,
log it (see "Before You Start," item 5).

**2.3 — Ridge regression at alpha=0 should match plain least squares.**
*Predict first*: at `alpha=0`, will the recovered coefficients differ at all
from ordinary least squares, or match (modulo floating point)?
`RidgeRegression(alpha=0)` on a 1-feature dataset should recover the same
slope/intercept as ordinary least squares (no regularization pulling
coefficients toward zero). Try it:
```python
import numpy as np
from stat_learning_suite import RidgeRegression
X = np.array([[1.0],[2.0],[3.0],[4.0]])
y = np.array([2.0, 4.0, 6.0, 8.0])  # perfect y = 2x
r = RidgeRegression(alpha=0.0)
r.fit(X, y)
print(r.coef_)  # expect ~[0.0, 2.0] (intercept ~0, slope ~2)
```

**2.4 — Break LDA's sign, see it invert.**
In `LDAClassifier.fit()`, change `self.w = np.linalg.solve(S_W, mu1 - mu0)`
to `np.linalg.solve(S_W, mu0 - mu1)` (swapped order).
*Before running*, write one sentence: why should swapping the subtraction
order flip which class the predictions favor?
Predictions for class 0 and class 1 should now flip. This is the same
"sign-flip bug" category as the real one I found and fixed in the OpenGL
renderer's reflection formula — worth noticing how a single swapped term
inverts a whole classifier.
Revert (`git restore stat_learning_suite.py` or Discard Changes in VS).

** Stretch 2.5 — Push alpha much higher.**
Reuse 2.3's dataset with `alpha=1000`. *Predict*: should the recovered slope
stay near 2.0, shrink toward 0, or do something else? Run it and check
`r.coef_` against your prediction — this is what "regularization strength"
actually does to a real fit, not just in the abstract.

<details><summary>Kabbalistic Lens (optional, provisional metaphor)</summary>

- **2.1 (hand-compute Euclidean distance)** is Hod — its own centroid words
  are "detail, precise, specificity, step, craft." This is the exercise
  where you refuse to trust the machine until you've done the arithmetic
  yourself.
- **2.2 (k=1 vs k=11)** is Chesed against Geburah, directly. k=1 is Chesed:
  unbounded closeness, every point trusted completely, 100% training
  accuracy because nothing is held back. k=11 is Geburah: "restriction,
  rigid, rules" — the vote is bound by a large, disciplined neighborhood,
  trading perfect fit for generalization. The same tension your sandbox
  already encodes as the Chesed/Geburah balancing pair for O(1) vs O(n²)
  algorithms, on a different axis.
- **2.3 (Ridge at alpha=0 → matches OLS)** — Binah is literally the alpha
  term. Its centroid is "constraint, structure, boundary, rule" —
  regularization is Binah's presence in the loss function. Dial alpha to 0
  and Binah's constraint vanishes; what's left is Chokmah's raw, undirected
  best-fit spark.
- **2.4 (LDA sign flip)** is Daath — the hidden sephirah, not usually drawn
  on the tree, fitting for a single swapped subtraction order that's exactly
  the kind of "gap, paradox, dissonance" invisible until it inverts every
  prediction downstream.
- **2.5 (alpha=1000)** is Geburah pushed to its own extreme: "severe,
  harsh, paralysis, burnout" — regularization strength isn't a metaphor
  here, it's Geburah's literal severity dial.

</details>

---

## Checkpoint A (before Module 3)

Without looking back at Module 1 or 2: from memory, what does
`upcast_and_get_max_speed(SportsCar("x"))` return (1.3), and what's the
Euclidean distance between `[1,1]` and `[4,5]` (2.1)? Check both. If either
slipped, that's fine — it's exactly the kind of gap spaced review is meant to
catch. Then continue.

*Kabbalistic Lens: this checkpoint (and B and C below) is a Yesod exercise
specifically — Yesod's centroid is "foundation, memory, latent, reflection."
Spaced recall without rereading tests what's actually settled into that
layer, versus what only looked learned in the moment.*

---

## Module 3 (Week 3): P2P Networks
**Files**: `dht_rca_node.py`, `grpc_web_bridge.py`

**3.1 — XOR distance by hand.**
*Predict*: should this print `True` or `False`, given that XOR distance is
defined as `int(a,16) ^ int(b,16)`?
```python
from dht_rca_node import generate_node_id, xor_distance
a = generate_node_id("node-a")
b = generate_node_id("node-b")
print(xor_distance(a, b) == (int(a, 16) ^ int(b, 16)))  # must print True
```

**3.2 — Predict a bucket index before running it.**
`_get_bucket_index` uses `dist.bit_length() - 1` (this was a real bug I
found and fixed — it used to use `int(math.log2(dist))`, which loses
precision above 2^53). If a distance is exactly `2**50`, predict the bucket
index before checking below.
<details><summary>Reveal answer</summary>
50, since `(2**50).bit_length() - 1 == 50`.
</details>
Check it against a `KademliaRoutingTable` instance. In one sentence: why does
`bit_length()` stay exact for huge integers while `log2()` (a floating-point
function) can lose precision above 2^53?

**3.3 — Extend the concurrency test.**
*Predict first*: will cross-talk appear at 100 concurrent threads, given it
didn't at 20?
Open `test_grpc_web_bridge.py`, find the 20-thread concurrent-client test,
change `range(20)` to `range(100)`, rerun. Confirm it still reports zero
cross-talk at higher concurrency. Run it 2-3 times, not once — concurrency
bugs are often intermittent, so a single clean run at higher thread count
proves less than a few repeated ones.

** Stretch 3.4 — Boundary distances.**
Predict the bucket index for the maximum possible 160-bit XOR distance
(`2**160 - 1`) and explain why a distance of exactly `0` (identical IDs)
is excluded from bucket routing entirely rather than landing in bucket 0.
Check both against the actual code.

<details><summary>Kabbalistic Lens (optional, provisional metaphor)</summary>

- **3.1 (XOR distance by hand)** is Binah — verifying the network's defining
  structural law, the same role Binah plays in the Module 1 lens ("the
  structure that defines the hierarchy"). Here it's the metric that defines
  the whole DHT's topology.
- **3.2 (bucket index precision bug)** is Yesod cracking into Daath. Yesod
  is the foundation/storage layer (the routing table itself), and the real
  bug — `log2()` losing precision above 2^53 — is a gap opening silently in
  ground that looked solid. This is the one exercise in the whole curriculum
  built directly from an actual defect, which makes it the most honest
  Daath moment in the set.
- **3.3 (20→100 concurrent threads, run it 2-3 times)** is Netzach, almost
  too literally: "grind, persistence, endurance, repeat, stubborn." Running
  it multiple times instead of once is the exercise itself teaching
  Netzach's discipline.
- **3.4 (max XOR distance, zero excluded)** is Gevurah's edge case: a rule
  that doesn't just restrict values but excludes a whole category
  (identical IDs) from the system entirely.

</details>

---

## Checkpoint B (before Module 4)

Purely from memory, redo exercise 1.2's break-observe-revert cycle without
rereading the instructions: break dynamic dispatch, confirm the "generic
vehicle" symptom, revert with git. If you fumble a step, that's useful
information about which part didn't stick the first time. Then continue.

*Kabbalistic Lens: another Yesod exercise — see Checkpoint A.*

---

## Module 4 (Week 4): 3D Graphics & Security
**Files**: `opengl_3d_scene_simulator.py`, `safe_memory_boundary_engine.py`

**4.1 — Hand-derive one matrix entry.**
For `fov=90°, aspect=1.0`: predict `create_perspective_projection`'s `[0][0]`
entry before checking — will it be exactly `1.0`, or very slightly off?
<details><summary>Reveal derivation</summary>
`f = 1/tan(45°) = 1.0`, so the `[0][0]` entry should be `1.0`.
</details>
Verify:
```python
from opengl_3d_scene_simulator import create_perspective_projection
print(create_perspective_projection(90, 1.0, 0.1, 100.0)[0][0])  # expect ~1.0 (prints 1.0000000000000002 -- floating-point tan/atan, not a bug)
```

**4.2 — Find the overflow boundary by hand.**
`safe_multiply_uint32(width, height)` overflows uint32 when
`width*height > 4294967295`. For `height=65536`, solve for the smallest
`width` that overflows before checking below.
<details><summary>Reveal derivation</summary>
`width > 65535.99998...`, so `width=65536` is the first overflowing value,
`width=65535` is the last safe one.
</details>
Verify both with `SafeMemoryAllocator.safe_multiply_uint32(65535, 65536)`
(no overflow) vs `(65536, 65536)` (overflow). In one sentence: why is
`65536` the exact tipping point and not `65535` or `65537`?

**4.3 — Reproduce the real lighting bug.**
*Before running*, write one sentence: why should a surface facing away from
the light get zero specular contribution, physically?
In `compute_phong_shading`, remove the `if n_dot_l > 0.0:` guard so specular
always computes regardless of whether the surface faces the light. Set up a
surface facing away from the light (see `test_opengl_3d_scene_simulator.py`'s
"light behind the surface" case) — intensity should jump from the correct
`0.25` (ambient only) back to `0.7` (the nonphysical bug this project
actually shipped with before it got caught).
Revert (`git restore opengl_3d_scene_simulator.py` or Discard Changes in VS).

** Stretch 4.4 — The mirrored boundary.**
With `width` fixed at `65536`, solve for the smallest `height` that
overflows. Predict first, then verify — same technique as 4.2, applied to
the other axis, to confirm you can generalize it rather than having
memorized one specific pair of numbers.

<details><summary>Kabbalistic Lens (optional, provisional metaphor)</summary>

- **4.1 (perspective matrix `[0][0]` entry)** is Chokmah — its centroid
  includes "vision, flash, spark." Field of view is, unglamorously, a
  literal field of vision. The floating-point residue
  (`1.0000000000000002`) is Chokmah's spark refracted through Malkuth's
  imperfect hardware.
- **4.2 (uint32 overflow boundary)** is Gevurah in its purest computational
  form: a wall at one exact integer, no negotiation.
- **4.3 (Phong shading bug)** is Tifereth, whose own centroid literally
  includes "beauty" alongside "balance, harmony, alignment." Removing the
  `n_dot_l > 0.0` guard doesn't just misrender a pixel, it breaks the
  harmony between simulated light and physical law — restoring the guard
  restores that alignment.
- **4.4 (mirrored boundary, other axis)** is Gevurah again, but now tested
  for whether you understood the law or just memorized one instance of it —
  Binah checking Gevurah's homework.

</details>

---

## Checkpoint C (before Module 5)

From memory: what coefficients should `alpha=0` Ridge regression recover on
2.3's dataset, and what does `safe_multiply_uint32(65535, 65536)` return
(4.2)? Check both, then continue to Module 5.

*Kabbalistic Lens: the third Yesod exercise — see Checkpoint A.*

---

## Module 5 (Special Track): Continuous Control & C
**Files**: `ddpg_quadcopter_rca_engine.py`, `alx_c_functions_nested_loops.c`

**5.1 — Hand-trace one physics step.**
Rotor speeds `[900,900,900,900]`, mass `1.25`, gravity `9.81`, `dt=0.05`.
Work through the physics by hand before revealing the trace below.
<details><summary>Reveal hand-trace</summary>
`total_thrust = 3600 * 0.025 = 90`; `az = 90/1.25 - 9.81 = 62.19`;
`v_z_new = 0 + 62.19*0.05 = 3.1095`; `z_new = 10.0 + 3.1095*0.05 = 10.155475`.
</details>
Verify against a fresh `QuadcopterTakeoffEnv().step(...)` call (`env.v[2]`
should be `3.1095`, `env.pose[2]` should be `10.155475`).

**5.2 — Compile with the real strict flags.**
*Predict*: if you declare a variable but never use it, which specific
warning will `-Werror` turn into a hard compile failure?
```bash
gcc -Wall -pedantic -Werror -Wextra -std=gnu89 alx_c_functions_nested_loops.c -o c_nested_loops && ./c_nested_loops
```
Should compile with zero warnings and zero errors. Now introduce the unused
variable and recompile to check your prediction. That's what the strict
flags are actually for.

**5.3 — Find the real training gap yourself.**
Read `DDPGAgent.step()` line by line and list every weight matrix that gets
a gradient update, *before* revealing the answer.
<details><summary>Reveal answer</summary>
Only `critic_out.W`. `actor_l1`, `actor_l2`, `actor_out`, `critic_l1`,
`critic_l2` are never touched — this is a real, documented gap in the
current code, not a trick question.
</details>
This is the same finding from the actual code review; the exercise is just
verifying you can independently spot it by reading, not being told.

** Stretch 5.4 — Trace a second physics step.**
Using the *output* of 5.1 (`v_z=3.1095`, `z=10.155475`) as the new starting
state, hand-trace one more step with the same rotor speeds. Predict whether
`v_z` keeps climbing at the same rate, and verify by calling `.step()` again
on the same env instance.

<details><summary>Kabbalistic Lens (optional, provisional metaphor)</summary>

- **5.1 (hand-trace physics step)** is Malkuth, unmistakably: "physical,
  manifestation, action, output, hardware." Mass, thrust, gravity, altitude
  — this is the module where the tree finally touches ground.
- **5.2 (`-Werror` strict compile flags)** is Gevurah with zero tolerance:
  the most literal rule-enforcement engine in the curriculum, a warning
  promoted to a hard failure by decree.
- **5.3 (finding that only `critic_out.W` gets a gradient)** is incomplete
  Chesed. Gradient descent is supposed to be Chesed's unbounded, generous
  flow reaching every layer; the real, documented gap is that flow dammed
  up before it reaches almost the whole network. Worth sitting with, since
  it's your own codebase's honestly-disclosed limitation, not a
  hypothetical.
- **5.4 (second physics step)** is Netzach again: the simulation's
  persistence across steps, confirming the trajectory continues rather than
  resetting.

</details>

---

## Module 6: The Philosophical Layer & Meta-Tooling
**Files**: `correspondence_ledger.py`, `attractor_correspondence_ledger.py`,
`rca_sandbox_gamma_correspondence_ledger.py`, `sephirotic_correspondence_ledger.py`,
`recursive_attractor_engine.py`, `standalone_rca_sandbox.py`, `LIBER_0.md`,
`docs/*_kabbalistic_hand_verification.md`

Unlike Modules 1–5, this module studies the layer *about* the codebase
rather than a single engine: the correspondence ledgers that turn
Sephirotic claims into checkable ledger entries, the attractor engine that
formalizes the project's own dynamical-systems axioms, and the honesty
discipline (`TESTING_STANDARD.md`, the three-register distinction) that
governs all of it. Same rule as everywhere else: predict before you run.

**If recursion itself is shaky ground**, read
`docs/recursion_primer_call_stack_basics.md` before 6.6 below — it covers
base cases, call-stack vs. tree recursion (with a measured
`fibonacci`-blowup example), and, concretely, why
`recursive_attractor_engine.py`'s own `iterate()` is neither of those but
a third thing (a plain loop). That distinction matters here specifically:
`docs/fixed_point_closure_and_the_y_combinator.md` (referenced in 6.6)
assumes the reader already has it.

**6.1 — Run a ledger, find the one row that can't pass.**
Before running anything, predict: in a `CorrespondenceLedger` built from
real code, which *kind* of claim would have to be marked `UNTESTABLE`
rather than `VERIFIED` or `FAILED`, no matter how good the test suite is?
```powershell
python attractor_correspondence_ledger.py
```
<details><summary>Reveal</summary>
The last row — `Consciousness-as-Attractor (core-axiom.md, Register C)` —
is the only one with `validator=None`. Every other row re-runs a real,
already-break-it-proofed test. This one is a metaphysical claim (that
consciousness *itself* is such a system), and no unit test against Python
code can validate or falsify a claim about consciousness in general —
that's not a limitation of this particular ledger, it's a limitation of
what code can ever check.
</details>
Run `rca_sandbox_gamma_correspondence_ledger.py` too and find its own
UNTESTABLE row — it's a *different kind* of unfalsifiable claim (a
cross-document identity claim, not a metaphysical one). Write one sentence
on why the two UNTESTABLE rows are unfalsifiable for different reasons.

**6.2 — Hand-verify the gamma cap, then check the running code.**
Pick a short repetitive text of your own (not one from the docs). Using
the Shannon-entropy formula in
`docs/rca_sandbox_gamma_kabbalistic_hand_verification.md`
(`h = -Σp·log2(p)`, `h_norm = h/h_max`, `gamma = clip(1-h_norm, 0, 0.85)`),
predict `compute_gamma()`'s output *on paper* before running anything.
```powershell
python -c "from standalone_rca_sandbox import compute_gamma; print(compute_gamma('YOUR TEXT HERE'))"
```
<details><summary>Reveal a worked reference case</summary>
`compute_gamma("refactor refactor refactor refactor refactor refactor")`
returns exactly `0.85` — one distinct token repeated six times is zero
Shannon entropy, which the formula caps at 0.85, not 1.0. If your own text
came out lower, that's correct: any additional distinct word lowers
`h_norm`'s denominator effect and pulls gamma down from the ceiling.
</details>

**6.3 — Trace the honesty guard's vacuous-truth trap by hand first.**
Before running anything: what should `CorrespondenceLedger.all_testable_passed()`
return for a ledger where *every* registered entry has `validator=None`?
Write your prediction, then write what plain Python's `all([])` returns
on an empty list (try it in a REPL) — are those the same thing?
```powershell
python -c "
from correspondence_ledger import CorrespondenceLedger
l = CorrespondenceLedger('demo')
l.register('X', 'Y', 'an untestable claim')
l.register('A', 'B', 'another untestable claim')
l.run()
print(l.all_testable_passed())
"
```
<details><summary>Reveal</summary>
It returns `False` — deliberately, via an explicit
`if not testable: return False` guard *before* the `all(...)` call.
Plain `all([])` returns `True` (an empty conjunction is vacuously true by
mathematical convention) — without the guard, a ledger that tested
*nothing* could report success. See
`docs/correspondence_ledger_kabbalistic_hand_verification.md` for the
full truth-table trace and the exact break-it proof that caught this when
the guard line was removed.
</details>

**6.4 — Catch a fabricated claim the same way it was actually caught.**
Read the `CORRECTION NOTICE` at the top of
`docs/linear_algebra_mathematical_testing_spec.md`. Pick any one of the
five corrected claims (the Ridge condition-number check is a good one —
it's the most specific), and independently re-verify it yourself, the
exact way it was originally caught: `grep` the real engine and its test
file for the relevant term.
```powershell
grep -rn "cond\|kappa\|condition" stat_learning_suite.py test_stat_learning_suite.py
```
Predict what you'll find *before* running the grep.
<details><summary>Reveal</summary>
Zero hits. No condition-number check exists anywhere in the engine or its
test — the claim in the original doc (`κ(XᵀX + αI) < 10⁵`) described
verification machinery that was never built. This is the same one-command
check that found the problem in the first place; the fix wasn't
sophisticated, it was just actually looking.
</details>

**6.5 — Sandbox Practicum: predict three `/eval` outputs before running them.**
Pick three short texts of your own: one repetitive/procedural, one about
ideas or creativity, one about physical needs (hunger, tiredness, pain).
Using `SEPHIROT_CENTROIDS`' keyword lists directly (top of
`standalone_rca_sandbox.py`), predict which sephirah each text's dominant
score will land on *before* running anything.
```powershell
python standalone_rca_sandbox.py
```
Then, inside the sandbox, run `/eval <your text>` for each one and compare
`Diagnosed Pattern (D2)` against your prediction.
<details><summary>Reveal a worked reference (three different texts than yours, for calibration)</summary>

| Text | Dominant | Confidence |
|---|---|---|
| "refactor refactor refactor refactor refactor refactor" | Hod | 95% |
| "the wisdom vision idea flash intuition spark creative genius" | Chokmah | 95% |
| "I am hungry and tired, need food and sleep" | Malkuth | 95% |

All three match their `SEPHIROT_CENTROIDS` keyword lists directly by
inspection — "refactor" isn't literally in Hod's list but stems-matches
"refactor" (Hod's list includes it exactly), "wisdom/vision/idea/spark"
are verbatim Chokmah centroid words, and "hungry/tired/food/sleep" are
verbatim Malkuth centroid words. If your own predictions were off, check
whether your text actually contained centroid words or just words that
felt thematically related — the scoring is literal keyword/cosine
matching, not semantic understanding, which is exactly what
`master_study_and_onboarding_manual.md`'s Chapter 3 already tells you
about this engine.
</details>

** Stretch 6.6 — Register a correspondence of your own.**
Every Kabbalistic Lens entry in Modules 1–5 above, and the
`ddpg_engine_kabbalistic_hand_verification.md` doc, describes a
correspondence claim in prose only — none of them have a
`correspondence_ledger.py` entry yet. Pick one (e.g. Module 5's "5.1 is
Malkuth" or the DDPG engine's Geburah RPM ceiling), write a new
`Correspondence` registration wiring its `validator` to an existing test
method via `from_unittest_methods()`, and confirm it reports `VERIFIED`
when you run your ledger. This is genuinely open-ended — there is no
single correct answer, only whether your ledger actually runs and passes.

<details><summary>Register Discipline Note (why this module has no "Kabbalistic Lens" of its own)</summary>

Every other module's Lens is an *added* mnemonic reading over
already-existing engineering exercises. This module is different: it's
already directly about the Sephirotic/philosophical layer, so adding
another metaphorical reading on top would be a lens over a lens. Instead,
the discipline worth carrying forward from this module is the
**three-register distinction** from
`docs/fixed_point_closure_and_the_y_combinator.md` §1: (A) traditional/
textual claims about Kabbalah, (B) formal claims checkable within this
codebase's own stated math, and (C) metaphysical claims about
consciousness itself. Every exercise above stays in (B). Exercise 6.1's
UNTESTABLE row is what happens when a claim tries to cross into (C) —
recognizing that boundary, not just computing correctly, is the actual
skill this module is teaching.

</details>

---

## Answer key note
None of these have a separate hidden answer key file — the point is each one
is self-checking: either the numbers match what you hand-computed (revealed
only after you've committed to a guess), or the assertion passes/fails, or
the behavior visibly changes when you break something and revert. If a check
doesn't come out as described above, that's worth chasing down — and worth
logging (see "Before You Start," item 5) — rather than assuming the exercise
text is wrong.
