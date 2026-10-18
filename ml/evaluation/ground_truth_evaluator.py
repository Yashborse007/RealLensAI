"""RealLens AI - Ground Truth Evaluation Framework.

Provides an independent evaluation layer for labelled benchmark datasets and test media.
Source labels are maintained independently from detector inference predictions.
Evaluates binary classification performance, confusion matrices, false positive / negative
rates, and per-generator breakdowns without conflating model outputs with ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from ml.evaluation.metrics import calculate_full_evaluation_metrics


class GroundTruthLabel(str, Enum):
    """Independently verified ground-truth media origin categories."""

    GENUINE_CAMERA = "GENUINE_CAMERA"
    AI_GENERATED = "AI_GENERATED"
    FACE_SWAP = "FACE_SWAP"
    MANIPULATED_OTHER = "MANIPULATED_OTHER"

    @classmethod
    def from_string(cls, raw: str) -> GroundTruthLabel:
        val = str(raw).strip().upper().replace(" ", "_").replace("-", "_")
        if val in {"REAL", "AUTHENTIC", "GENUINE", "GENUINE_CAMERA", "CAMERA"}:
            return cls.GENUINE_CAMERA
        if val in {"AI_GENERATED", "SYNTHETIC", "GENERATED", "DIFFUSION", "GAN", "FLOW", "GOOGLE_FLOW"}:
            return cls.AI_GENERATED
        if val in {"FACE_SWAP", "DEEPFAKE", "FACESWAP"}:
            return cls.FACE_SWAP
        return cls.MANIPULATED_OTHER

    @property
    def is_manipulated(self) -> bool:
        """Returns True if the ground truth represents synthetic or manipulated media."""
        return self != GroundTruthLabel.GENUINE_CAMERA


class EvaluationOutcome(str, Enum):
    """Evaluation result comparing predicted binary class with ground truth."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    TRUE_NEGATIVE = "TRUE_NEGATIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FALSE_NEGATIVE = "FALSE_NEGATIVE"


@dataclass
class EvaluationSample:
    """A single evaluation record with separate ground truth and model output."""

    sample_id: str
    ground_truth: GroundTruthLabel
    generator: str = "unknown"
    fake_probability: float = 0.0
    predicted_label: str = "REAL"
    threshold: float = 0.50
    outcome: EvaluationOutcome = field(init=False)
    decision_margin: float = field(init=False)

    def __post_init__(self):
        self.decision_margin = round(abs(float(self.fake_probability) - float(self.threshold)), 6)
        is_gt_fake = self.ground_truth.is_manipulated
        is_pred_fake = str(self.predicted_label).upper() == "FAKE"

        if is_gt_fake and is_pred_fake:
            self.outcome = EvaluationOutcome.TRUE_POSITIVE
        elif not is_gt_fake and not is_pred_fake:
            self.outcome = EvaluationOutcome.TRUE_NEGATIVE
        elif not is_gt_fake and is_pred_fake:
            self.outcome = EvaluationOutcome.FALSE_POSITIVE
        else:
            self.outcome = EvaluationOutcome.FALSE_NEGATIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "ground_truth": self.ground_truth.value,
            "is_manipulated_ground_truth": self.ground_truth.is_manipulated,
            "generator": self.generator,
            "fake_probability": round(self.fake_probability, 6),
            "predicted_label": self.predicted_label,
            "threshold": self.threshold,
            "decision_margin": self.decision_margin,
            "evaluation_outcome": self.outcome.value,
        }


