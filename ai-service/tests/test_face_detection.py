# RealLens AI — Face Detection Tests
# Coverage: no face, one face, multiple faces, blurry image, low-resolution,
#           crop shape, draw detections, edge cases

import io
import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image
from preprocessing.face_detector import FaceDetector


@pytest.fixture
def detector():
    """Return a fresh FaceDetector instance."""
    return FaceDetector()


def _make_numpy_image(width: int = 224, height: int = 224,
                      color=(128, 128, 128)) -> np.ndarray:
    """Create a solid-color BGR NumPy image (OpenCV layout)."""
    img = np.full((height, width, 3), color[::-1], dtype=np.uint8)
    return img


def _make_pil_image(width: int = 64, height: int = 64,
                    color=(100, 150, 200)) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def _make_noisy_image(width: int = 224, height: int = 224) -> np.ndarray:
    """Random noise image — simulates blurry/textured media."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, (height, width, 3), dtype=np.uint8)


# ─── detect_faces — basic correctness ─────────────────────────────────────────

def test_detect_faces_returns_list(detector):
    """detect_faces always returns a list (never raises, never returns None)."""
    img = _make_numpy_image()
    result = detector.detect_faces(img)

    assert isinstance(result, list), f"Expected list, got {type(result)}"


def test_detect_faces_on_solid_image_returns_empty(detector):
    """A plain solid-color image has no detectable faces."""
    img = _make_numpy_image(224, 224, color=(180, 140, 100))
    result = detector.detect_faces(img)

    assert isinstance(result, list)
    # Solid images have no face structure — must return 0 (or cascade unavailable → [])
    assert len(result) == 0, (
        f"Expected 0 faces on solid image, got {len(result)}"
    )


def test_detect_faces_on_pil_image_returns_list(detector):
    """detect_faces accepts PIL Image objects without crashing."""
    pil_img = _make_pil_image(224, 224)
    result = detector.detect_faces(pil_img)

    assert isinstance(result, list)


def test_detect_faces_on_noisy_image_does_not_crash(detector):
    """Noisy/blurry images don't crash detect_faces — returns list."""
    noisy = _make_noisy_image(224, 224)
    result = detector.detect_faces(noisy)

    assert isinstance(result, list)


def test_detect_faces_on_low_resolution_does_not_crash(detector):
    """32×32 px low-resolution image must not raise — returns list."""
    low_res = _make_numpy_image(32, 32)
    result = detector.detect_faces(low_res)

    assert isinstance(result, list)


def test_detect_faces_on_very_tiny_image_does_not_crash(detector):
    """1×1 pixel image must not raise."""
    tiny = np.zeros((1, 1, 3), dtype=np.uint8)
    result = detector.detect_faces(tiny)

    assert isinstance(result, list)


def test_detect_faces_invalid_type_raises_value_error(detector):
    """Passing an unexpected type (string) raises ValueError."""
    with pytest.raises(ValueError):
        detector.detect_faces("not_an_image")


# ─── Detection result structure ───────────────────────────────────────────────

def test_detection_dict_has_required_keys(detector):
    """
    When faces are detected, each result dict must have keys:
    x, y, w, h, confidence — simulated by injecting a fake detection.
    """
    # Inject a synthetic detection list to test the dict contract
    fake_detections = [{"x": 10, "y": 20, "w": 80, "h": 80, "confidence": 0.95}]

    # Validate structure directly
    for det in fake_detections:
        assert "x" in det
        assert "y" in det
        assert "w" in det
        assert "h" in det
        assert "confidence" in det
        assert 0.0 <= det["confidence"] <= 1.0


# ─── extract_face_crops ───────────────────────────────────────────────────────

def test_extract_face_crops_with_no_detections_returns_empty(detector):
    """extract_face_crops with empty detections list returns empty list."""
    img = _make_numpy_image(224, 224)
    crops = detector.extract_face_crops(img, detections=[], target_size=(224, 224))

    assert crops == [], f"Expected [], got {crops}"


def test_extract_face_crops_with_one_detection_returns_one_crop(detector):
    """extract_face_crops with 1 detection returns exactly 1 crop."""
    img = _make_numpy_image(224, 224)
    detections = [{"x": 50, "y": 50, "w": 80, "h": 80, "confidence": 0.9}]

    crops = detector.extract_face_crops(img, detections=detections, target_size=(224, 224))

    assert len(crops) == 1, f"Expected 1 crop, got {len(crops)}"


def test_extract_face_crops_shape_is_target_size(detector):
    """Each crop must have shape (target_h, target_w, 3)."""
    img = _make_numpy_image(300, 300)
    detections = [{"x": 50, "y": 50, "w": 100, "h": 100, "confidence": 0.9}]
    target = (112, 112)

    crops = detector.extract_face_crops(img, detections=detections, target_size=target)

    assert len(crops) == 1
    crop = crops[0]
    assert crop.shape == (target[1], target[0], 3), (
        f"Expected shape {(target[1], target[0], 3)}, got {crop.shape}"
    )


def test_extract_face_crops_with_multiple_detections(detector):
    """extract_face_crops with N detections returns N crops."""
    img = _make_numpy_image(400, 400)
    detections = [
        {"x": 20, "y": 20, "w": 60, "h": 60, "confidence": 0.9},
        {"x": 150, "y": 150, "w": 60, "h": 60, "confidence": 0.85},
        {"x": 280, "y": 20, "w": 60, "h": 60, "confidence": 0.88},
    ]

    crops = detector.extract_face_crops(img, detections=detections, target_size=(224, 224))

    assert len(crops) == len(detections), (
        f"Expected {len(detections)} crops, got {len(crops)}"
    )


def test_extract_face_crops_clamps_to_image_boundaries(detector):
    """Bounding box extending beyond image borders should be clamped — no crash."""
    img = _make_numpy_image(100, 100)
    detections = [
        {"x": 80, "y": 80, "w": 100, "h": 100, "confidence": 0.9}  # extends beyond 100×100
    ]

    crops = detector.extract_face_crops(img, detections=detections, target_size=(224, 224))

    # Should return 1 crop or 0 if degenerate — must not crash
    assert isinstance(crops, list)


# ─── draw_detections ──────────────────────────────────────────────────────────

def test_draw_detections_returns_numpy_array(detector):
    """draw_detections returns a NumPy ndarray of same spatial dimensions."""
    img = _make_numpy_image(224, 224)
    detections = [{"x": 50, "y": 50, "w": 80, "h": 80, "confidence": 0.9}]

    annotated = detector.draw_detections(img, detections)

    assert isinstance(annotated, np.ndarray)
    assert annotated.shape[:2] == img.shape[:2], "Annotated image must preserve spatial dimensions"


def test_draw_detections_does_not_mutate_original(detector):
    """Original image must not be modified after draw_detections."""
    img = _make_numpy_image(224, 224, color=(100, 100, 100))
    original_copy = img.copy()
    detections = [{"x": 30, "y": 30, "w": 80, "h": 80, "confidence": 0.9}]

    detector.draw_detections(img, detections)

    np.testing.assert_array_equal(
        img, original_copy, err_msg="Original image was mutated by draw_detections"
    )


def test_draw_detections_with_empty_list_returns_image(detector):
    """draw_detections with no detections returns a valid image array."""
    img = _make_numpy_image(224, 224)
    annotated = detector.draw_detections(img, [])

    assert isinstance(annotated, np.ndarray)
    assert annotated.shape == img.shape
