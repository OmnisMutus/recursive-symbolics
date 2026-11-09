#!/usr/bin/env python3
"""
test_hello_world_repo_simulator.py
Runnable unit test suite for hello_world_repo_simulator.py.

The critical check here is NOT "does this produce a 40-char hex string"
(trivially satisfiable by any SHA-1 call on any garbage bytes) -- it's
"does this produce the SAME hash a real, independent construction of the
Git object byte format would produce." Tests below build the expected
bytes manually, via a code path that does NOT call anything in
hello_world_repo_simulator.py, and compare hashes.
"""

import sys
import hashlib
import unittest
from pathlib import Path as _BootstrapPath
_REPO_ROOT = _BootstrapPath(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)

from hello_world_repo_simulator import (
    compute_git_commit_sha1, compute_git_blob_sha1, build_commit_object_content,
)


class TestGitCommitHashing(unittest.TestCase):

    def test_commit_hash_matches_independently_built_git_object_bytes(self):
        # This reference is built by hand, directly in the test, using
        # raw string formatting and hashlib -- it does NOT call
        # build_commit_object_content() or compute_git_commit_sha1().
        # If the engine's internal format is wrong in any way (missing
        # newline, wrong field order, wrong header), this WILL diverge.
        tree_sha = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        parent_sha = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
        author_line = "Jane Dev <jane@example.com> 1700000000 +0000"
        committer_line = "Jane Dev <jane@example.com> 1700000000 +0000"
        message = "Initial commit"

        reference_content = (
            f"tree {tree_sha}\n"
            f"parent {parent_sha}\n"
            f"author {author_line}\n"
            f"committer {committer_line}\n"
            f"\n"
            f"{message}\n"
        ).encode("utf-8")
        reference_header = f"commit {len(reference_content)}\0".encode("utf-8")
        expected_hash = hashlib.sha1(reference_header + reference_content).hexdigest()

        actual_hash = compute_git_commit_sha1(
            tree_sha, parent_sha, author_line, committer_line, message
        )

        self.assertEqual(actual_hash, expected_hash)

    def test_commit_hash_is_40_char_lowercase_hex(self):
        h = compute_git_commit_sha1(
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
            None,
            "A <a@x.com> 1700000000 +0000",
            "A <a@x.com> 1700000000 +0000",
            "msg",
        )
        self.assertEqual(len(h), 40)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_root_commit_omits_parent_line_and_changes_hash(self):
        # A root commit (no parent) must NOT include a "parent" line at
        # all -- not an empty one, not a placeholder. Confirm omitting
        # parent_sha actually changes the byte content (and thus hash)
        # vs. providing one, proving the parent line is really being
        # conditionally included/excluded rather than always present.
        common_args = (
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
            "author line placeholder <a@x.com> 1700000000 +0000",
            "author line placeholder <a@x.com> 1700000000 +0000",
            "msg",
        )
        hash_with_parent = compute_git_commit_sha1(
            common_args[0], "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            common_args[1], common_args[2], common_args[3],
        )
        hash_without_parent = compute_git_commit_sha1(
            common_args[0], None, common_args[1], common_args[2], common_args[3],
        )
        self.assertNotEqual(hash_with_parent, hash_without_parent)

    def test_root_commit_content_has_no_parent_line(self):
        content = build_commit_object_content(
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
            None,
            "A <a@x.com> 1700000000 +0000",
            "A <a@x.com> 1700000000 +0000",
            "msg",
        )
        self.assertNotIn(b"parent", content)

    def test_different_messages_produce_different_hashes(self):
        base_args = (
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904", None,
            "A <a@x.com> 1700000000 +0000",
            "A <a@x.com> 1700000000 +0000",
        )
        h1 = compute_git_commit_sha1(*base_args, "First message")
        h2 = compute_git_commit_sha1(*base_args, "Second message")
        self.assertNotEqual(h1, h2)

    def test_identical_inputs_produce_identical_hash(self):
        # Determinism check: same inputs, same output, every time --
        # a commit hash must be reproducible, not dependent on any
        # hidden state (timestamps generated internally, random salts, etc).
        args = (
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
            "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "A <a@x.com> 1700000000 +0000",
            "A <a@x.com> 1700000000 +0000",
            "Same message",
        )
        h1 = compute_git_commit_sha1(*args)
        h2 = compute_git_commit_sha1(*args)
        self.assertEqual(h1, h2)


class TestGitBlobHashing(unittest.TestCase):

    def test_blob_hash_matches_known_git_value(self):
        # This is a well-known, publicly documented Git test vector:
        # an EMPTY file has a fixed, famous blob SHA-1 in every Git repo:
        # e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
        # This value is independent of this codebase entirely -- it's
        # the same in every real Git installation on earth for an empty
        # file, which makes it a strong ground-truth check.
        self.assertEqual(
            compute_git_blob_sha1(""),
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
        )

    def test_blob_hash_matches_independently_built_bytes(self):
        content = "Hello, World!\n"
        reference_bytes = content.encode("utf-8")
        reference_header = f"blob {len(reference_bytes)}\0".encode("utf-8")
        expected = hashlib.sha1(reference_header + reference_bytes).hexdigest()
        self.assertEqual(compute_git_blob_sha1(content), expected)


def run_unit_test_suite():
    print("=" * 72)
    print("  GIT SHA-1 COMMIT/BLOB HASHING — UNIT TEST SUITE")
    print("  Verifying Against Independently-Built Git Object Bytes")
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
    status = "ALL PASSED (hashes verified against independent Git object bytes + known Git test vector)" if result.wasSuccessful() else "FAILED — see output above"
    print(f"  Result               : {status}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_unit_test_suite()
    sys.exit(0 if success else 1)
