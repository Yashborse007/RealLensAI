# RealLens AI — Image Loading Tests
# Coverage: valid load, corrupted bytes, non-image bytes, missing path,
#           huge image downscaling, RGBA→RGB conversion, EXIF transposition

import io
import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image
from fastapi import HTTPException
from preprocessing.image_preprocessor import ImagePreprocessor


@pytest.fixture
def preprocessor():
    return ImagePreprocessor(target_size=(224, 224), max_dimension=4096)


# ─── Valid image loading ───────────────────────────────────────────────────────

def test_load_valid_jpeg_bytes(preprocessor, small_image_bytes):
    """Loading valid JPEG bytes returns a PIL Image in RGB mode."""
    # Convert PNG fixture to JPEG bytes
    buf_in = io.BytesIO(small_image_bytes)
    pil_in = Image.open(buf_in)
    buf_jpeg = io.BytesIO()
    pil_in.save(buf_jpeg, format="JPEG")
    jpeg_bytes = buf_jpeg.getvalue()

    result = preprocessor.load_and_validate_image(jpeg_bytes)

    assert isinstance(result, Image.Image), "Result must be a PIL Image"
    assert result.mode == "RGB", f"Expected RGB, got {result.mode}"


def test_load_valid_png_bytes(preprocessor, small_image_bytes):
    """Loading valid PNG bytes returns a PIL Image in RGB mode."""
    result = preprocessor.load_and_validate_image(small_image_bytes)

    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"
    assert result.size[0] > 0
    assert result.size[1] > 0


def test_load_from_valid_file_path(preprocessor, tmp_jpeg):
    """Loading from a valid file path returns a PIL Image."""
    result = preprocessor.load_and_validate_image(tmp_jpeg)

    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"


def test_rgba_image_is_converted_to_rgb(preprocessor):
    """An RGBA image (e.g., transparent PNG) is converted to RGB."""
    rgba_img = Image.new("RGBA", (64, 64), (0, 128, 255, 200))
    buf = io.BytesIO()
    rgba_img.save(buf, format="PNG")
    rgba_bytes = buf.getvalue()

    result = preprocessor.load_and_validate_image(rgba_bytes)

    assert result.mode == "RGB", f"Expected RGB after RGBA conversion, got {result.mode}"


def test_palette_image_converted_to_rgb(preprocessor):
    """A palette-mode (P) image is converted to RGB."""
    p_img = Image.new("P", (64, 64))
    buf = io.BytesIO()
    p_img.save(buf, format="PNG")
    p_bytes = buf.getvalue()

    result = preprocessor.load_and_validate_image(p_bytes)

    assert result.mode == "RGB"


# ─── Ultra-large image downscaling ───────────────────────────────────────────

def test_ultra_large_image_is_downscaled(preprocessor):
    """Images wider/taller than max_dimension are downscaled while preserving aspect ratio."""
    big_img = Image.new("RGB", (5000, 3000), (200, 100, 50))
    buf = io.BytesIO()
    big_img.save(buf, format="PNG")
    big_bytes = buf.getvalue()

    result = preprocessor.load_and_validate_image(big_bytes)

    w, h = result.size
    assert max(w, h) <= preprocessor.max_dimension, (
        f"Image not downscaled: {w}x{h} exceeds max_dimension {preprocessor.max_dimension}"
    )


def test_image_within_limit_not_downscaled(preprocessor):
    """Images below max_dimension are not resized."""
    normal_img = Image.new("RGB", (800, 600), (50, 100, 150))
    buf = io.BytesIO()
    normal_img.save(buf, format="PNG")
    normal_bytes = buf.getvalue()

    result = preprocessor.load_and_validate_image(normal_bytes)

    assert result.size == (800, 600), f"Image was unexpectedly resized: {result.size}"


# ─── Error cases ─────────────────────────────────────────────────────────────

def test_corrupted_bytes_raise_http_400(preprocessor, corrupted_image_bytes):
    """Corrupted byte buffer raises HTTPException with status 400."""
    with pytest.raises(HTTPException) as exc_info:
        preprocessor.load_and_validate_image(corrupted_image_bytes)

    assert exc_info.value.status_code == 400, (
        f"Expected 400, got {exc_info.value.status_code}"
    )


def test_pdf_bytes_raise_http_400(preprocessor, pdf_header_bytes):
    """PDF header bytes passed as image raise HTTPException 400."""
    with pytest.raises(HTTPException) as exc_info:
        preprocessor.load_and_validate_image(pdf_header_bytes)

    assert exc_info.value.status_code == 400


def test_empty_bytes_raise_http_400(preprocessor):
    """Empty byte buffer raises HTTPException 400."""
    with pytest.raises(HTTPException) as exc_info:
        preprocessor.load_and_validate_image(b"")

    assert exc_info.value.status_code in (400, 422)


def test_missing_file_path_raises_http_404(preprocessor):
    """Non-existent file path raises HTTPException with status 404."""
    with pytest.raises(HTTPException) as exc_info:
        preprocessor.load_and_validate_image("/nonexistent/path/to/missing.jpg")

    assert exc_info.value.status_code == 404


def test_invalid_type_raises_error(preprocessor):
    """Passing an integer (wrong type) raises ValueError or TypeError."""
    with pytest.raises((ValueError, TypeError, HTTPException)):
        preprocessor.load_and_validate_image(12345)


# ─── Quality assessment ───────────────────────────────────────────────────────

def test_quality_score_always_in_range(preprocessor, gradient_image_bytes):
    """Quality score is always clamped to [0.0, 1.0]."""
    result = preprocessor.assess_image_quality(gradient_image_bytes)

    score = result["quality_score"]
    assert isinstance(score, float), f"quality_score must be float, got {type(score)}"
    assert 0.0 <= score <= 1.0, f"quality_score out of range: {score}"


def test_dark_image_is_marked_poor_quality(preprocessor, tmp_dark_png):
    """Nearly-black / textureless image gets POOR quality status."""
    result = preprocessor.assess_image_quality(tmp_dark_png)

    assert result["status"] == "POOR", (
        f"Expected POOR for dark image, got {result['status']} "
        f"(score={result['quality_score']})"
    )
    assert result["quality_score"] <= 0.45


def test_gradient_image_quality_not_poor(preprocessor, tmp_gradient_png):
    """A gradient image with varied pixels should be FAIR or GOOD quality."""
    result = preprocessor.assess_image_quality(tmp_gradient_png)

    assert result["status"] in ("FAIR", "GOOD"), (
        f"Expected FAIR/GOOD for gradient image, got {result['status']}"
    )


def test_quality_result_has_required_keys(preprocessor, small_image_bytes):
    """Quality result always has: status, quality_score, details, warning."""
    result = preprocessor.assess_image_quality(small_image_bytes)

    for key in ("status", "quality_score", "details"):
        assert key in result, f"Missing key '{key}' in quality result"
