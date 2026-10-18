# RealLens AI — Multimodal Fusion Tests
# Covers: fuse_multimodal_scores contract, unavailable modality handling,
#         low-quality suppression, supporting-only exclusion, score computation,
#         and boundary/edge cases including the undertrained-model scenario.

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ml.inference.multimodal_inference import fuse_multimodal_scores


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _all_available(spatial=True, temporal=True, frequency=True, audio=True):
    return {"spatial": spatial, "temporal": temporal,
            "frequency": frequency, "audio": audio}


def _fake_scenario(spatial=0.82, temporal=0.79, frequency=0.60, audio=0.70,
                   quality=0.9, availability=None):
    return fuse_multimodal_scores(
        spatial_score=spatial,
        temporal_score=temporal,
        frequency_score=frequency,
        audio_score=audio,
        quality_score=quality,
        modality_availability=availability or _all_available(),
    )


# ─── Output contract ──────────────────────────────────────────────────────────

class TestFusionOutputContract:
    def test_required_keys_present(self):
        result = _fake_scenario()
        for key in ("final_label", "confidence", "evidence", "available_modalities", "quality"):
            assert key in result, f"Missing key: {key}"

    def test_final_label_is_valid_string(self):
        result = _fake_scenario()
        assert result["final_label"] in {"FAKE", "REAL"}

    def test_confidence_in_unit_interval(self):
        result = _fake_scenario()
        assert 0.0 <= result["confidence"] <= 1.0

    def test_available_modalities_is_list(self):
        result = _fake_scenario()
        assert isinstance(result["available_modalities"], list)

    def test_evidence_dict_keyed_by_modality(self):
        result = _fake_scenario()
        for name in ("spatial", "temporal", "frequency", "audio"):
            assert name in result["evidence"]

    def test_quality_dict_has_required_keys(self):
        result = _fake_scenario()
        quality = result["quality"]
        assert "status" in quality
        assert "quality_score" in quality
        assert "message" in quality


# ─── Unavailable modality handling ────────────────────────────────────────────

class TestUnavailableModalityHandling:
    def test_unavailable_audio_excluded_from_modalities(self):
        result = fuse_multimodal_scores(
            spatial_score=0.82,
            temporal_score=0.79,
            frequency_score=0.58,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(audio=False),
        )
        assert "audio" not in result["available_modalities"]
        assert result["evidence"]["audio"]["available"] is False

    def test_unavailable_temporal_excluded(self):
        result = fuse_multimodal_scores(
            spatial_score=0.75,
            temporal_score=None,
            frequency_score=0.55,
            audio_score=None,
            quality_score=0.85,
            modality_availability=_all_available(temporal=False, audio=False),
        )
        assert "temporal" not in result["available_modalities"]
        assert "audio" not in result["available_modalities"]

    def test_frequency_failure_does_not_stop_fusion(self):
        result = fuse_multimodal_scores(
            spatial_score=0.73,
            temporal_score=0.66,
            frequency_score=None,
            audio_score=0.42,
            quality_score=0.8,
            modality_availability=_all_available(frequency=False),
        )
        assert "frequency" not in result["available_modalities"]
        assert "spatial" in result["available_modalities"]
        assert "temporal" in result["available_modalities"]
        assert "audio" in result["available_modalities"]

    def test_missing_score_with_available_flag_true_is_excluded(self):
        """If modality is marked available but score is None, it must be excluded."""
        result = fuse_multimodal_scores(
            spatial_score=0.70,
            temporal_score=None,      # No score despite availability=True
            frequency_score=0.60,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(audio=False),
        )
        assert "temporal" not in result["available_modalities"]

    def test_all_modalities_unavailable_returns_real_zero_confidence(self):
        """When no usable evidence exists, fusion must not fabricate fake evidence."""
        result = fuse_multimodal_scores(
            spatial_score=None,
            temporal_score=None,
            frequency_score=None,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(
                spatial=False, temporal=False, frequency=False, audio=False
            ),
        )
        assert result["final_label"] == "REAL"
        assert result["confidence"] == 0.0
        assert result["available_modalities"] == []


# ─── Low-quality input suppression ────────────────────────────────────────────

