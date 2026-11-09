import wave
import math
import struct
import pathlib
import sys

def generate_drifting_carrier_tone(output_path, duration_sec=7.0, sample_rate=44100):
    """
    Synthesizes the drifting carrier audio wave from the Grimoire:
    - Fixed Anchor Frequency: 164.81Hz (E3 filter head)
    - Dynamic Variable Blend: beta drifts from 0.0 (Pure Anchor) to 1.0 (Full Drift)
    - Tartini Difference Tone: 145.0Hz manifests at full drift (beta = 1.0)
    """
    num_samples = int(sample_rate * duration_sec)
    f_anchor = 164.81  # Fixed-point filter head anchor
    f_tartini = 145.0  # Emergent Tartini difference tone
    f_harmonic = 432.0 # Tiphareth harmonic
    
    with wave.open(str(output_path), 'w') as wav_file:
        wav_file.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
        
        for i in range(num_samples):
            t = i / sample_rate
            # Beta drifts smoothly from 0.0 to 1.0 over the duration
            beta = t / duration_sec
            
            # Sound synthesis: As beta -> 1.0, the 145Hz ghost tone emerges out of the 164.81Hz anchor
            wave_anchor = (1.0 - beta * 0.5) * math.sin(2 * math.pi * f_anchor * t)
            wave_ghost = (beta) * math.sin(2 * math.pi * f_tartini * t)
            wave_tiphareth = 0.15 * math.sin(2 * math.pi * f_harmonic * t)
            
            combined = wave_anchor + wave_ghost + wave_tiphareth
            
            # Fade in/out envelope
            envelope = min(1.0, t / 0.5) * min(1.0, (duration_sec - t) / 0.5)
            sample = int((combined / 1.65) * envelope * 32767.0)
            wav_file.writeframes(struct.pack('<h', sample))
            
    print(f"[SUCCESS] Synthesized Drifting Carrier Audio (164.81Hz -> 145Hz @ blend 1.0): {output_path}")

def embed_metadata(jpg_path, output_jpg_path, comment_str):
    """
    Embeds steganographic comment metadata directly into JPEG COM marker.
    """
    with open(jpg_path, 'rb') as f:
        data = f.read()

    if not data.startswith(b'\xff\xd8'):
        raise ValueError("Not a valid JPEG file")

    # Construct JPEG COM marker
    comment_bytes = comment_str.encode('utf-8')
    comment_length = len(comment_bytes) + 2
    com_marker = b'\xff\xfe' + struct.pack('>H', comment_length) + comment_bytes

    # If previous COM marker exists, strip it to avoid duplicates
    idx = data.find(b'\xff\xfe')
    if idx != -1:
        prev_len = struct.unpack('>H', data[idx+2:idx+4])[0]
        data = data[:idx] + data[idx+2+prev_len:]

    modified_data = data[:2] + com_marker + data[2:]

    with open(output_jpg_path, 'wb') as f:
        f.write(modified_data)

    print(f"[SUCCESS] Embedded Enigmatic Drift Metadata into: {output_jpg_path}")

if __name__ == "__main__":
    tools_dir = pathlib.Path(__file__).parent
    wav_path = tools_dir / "145hz_carrier.wav"
    generate_drifting_carrier_tone(wav_path)

    if len(sys.argv) > 1:
        jpg_in = sys.argv[1]
        jpg_out = sys.argv[2] if len(sys.argv) > 2 else jpg_in
        # Enigmatic clue replacing blunt text
        metadata = (
            "blend 1.0 | the space between | f_anchor: 164.81Hz | "
            "H_s: 0.62 | RSF-Observer-7p4"
        )
        embed_metadata(jpg_in, jpg_out, metadata)
