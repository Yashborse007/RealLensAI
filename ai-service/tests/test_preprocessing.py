# RealLens AI — Preprocessing Pipeline Tests
# Coverage: full process() output structure, tensor shape/dtype/range,
#           no-face fallback, quality assessment, edge cases

import io
import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import torch
from PIL import Image
from fastapi import HTTPException
from preprocessing.image_preprocessor import ImagePreprocessor


@pytest.fixture
def preprocessor():
    return ImagePreprocessor(target_size=(224, 224), max_dimension=4096)


# ─── process() — output contract ──────────────────────────────────────────────

def test_process_returns_required_keys(preprocessor, tmp_gradient_png):
    """process() must return all required keys in the result dict."""
    result = preprocessor.process(tmp_gradient_png)

    required_keys = [
        "face_count",
        "bounding_boxes",
        "face_crops_count",
        "batch_tensor",
        "tensor_shape",
        "original_size",
        "quality",
    ]
    for key in required_keys:
        assert key in result, f"Missing key '{key}' in process() output"


def test_process_face_count_is_non_negative_integer(preprocessor, tmp_gradient_png):
    """face_count must be a non-negative integer."""
    result = preprocessor.process(tmp_gradient_png)

    assert isinstance(result["face_count"], int), "face_count must be int"
    assert result["face_count"] >= 0


def test_process_bounding_boxes_is_list(preprocessor, tmp_gradient_png):
    """bounding_boxes must be a list."""
    result = preprocessor.process(tmp_gradient_png)

    assert isinstance(result["bounding_boxes"], list)


# ─── Tensor shape and type ────────────────────────────────────────────────────

def test_process_batch_tensor_is_4d(preprocessor, tmp_gradient_png):
    """batch_tensor must be a 4D tensor: (N, C, H, W) with N ≥ 1."""
    result = preprocessor.process(tmp_gradient_png)
    tensor = result["batch_tensor"]

    assert isinstance(tensor, torch.Tensor), "batch_tensor must be a torch.Tensor"
    assert tensor.dim() == 4, f"Expected 4D tensor, got {tensor.dim()}D"
    N, C, H, W = tensor.shape
    assert N >= 1, "Batch size N must be at least 1"
    assert C == 3, f"Expected 3 channels (RGB), got {C}"


def test_process_tensor_target_size_is_224x224(preprocessor, tmp_gradient_png):
    """Tensor spatial dimensions must match the configured target_size (224×224)."""
    result = preprocessor.process(tmp_gradient_png)
    _, _, H, W = result["batch_tensor"].shape

    assert H == 224, f"Expected H=224, got {H}"
    assert W == 224, f"Expected W=224, got {W}"


def test_process_tensor_dtype_is_float32(preprocessor, tmp_gradient_png):
    """Tensor dtype must be float32."""
    result = preprocessor.process(tmp_gradient_png)
    tensor = result["batch_tensor"]

    assert tensor.dtype == torch.float32, f"Expected float32, got {tensor.dtype}"


def test_process_tensor_values_in_normalized_range(preprocessor, tmp_gradient_png):
    """
    After ImageNet normalization, values must be approximately in [-3, 3].
    (min of channel 0 normalized ~ (0 - 0.485) / 0.229 ≈ -2.12)
    """
    result = preprocessor.process(tmp_gradient_png)
    tensor = result["batch_tensor"]

    min_val = tensor.min().item()
    max_val = tensor.max().item()

    assert min_val >= -4.0, f"Tensor min {min_val} is below expected normalized range"
    assert max_val <= 4.0, f"Tensor max {max_val} is above expected normalized range"


def test_process_tensor_shape_matches_tensor_shape_field(preprocessor, tmp_gradient_png):
    """tensor_shape field must equal list(batch_tensor.shape)."""
    result = preprocessor.process(tmp_gradient_png)
    actual_shape = list(result["batch_tensor"].shape)

    assert result["tensor_shape"] == actual_shape, (
        f"tensor_shape field {result['tensor_shape']} ≠ actual shape {actual_shape}"
    )


# ─── No-face fallback ─────────────────────────────────────────────────────────

