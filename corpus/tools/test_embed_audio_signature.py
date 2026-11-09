#!/usr/bin/env python3
"""
test_embed_audio_signature.py
Independent correctness test for embed_audio_signature.py's
generate_drifting_carrier_tone() (sine-wave synthesis) and
embed_metadata() (JPEG COM-marker steganographic embedding).

INDEPENDENT GROUND TRUTH: `reference_sample()` below re-derives the
exact per-sample formula in a second, separate implementation (not a
call into generate_drifting_carrier_tone() or a re-read of its own
output compared to itself) -- same math.sin arithmetic, transcribed
directly from the function's own docstring/body, used to compute
EXPECTED int16 samples independently, then compared against the REAL
WAV file's actual bytes read back via the standard library `wave`
module. The JPEG marker byte structure is likewise hand-derived from
the JPEG COM-marker spec (marker bytes 0xFF 0xFE, then a 2-byte
big-endian length covering the length field itself plus the comment),
not assumed from embed_metadata()'s own code.
"""

import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import embed_audio_signature as eas  # noqa: E402


def reference_sample(t, duration_sec):
    """Independent re-derivation of one output sample's exact int16
    value, transcribed from generate_drifting_carrier_tone()'s own
    formula (f_anchor=164.81, f_tartini=145.0, f_harmonic=432.0)."""
    f_anchor = 164.81
    f_tartini = 145.0
    f_harmonic = 432.0
    beta = t / duration_sec
    wave_anchor = (1.0 - beta * 0.5) * math.sin(2 * math.pi * f_anchor * t)
    wave_ghost = beta * math.sin(2 * math.pi * f_tartini * t)
    wave_tiphareth = 0.15 * math.sin(2 * math.pi * f_harmonic * t)
    combined = wave_anchor + wave_ghost + wave_tiphareth
    envelope = min(1.0, t / 0.5) * min(1.0, (duration_sec - t) / 0.5)
    return int((combined / 1.65) * envelope * 32767.0)


class TestGenerateDriftingCarrierTone(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _generate_and_read_samples(self, duration_sec, sample_rate):
        out_path = Path(self._tmpdir) / "test_tone.wav"
        eas.generate_drifting_carrier_tone(out_path, duration_sec=duration_sec, sample_rate=sample_rate)
        with wave.open(str(out_path), "r") as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
            params = wf.getparams()
        samples = struct.unpack(f"<{n}h", raw)
        return samples, params

    def test_wav_format_parameters(self):
        _, params = self._generate_and_read_samples(duration_sec=0.02, sample_rate=1000)
        self.assertEqual(params.nchannels, 1)
        self.assertEqual(params.sampwidth, 2)
        self.assertEqual(params.framerate, 1000)
        self.assertEqual(params.nframes, 20)  # 1000 * 0.02

    def test_first_sample_is_exactly_zero(self):
        # t=0 -> beta=0, all three sine terms are sin(0)=0, envelope=0.
        samples, _ = self._generate_and_read_samples(duration_sec=0.02, sample_rate=1000)
        self.assertEqual(samples[0], 0)

    def test_every_sample_matches_independent_reference_exactly(self):
        duration_sec = 0.02
        sample_rate = 1000
        samples, _ = self._generate_and_read_samples(duration_sec, sample_rate)
        for i, actual in enumerate(samples):
            t = i / sample_rate
            expected = reference_sample(t, duration_sec)
            self.assertEqual(actual, expected, f"sample {i} (t={t}): expected {expected}, got {actual}")

    def test_samples_stay_within_16_bit_signed_range(self):
        samples, _ = self._generate_and_read_samples(duration_sec=1.0, sample_rate=2000)
        for s in samples:
            self.assertGreaterEqual(s, -32768)
            self.assertLessEqual(s, 32767)

    def test_envelope_fades_in_then_out(self):
        # With a 7-second default-style duration, sample amplitude near
        # the very start and very end should be smaller than amplitude
        # comfortably inside the 0.5s fade window (envelope == 1 there).
        duration_sec = 2.0
        sample_rate = 1000
        samples, _ = self._generate_and_read_samples(duration_sec, sample_rate)
        near_start = abs(samples[5])       # t=0.005s, deep in fade-in
        mid = max(abs(s) for s in samples[600:700])  # t~0.6-0.7s, envelope==1 region
        self.assertLess(near_start, mid)


class TestEmbedMetadata(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write(self, name, data):
        path = Path(self._tmpdir) / name
        path.write_bytes(data)
        return path

    def test_rejects_non_jpeg_input(self):
        bad = self._write("not_a_jpeg.jpg", b"\x00\x01not a jpeg at all")
        out = Path(self._tmpdir) / "out.jpg"
        with self.assertRaises(ValueError):
            eas.embed_metadata(str(bad), str(out), "hello")

    def test_inserts_com_marker_immediately_after_soi(self):
        # A minimal fake JPEG: SOI + arbitrary body + EOI.
        fake = b"\xff\xd8" + b"\x00" * 20 + b"\xff\xd9"
        in_path = self._write("in.jpg", fake)
        out_path = Path(self._tmpdir) / "out.jpg"
        eas.embed_metadata(str(in_path), str(out_path), "hello")
        result = out_path.read_bytes()

        comment_bytes = b"hello"
        comment_length = len(comment_bytes) + 2
        expected_marker = b"\xff\xfe" + struct.pack(">H", comment_length) + comment_bytes
        # Hand-derived expectation: SOI, then the marker, then the
        # untouched rest of the original file.
        self.assertEqual(result, b"\xff\xd8" + expected_marker + b"\x00" * 20 + b"\xff\xd9")

    def test_deduplicates_a_pre_existing_com_marker(self):
        old_comment = b"OLD COMMENT"
        old_length = len(old_comment) + 2
        old_marker = b"\xff\xfe" + struct.pack(">H", old_length) + old_comment
        fake = b"\xff\xd8" + old_marker + b"\x00" * 10 + b"\xff\xd9"
        in_path = self._write("in_with_marker.jpg", fake)
        out_path = Path(self._tmpdir) / "out.jpg"
        eas.embed_metadata(str(in_path), str(out_path), "new comment")
        result = out_path.read_bytes()

        self.assertNotIn(old_comment, result)
        self.assertEqual(result.count(b"\xff\xfe"), 1)  # exactly one COM marker, not two
        new_comment_bytes = b"new comment"
        new_length = len(new_comment_bytes) + 2
        expected_marker = b"\xff\xfe" + struct.pack(">H", new_length) + new_comment_bytes
        self.assertEqual(result, b"\xff\xd8" + expected_marker + b"\x00" * 10 + b"\xff\xd9")

    def test_can_overwrite_input_path_when_output_equals_input(self):
        fake = b"\xff\xd8" + b"\x00" * 5 + b"\xff\xd9"
        in_path = self._write("inplace.jpg", fake)
        eas.embed_metadata(str(in_path), str(in_path), "x")
        result = in_path.read_bytes()
        self.assertIn(b"\xff\xfe", result)


def run_unit_test_suite():
    print("=" * 72)
    print("  EMBED_AUDIO_SIGNATURE.PY -- CORRECTNESS TEST SUITE")
    print("=" * 72 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("Test") and isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(obj))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 72)
    print(f"  Total: {result.testsRun}  Failures: {len(result.failures)}  Errors: {len(result.errors)}")
    print(f"  Result: {'ALL PASSED' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 72)
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_unit_test_suite() else 1)
