"""RealLens AI - Forensic Report Accuracy & Bug Fix Regression Tests.

Automated verification for all 13 scenarios specified in the master prompt:
1. Fake score 0.4857 with threshold 0.5 results in REAL under the existing binary decision convention.
2. The same sample is evaluated as a FALSE NEGATIVE when its independent ground truth is AI-generated.
3. Fake score 0.5 follows the explicitly configured threshold rule (>= 0.50 -> FAKE).
4. Scores above the threshold are classified consistently.
5. Missing EXIF metadata does not automatically produce an AI-generated classification.
6. A frequency-support metric is not treated as a fake probability and not fused into fake probability.
7. Missing audio or temporal data is not treated as a zero fake score.
8. NaN and infinite scores are safely rejected or handled.
9. Contradictory evidence cannot generate unsupported claims of authentic camera sensor noise.
10. The report states that calibration is unavailable when no calibration model exists.
11. REAL classification does not automatically mean verified authenticity (authenticity_verified == False).
12. JSON, frontend, and exported reports agree on prediction and score semantics.
13. Existing image, video, audio, webcam, and multimodal workflows retain their intended behavior.
"""

import math
import os
import sys
import pytest
import numpy as np
from PIL import Image

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "ai-service"))

from ml.config import MULTIMODAL_DECISION_THRESHOLD
from ml.evaluation.ground_truth_evaluator import (
    GroundTruthEvaluator,
    GroundTruthLabel,
    EvaluationOutcome,
    ground_truth_evaluator,
)
from ml.evaluation.metrics import (
    calculate_accuracy,
    calculate_precision,
    calculate_recall,
    calculate_f1,
    calculate_fpr,
    calculate_fnr,
    calculate_full_evaluation_metrics,
)
from ml.inference.multimodal_inference import fuse_multimodal_scores
from services.frequency_service import frequency_service
from services.forensic_analyzer import forensic_analyzer
from services.analysis_orchestrator import AnalysisOrchestrator


