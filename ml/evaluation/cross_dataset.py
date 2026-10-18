from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ml.evaluation.robustness import (
    AI_SERVICE_ROOT,
    REPORTS_ROOT,
    load_detector,
    parse_label,
    score_frame,
    score_video,
    sha256_file,
)


EXPECTED_DATASETS = ("DATASET_A", "DATASET_B", "DATASET_C")
COMPARISON_FIELDS = (
    "training_dataset",
    "dataset",
    "split",
    "status",
    "identity_disjoint",
    "samples",
    "identities",
    "manipulation_types",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "ece",
    "brier_score",
    "inference_mean_ms",
    "inference_median_ms",
    "inference_p95_ms",
    "dataset_version",
    "license",
    "source_url",
    "preprocessing",
    "model_version",
)


@dataclass(frozen=True)
class ManifestRow:
    sample_id: str
    dataset: str
    split: str
    path: Path
    label: int
    source_label: str
    identity_id: str
    identity_namespace: str
    manipulation_type: str
    dataset_version: str
    license: str
    source_url: str
    preprocessing: str


def load_manifest(path: Path) -> List[ManifestRow]:
    rows: List[ManifestRow] = []
    seen_ids = set()
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = {field.strip().lower() for field in (reader.fieldnames or [])}
        required = {"dataset", "split", "path", "label"}
        missing = sorted(required - columns)
        if missing:
            raise ValueError(f"Manifest is missing required columns: {', '.join(missing)}")

        for row_number, raw_row in enumerate(reader, start=2):
            row = {key.strip().lower(): value or "" for key, value in raw_row.items() if key}
            dataset = row.get("dataset", "").strip().upper()
            split = row.get("split", "").strip().lower()
            if dataset not in EXPECTED_DATASETS:
                raise ValueError(f"Manifest row {row_number} has unsupported dataset {dataset!r}.")
            if split not in {"train", "validation", "val", "test"}:
                raise ValueError(f"Manifest row {row_number} has unsupported split {split!r}.")
            if dataset != "DATASET_A" and split == "train":
                raise ValueError(f"Only DATASET_A may contain training rows (row {row_number}).")

            media_path = Path(row.get("path", "").strip())
            if not media_path.is_absolute():
                media_path = path.parent / media_path
            media_path = media_path.resolve()
            if not media_path.is_file():
                raise ValueError(f"Manifest row {row_number} references missing media: {media_path}")
            if media_path.suffix.lower() not in {
                ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".avi", ".mov", ".mkv", ".webm",
            }:
                raise ValueError(f"Unsupported visual media file: {media_path}")

            source_label = row.get("label", "").strip()
            if not source_label:
                raise ValueError(f"Manifest row {row_number} has no label.")
            sample_id = row.get("sample_id", "").strip() or f"sample-{len(rows) + 1:06d}"
            if sample_id in seen_ids:
                raise ValueError(f"Manifest row {row_number} duplicates sample_id {sample_id!r}.")
            seen_ids.add(sample_id)
            rows.append(ManifestRow(
                sample_id=sample_id,
                dataset=dataset,
                split="validation" if split == "val" else split,
                path=media_path,
                label=parse_label(source_label),
                source_label=source_label,
                identity_id=row.get("identity_id", "").strip(),
                identity_namespace=row.get("identity_namespace", "").strip(),
                manipulation_type=row.get("manipulation_type", "").strip() or "not_recorded",
                dataset_version=row.get("dataset_version", "").strip(),
                license=row.get("license", "").strip(),
                source_url=row.get("source_url", "").strip(),
                preprocessing=row.get("preprocessing", "").strip(),
            ))

    if not rows:
        raise ValueError("The cross-dataset manifest has no rows.")
    return rows


def _metadata_values(rows: Sequence[ManifestRow], field: str) -> List[str]:
    return sorted({value for row in rows if (value := getattr(row, field))})