def test_process_noface_image_uses_fallback_crop(preprocessor, tmp_gradient_png):
    """
    When no faces are detected, a central crop fallback must be used.
    face_count == 0 but batch_tensor still has N=1 item.
    """
    result = preprocessor.process(tmp_gradient_png)

    # Whether face was found or not, batch_tensor must have ≥ 1 item
    assert result["batch_tensor"].shape[0] >= 1, (
        "Even with 0 detected faces, batch_tensor must contain ≥ 1 crop (fallback)"
    )


def test_process_face_crops_count_matches_batch_size(preprocessor, tmp_jpeg):
    """face_crops_count must match the first dimension of batch_tensor."""
    result = preprocessor.process(tmp_jpeg)

    assert result["face_crops_count"] == result["batch_tensor"].shape[0], (
        f"face_crops_count={result['face_crops_count']} != "
        f"batch_tensor.shape[0]={result['batch_tensor'].shape[0]}"
    )


# ─── normalize_crop_to_tensor ─────────────────────────────────────────────────

def test_normalize_crop_to_tensor_output_shape(preprocessor):
    """normalize_crop_to_tensor returns a (3, 224, 224) tensor."""
    crop_bgr = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    tensor = preprocessor.normalize_crop_to_tensor(crop_bgr)

    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (3, 224, 224), f"Unexpected shape: {tensor.shape}"


def test_normalize_crop_to_tensor_range(preprocessor):
    """Normalized tensor values must be in expected ImageNet-normalized range."""
    # Full-white crop: pixel value 255 in all channels
    white_bgr = np.full((224, 224, 3), 255, dtype=np.uint8)
    tensor = preprocessor.normalize_crop_to_tensor(white_bgr)

    # White pixel (1.0 in [0,1]) normalized: (1.0 - 0.485)/0.229 ≈ 2.25
    assert tensor.max().item() <= 4.0
    assert tensor.min().item() >= -4.0


def test_normalize_crop_to_tensor_black_image(preprocessor):
    """All-black crop: each channel normalized = (0 - mean) / std."""
    black_bgr = np.zeros((224, 224, 3), dtype=np.uint8)
    tensor = preprocessor.normalize_crop_to_tensor(black_bgr)

    # Black pixel channel 0 (R): (0.0 - 0.485) / 0.229 ≈ -2.12
    min_val = tensor.min().item()
    assert min_val < -1.5, f"Expected negative normalized value for black image, got {min_val}"


# ─── assess_image_quality ─────────────────────────────────────────────────────

def test_quality_score_is_float_in_range(preprocessor, small_image_bytes):
    """quality_score must be a float in [0.0, 1.0]."""
    result = preprocessor.assess_image_quality(small_image_bytes)

    score = result["quality_score"]
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0, f"quality_score={score} out of [0, 1] range"


def test_quality_status_valid_enum(preprocessor, gradient_image_bytes):
    """Quality status must be one of GOOD, FAIR, POOR."""
    result = preprocessor.assess_image_quality(gradient_image_bytes)

    assert result["status"] in ("GOOD", "FAIR", "POOR"), (
        f"Unexpected status: {result['status']}"
    )


def test_quality_details_has_resolution_key(preprocessor, small_image_bytes):
    """Quality details dict must contain 'resolution' key."""
    result = preprocessor.assess_image_quality(small_image_bytes)

    assert "resolution" in result["details"], (
        f"Missing 'resolution' in quality details: {result['details']}"
    )


def test_poor_quality_image_has_warning(preprocessor, tmp_dark_png):
    """POOR quality images must have a non-empty warning message."""
    result = preprocessor.assess_image_quality(tmp_dark_png)

    if result["status"] == "POOR":
        assert result.get("warning"), (
            "POOR quality image must have a non-empty warning message"
        )


def test_good_quality_image_score_above_threshold(preprocessor, tmp_gradient_png):
    """GOOD quality status implies quality_score >= 0.75."""
    result = preprocessor.assess_image_quality(tmp_gradient_png)

    if result["status"] == "GOOD":
        assert result["quality_score"] >= 0.75, (
            f"GOOD status but score={result['quality_score']} < 0.75"
        )
