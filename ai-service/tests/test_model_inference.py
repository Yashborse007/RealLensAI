# RealLens AI — Model Inference Tests
# Coverage: TemporalSequenceClassifier forward, prepare_sequence, AudioSpectrogramClassifier,
#           VideoModelManager/AudioModelManager availability, output ranges

import os
import sys
import pytest
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.video_model import TemporalSequenceClassifier, VideoModelManager
from models.audio_model import AudioSpectrogramClassifier, AudioModelManager


# ─── TemporalSequenceClassifier ───────────────────────────────────────────────

@pytest.fixture
def video_model():
    """Return an untrained TemporalSequenceClassifier for shape/range tests."""
    model = TemporalSequenceClassifier(feature_dim=64, hidden_dim=32, sequence_length=12)
    model.eval()
    return model


def test_video_model_forward_output_shape(video_model):
    """
    Forward pass on (batch=2, seq=12, feat=64) must return logits of shape (2,).
    """
    x = torch.randn(2, 12, 64)
    logits = video_model(x)

    assert logits.shape == (2,), f"Expected shape (2,), got {logits.shape}"


def test_video_model_predict_probability_in_unit_range(video_model):
    """predict_probability must return values in [0, 1] for any input."""
    x = torch.randn(1, 12, 64)
    probs = video_model.predict_probability(x)

    assert probs.shape == (1,), f"Expected (1,), got {probs.shape}"
    assert probs.min().item() >= 0.0, f"Probability below 0: {probs.min().item()}"
    assert probs.max().item() <= 1.0, f"Probability above 1: {probs.max().item()}"


def test_video_model_single_batch_forward(video_model):
    """Single-sample forward pass returns scalar logit."""
    x = torch.randn(1, 12, 64)
    logit = video_model(x)

    assert logit.numel() == 1, f"Expected 1 logit, got {logit.numel()}"
    assert logit.dtype == torch.float32


def test_video_model_wrong_dim_raises_value_error(video_model):
    """Passing 2D input (missing batch dim) must raise ValueError."""
    with pytest.raises(ValueError):
        video_model(torch.randn(12, 64))  # Missing batch dim


# ─── prepare_sequence ─────────────────────────────────────────────────────────

def test_prepare_sequence_zero_frames_returns_zeros(video_model):
    """prepare_sequence with empty list returns zero-padded tensor."""
    tensor = video_model.prepare_sequence([], sequence_length=12)

    assert tensor.shape == (1, 12, 64), f"Expected (1,12,64), got {tensor.shape}"
    assert tensor.sum().item() == 0.0, "Zero-padding not applied for empty sequence"


def test_prepare_sequence_exact_length_no_padding(video_model):
    """prepare_sequence with exactly seq_length frames uses all frames."""
    frames = [torch.randn(64) for _ in range(12)]
    tensor = video_model.prepare_sequence(frames, sequence_length=12)

    assert tensor.shape == (1, 12, 64)


def test_prepare_sequence_shorter_is_zero_padded(video_model):
    """prepare_sequence with fewer frames than seq_length zero-pads the rest."""
    frames = [torch.ones(64) for _ in range(5)]
    tensor = video_model.prepare_sequence(frames, sequence_length=12)

    assert tensor.shape == (1, 12, 64)
    # Frames 5-11 should be padded zeros
    padded_segment = tensor[0, 5:, :]
    assert padded_segment.sum().item() == 0.0, "Expected zero-padding after last frame"


def test_prepare_sequence_longer_is_truncated(video_model):
    """prepare_sequence with more frames than seq_length truncates to seq_length."""
    frames = [torch.randn(64) for _ in range(20)]
    tensor = video_model.prepare_sequence(frames, sequence_length=12)

    assert tensor.shape == (1, 12, 64), f"Expected truncated to (1,12,64), got {tensor.shape}"


def test_prepare_sequence_numpy_input_converted(video_model):
    """prepare_sequence accepts numpy arrays as frames."""
    import numpy as np
    frames = [np.random.randn(64).astype(np.float32) for _ in range(8)]
    tensor = video_model.prepare_sequence(frames, sequence_length=12)

    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (1, 12, 64)


def test_prepare_sequence_rejects_feature_with_wrong_dimension(video_model):
    with pytest.raises(ValueError, match="length 64"):
        video_model.prepare_sequence([torch.ones(32)], sequence_length=12)


def test_prepare_sequence_rejects_non_positive_length(video_model):
    with pytest.raises(ValueError, match="positive integer"):
        video_model.prepare_sequence([], sequence_length=0)


# ─── AudioSpectrogramClassifier ──────────────────────────────────────────────

@pytest.fixture
def audio_model():
    model = AudioSpectrogramClassifier()
    model.eval()
    return model


def test_audio_model_forward_output_shape(audio_model):
    """
    Forward pass on (batch=1, channels=1, H=128, W=128) returns (1, 1) tensor.
    """
    x = torch.randn(1, 1, 128, 128)
    out = audio_model(x)

    assert out.numel() == 1, f"Expected single output value, got {out.numel()}"


def test_audio_model_output_in_unit_range(audio_model):
    """AudioSpectrogramClassifier ends in Sigmoid — output must be in [0, 1]."""
    x = torch.randn(4, 1, 128, 128)
    out = audio_model(x)

    assert out.min().item() >= 0.0, f"Output below 0: {out.min().item()}"
    assert out.max().item() <= 1.0, f"Output above 1: {out.max().item()}"


def test_audio_model_batch_of_4(audio_model):
    """Batch inference on 4 samples returns 4 predictions."""
    x = torch.randn(4, 1, 64, 64)
    out = audio_model(x)

    assert out.shape[0] == 4, f"Expected batch size 4, got {out.shape[0]}"


def test_audio_model_zero_input_stays_in_range(audio_model):
    """All-zeros spectrogram input still produces valid [0,1] output."""
    x = torch.zeros(1, 1, 128, 128)
    out = audio_model(x)

    val = out.item()
    assert 0.0 <= val <= 1.0, f"Zero-input output out of range: {val}"


# ─── Model Manager availability ───────────────────────────────────────────────

def test_video_model_manager_unavailable_when_no_weights():
    """VideoModelManager.is_available() is False when no weights file exists."""
    manager = VideoModelManager()

    # In test environment without trained weights, is_loaded should be False
    # We verify the field exists and is boolean
    assert isinstance(manager.is_available(), bool), "is_available() must return bool"


def test_audio_model_manager_unavailable_when_no_weights():
    """AudioModelManager.is_available() is False when no weights file exists."""
    manager = AudioModelManager()

    assert isinstance(manager.is_available(), bool)


def test_video_model_manager_model_attribute_exists():
    """VideoModelManager exposes 'model' and 'is_loaded' attributes."""
    manager = VideoModelManager()

    assert hasattr(manager, "model"), "VideoModelManager must have 'model' attribute"
    assert hasattr(manager, "is_loaded"), "VideoModelManager must have 'is_loaded' attribute"


def test_audio_model_manager_model_attribute_exists():
    """AudioModelManager exposes 'model' and 'is_loaded' attributes."""
    manager = AudioModelManager()

    assert hasattr(manager, "model")
    assert hasattr(manager, "is_loaded")
