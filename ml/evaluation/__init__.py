from importlib import import_module

__all__ = [
    "calculate_accuracy",
    "calculate_precision",
    "calculate_recall",
    "calculate_f1",
    "calculate_roc_auc",
    "calculate_confusion_matrix",
    "calculate_fpr",
    "calculate_fnr",
    "calculate_full_evaluation_metrics",
    "GroundTruthLabel",
    "EvaluationOutcome",
    "EvaluationSample",
    "GroundTruthEvaluator",
    "ground_truth_evaluator",
]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name in {"GroundTruthLabel", "EvaluationOutcome", "EvaluationSample", "GroundTruthEvaluator", "ground_truth_evaluator"}:
        return getattr(import_module(".ground_truth_evaluator", __name__), name)
    return getattr(import_module(".metrics", __name__), name)

