from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def calculate_accuracy(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    return float(accuracy_score(y_true, y_pred))


def calculate_precision(y_true: Sequence[int], y_pred: Sequence[int], zero_division: int = 0) -> float:
    return float(precision_score(y_true, y_pred, zero_division=zero_division))


def calculate_recall(y_true: Sequence[int], y_pred: Sequence[int], zero_division: int = 0) -> float:
    return float(recall_score(y_true, y_pred, zero_division=zero_division))


def calculate_f1(y_true: Sequence[int], y_pred: Sequence[int], zero_division: int = 0) -> float:
    return float(f1_score(y_true, y_pred, zero_division=zero_division))


def calculate_fpr(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp = float(cm[0, 0]), float(cm[0, 1])
    denom = fp + tn
    return float(fp / denom) if denom > 0 else 0.0


def calculate_fnr(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    fn, tp = float(cm[1, 0]), float(cm[1, 1])
    denom = fn + tp
    return float(fn / denom) if denom > 0 else 0.0


def calculate_full_evaluation_metrics(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    y_score: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp = int(cm[0, 0]), int(cm[0, 1])
    fn, tp = int(cm[1, 0]), int(cm[1, 1])

    acc = calculate_accuracy(y_true, y_pred)
    prec = calculate_precision(y_true, y_pred)
    rec = calculate_recall(y_true, y_pred)
    f1 = calculate_f1(y_true, y_pred)
    fpr = calculate_fpr(y_true, y_pred)
    fnr = calculate_fnr(y_true, y_pred)

    roc_auc = None
    if y_score is not None:
        try:
            # Requires at least one positive and one negative sample
            if len(set(y_true)) > 1:
                roc_auc = calculate_roc_auc(y_true, y_score)
        except Exception:
            roc_auc = None

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "confusion_matrix": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
            "raw": [[tn, fp], [fn, tp]],
        },
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "total_samples": len(y_true),
    }