def _identity_state(training_rows: Sequence[ManifestRow], testing_rows: Sequence[ManifestRow], cross_dataset: bool) -> Tuple[str, List[str]]:
    if not training_rows or any(not row.identity_id for row in (*training_rows, *testing_rows)):
        return "not_verifiable", []

    if cross_dataset:
        namespaces = {row.identity_namespace for row in (*training_rows, *testing_rows)}
        if "" in namespaces or len(namespaces) != 1:
            return "not_comparable", []
        namespace = next(iter(namespaces))
    else:
        namespaces = {row.identity_namespace or row.dataset for row in (*training_rows, *testing_rows)}
        if len(namespaces) != 1:
            return "not_comparable", []
        namespace = next(iter(namespaces))

    training_ids = {row.identity_id for row in training_rows}
    testing_ids = {row.identity_id for row in testing_rows}
    overlaps = sorted(training_ids & testing_ids)
    return ("overlap" if overlaps else "verified_disjoint"), [f"{namespace}:{identity}" for identity in overlaps]


def _identity_fingerprints(rows: Sequence[ManifestRow]) -> List[str]:
    identities = {
        f"{row.identity_namespace or row.dataset}:{row.identity_id}"
        for row in rows
        if row.identity_id
    }
    return sorted(hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16] for identity in identities)


