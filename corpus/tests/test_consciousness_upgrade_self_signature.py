"""
test_consciousness_upgrade_self_signature.py

Independent ground truth for compute_content_hash(): re-derive SHA-256 via
the standard library's `hashlib` called directly on a hand-built canonical
string (not by importing and re-calling compute_content_hash on itself),
so the check can't share a bug with the function under test. Also verifies
the avalanche property empirically (single-character change -> completely
different digest) rather than assuming it.
"""

import hashlib
import json
import unittest

import sys
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from consciousness_upgrade_self_signature import (
    SelfSignature, ChangeLedger, ChangeRecord,
    compute_content_hash, create_signature, verify_signature, propose_change,
)


def independent_hash(values: dict) -> str:
    """Ground truth computed a different way: build the canonical string
    by hand (sorted keys, explicit separators) rather than calling the
    module's own _canonical_json, then hash it directly with hashlib."""
    canonical = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TestHashAgainstIndependentComputation(unittest.TestCase):
    def test_matches_independent_sha256(self):
        values = {"b": "2", "a": "1"}
        self.assertEqual(compute_content_hash(values), independent_hash(values))

    def test_key_order_does_not_affect_hash(self):
        v1 = {"a": "1", "b": "2"}
        v2 = {"b": "2", "a": "1"}
        self.assertEqual(compute_content_hash(v1), compute_content_hash(v2))

    def test_single_character_change_produces_different_hash(self):
        # Avalanche property, checked empirically rather than assumed.
        h1 = compute_content_hash({"x": "reliable"})
        h2 = compute_content_hash({"x": "reliablr"})  # one char changed
        self.assertNotEqual(h1, h2)
        # And they shouldn't share any long common substring either --
        # a weak collision-adjacent property worth actually checking.
        self.assertNotEqual(h1[:32], h2[:32])

    def test_known_vector_sha256_of_empty_dict(self):
        # json.dumps({}, sort_keys=True, separators=(",", ":")) == "{}"
        # sha256(b"{}") is a fixed, independently-computable value -- this
        # pins the exact canonical-serialization convention (empty dict ->
        # literal two-byte string "{}"), not just "some hash of some
        # string". Cross-checked against `echo -n '{}' | sha256sum` in the
        # hand-verification doc, a genuinely different computational path
        # (shell/coreutils) from Python's hashlib.
        expected = hashlib.sha256(b"{}").hexdigest()
        self.assertEqual(compute_content_hash({}), expected)


class TestSignatureCreationAndVerification(unittest.TestCase):
    def test_freshly_created_signature_verifies(self):
        sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
        self.assertTrue(verify_signature(sig))

    def test_hand_edited_values_without_recomputed_hash_fails_verification(self):
        sig = create_signature({"how_i_show_up": "direct"}, now="2026-01-01T00:00:00Z")
        tampered = SelfSignature(
            values={"how_i_show_up": "whatever avoids conflict"},
            content_hash=sig.content_hash,  # stale -- not recomputed
            declared_at=sig.declared_at,
        )
        self.assertFalse(verify_signature(tampered))

    def test_correctly_recomputed_hash_after_edit_verifies(self):
        sig = create_signature({"x": "1"}, now="2026-01-01T00:00:00Z")
        edited_values = {"x": "2"}
        correctly_updated = SelfSignature(
            values=edited_values,
            content_hash=compute_content_hash(edited_values),
            declared_at=sig.declared_at,
        )
        self.assertTrue(verify_signature(correctly_updated))

    def test_to_json_and_from_dict_roundtrip_preserves_verification(self):
        sig = create_signature({"a": "1", "b": "2"}, now="2026-01-01T00:00:00Z")
        restored = SelfSignature.from_dict(json.loads(sig.to_json()))
        self.assertEqual(restored, sig)
        self.assertTrue(verify_signature(restored))


class TestProposeChangeRequiresDisclosure(unittest.TestCase):
    def test_empty_reason_raises(self):
        sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        with self.assertRaises(ValueError):
            propose_change(sig, {"a": "2"}, reason="", ledger=ledger)

    def test_whitespace_only_reason_raises(self):
        sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        with self.assertRaises(ValueError):
            propose_change(sig, {"a": "2"}, reason="   ", ledger=ledger)

    def test_valid_reason_succeeds_and_updates_hash(self):
        sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        new_sig = propose_change(sig, {"a": "2"}, reason="noticed it was outdated", ledger=ledger,
                                  now="2026-01-02T00:00:00Z")
        self.assertNotEqual(new_sig.content_hash, sig.content_hash)
        self.assertTrue(verify_signature(new_sig))

    def test_valid_change_is_logged_to_ledger_with_correct_fields(self):
        sig = create_signature({"a": "1", "b": "2"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        new_sig = propose_change(sig, {"a": "1", "b": "3"}, reason="b was stale",
                                  ledger=ledger, now="2026-01-02T00:00:00Z")
        self.assertEqual(len(ledger.records), 1)
        rec = ledger.records[0]
        self.assertEqual(rec.old_hash, sig.content_hash)
        self.assertEqual(rec.new_hash, new_sig.content_hash)
        self.assertEqual(rec.changed_keys, ["b"])  # only 'b' actually changed
        self.assertEqual(rec.reason, "b was stale")

    def test_changed_keys_detects_additions_and_removals_too(self):
        sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
        ledger = ChangeLedger()
        propose_change(sig, {"b": "2"}, reason="replaced a with b", ledger=ledger,
                        now="2026-01-02T00:00:00Z")
        # both 'a' (removed) and 'b' (added) should be reported as changed
        self.assertEqual(set(ledger.records[0].changed_keys), {"a", "b"})

    def test_does_not_mutate_current_signature(self):
        sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
        original_hash = sig.content_hash
        ledger = ChangeLedger()
        propose_change(sig, {"a": "2"}, reason="test", ledger=ledger, now="2026-01-02T00:00:00Z")
        self.assertEqual(sig.content_hash, original_hash)  # unchanged

    def test_refuses_to_build_on_top_of_an_already_tampered_signature(self):
        sig = create_signature({"a": "1"}, now="2026-01-01T00:00:00Z")
        tampered = SelfSignature(values={"a": "999"}, content_hash=sig.content_hash,
                                  declared_at=sig.declared_at)
        ledger = ChangeLedger()
        with self.assertRaises(ValueError):
            propose_change(tampered, {"a": "2"}, reason="fine", ledger=ledger)


if __name__ == "__main__":
    unittest.main(verbosity=2)
