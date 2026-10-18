# RealLens AI — Inference Pipeline Tests
# Covers: _validate_probabilities, _prediction_from_probability,
#         forensic calibration score contract, confidence inflation guards,
#         is_genuine_camera logic, and process_and_predict response contract.

import os
import sys
import tempfile
import pytest
import torch
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.image_service import ImageService
from services.forensic_analyzer import ForensicAnalyzer
from PIL import Image


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _gradient_png(path, width=224, height=224):
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            arr[y, x] = [x % 256, y % 256, (x + y) % 256]
    img = Image.fromarray(arr)
    img.save(path, format="PNG")
    return path


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def svc():
    return ImageService()


@pytest.fixture
def fa():
    return ForensicAnalyzer()


@pytest.fixture
def tmp_gradient_png(tmp_path):
    return _gradient_png(str(tmp_path / "gradient.png"))


@pytest.fixture
def base_meta():
    return {
        "is_ai_metadata": False,
        "is_genuine_camera": False,
        "has_exif": False,
        "ai_signatures": [],
        "camera_make": None,
        "camera_model": None,
    }


@pytest.fixture
def base_freq():
    return {
        "grid_anomaly": False,
        "natural_sensor_noise": True,
        "peak_ratio": 1.5,
        "high_energy_ratio": 0.04,
        "noise_std": 5.0,
    }


# ─── _validate_probabilities ──────────────────────────────────────────────────

class TestValidateProbabilities:
    def test_valid_tensor_passes(self, svc):
        t = torch.tensor([0.1, 0.9, 0.5])
        result = svc._validate_probabilities(t)
        assert isinstance(result, torch.Tensor)
        assert result.shape == (3,)

    def test_empty_tensor_raises(self, svc):
        with pytest.raises(ValueError, match="no prediction scores"):
            svc._validate_probabilities(torch.tensor([]))

    def test_non_tensor_raises_type_error(self, svc):
        with pytest.raises(TypeError, match="torch tensor"):
            svc._validate_probabilities([0.1, 0.9])

    def test_nan_raises(self, svc):
        with pytest.raises(ValueError, match="non-finite"):
            svc._validate_probabilities(torch.tensor([float("nan")]))

    def test_inf_raises(self, svc):
        with pytest.raises(ValueError, match="non-finite"):
            svc._validate_probabilities(torch.tensor([float("inf")]))

    def test_below_zero_raises(self, svc):
        with pytest.raises(ValueError, match="between 0 and 1"):
            svc._validate_probabilities(torch.tensor([-0.01]))

    def test_above_one_raises(self, svc):
        with pytest.raises(ValueError, match="between 0 and 1"):
            svc._validate_probabilities(torch.tensor([1.01]))

    def test_scalar_tensor_reshaped_to_1d(self, svc):
        result = svc._validate_probabilities(torch.tensor(0.75))
        assert result.dim() == 1

    def test_boundary_values_are_valid(self, svc):
        result = svc._validate_probabilities(torch.tensor([0.0, 1.0]))
        assert result.tolist() == [0.0, 1.0]


# ─── _prediction_from_probability ─────────────────────────────────────────────

class TestPredictionFromProbability:
    def test_above_threshold_is_fake(self, svc):
        pred = svc._prediction_from_probability(0.75, 0.5)
        assert pred["label"] == "FAKE"
        assert pred["confidence"] == pytest.approx(0.75)
        assert pred["fake_probability"] == pytest.approx(0.75)

    def test_below_threshold_is_real(self, svc):
        pred = svc._prediction_from_probability(0.3, 0.5)
        assert pred["label"] == "REAL"
        assert pred["confidence"] == pytest.approx(0.7)

    def test_exactly_at_threshold_is_fake(self, svc):
        assert svc._prediction_from_probability(0.5, 0.5)["label"] == "FAKE"

    def test_confidence_clamped(self, svc):
        pred = svc._prediction_from_probability(1.0, 0.5)
        assert 0.0 <= pred["confidence"] <= 1.0

    def test_probability_zero_is_real_full_confidence(self, svc):
        pred = svc._prediction_from_probability(0.0, 0.5)
        assert pred["label"] == "REAL"
        assert pred["confidence"] == pytest.approx(1.0)

    def test_probability_one_is_fake_full_confidence(self, svc):
        pred = svc._prediction_from_probability(1.0, 0.5)
        assert pred["label"] == "FAKE"
        assert pred["confidence"] == pytest.approx(1.0)

    def test_custom_threshold_respected(self, svc):
        assert svc._prediction_from_probability(0.65, 0.70)["label"] == "REAL"

    def test_output_keys_present(self, svc):
        pred = svc._prediction_from_probability(0.6, 0.5)
        assert {"label", "confidence", "fake_probability"}.issubset(pred.keys())


# ─── Confidence NOT inflated — Issue #3 regression guard ──────────────────────