def _classification_metrics(labels: Sequence[int], scores: Sequence[float], predictions: Sequence[int]) -> Dict[str, Optional[float]]:
    if not labels:
        return {"accuracy": None, "precision": None, "recall": None, "f1": None, "roc_auc": None, "ece": None, "brier_score": None}

    tp = sum(actual == 1 and predicted == 1 for actual, predicted in zip(labels, predictions))
    tn = sum(actual == 0 and predicted == 0 for actual, predicted in zip(labels, predictions))
    fp = sum(actual == 0 and predicted == 1 for actual, predicted in zip(labels, predictions))
    fn = sum(actual == 1 and predicted == 0 for actual, predicted in zip(labels, predictions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    positive_scores = [score for label, score in zip(labels, scores) if label == 1]
    negative_scores = [score for label, score in zip(labels, scores) if label == 0]
    auc = None
    if positive_scores and negative_scores:
        sorted_indices = sorted(range(len(scores)), key=scores.__getitem__)
        positive_rank_sum = 0.0
        index = 0
        while index < len(sorted_indices):
            tie_end = index + 1
            score = scores[sorted_indices[index]]
            while tie_end < len(sorted_indices) and scores[sorted_indices[tie_end]] == score:
                tie_end += 1
            average_rank = ((index + 1) + tie_end) / 2
            positive_rank_sum += average_rank * sum(
                labels[sorted_indices[position]] == 1
                for position in range(index, tie_end)
            )
            index = tie_end
        positive_count = len(positive_scores)
        negative_count = len(negative_scores)
        auc = (positive_rank_sum - positive_count * (positive_count + 1) / 2) / (positive_count * negative_count)

    correct_confidences = [max(score, 1.0 - score) for score in scores]
    correct_predictions = [int(prediction == label) for prediction, label in zip(predictions, labels)]
    bin_count = 10
    ece = 0.0
    for bin_index in range(bin_count):
        lower = bin_index / bin_count
        upper = (bin_index + 1) / bin_count
        members = [
            index for index, confidence in enumerate(correct_confidences)
            if lower <= confidence < upper or (bin_index == bin_count - 1 and confidence == 1.0)
        ]
        if members:
            mean_confidence = sum(correct_confidences[index] for index in members) / len(members)
            mean_accuracy = sum(correct_predictions[index] for index in members) / len(members)
            ece += len(members) / len(labels) * abs(mean_accuracy - mean_confidence)

    brier_score = sum((score - label) ** 2 for label, score in zip(labels, scores)) / len(labels)
    return {
        "accuracy": (tp + tn) / len(labels),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": auc,
        "ece": ece,
        "brier_score": brier_score,
    }


def _latency_summary(latencies_ms: Sequence[float]) -> Dict[str, Optional[float]]:
    if not latencies_ms:
        return {"inference_mean_ms": None, "inference_median_ms": None, "inference_p95_ms": None}
    sorted_values = sorted(latencies_ms)
    p95_index = max(0, min(len(sorted_values) - 1, int(0.95 * len(sorted_values) + 0.999999) - 1))
    return {
        "inference_mean_ms": sum(sorted_values) / len(sorted_values),
        "inference_median_ms": statistics.median(sorted_values),
        "inference_p95_ms": sorted_values[p95_index],
    }


def _hardware_snapshot(device: str) -> Dict[str, Any]:
    hardware = {
        "platform": platform.platform(),
        "processor": platform.processor() or "not_reported",
        "logical_cpu_count": os.cpu_count(),
        "device": device,
        "gpu_name": None,
        "gpu_memory_total_mb": None,
        "ram_total_mb": None,
        "ram_available_mb": None,
    }
    try:
        import psutil

        memory = psutil.virtual_memory()
        hardware["ram_total_mb"] = round(memory.total / (1024 * 1024), 2)
        hardware["ram_available_mb"] = round(memory.available / (1024 * 1024), 2)
    except ImportError:
        pass
    try:
        import torch

        if torch.cuda.is_available():
            hardware["gpu_name"] = torch.cuda.get_device_name(0)
            hardware["gpu_memory_total_mb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 2)
    except (ImportError, RuntimeError):
        pass
    return hardware


def _write_table_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMPARISON_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown_table(path: Path, rows: Sequence[Dict[str, Any]], blockers: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ("dataset", "split", "status", "identity_disjoint", "samples", "accuracy", "precision", "recall", "f1", "roc_auc", "ece", "brier_score", "inference_mean_ms", "inference_p95_ms")
    lines = ["# Cross-Dataset Evaluation", "", "No target score is assumed; values are written only after predictions are generated.", ""]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        cells = ["" if row.get(column) is None else str(row.get(column, "")) for column in columns]
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    if blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in blockers)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _empty_rows() -> List[Dict[str, Any]]:
    return [
        {
            "training_dataset": "DATASET_A",
            "dataset": dataset,
            "split": "test",
            "status": "not_run" if dataset != "DATASET_C" else "not_available",
            "identity_disjoint": "not_verifiable",
        }
        for dataset in EXPECTED_DATASETS
    ]


def run(args: argparse.Namespace) -> int:
    blockers: List[str] = []
    comparison_rows = _empty_rows()
    report: Dict[str, Any] = {
        "schema_version": 1,
        "status": "not_run",
        "training_dataset": "DATASET_A",
        "evaluation_splits": ["DATASET_A/test", "DATASET_B/test", "DATASET_C/test when available"],
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": None,
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": None,
        "model": None,
        "hardware": None,
        "preprocessing": "AIDE image pipeline: face detection, face crop or center-crop fallback, resize/normalize; videos use sampled-frame mean fake probability.",
        "identity_policy": "Check identity IDs and namespaces against DATASET_A train where comparable; exact file SHA-256 duplicates are also excluded.",
        "identity_checks": {},
        "dataset_documentation": {},
        "comparison": comparison_rows,
        "blockers": blockers,
    }

    if not args.manifest.is_file():
        blockers.append(f"Cross-dataset manifest not found: {args.manifest}")
    if not args.checkpoint.is_file():
        blockers.append(f"Trained checkpoint not found: {args.checkpoint}")
    if blockers:
        _write_table_csv(args.comparison_csv, comparison_rows)
        _write_markdown_table(args.comparison_md, comparison_rows, blockers)
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return 2

    try:
        rows = load_manifest(args.manifest)
        training_rows = [row for row in rows if row.dataset == "DATASET_A" and row.split == "train"]
        if not training_rows:
            raise ValueError("Manifest must contain DATASET_A training rows for identity and overlap checks.")
        test_rows_by_dataset = {
            dataset: [row for row in rows if row.dataset == dataset and row.split == "test"]
            for dataset in EXPECTED_DATASETS
        }
        if not test_rows_by_dataset["DATASET_A"]:
            raise ValueError("Manifest must contain the held-out DATASET_A test split.")

        report["manifest_sha256"] = sha256_file(args.manifest)
        training_hashes = {sha256_file(row.path) for row in training_rows}
        identity_results: Dict[str, Dict[str, Any]] = {}
        for dataset, test_rows in test_rows_by_dataset.items():
            if not test_rows:
                identity_results[dataset] = {"status": "not_available", "overlap_count": 0}
                continue
            cross = dataset != "DATASET_A"
            state, overlapping_ids = _identity_state(training_rows, test_rows, cross_dataset=cross)
            duplicate_samples = [row.sample_id for row in test_rows if sha256_file(row.path) in training_hashes]
            if duplicate_samples:
                state = "duplicate_content"
            identity_results[dataset] = {
                "status": state,
                "overlap_count": len(overlapping_ids),
                "overlapping_identity_fingerprints": sorted(
                    hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
                    for identity in overlapping_ids
                ),
                "duplicate_content_sample_ids": duplicate_samples,
                "training_identity_count": len({row.identity_id for row in training_rows if row.identity_id}),
                "test_identity_count": len({row.identity_id for row in test_rows if row.identity_id}),
                "training_identity_fingerprints": _identity_fingerprints(training_rows),
                "test_identity_fingerprints": _identity_fingerprints(test_rows),
                "identity_namespace_comparison": "global namespace match required across datasets" if cross else "within DATASET_A",
            }
        report["identity_checks"] = identity_results
        report["dataset_documentation"] = {
            dataset: {
                "dataset_version": _metadata_values([row for row in rows if row.dataset == dataset], "dataset_version"),
                "license": _metadata_values([row for row in rows if row.dataset == dataset], "license"),
                "source_url": _metadata_values([row for row in rows if row.dataset == dataset], "source_url"),
                "preprocessing": _metadata_values([row for row in rows if row.dataset == dataset], "preprocessing"),
                "manipulation_types": sorted({row.manipulation_type for row in rows if row.dataset == dataset}),
                "identity_count": len({(row.identity_namespace or row.dataset, row.identity_id) for row in rows if row.dataset == dataset and row.identity_id}),
                "split_identity_counts": {
                    split: len({row.identity_id for row in rows if row.dataset == dataset and row.split == split and row.identity_id})
                    for split in ("train", "validation", "test")
                },
                "identity_metadata_complete": bool([row for row in rows if row.dataset == dataset]) and all(row.identity_id for row in rows if row.dataset == dataset),
            }
            for dataset in EXPECTED_DATASETS
        }

        detector, face_detector, preprocessor, threshold, device, model_metadata = load_detector(args.checkpoint, None)
        training_config = model_metadata.get("training_config", {})
        checkpoint_training_dataset = training_config.get("dataset_name") or training_config.get("training_dataset")
        if checkpoint_training_dataset and str(checkpoint_training_dataset).upper() != "DATASET_A":
            raise ValueError(f"Checkpoint training dataset is {checkpoint_training_dataset!r}, not DATASET_A.")

        report["checkpoint_sha256"] = sha256_file(args.checkpoint)
        report["model"] = {
            "architecture": "AIDEImageDetector",
            "model_version": model_metadata.get("model_version", "unknown"),
            "preprocessing_version": model_metadata.get("preprocessing_version", "unknown"),
            "checkpoint_training_dataset": checkpoint_training_dataset or "unverified",
            "training_dataset_provenance_verified": bool(checkpoint_training_dataset),
            "training_config": {
                key: training_config[key]
                for key in (
                    "dataset_name", "training_dataset", "training_manifest_sha256",
                    "training_samples_sha256", "split_policy", "epochs", "lr",
                )
                if key in training_config
            },
            "decision_threshold": threshold,
            "device": device,
        }
        report["hardware"] = _hardware_snapshot(device)
        report["preprocessing"] = {
            "image": "RGB; AIDE face detector; face crop or center-crop fallback; ImagePreprocessor tensor normalization.",
            "video": f"Sample at {args.sample_fps:g} FPS up to {args.max_frames} frames; apply image preprocessing per frame; mean fake probability.",
            "identity_preprocessing": "No identity transformation; original source labels and files are read-only.",
        }

        evaluated: Dict[str, Dict[str, Any]] = {}
        for dataset, test_rows in test_rows_by_dataset.items():
            table_index = EXPECTED_DATASETS.index(dataset)
            table_row = comparison_rows[table_index]
            table_row.update({
                "identity_disjoint": identity_results[dataset]["status"],
                "samples": len(test_rows),
                "identities": report["dataset_documentation"][dataset]["identity_count"],
                "manipulation_types": ";".join(report["dataset_documentation"][dataset]["manipulation_types"]),
                "dataset_version": ";".join(report["dataset_documentation"][dataset]["dataset_version"]),
                "license": ";".join(report["dataset_documentation"][dataset]["license"]) or "not_recorded",
                "source_url": ";".join(report["dataset_documentation"][dataset]["source_url"]),
                "preprocessing": ";".join(report["dataset_documentation"][dataset]["preprocessing"]) or "AIDE default preprocessing",
                "model_version": model_metadata.get("model_version", "unknown"),
            })
            if not test_rows:
                table_row["status"] = "not_available"
                continue
            identity_state = identity_results[dataset]["status"]
            if identity_state in {"overlap", "duplicate_content"}:
                table_row["status"] = "skipped_leakage"
                continue

            records = []
            for sample in test_rows:
                started_at = time.perf_counter()
                if sample.path.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
                    fake_probability = score_video(
                        sample.path, detector, face_detector, preprocessor, args.sample_fps, args.max_frames
                    )
                else:
                    from PIL import Image

                    with Image.open(sample.path) as image:
                        fake_probability = score_frame(image, detector, face_detector, preprocessor, threshold)
                latency_ms = (time.perf_counter() - started_at) * 1000
                if device.startswith("cuda"):
                    import torch

                    torch.cuda.synchronize()
                    latency_ms = (time.perf_counter() - started_at) * 1000
                records.append({
                    "sample_id": sample.sample_id,
                    "label": sample.label,
                    "source_label": sample.source_label,
                    "fake_probability": fake_probability,
                    "prediction": int(fake_probability >= threshold),
                    "confidence": max(fake_probability, 1.0 - fake_probability),
                    "inference_ms": latency_ms,
                    "identity_fingerprint": _identity_fingerprints([sample])[0] if sample.identity_id else None,
                    "manipulation_type": sample.manipulation_type,
                })

            metrics = _classification_metrics(
                [record["label"] for record in records],
                [record["fake_probability"] for record in records],
                [record["prediction"] for record in records],
            )
            metrics.update(_latency_summary([record["inference_ms"] for record in records]))
            metrics["sample_count"] = len(records)
            metrics["identity_disjoint"] = identity_state
            metrics["identity_count"] = report["dataset_documentation"][dataset]["identity_count"]
            metrics["manipulation_types"] = report["dataset_documentation"][dataset]["manipulation_types"]
            metrics["predictions"] = records
            evaluated[dataset] = metrics
            table_row.update({key: metrics.get(key) for key in (
                "accuracy", "precision", "recall", "f1", "roc_auc", "ece", "brier_score",
                "inference_mean_ms", "inference_median_ms", "inference_p95_ms",
            )})
            table_row["status"] = "completed" if identity_state == "verified_disjoint" else "completed_identity_unverified"

        report["results"] = evaluated
        report["comparison"] = comparison_rows
        report["status"] = "completed" if evaluated and all(result.get("identity_disjoint") == "verified_disjoint" for result in evaluated.values()) else "completed_with_identity_gaps" if evaluated else "completed_with_skips"
    except Exception as exc:
        blockers.append(f"Evaluation not completed: {type(exc).__name__}: {exc}")
        report["status"] = "not_run"
        report["results"] = {}
        comparison_rows = _empty_rows()
        for row in comparison_rows:
            row["status"] = "not_run"
        report["comparison"] = comparison_rows

    report["blockers"] = blockers
    _write_table_csv(args.comparison_csv, comparison_rows)
    _write_markdown_table(args.comparison_md, comparison_rows, blockers)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return 0 if report["results"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare DATASET_A-trained AIDE performance across held-out visual datasets.")
    parser.add_argument("--manifest", type=Path, default=AI_SERVICE_ROOT / "datasets" / "cross_dataset_manifest.csv")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path(
            os.environ.get(
                "IMAGE_MODEL_PATH",
                Path(__file__).resolve().parents[1]
                / "checkpoints"
                / "image"
                / "best_model.pth",
            )
        ),
    )
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--max-frames", type=int, default=16)
    parser.add_argument("--report-json", type=Path, default=REPORTS_ROOT / "cross_dataset_report.json")
    parser.add_argument("--comparison-csv", type=Path, default=REPORTS_ROOT / "cross_dataset_comparison.csv")
    parser.add_argument("--comparison-md", type=Path, default=REPORTS_ROOT / "cross_dataset_comparison.md")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.sample_fps <= 0 or args.max_frames <= 0:
        parser.error("--sample-fps and --max-frames must be positive.")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())