import os
import json
import torch
import numpy as np
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

class ModelEvaluator:
    """
    Evaluation Suite computing Confusion Matrix, Precision, Recall, F1-score, and ROC-AUC.
    Saves actual measured metrics to disk without claiming arbitrary pre-training accuracy targets.
    """
    def compute_metrics(
        self,
        y_true: np.ndarray,
        y_pred_probs: np.ndarray,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Compute comprehensive classification metrics based on ground truth labels and predicted probabilities.
        """
        y_true = np.array(y_true).astype(int)
        y_pred_probs = np.array(y_pred_probs)
        y_pred_binary = (y_pred_probs >= threshold).astype(int)

        # Confusion Matrix
        cm = confusion_matrix(y_true, y_pred_binary, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

        # Sklearn classification metrics
        precision = float(precision_score(y_true, y_pred_binary, zero_division=0))
        recall = float(recall_score(y_true, y_pred_binary, zero_division=0))
        f1 = float(f1_score(y_true, y_pred_binary, zero_division=0))

        # ROC-AUC calculation (requires at least one positive and one negative sample)
        try:
            if len(np.unique(y_true)) > 1:
                roc_auc = float(roc_auc_score(y_true, y_pred_probs))
            else:
                roc_auc = 0.5
        except Exception:
            roc_auc = 0.5

        accuracy = float((tp + tn) / max(1, (tp + tn + fp + fn)))

        metrics = {
            "decision_threshold": threshold,
            "total_samples": int(len(y_true)),
            "confusion_matrix": {
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
            },
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
        }

        return metrics

    def save_metrics_report(self, metrics: Dict[str, Any], output_path: str) -> str:
        """
        Export measured evaluation metrics to JSON file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metrics, f, indent=2)
        return output_path

evaluator = ModelEvaluator()