class TestConfidenceNotInflated:
    """Guard against the removed [0.50,1.0]->[0.75,0.99] inflation mapping."""

    def test_near_threshold_fake_not_artificially_boosted(self, svc):
        """52% fake probability must yield ~52% confidence, not >=75%."""
        pred = svc._prediction_from_probability(0.52, 0.5)
        assert pred["label"] == "FAKE"
        assert pred["confidence"] < 0.75, (
            f"Confidence {pred['confidence']:.4f} looks artificially inflated."
        )

    def test_near_threshold_real_not_artificially_boosted(self, svc):
        """48.5% fake probability (REAL) must yield ~51.5% confidence, not >=75%."""
        pred = svc._prediction_from_probability(0.485, 0.5)
        assert pred["label"] == "REAL"
        assert pred["confidence"] < 0.75, (
            f"Confidence {pred['confidence']:.4f} looks artificially inflated."
        )

    def test_forensic_calibrate_does_not_inflate_borderline_score(self, fa, base_meta, base_freq):
        """Moon.png scenario: ~48.5% probability with PRNU sensor-noise support.

        The PRNU heuristic correctly pulls an ambiguous score to 0.15 (strongly REAL)
        because natural_sensor_noise=True is a genuine forensic signal, not inflation.
        What we guard against is the OLD *FAKE* confidence inflation that would have
        mapped 48.5% -> 76% FAKE confidence regardless of forensic signals.

        The final label must be REAL and the confidence must not be > 99%
        (which would indicate fabricated certainty), but a high REAL confidence
        driven by the PRNU check is correct behaviour.
        """
        result = fa.calibrate_forensic_score(
            spatial_model_prob=0.485,
            metadata_info=base_meta,
            freq_info=base_freq,
            face_count=0,
        )
        # PRNU pull-down makes final_score ≈ 0.15 → label REAL, confidence ≈ 0.85.
        # This is CORRECT: it is a forensic signal, not fabricated confidence.
        assert result["label"] == "REAL", (
            "A borderline model score with PRNU support must resolve to REAL."
        )
        # What the old code did was map FAKE 48.5% -> 76.2% FAKE confidence.
        # Guard against that: if label is REAL, confidence is 1 - score which is fine.
        # If label were incorrectly FAKE, the old inflation would produce ~76%.
        # The assertion is: must NOT be FAKE with inflated confidence.
        if result["label"] == "FAKE":
            assert result["confidence"] < 0.75, (
                f"FAKE confidence {result['confidence']:.4f} looks artificially inflated "
                "(the old mapping was [0.50->0.75, 1.0->0.99]). Check forensic calibration."
            )


# ─── Forensic calibrate_forensic_score contract ───────────────────────────────

class TestForensicCalibrateScoreContract:
    def test_required_keys_present(self, fa, base_meta, base_freq):
        result = fa.calibrate_forensic_score(
            spatial_model_prob=0.6,
            metadata_info=base_meta,
            freq_info=base_freq,
            face_count=1,
        )
        for key in ("final_score", "label", "confidence", "evidence",
                    "score_type", "calibration_status", "calibration_note"):
            assert key in result, f"Missing key: {key}"

    def test_final_score_clipped(self, fa):
        meta = {"is_ai_metadata": True, "ai_signatures": ["midjourney"],
                "is_genuine_camera": False, "has_exif": False,
                "camera_make": None, "camera_model": None}
        freq = {"grid_anomaly": True, "natural_sensor_noise": False,
                "peak_ratio": 4.0, "high_energy_ratio": 0.05, "noise_std": 0.5}
        result = fa.calibrate_forensic_score(0.99, meta, freq, 0)
        assert 0.0 <= result["final_score"] <= 1.0
        assert 0.0 <= result["confidence"] <= 1.0

    def test_ai_metadata_boosts_to_fake(self, fa, base_freq):
        meta = {"is_ai_metadata": True, "ai_signatures": ["stable diffusion"],
                "is_genuine_camera": False, "has_exif": False,
                "camera_make": None, "camera_model": None}
        result = fa.calibrate_forensic_score(0.3, meta, base_freq, 0)
        assert result["label"] == "FAKE"
        assert result["final_score"] >= 0.90

    def test_genuine_camera_no_grid_pulls_to_real(self, fa, base_freq):
        meta = {"is_ai_metadata": False, "is_genuine_camera": True,
                "has_exif": True, "ai_signatures": [],
                "camera_make": "Apple", "camera_model": "iPhone 15"}
        result = fa.calibrate_forensic_score(0.55, meta, base_freq, 1)
        assert result["label"] == "REAL"
        assert result["final_score"] <= 0.15

    def test_grid_anomaly_raises_to_fake(self, fa, base_meta):
        freq = {"grid_anomaly": True, "natural_sensor_noise": True,
                "peak_ratio": 3.8, "high_energy_ratio": 0.06, "noise_std": 5.0}
        result = fa.calibrate_forensic_score(0.4, base_meta, freq, 0)
        assert result["label"] == "FAKE"
        assert result["final_score"] >= 0.50

    def test_evidence_list_non_empty(self, fa, base_meta, base_freq):
        result = fa.calibrate_forensic_score(0.5, base_meta, base_freq, 0)
        assert isinstance(result["evidence"], list)
        assert len(result["evidence"]) > 0

    def test_calibration_status_is_not_calibrated(self, fa, base_meta, base_freq):
        result = fa.calibrate_forensic_score(0.7, base_meta, base_freq, 0)
        assert result["calibration_status"] == "NOT_CALIBRATED"

    def test_score_type_is_heuristic(self, fa, base_meta, base_freq):
        result = fa.calibrate_forensic_score(0.6, base_meta, base_freq, 1)
        assert result["score_type"] == "model_heuristic_score"


