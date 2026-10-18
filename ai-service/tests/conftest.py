# RealLens AI — pytest configuration and fixtures
# conftest.py — shared fixtures for all ai-service tests

import io
import os
import sys
import struct
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest

# Support imports from both the service package and repository-level ml package.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "ai-service"
sys.path.insert(0, str(AI_SERVICE_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT))


# ─── Synthetic image generators ───────────────────────────────────────────────

def _solid_color_png_bytes(width: int = 64, height: int = 64, color=(128, 100, 80)) -> bytes:
    """
    Return raw PNG bytes for a solid-color image.
    Requires Pillow (already a project dependency via preprocessing).
    """
    from PIL import Image
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _gradient_png_bytes(width: int = 224, height: int = 224) -> bytes:
    """Return PNG bytes of a gradient (higher blur variance → GOOD quality)."""
    from PIL import Image
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            arr[y, x] = [x % 256, y % 256, (x + y) % 256]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _almost_black_png_bytes(width: int = 64, height: int = 64) -> bytes:
    """Nearly invisible / extremely dark image → POOR quality."""
    return _solid_color_png_bytes(width, height, color=(2, 2, 2))


def _tiny_png_bytes() -> bytes:
    """8×8 px image — low resolution."""
    return _solid_color_png_bytes(8, 8)


def _silent_wav_bytes(duration_s: float = 0.5, sample_rate: int = 22050) -> bytes:
    """Return bytes of a real but silent WAV file."""
    buf = io.BytesIO()
    n_frames = int(duration_s * sample_rate)
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


def _tone_wav_bytes(freq_hz: float = 440.0, duration_s: float = 1.0,
                    sample_rate: int = 22050, amplitude: float = 0.5) -> bytes:
    """Return bytes of a pure sine-wave WAV (non-silent audio)."""
    buf = io.BytesIO()
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    samples = (amplitude * np.sin(2 * np.pi * freq_hz * t) * 32767).astype(np.int16)
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_jpeg(tmp_path):
    """Write a tiny JPEG to disk and return its path."""
    from PIL import Image
    img = Image.new("RGB", (64, 64), (100, 150, 200))
    p = tmp_path / "test.jpg"
    img.save(str(p), format="JPEG")
    return str(p)


@pytest.fixture
def tmp_gradient_png(tmp_path):
    """Write a 224×224 gradient PNG and return its path."""
    p = tmp_path / "gradient.png"
    p.write_bytes(_gradient_png_bytes(224, 224))
    return str(p)


@pytest.fixture
def tmp_dark_png(tmp_path):
    """Almost-black PNG → POOR quality."""
    p = tmp_path / "dark.png"
    p.write_bytes(_almost_black_png_bytes())
    return str(p)


@pytest.fixture
def tmp_tiny_png(tmp_path):
    """8×8 tiny PNG → low resolution."""
    p = tmp_path / "tiny.png"
    p.write_bytes(_tiny_png_bytes())
    return str(p)


@pytest.fixture
def tmp_corrupted_file(tmp_path):
    """File with .jpg extension but garbage content."""
    p = tmp_path / "corrupted.jpg"
    p.write_bytes(b"NOT_A_JPEG_####GARBAGE_BYTES####")
    return str(p)


@pytest.fixture
def tmp_silent_wav(tmp_path):
    """Silent WAV file on disk."""
    p = tmp_path / "silent.wav"
    p.write_bytes(_silent_wav_bytes(duration_s=0.5))
    return str(p)


@pytest.fixture
def tmp_tone_wav(tmp_path):
    """440Hz sine wave WAV file."""
    p = tmp_path / "tone.wav"
    p.write_bytes(_tone_wav_bytes(duration_s=2.0))
    return str(p)


@pytest.fixture
def small_image_bytes():
    """Return raw PNG bytes (64×64) without touching disk."""
    return _solid_color_png_bytes(64, 64)


@pytest.fixture
def gradient_image_bytes():
    """Return 224×224 gradient PNG bytes."""
    return _gradient_png_bytes(224, 224)


@pytest.fixture
def corrupted_image_bytes():
    return b"NOT_A_REAL_IMAGE_BYTES_CORRUPT_DATA####"


@pytest.fixture
def pdf_header_bytes():
    """PDF file mistakenly passed as image."""
    return b"%PDF-1.4 1 0 obj<</Type /Catalog>>endobj"


@pytest.fixture
def silent_wav_bytes():
    return _silent_wav_bytes(duration_s=0.5)


@pytest.fixture
def tone_wav_bytes():
    return _tone_wav_bytes(duration_s=2.0)
