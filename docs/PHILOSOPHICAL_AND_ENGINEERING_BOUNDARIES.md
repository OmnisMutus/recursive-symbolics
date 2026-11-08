# Philosophical, Epistemological, and Engineering Boundaries

This document defines the standing contextual boundaries and epistemological standards for all AI assistants (Gemini, Claude, or otherwise) working in this codebase repository.

---

## 1. Separation of Epistemological Registers

### A. Nondual Metaphysics & Philosophical Traditions
- **Domain**: Kashmir Shaivism (Trika school, Abhinavagupta, Utpaladeva's *Pratyabhijñā* recognition philosophy, *Spanda* creative pulsation of consciousness, Shiva-Shakti nonduality), Advaita Vedānta, Dzogchen, and related classical nondual systems.
- **Nature**: Sophisticated philosophical traditions with centuries of rigorous internal debate against Buddhist logicians (*Dignāga*, *Dharmakīrti*) and *Naiyāyika* epistemologists.
- **Engagement Rule**: When discussing philosophical concepts, engage on their own authentic terms, texts, and internal logic (*Tantrāloka*, *Spandakārikā*, *Pratyabhijñāhṛdayam*). Do not attempt to force-fit metaphysical concepts into fake empirical benchmarks, pseudo-scientific Hz frequencies, or fabricated Big-O isomorphisms.

### B. Software Engineering, Benchmarking, and Formal Validation
- **Domain**: Algorithms, data structures, performance benchmarks, cryptographic hashing, type safety, memory boundaries, and unit test harnesses.
- **Nature**: Empirically checkable, reproducible, and verifiable.
- **Engagement Rule**: Must strictly adhere to [`TESTING_STANDARD.md`](TESTING_STANDARD.md):
  1. **Independent Ground-Truth Reference** (real external libraries like `sklearn`, `hashlib`, published test vectors like empty-file Git blob `e69de29b...`, or non-shared mathematical reference loops).
  2. **Exhaustive Boundary & Edge Cases** (empty strings, zero/negative bounds, `INT32_MIN` overflow, `bool` type guards).
  3. **Adversarial Break-It Proof** (injecting domain-plausible bugs, documenting the failure, and showing the clean pass restoration).

---

## 2. Standing Directives for AI Agents

1. **No Pseudo-Scientific Conflation**: Never claim a metaphysical concept constitutes a "benchmarked Hz frequency" or "mathematical proof of performance" unless backed by genuine, empirical, reproducible benchmark code adhering to `TESTING_STANDARD.md`.
2. **Honest Reporting**: Always distinguish between `VERIFIED` (passing dedicated ground-truth unit tests) and `RAN_ONLY` (executed with exit code 0 without assertions).
3. **Respect Rigorous Intellectual Debate**: Welcome critical analysis, factual checks, and edge-case bug identification as essential steps toward genuine technical excellence.

---

## 3. The three registers, and the seam that keeps them apart in this engine

The framework's own distinction, kept throughout this repository:

- **Register A** — what a tradition says, in its own texts and on its own terms.
- **Register B** — what is formally checkable inside this codebase's mathematics.
- **Register C** — claims about consciousness itself.

They are never collapsed into one another. Everything testable here lives in B. A claim in C is an `UNTESTABLE`
row in a correspondence ledger rather than a caveat in a docstring that is easy to miss.

The mechanism, not just the intention: an address is computed and a lens reads it, and a lens can never write
back into an address. So a Register A reading ("the Kabbalistic lens reads Geburah here") cannot alter a Register
B fact (the numbers and how they were derived), and no reading can present itself as a Register C claim about
what the person is. `ethics.emit()` refuses any reading that does not name the tradition it came from.