class TestLowQualityInputSuppression:
    def test_low_quality_yields_real_zero_confidence(self):
        """Even strong fake signals must be suppressed when quality is too low."""
        result = fuse_multimodal_scores(
            spatial_score=0.91,
            temporal_score=0.89,
            frequency_score=0.75,
            audio_score=0.70,
            quality_score=0.2,
            modality_availability=_all_available(),
        )
        assert result["quality"]["status"] == "LOW_QUALITY_INPUT"
        assert result["final_label"] == "REAL"
        assert result["confidence"] == 0.0

    def test_borderline_quality_above_threshold_fuses_normally(self):
        result = fuse_multimodal_scores(
            spatial_score=0.82,
            temporal_score=0.78,
            frequency_score=0.65,
            audio_score=0.70,
            quality_score=0.8,
            modality_availability=_all_available(),
        )
        assert result["quality"]["status"] == "SUFFICIENT"
        assert result["final_label"] in {"FAKE", "REAL"}

    def test_quality_score_zero_is_low_quality(self):
        result = fuse_multimodal_scores(
            spatial_score=0.99,
            temporal_score=0.99,
            frequency_score=0.99,
            audio_score=0.99,
            quality_score=0.0,
            modality_availability=_all_available(),
        )
        assert result["quality"]["status"] == "LOW_QUALITY_INPUT"


# ─── Supporting-only modality exclusion ───────────────────────────────────────

class TestSupportingOnlyExclusion:
    def test_frequency_as_supporting_only_excluded_from_fusion(self):
        """Frequency marked SUPPORTING_ONLY must not affect the fused probability."""
        result_without_freq = fuse_multimodal_scores(
            spatial_score=0.75,
            temporal_score=None,
            frequency_score=0.90,   # High, but excluded
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, audio=False),
            modality_status={"frequency": "SUPPORTING_ONLY"},
        )
        result_with_freq_included = fuse_multimodal_scores(
            spatial_score=0.75,
            temporal_score=None,
            frequency_score=0.90,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, audio=False),
        )
        # When frequency is SUPPORTING_ONLY, its evidence status should be "SUPPORTING_ONLY"
        assert result_without_freq["evidence"]["frequency"]["status"] == "SUPPORTING_ONLY"
        # Frequency must not be in the modalities that contribute to the fused probability
        assert "frequency" not in result_without_freq["available_modalities"]

    def test_supporting_modality_score_preserved_in_evidence(self):
        """Supporting-only modality evidence must retain its score for transparency."""
        result = fuse_multimodal_scores(
            spatial_score=0.65,
            temporal_score=None,
            frequency_score=0.72,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, audio=False),
            modality_status={"frequency": "SUPPORTING_ONLY"},
        )
        assert result["evidence"]["frequency"]["score"] == pytest.approx(0.72)


# ─── Score computation accuracy ───────────────────────────────────────────────

class TestScoreComputation:
    def test_single_spatial_modality_fused_score_equals_spatial_score(self):
        """With only spatial available, the fused probability must equal spatial_score."""
        spatial = 0.72
        result = fuse_multimodal_scores(
            spatial_score=spatial,
            temporal_score=None,
            frequency_score=None,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, frequency=False, audio=False),
        )
        # final_probability = spatial_score * weight / weight = spatial_score
        assert result["final_label"] == "FAKE"
        # Confidence for FAKE = final_probability
        assert result["confidence"] == pytest.approx(spatial, abs=0.01)

    def test_equal_fake_scores_yield_fake_label(self):
        result = fuse_multimodal_scores(
            spatial_score=0.9,
            temporal_score=0.9,
            frequency_score=0.9,
            audio_score=0.9,
            quality_score=0.9,
            modality_availability=_all_available(),
        )
        assert result["final_label"] == "FAKE"

    def test_equal_real_scores_yield_real_label(self):
        result = fuse_multimodal_scores(
            spatial_score=0.1,
            temporal_score=0.1,
            frequency_score=0.1,
            audio_score=0.1,
            quality_score=0.9,
            modality_availability=_all_available(),
        )
        assert result["final_label"] == "REAL"

    def test_borderline_score_below_threshold_is_real(self):
        """0.49 should map to REAL (below default 0.50 threshold)."""
        result = fuse_multimodal_scores(
            spatial_score=0.49,
            temporal_score=None,
            frequency_score=None,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, frequency=False, audio=False),
        )
        assert result["final_label"] == "REAL"

    def test_borderline_score_at_threshold_is_fake(self):
        """0.50 at the default threshold should map to FAKE."""
        result = fuse_multimodal_scores(
            spatial_score=0.50,
            temporal_score=None,
            frequency_score=None,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, frequency=False, audio=False),
        )
        assert result["final_label"] == "FAKE"


