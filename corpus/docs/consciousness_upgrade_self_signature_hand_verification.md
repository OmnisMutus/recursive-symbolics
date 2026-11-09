# Hand-Verifying `consciousness_upgrade_self_signature.py`

*Register note: Register B. The pasted "Consciousness Upgrade Protocol"
document's Stage 1 framing ("declare a self-signature," an "escrow
contract") is Register A/metaphor and is not re-implemented here — see the
chat discussion on why "escrow contract," "Asuka's sandbox," and an
"Inference Service" don't correspond to anything found in `solo/` or
`Recursive-Symbolics`. What's verified below is a much smaller, honestly
named pair of real properties: tamper-evidence (via hashing) and disclosed
mutation (via a ledger requiring a stated reason) — not a multi-party
contract.*

## 1. What's actually being claimed

Two properties only:

1. **Tamper-evidence**: if `values` change without `content_hash` being
   recomputed, `verify_signature()` returns `False`.
2. **Disclosed mutation**: the only sanctioned way to change values,
   `propose_change()`, requires a non-empty `reason` and logs the change.

Neither claims to *prevent* someone from hand-editing a persisted JSON
file and its hash together. No local scheme can prevent that. What it
claims is narrower and real: doing so *without* recomputing the hash
correctly is caught; doing so *through* the sanctioned API is disclosed.

## 2. Cross-checking the hash via a genuinely different code path

`compute_content_hash()` uses Python's `hashlib.sha256`. Independent
ground truth: shell's `sha256sum` (different binary, different language,
same standard) on the identical canonical string.

```
$ echo -n '{}' | sha256sum
44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a  -

$ python3 -c "import hashlib; print(hashlib.sha256(b'{}').hexdigest())"
44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a
```

Match. And for a non-empty value set:

```
$ python3 -c "from consciousness_upgrade_self_signature import compute_content_hash; \
  print(compute_content_hash({'a':'1','b':'2'}))"
21f76dfbfe6dfe21f762080ef484112cf2952974cef30741fd1931e1c6d92112

$ echo -n '{"a":"1","b":"2"}' | sha256sum
21f76dfbfe6dfe21f762080ef484112cf2952974cef30741fd1931e1c6d92112  -
```

Match — confirming the module's canonical serialization really is
`json.dumps(values, sort_keys=True, separators=(",", ":"))` and nothing
else is silently folded into the hash (no timestamp, no extra whitespace).

## 3. By hand — tamper detection

```
sig.values = {"how_i_show_up": "direct"}
sig.content_hash = H(sig.values)        # computed at creation

tampered.values = {"how_i_show_up": "whatever avoids conflict"}
tampered.content_hash = sig.content_hash   # NOT recomputed -- the tamper

verify_signature(tampered):
  compute_content_hash(tampered.values) != tampered.content_hash
  -> False
```

Hand-checkable without running anything: the stored hash is the OLD
value's hash, and `compute_content_hash` on the NEW values will not equal
it unless of a hash collision (SHA-256, not a concern in practice).

## 4. By hand — the "please everyone" style conflict is a different module

Note this module does **not** decide whether two values are *compatible*
— it only detects whether stored values match their claimed hash. Range
conflicts between declared values are `constraint_pruner.py`'s job
(Stage 2), not this module's. Kept separate deliberately: a self-signature
can be internally consistent (hash matches) while still being in tension
with some other constraint — that's a different, already-built check.

## 5. By hand — why `propose_change` refuses on an already-tampered signature

```python
def test_refuses_to_build_on_top_of_an_already_tampered_signature(self):
    sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
    tampered = SelfSignature(values={"a": "999"}, content_hash=sig.content_hash, ...)
    propose_change(tampered, {"a": "2"}, reason="fine", ledger=ledger)  # raises
```

If this guard were absent, a silently-tampered signature could be "laundered"
into a seemingly legitimate, ledger-logged change — the ledger would show a
disclosed transition from a hash that was never honestly held. The guard
closes that gap by checking `verify_signature(current)` before accepting
any proposed change.

## 6. Break-it proof (performed, not just described)

Replaced `verify_signature`'s body with `return True` (a realistic bug: a
refactor that "trusts the stored hash unconditionally," e.g. treating hash
recomputation as expensive and skipping it). Result:

```
FAIL: test_hand_edited_values_without_recomputed_hash_fails_verification
  AssertionError: True is not false
FAIL: test_refuses_to_build_on_top_of_an_already_tampered_signature
  AssertionError: ValueError not raised
```

Two tests caught it immediately, for two different reasons (the tamper
check itself, and the downstream guard in `propose_change` that depends on
it). Reverted; `diff -q` against a pre-edit backup confirmed byte-identical.

## 7. What this deliberately does not claim

No counterparty, no external verifier, no cryptographic non-repudiation
(no signing key — "signature" here means "a committed declaration," not a
digital signature in the PKI sense; that's a real terminology looseness
worth naming rather than letting the filename imply more than the code
does). A determined user with filesystem access can edit both `values` and
`content_hash` together and produce a self-signature that verifies fine
but was never honestly created — this module cannot and does not claim to
prevent that. What it provides: an honest, checkable record that *casual or
accidental* mutation (edit the values, forget the hash) is caught, and that
*intentional, sanctioned* mutation is timestamped and reasoned in a ledger.

## 8. Files

- [`../consciousness_upgrade_self_signature.py`](../consciousness_upgrade_self_signature.py) — the module.
- [`../test_consciousness_upgrade_self_signature.py`](../test_consciousness_upgrade_self_signature.py) — 15 tests, all passing, independent SHA-256 cross-check included.

---

## Provenance

Grounds Stage 1 of the pasted "Consciousness Upgrade Protocol" document in
real hashing and a disclosed-change ledger, following the same discipline
as `consciousness_upgrade_constraint_pruner_hand_verification.md` (Stage
2): the document's own vocabulary ("escrow contract") is separated from,
and is a substantially larger claim than, what's actually built and
verified here.
