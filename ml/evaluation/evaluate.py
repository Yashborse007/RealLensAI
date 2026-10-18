from __future__ import annotations

from typing import Dict, Sequence

from ml.evaluation.metrics import (
    calculate_accuracy,
    calculate_confusion_matrix,
    calculate_f1,
    calculate_precision,
    calculate_recall,
    calculate_roc_auc,
)


def evaluate_predictions(y_true: Sequence[int], y_pred: Sequence[int], y_score: Sequence[float]) -> Dict[str, float]:
    """Compute standard binary classification metrics from actual model outputs."""
    return {
        "accuracy": calculate_accuracy(y_true, y_pred),
        "precision": calculate_precision(y_true, y_pred),
        "recall": calculate_recall(y_true, y_pred),
        "f1": calculate_f1(y_true, y_pred),
        "roc_auc": calculate_roc_auc(y_true, y_score),
        "confusion_matrix": calculate_confusion_matrix(y_true, y_pred).tolist(),
    }