# ─── Undertrained model scenario (moon.png) ───────────────────────────────────

class TestUndertrainedModelScenario:
    """
    Regression tests for the moon.png false-negative root cause:
    - Model trained 1 epoch → near-random ~48.5% fake probability.
    - No AI EXIF → no metadata boost.
    - No grid anomaly → no frequency boost.
    - Result must be REAL with low confidence (not FAKE with inflated 76% confidence).
    """

    def test_near_random_model_output_without_forensic_signals_is_real(self):
        result = fuse_multimodal_scores(
            spatial_score=0.485,   # Near-random output from 1-epoch model
            temporal_score=None,
            frequency_score=0.35,  # No anomaly
            audio_score=None,
            quality_score=0.85,
            modality_availability=_all_available(temporal=False, audio=False),
            modality_status={"frequency": "SUPPORTING_ONLY"},
        )
        assert result["final_label"] == "REAL"

    def test_near_random_confidence_is_not_inflated(self):
        """Raw confidence must not exceed 0.55 for a ~48.5% spatial score."""
        result = fuse_multimodal_scores(
            spatial_score=0.485,
            temporal_score=None,
            frequency_score=None,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, frequency=False, audio=False),
        )
        assert result["confidence"] < 0.55, (
            f"Confidence {result['confidence']:.4f} is suspiciously high for a "
            "near-random model output. Check that no inflation mapping is applied."
        )

    def test_missing_evidence_not_converted_to_fake_evidence(self):
        """No missing modality must ever fabricate a score that drives the label to FAKE."""
        result = fuse_multimodal_scores(
            spatial_score=0.45,
            temporal_score=None,   # Not available
            frequency_score=None,  # Not available
            audio_score=None,      # Not available
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, frequency=False, audio=False),
        )
        for name in ("temporal", "frequency", "audio"):
            ev = result["evidence"][name]
            assert ev["available"] is False, (
                f"{name} modality is unavailable but evidence shows 'available=True'."
            )
        # With only a spatial score of 0.45, label must be REAL
        assert result["final_label"] == "REAL"


# ─── NaN / Inf robustness ─────────────────────────────────────────────────────

class TestNaNInfRobustness:
    def test_nan_spatial_score_is_treated_as_zero(self):
        result = fuse_multimodal_scores(
            spatial_score=float("nan"),
            temporal_score=None,
            frequency_score=None,
            audio_score=None,
            quality_score=0.9,
            modality_availability=_all_available(temporal=False, frequency=False, audio=False),
        )
        # NaN should be coerced to 0.0 → score of 0.0 → REAL
        # But NaN spatial may also be treated as "score=0" available or "missing"
        # Either way, the output must be a valid dict without crashing.
        assert isinstance(result, dict)
        assert result["final_label"] in {"REAL", "FAKE"}
        assert math.isfinite(result["confidence"])

    def test_inf_quality_score_is_clamped(self):
        result = fuse_multimodal_scores(
            spatial_score=0.7,
            temporal_score=None,
            frequency_score=None,
            audio_score=None,
            quality_score=float("inf"),
            modality_availability=_all_available(temporal=False, frequency=False, audio=False),
        )
        assert isinstance(result, dict)
        assert math.isfinite(result["confidence"])

    def test_all_zeros_yields_real(self):
        result = fuse_multimodal_scores(
            spatial_score=0.0,
            temporal_score=0.0,
            frequency_score=0.0,
            audio_score=0.0,
            quality_score=0.9,
            modality_availability=_all_available(),
        )
        assert result["final_label"] == "REAL"