class GroundTruthEvaluator:
    """Evaluates detector inference outputs against independent ground-truth labels."""

    def __init__(self, default_threshold: float = 0.50):
        self.default_threshold = default_threshold

    def evaluate_sample(
        self,
        sample_id: str,
        ground_truth: str | GroundTruthLabel,
        fake_probability: float,
        threshold: Optional[float] = None,
        generator: str = "unknown",
    ) -> EvaluationSample:
        thresh = threshold if threshold is not None else self.default_threshold
        pred_label = "FAKE" if fake_probability >= thresh else "REAL"
        gt_enum = (
            ground_truth
            if isinstance(ground_truth, GroundTruthLabel)
            else GroundTruthLabel.from_string(ground_truth)
        )
        return EvaluationSample(
            sample_id=sample_id,
            ground_truth=gt_enum,
            generator=generator,
            fake_probability=fake_probability,
            predicted_label=pred_label,
            threshold=thresh,
        )

    def evaluate_dataset(
        self,
        samples: Sequence[EvaluationSample | Dict[str, Any]],
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        evaluated_samples: List[EvaluationSample] = []
        for s in samples:
            if isinstance(s, EvaluationSample):
                evaluated_samples.append(s)
            elif isinstance(s, dict):
                evaluated_samples.append(
                    self.evaluate_sample(
                        sample_id=s.get("sample_id", s.get("id", "sample")),
                        ground_truth=s.get("ground_truth", "GENUINE_CAMERA"),
                        fake_probability=float(s.get("fake_probability", s.get("score", 0.0))),
                        threshold=threshold or s.get("threshold", self.default_threshold),
                        generator=s.get("generator", "unknown"),
                    )
                )

        if not evaluated_samples:
            return {
                "total_samples": 0,
                "message": "No evaluation samples provided.",
            }

        y_true = [1 if s.ground_truth.is_manipulated else 0 for s in evaluated_samples]
        y_pred = [1 if s.predicted_label == "FAKE" else 0 for s in evaluated_samples]
        y_score = [s.fake_probability for s in evaluated_samples]

        overall_metrics = calculate_full_evaluation_metrics(y_true, y_pred, y_score)

        # Per-generator breakdown
        generators = set(s.generator for s in evaluated_samples if s.generator != "unknown")
        per_generator: Dict[str, Dict[str, Any]] = {}
        for gen in sorted(generators):
            gen_samples = [s for s in evaluated_samples if s.generator == gen]
            gen_true = [1 if s.ground_truth.is_manipulated else 0 for s in gen_samples]
            gen_pred = [1 if s.predicted_label == "FAKE" else 0 for s in gen_samples]
            gen_scores = [s.fake_probability for s in gen_samples]
            per_generator[gen] = calculate_full_evaluation_metrics(gen_true, gen_pred, gen_scores)
            per_generator[gen]["sample_count"] = len(gen_samples)

        return {
            "overall_metrics": overall_metrics,
            "per_generator_metrics": per_generator,
            "evaluated_samples": [s.to_dict() for s in evaluated_samples],
            "total_evaluated": len(evaluated_samples),
        }

    def evaluate_watch_repairing_case(
        self,
        actual_prediction_score: float = 0.485685,
        threshold: float = 0.50,
        ground_truth_generator: str = "Google Flow AI",
    ) -> Dict[str, Any]:
        """Specific evaluation audit for the reproducible test image WatchRepairing.png.

        Ground Truth: Known AI-Generated image from Google Flow AI generation history.
        Actual Model Prediction: fake_probability = 0.4857 < 0.50 -> REAL.
        Evaluation Outcome: FALSE NEGATIVE.
        Note: The model prediction is recorded as-is without rewriting it to match ground truth.
        """
        sample = self.evaluate_sample(
            sample_id="WatchRepairing.png",
            ground_truth=GroundTruthLabel.AI_GENERATED,
            fake_probability=actual_prediction_score,
            threshold=threshold,
            generator=ground_truth_generator,
        )
        return {
            "sample_id": sample.sample_id,
            "ground_truth": sample.ground_truth.value,
            "ground_truth_description": f"Known synthetic media generated via {ground_truth_generator}.",
            "actual_model_output": {
                "fake_probability": sample.fake_probability,
                "predicted_label": sample.predicted_label,
                "threshold": sample.threshold,
                "decision_margin": sample.decision_margin,
                "decision_margin_percentage": f"{sample.decision_margin * 100:.2f}%",
            },
            "evaluation_outcome": sample.outcome.value,
            "forensic_conclusion": (
                "FALSE NEGATIVE: The detector model predicted REAL (fake_probability: 0.4857 < 0.50), "
                f"while the independent verified ground truth is {sample.ground_truth.value} ({ground_truth_generator}). "
                "The actual model score is faithfully preserved without fabricating or forcing a synthetic label."
            ),
        }


ground_truth_evaluator = GroundTruthEvaluator()

__all__ = [
    "GroundTruthLabel",
    "EvaluationOutcome",
    "EvaluationSample",
    "GroundTruthEvaluator",
    "ground_truth_evaluator",
]