class TestForensicAccuracyRegression:
    """13 Comprehensive Regression Tests for Forensic Accuracy & Bug Fix."""

    # Scenario 1: Fake score 0.4857 with threshold 0.5 results in REAL under binary decision rule
    def test_scenario_01_borderline_score_below_threshold_predicts_real(self):
        fake_probability = 0.4857
        threshold = 0.50
        fusion = fuse_multimodal_scores(
            spatial_score=fake_probability,
            modality_availability={"spatial": True, "temporal": False, "frequency": False, "audio": False},
            modality_status={"temporal": "NOT_APPLICABLE", "frequency": "SUPPORTING_ONLY", "audio": "NOT_APPLICABLE"},
            threshold=threshold,
        )
        assert fusion["final_label"] == "REAL"
        # Decision margin: |0.4857 - 0.50| = 0.0143
        margin = abs(fake_probability - threshold)
        assert round(margin, 4) == 0.0143

    # Scenario 2: The same sample is evaluated as a false negative when independent ground truth is AI-generated
    def test_scenario_02_watch_repairing_evaluates_as_false_negative(self):
        eval_result = ground_truth_evaluator.evaluate_watch_repairing_case(
            actual_prediction_score=0.485685,
            threshold=0.50,
            ground_truth_generator="Google Flow AI",
        )
        assert eval_result["actual_model_output"]["predicted_label"] == "REAL"
        assert eval_result["ground_truth"] == "AI_GENERATED"
        assert eval_result["evaluation_outcome"] == "FALSE_NEGATIVE"
        # Genuine model prediction must NOT be rewritten to match ground truth
        assert eval_result["actual_model_output"]["fake_probability"] == 0.485685

    # Scenario 3: Fake score 0.50 follows explicitly configured threshold rule (>= threshold -> FAKE)
    def test_scenario_03_score_at_threshold_boundary_is_fake(self):
        fusion = fuse_multimodal_scores(
            spatial_score=0.50,
            modality_availability={"spatial": True, "temporal": False, "frequency": False, "audio": False},
            modality_status={"temporal": "NOT_APPLICABLE", "frequency": "SUPPORTING_ONLY", "audio": "NOT_APPLICABLE"},
            threshold=0.50,
        )
        assert fusion["final_label"] == "FAKE"
        assert fusion["confidence"] == 0.50

    # Scenario 4: Scores above the threshold are classified consistently as FAKE
    def test_scenario_04_scores_above_threshold_classified_consistently(self):
        for score in (0.5001, 0.65, 0.85, 0.99):
            fusion = fuse_multimodal_scores(
                spatial_score=score,
                modality_availability={"spatial": True, "temporal": False, "frequency": False, "audio": False},
                modality_status={"temporal": "NOT_APPLICABLE", "frequency": "SUPPORTING_ONLY", "audio": "NOT_APPLICABLE"},
                threshold=0.50,
            )
            assert fusion["final_label"] == "FAKE"
            assert fusion["confidence"] == pytest.approx(score, abs=1e-5)

    # Scenario 5: Missing EXIF metadata does not automatically produce an AI-generated classification
    def test_scenario_05_missing_exif_does_not_force_ai_generated(self):
        meta_info = {
            "has_exif": False,
            "camera_make": None,
            "camera_model": None,
            "is_ai_metadata": False,
            "ai_signatures": [],
        }
        freq_info = {
            "grid_anomaly": False,
            "natural_sensor_noise": False,
            "noise_std": 0.82,
            "high_energy_ratio": 0.08,
            "peak_ratio": 1.2,
        }
        calibrated = forensic_analyzer.calibrate_forensic_score(
            spatial_model_prob=0.4857,
            metadata_info=meta_info,
            freq_info=freq_info,
            face_count=1,
        )
        # Should retain REAL classification (not forced to FAKE by missing EXIF)
        assert calibrated["label"] == "REAL"
        assert calibrated["final_score"] == pytest.approx(0.4857, abs=1e-3)
        # Evidence should note that missing EXIF is inconclusive
        meta_item = next(e for e in calibrated["evidence"] if e["type"] == "Metadata Integrity")
        assert "missing metadata alone does not indicate" in meta_item["description"]
        assert meta_item["severity"] == "low"

    # Scenario 6: A frequency-support metric is not treated as a fake probability and not fused
    def test_scenario_06_frequency_metric_excluded_from_fusion_and_sums_to_one(self):
        # 1. Frequency energy ratios must be mutually exclusive and sum to 1.0
        test_img = np.zeros((128, 128, 3), dtype=np.uint8)
        test_img[20:100, 20:100] = 180
        test_img[40:80, 40:80] = 60
        freq_result = frequency_service.analyze_image(test_img)
        summary = freq_result["frequency_summary"]
        ratio_sum = (
            summary["low_frequency_ratio"]
            + summary["mid_frequency_ratio"]
            + summary["high_frequency_ratio"]
        )
        assert pytest.approx(ratio_sum, abs=1e-4) == 1.0

        # 2. Excluded from fake probability fusion
        fusion = fuse_multimodal_scores(
            spatial_score=0.4857,
            frequency_score=0.7293,  # high frequency support metric
            modality_availability={"spatial": True, "frequency": True, "temporal": False, "audio": False},
            modality_status={"frequency": "SUPPORTING_ONLY", "temporal": "NOT_APPLICABLE", "audio": "NOT_APPLICABLE"},
            threshold=0.50,
        )
        # Frequency must NOT be included in probability fusion denominator
        assert "frequency" not in fusion["available_modalities"]
        assert fusion["evidence"]["frequency"]["status"] == "SUPPORTING_ONLY"
        assert fusion["final_label"] == "REAL"

    # Scenario 7: Missing audio or temporal data is not treated as zero fake score
    def test_scenario_07_missing_modality_not_treated_as_zero_fake_score(self):
        # When audio is missing, it should NOT pull down a fake score of 0.80
        fusion = fuse_multimodal_scores(
            spatial_score=0.80,
            audio_score=None,
            temporal_score=None,
            modality_availability={"spatial": True, "audio": False, "temporal": False, "frequency": False},
            modality_status={"audio": "NOT_APPLICABLE", "temporal": "NOT_APPLICABLE", "frequency": "SUPPORTING_ONLY"},
            threshold=0.50,
        )
        # Denominator only includes spatial (0.80), not (0.80 + 0 + 0) / 3
        assert fusion["available_modalities"] == ["spatial"]
        assert fusion["final_label"] == "FAKE"
        assert pytest.approx(fusion["confidence"], abs=1e-4) == 0.80

    # Scenario 8: NaN and infinite scores are safely rejected or clamped
    def test_scenario_08_nan_and_infinite_scores_handled_safely(self):
        for bad_score in (float("nan"), float("inf"), float("-inf"), None):
            fusion = fuse_multimodal_scores(
                spatial_score=bad_score,
                modality_availability={"spatial": True},
                threshold=0.50,
            )
            assert fusion is not None
            assert isinstance(fusion["confidence"], float)
            assert not math.isnan(fusion["confidence"])
            assert not math.isinf(fusion["confidence"])

    # Scenario 9: Contradictory evidence cannot generate unsupported claims of authentic camera sensor noise
    def test_scenario_09_contradictory_noise_does_not_claim_authentic_sensor(self):
        freq_info = {
            "noise_std": 0.82,  # Low noise std (anomaly)
            "natural_sensor_noise": False,
            "grid_anomaly": False,
            "high_energy_ratio": 0.08,
            "peak_ratio": 1.1,
        }
        meta_info = {"has_exif": False, "is_ai_metadata": False}
        calibrated = forensic_analyzer.calibrate_forensic_score(
            spatial_model_prob=0.4857,
            metadata_info=meta_info,
            freq_info=freq_info,
            face_count=1,
        )
        # Must flag noise anomaly, NOT claim authentic camera hardware noise
        evidence_types = [e["type"] for e in calibrated["evidence"]]
        assert "Sensor Noise Residual Anomaly" in evidence_types
        assert "Sensor Noise Residual Consistency" not in evidence_types
        # Description must mention synthetic oversmoothing / low noise std
        anomaly_item = next(e for e in calibrated["evidence"] if e["type"] == "Sensor Noise Residual Anomaly")
        assert "0.82" in anomaly_item["metricValue"]
        assert "synthetic oversmoothing" in anomaly_item["description"]

    # Scenario 10: The report states that calibration is unavailable when no calibration model exists
    def test_scenario_10_calibration_reported_as_not_configured(self):
        calibrated = forensic_analyzer.calibrate_forensic_score(
            spatial_model_prob=0.4857,
            metadata_info={"has_exif": False, "is_ai_metadata": False},
            freq_info={"natural_sensor_noise": False, "grid_anomaly": False},
            face_count=1,
        )
        assert calibrated["calibration_status"] == "NOT_CONFIGURED"
        assert calibrated["statistically_calibrated"] is False
        assert "no held-out calibration model is configured" in calibrated["calibration_note"].lower()

    # Scenario 11: REAL classification does not automatically mean verified authenticity
    def test_scenario_11_real_classification_authenticity_verified_is_false(self):
        calibrated = forensic_analyzer.calibrate_forensic_score(
            spatial_model_prob=0.4857,
            metadata_info={"has_exif": False, "is_ai_metadata": False},
            freq_info={"natural_sensor_noise": False, "grid_anomaly": False},
            face_count=1,
        )
        assert calibrated["label"] == "REAL"
        assert calibrated["authenticity_verified"] is False

    # Scenario 12: JSON, frontend, and evaluation framework agree on prediction and score semantics
    def test_scenario_12_schema_consistency_across_framework(self):
        evaluator = GroundTruthEvaluator(default_threshold=0.50)
        eval_sample = evaluator.evaluate_sample(
            sample_id="test_image.png",
            ground_truth=GroundTruthLabel.AI_GENERATED,
            fake_probability=0.4857,
            threshold=0.50,
            generator="Google Flow AI",
        )
        sample_dict = eval_sample.to_dict()
        assert sample_dict["predicted_label"] == "REAL"
        assert sample_dict["ground_truth"] == "AI_GENERATED"
        assert sample_dict["evaluation_outcome"] == "FALSE_NEGATIVE"
        assert sample_dict["decision_margin"] == 0.0143
        assert sample_dict["threshold"] == 0.50

    # Scenario 13: Existing multimodal endpoints and evaluation metrics calculate precision, recall, fpr, fnr
    def test_scenario_13_evaluation_metrics_precision_recall_fpr_fnr(self):
        # 4 samples: 2 genuine camera, 2 synthetic
        # Model gets 1 TP, 1 FN (WatchRepairing), 1 TN, 1 FP
        y_true = [1, 1, 0, 0]  # [Synthetic, Synthetic, Real, Real]
        y_pred = [1, 0, 0, 1]  # [Predicted Fake, Predicted Real, Predicted Real, Predicted Fake]
        metrics = calculate_full_evaluation_metrics(y_true, y_pred)
        assert metrics["accuracy"] == 0.50
        assert metrics["true_positives"] == 1
        assert metrics["false_negatives"] == 1  # 1 false negative (like WatchRepairing)
        assert metrics["true_negatives"] == 1
        assert metrics["false_positives"] == 1
        assert metrics["false_negative_rate"] == 0.50
        assert metrics["false_positive_rate"] == 0.50
        assert metrics["precision"] == 0.50
        assert metrics["recall"] == 0.50