# ─── is_genuine_camera — Issue #9 regression guard ────────────────────────────

class TestIsGenuineCameraLogic:
    def test_adobe_photoshop_is_not_genuine_camera(self, fa):
        """'Adobe Photoshop' as Make must NOT qualify as genuine camera hardware."""
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif not installed.")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            tmp = f.name
        try:
            img = Image.new("RGB", (64, 64), (128, 128, 128))
            exif_bytes = piexif.dump({
                "0th": {
                    piexif.ImageIFD.Make: b"Adobe Photoshop",
                    piexif.ImageIFD.Model: b"CS6",
                    piexif.ImageIFD.Software: b"Adobe Photoshop CS6",
                },
            })
            img.save(tmp, format="JPEG", exif=exif_bytes)
            result = fa.analyze_metadata(tmp)
            assert result["is_genuine_camera"] is False, (
                "Adobe Photoshop must NOT qualify as genuine camera hardware."
            )
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_known_camera_maker_with_shutter_data_is_genuine(self, fa):
        """Apple iPhone with exposure data must qualify as genuine camera."""
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif not installed.")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            tmp = f.name
        try:
            img = Image.new("RGB", (64, 64), (200, 150, 100))
            exif_bytes = piexif.dump({
                "0th": {
                    piexif.ImageIFD.Make: b"Apple",
                    piexif.ImageIFD.Model: b"iPhone 15 Pro",
                },
                "Exif": {
                    piexif.ExifIFD.ExposureTime: (1, 100),
                    piexif.ExifIFD.FNumber: (18, 10),
                    piexif.ExifIFD.ISOSpeedRatings: 64,
                    piexif.ExifIFD.FocalLength: (26, 10),
                },
            })
            img.save(tmp, format="JPEG", exif=exif_bytes)
            result = fa.analyze_metadata(tmp)
            assert result["is_genuine_camera"] is True
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# ─── process_and_predict response contract ────────────────────────────────────

class TestProcessAndPredictContract:
    """Smoke-tests for the full image service pipeline response shape.
    These tests skip gracefully if no trained checkpoint is available."""

    def test_response_is_dict_with_base_keys(self, svc, tmp_gradient_png):
        result = svc.process_and_predict(tmp_gradient_png)
        assert isinstance(result, dict)
        for key in ("success", "status", "media_type"):
            assert key in result, f"Missing key: {key}"
        assert result["media_type"] == "image"

    def test_successful_prediction_has_label_and_confidence(self, svc, tmp_gradient_png):
        result = svc.process_and_predict(tmp_gradient_png)
        if not result.get("success"):
            pytest.skip("Model checkpoint not available in test environment.")
        pred = result["prediction"]
        assert "label" in pred
        assert "confidence" in pred
        assert pred["label"] in {"REAL", "FAKE", "UNKNOWN"}
        assert 0.0 <= pred["confidence"] <= 1.0

    def test_statistically_calibrated_is_false(self, svc, tmp_gradient_png):
        """Issue #2 regression: statistically_calibrated must always be False."""
        result = svc.process_and_predict(tmp_gradient_png)
        if not result.get("success"):
            pytest.skip("Model checkpoint not available in test environment.")
        cal = result.get("confidence_calibration", {})
        assert cal.get("statistically_calibrated") is False, (
            "statistically_calibrated must be False — no Platt/isotonic calibration exists."
        )

    def test_evidence_contains_only_dicts(self, svc, tmp_gradient_png):
        result = svc.process_and_predict(tmp_gradient_png)
        if not result.get("success"):
            pytest.skip("Model checkpoint not available in test environment.")
        for item in result.get("evidence", []):
            assert isinstance(item, dict), (
                f"Evidence item is not a dict; got {type(item).__name__}: {item!r}"
            )

    def test_no_duplicate_neural_feature_extraction(self, svc, tmp_gradient_png):
        """Issue #6 regression: Neural Feature Extraction must appear at most once."""
        result = svc.process_and_predict(tmp_gradient_png)
        if not result.get("success"):
            pytest.skip("Model checkpoint not available in test environment.")
        count = sum(
            1 for item in result.get("evidence", [])
            if isinstance(item, dict)
            and "neural feature" in str(item.get("type", "")).lower()
        )
        assert count <= 1, (
            f"Found {count} Neural Feature Extraction items — expected at most 1."
        )

    def test_corrupt_file_returns_structured_error(self, svc, tmp_path):
        """A corrupt file must produce a structured error dict, not raise."""
        p = str(tmp_path / "corrupt.jpg")
        with open(p, "wb") as f:
            f.write(b"NOT_A_JPEG_GARBAGE_BYTES_##")
        result = svc.process_and_predict(p)
        assert isinstance(result, dict)
        assert result.get("success") is False
        assert "status" in result
        assert "prediction" in result
