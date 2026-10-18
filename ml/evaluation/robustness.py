from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AI_SERVICE_ROOT = REPOSITORY_ROOT / "ai-service"
REPORTS_ROOT = REPOSITORY_ROOT / "reports"
CHECKPOINT_ROOT = REPOSITORY_ROOT / "ml" / "checkpoints"
VARIANTS = (
    "original",
    "jpeg_compression",
    "resize",
    "blur",
    "gaussian_noise",
    "brightness_change",
    "contrast_change",
    "frame_rate_reduction",
)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
CSV_FIELDS = (
    "sample_id",
    "modality",
    "variant",
    "source_path",
    "ground_truth",
    "prediction",
    "confidence",
    "fake_probability",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "auc",
    "status",
)


@dataclass(frozen=True)
class TestSample:
    sample_id: str
    path: Path
    label: int
    source_label: str
    modality: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_label(value: str) -> int:
    normalized = value.strip().lower()
    if normalized in {"real", "0"}:
        return 0
    if normalized in {"fake", "1"}:
        return 1
    raise ValueError(f"Unsupported test label {value!r}; use REAL/FAKE or 0/1.")


def load_test_manifest(manifest_path: Path) -> Tuple[List[TestSample], str]:
    samples: List[TestSample] = []
    sample_ids = set()
    with manifest_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = {field.strip().lower() for field in (reader.fieldnames or [])}
        path_field = "path" if "path" in fields else "filepath" if "filepath" in fields else None
        label_field = "label" if "label" in fields else "ground_truth" if "ground_truth" in fields else None
        if path_field is None or label_field is None:
            raise ValueError("Manifest must contain path and label columns.")

        split_field = "split" if "split" in fields else None
        for row_number, row in enumerate(reader, start=2):
            normalized_row = {key.strip().lower(): value or "" for key, value in row.items() if key}
            if split_field and normalized_row.get(split_field, "").strip().lower() != "test":
                continue
            raw_path = normalized_row.get(path_field, "").strip()
            source_label = normalized_row.get(label_field, "").strip()
            if not raw_path or not source_label:
                raise ValueError(f"Manifest row {row_number} has an empty path or label.")

            media_path = Path(raw_path)
            if not media_path.is_absolute():
                media_path = manifest_path.parent / media_path
            media_path = media_path.resolve()
            if not media_path.is_file():
                raise ValueError(f"Manifest row {row_number} references missing media: {media_path}")

            extension = media_path.suffix.lower()
            if extension in IMAGE_EXTENSIONS:
                modality = "image"
            elif extension in VIDEO_EXTENSIONS:
                modality = "video"
            else:
                raise ValueError(f"Unsupported media type for {media_path.name}; expected image or video.")

            sample_id = normalized_row.get("sample_id", "").strip() or f"sample-{len(samples) + 1:05d}"
            if sample_id in sample_ids:
                raise ValueError(f"Manifest row {row_number} duplicates sample_id {sample_id!r}.")
            sample_ids.add(sample_id)
            samples.append(TestSample(sample_id, media_path, parse_label(source_label), source_label, modality))

    if not samples:
        raise ValueError("The test manifest contains no test samples.")
    return samples, "split=test column" if "split" in fields else "all manifest rows (explicit test manifest)"


def experiment_configuration(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment": "visual-media-robustness",
        "threshold_override": args.threshold,
        "seed": args.seed,
        "video_sample_fps": args.sample_fps,
        "video_max_frames": args.max_frames,
        "variants": {
            "original": {"mutation": "none"},
            "jpeg_compression": {"quality": 35},
            "resize": {"scale": 0.5, "resample": "LANCZOS"},
            "blur": {"gaussian_radius": 2.0},
            "gaussian_noise": {"mean": 0, "standard_deviation": 25, "clip": [0, 255]},
            "brightness_change": {"factor": 0.6},
            "contrast_change": {"factor": 0.6},
            "frame_rate_reduction": {"frame_stride": 2, "output_fps_factor": 0.5},
        },
        "label_policy": "Read source test labels once; never rewrite media, labels, or manifest.",
        "checkpoint": str(args.checkpoint.resolve()),
        "test_manifest": str(args.manifest.resolve()),
        "outputs": {
            "results_csv": str(args.results_csv.resolve()),
            "report_json": str(args.report_json.resolve()),
            "config_json": str(args.config_json.resolve()),
            "chart_png": str(args.chart_png.resolve()),
        },
    }


def write_empty_results(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=CSV_FIELDS).writeheader()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def metric_summary(labels: Sequence[int], scores: Sequence[float], predictions: Sequence[int]) -> Dict[str, Optional[float]]:
    if not labels:
        return {"accuracy": None, "precision": None, "recall": None, "f1": None, "auc": None}

    true_positive = sum(actual == 1 and predicted == 1 for actual, predicted in zip(labels, predictions))
    true_negative = sum(actual == 0 and predicted == 0 for actual, predicted in zip(labels, predictions))
    false_positive = sum(actual == 0 and predicted == 1 for actual, predicted in zip(labels, predictions))
    false_negative = sum(actual == 1 and predicted == 0 for actual, predicted in zip(labels, predictions))
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    auc: Optional[float] = None
    if len(set(labels)) == 2:
        try:
            from sklearn.metrics import roc_auc_score

            auc = float(roc_auc_score(labels, scores))
        except ImportError as exc:
            raise RuntimeError("scikit-learn is required to calculate AUC.") from exc

    return {
        "accuracy": (true_positive + true_negative) / len(labels),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc,
    }


def make_image_variant(image: Any, variant: str, seed: int) -> Any:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    import numpy as np

    image = ImageOps.exif_transpose(image.convert("RGB"))
    if variant == "original":
        return image
    if variant == "jpeg_compression":
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=35)
        buffer.seek(0)
        with Image.open(buffer) as compressed:
            return compressed.convert("RGB").copy()
    if variant == "resize":
        width, height = image.size
        return image.resize((max(1, round(width * 0.5)), max(1, round(height * 0.5))), Image.Resampling.LANCZOS)
    if variant == "blur":
        return image.filter(ImageFilter.GaussianBlur(radius=2.0))
    if variant == "gaussian_noise":
        pixels = np.asarray(image, dtype=np.float32)
        generator = np.random.default_rng(seed)
        noisy = np.clip(pixels + generator.normal(0, 25, pixels.shape), 0, 255).astype(np.uint8)
        return Image.fromarray(noisy, mode="RGB")
    if variant == "brightness_change":
        return ImageEnhance.Brightness(image).enhance(0.6)
    if variant == "contrast_change":
        return ImageEnhance.Contrast(image).enhance(0.6)
    raise ValueError(f"Variant {variant!r} is not an image transformation.")


def materialize_video_variant(source: Path, target: Path, variant: str, seed: int) -> None:
    import cv2
    import numpy as np
    from PIL import Image

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"Could not open video {source}.")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError(f"Video has invalid metadata: {source}.")

    output_fps = fps / 2 if variant == "frame_rate_reduction" else fps
    output_width = max(1, round(width * 0.5)) if variant == "resize" else width
    output_height = max(1, round(height * 0.5)) if variant == "resize" else height
    writer = cv2.VideoWriter(
        str(target), cv2.VideoWriter_fourcc(*"mp4v"), output_fps, (output_width, output_height)
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError("OpenCV could not initialize the MP4 variant writer.")

    frame_index = 0
    generator = np.random.default_rng(seed)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if variant == "frame_rate_reduction" and frame_index % 2:
                frame_index += 1
                continue

            if variant != "original":
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb)
                if variant == "gaussian_noise":
                    pixels = np.asarray(image, dtype=np.float32)
                    noise = generator.normal(0, 25, pixels.shape)
                    image = Image.fromarray(np.clip(pixels + noise, 0, 255).astype(np.uint8), mode="RGB")
                else:
                    image = make_image_variant(image, variant, seed + frame_index)
                frame = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
            writer.write(frame)
            frame_index += 1
    finally:
        capture.release()
        writer.release()

    if frame_index == 0 or not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError(f"Video variant {variant} produced no output frames.")


def load_detector(checkpoint_path: Path, threshold_override: Optional[float]) -> Tuple[Any, Any, Any, float, str, Dict[str, Any]]:
    import torch

    from ml.config import IMAGE_DECISION_THRESHOLD, get_torch_device
    from ml.models.image.aide_model import AIDEImageDetector
    from preprocessing.face_detector import face_detector
    from preprocessing.image_preprocessor import ImagePreprocessor

    detector = AIDEImageDetector()
    checkpoint = detector.load_checkpoint(str(checkpoint_path), device=get_torch_device())
    if not checkpoint.get("success"):
        raise RuntimeError(checkpoint.get("message", "Detector checkpoint could not be loaded."))
    device = torch.device(get_torch_device())
    detector.to(device)
    detector.eval()
    threshold = float(threshold_override if threshold_override is not None else checkpoint.get("threshold", IMAGE_DECISION_THRESHOLD))
    preprocessor = ImagePreprocessor()
    payload = checkpoint.get("payload", {})
    metadata = {
        "model_version": checkpoint.get("model_version", "AIDE-CNN-v1.0"),
        "preprocessing_version": checkpoint.get("preprocessing_version", "unknown"),
        "training_config": payload.get("config", {}) if isinstance(payload, dict) else {},
    }
    return detector, face_detector, preprocessor, threshold, str(device), metadata


def score_frame(image: Any, detector: Any, face_detector: Any, preprocessor: Any, threshold: float) -> float:
    import cv2
    import numpy as np
    import torch

    rgb = np.asarray(image.convert("RGB"))
    frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    detections = face_detector.detect_faces(frame)
    crops = face_detector.extract_face_crops(frame, detections, target_size=preprocessor.target_size) if detections else []
    if not crops:
        height, width = frame.shape[:2]
        side = min(height, width)
        top, left = (height - side) // 2, (width - side) // 2
        crop = frame[top:top + side, left:left + side]
        crops = [cv2.resize(crop, preprocessor.target_size, interpolation=cv2.INTER_AREA)]

    batch = torch.stack([preprocessor.normalize_crop_to_tensor(crop) for crop in crops])
    batch = batch.to(next(detector.parameters()).device)
    with torch.inference_mode():
        scores = detector.predict_probability(batch)
    if batch.is_cuda:
        torch.cuda.synchronize(batch.device)
    return float(scores.mean().item())


def score_video(path: Path, detector: Any, face_detector: Any, preprocessor: Any, sample_fps: float, max_frames: int) -> float:
    import cv2
    import numpy as np
    from PIL import Image

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video for inference: {path}.")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if source_fps <= 0 or frame_count <= 0:
        capture.release()
        raise ValueError(f"Video has invalid metadata: {path}.")

    stride = max(1, round(source_fps / sample_fps))
    indices = list(range(0, frame_count, stride))
    if len(indices) > max_frames:
        selected_positions = np.linspace(0, len(indices) - 1, max_frames).round().astype(int)
        indices = [indices[position] for position in selected_positions]

    scores = []
    try:
        for frame_number in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            scores.append(score_frame(Image.fromarray(rgb), detector, face_detector, preprocessor, threshold))
    finally:
        capture.release()
    if not scores:
        raise ValueError(f"No frames could be sampled from {path}.")
    return float(sum(scores) / len(scores))


def render_chart(summary: Dict[str, Dict[str, Any]], chart_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    variant_names = list(VARIANTS)
    metric_names = ("accuracy", "precision", "recall", "f1", "auc")
    modality_names = sorted({key.split("/", 1)[0] for key in summary})
    figure, axes = plt.subplots(len(modality_names), 1, figsize=(11, max(4, 3.5 * len(modality_names))), squeeze=False)

    for axis, modality in zip(axes[:, 0], modality_names):
        for metric_name in metric_names:
            values = [summary.get(f"{modality}/{variant}", {}).get(metric_name) for variant in variant_names]
            positions = [index for index, value in enumerate(values) if value is not None]
            if positions:
                axis.plot(positions, [values[index] for index in positions], marker="o", label=metric_name.upper())
        axis.set_title(f"{modality.title()} robustness metrics")
        axis.set_xticks(range(len(variant_names)), [name.replace("_", "\n") for name in variant_names])
        axis.set_ylim(0, 1)
        axis.set_ylabel("Score")
        axis.grid(axis="y", alpha=0.25)
        axis.legend(loc="lower left", ncols=5)

    figure.tight_layout()
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(chart_path, dpi=160)
    plt.close(figure)


def run_experiment(args: argparse.Namespace) -> int:
    config = experiment_configuration(args)
    write_json(args.config_json, config)
    write_empty_results(args.results_csv)
    report: Dict[str, Any] = {
        "schema_version": 1,
        "status": "not_run",
        "configuration": config,
        "blockers": [],
        "dataset": None,
        "checkpoint_sha256": None,
        "labels_mutated": False,
        "results_by_modality_and_variant": {},
        "chart": None,
    }

    if not args.manifest.is_file():
        report["blockers"].append(f"Test manifest not found: {args.manifest}")
    if not args.checkpoint.is_file():
        report["blockers"].append(f"Trained checkpoint not found: {args.checkpoint}")
    if report["blockers"]:
        write_json(args.report_json, report)
        return 2

    try:
        samples, split_source = load_test_manifest(args.manifest)
        detector, face_detector, preprocessor, threshold, device, _model_metadata = load_detector(args.checkpoint, args.threshold)
        report["checkpoint_sha256"] = sha256_file(args.checkpoint)
        report["dataset"] = {
            "manifest": str(args.manifest.resolve()),
            "manifest_sha256": sha256_file(args.manifest),
            "test_sample_count": len(samples),
            "split_source": split_source,
            "original_labels": {sample.sample_id: sample.source_label for sample in samples},
        }
        report["model"] = {
            "name": "AIDEImageDetector",
            "checkpoint": str(args.checkpoint.resolve()),
            "threshold": threshold,
            "device": device,
            "video_scoring": "mean fake probability from sampled frames using the trained image detector; no temporal model score",
        }

        raw_records: List[Dict[str, Any]] = []
        modality_variant_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        with tempfile.TemporaryDirectory(prefix="reallens-robustness-") as temp_directory:
            temp_root = Path(temp_directory)
            for sample_index, sample in enumerate(samples):
                applicable_variants = VARIANTS if sample.modality == "video" else VARIANTS[:-1]
                for variant_index, variant in enumerate(applicable_variants):
                    variant_path = sample.path
                    if variant != "original":
                        variant_path = temp_root / f"{sample_index}_{variant}.mp4"
                        if sample.modality == "image":
                            from PIL import Image

                            with Image.open(sample.path) as source_image:
                                transformed = make_image_variant(source_image, variant, args.seed + sample_index * 101 + variant_index)
                                variant_path = temp_root / f"{sample_index}_{variant}.png"
                                transformed.save(variant_path, format="PNG")
                        else:
                            materialize_video_variant(
                                sample.path,
                                variant_path,
                                variant,
                                args.seed + sample_index * 101 + variant_index,
                            )

                    if sample.modality == "image":
                        from PIL import Image

                        with Image.open(variant_path) as inference_image:
                            fake_probability = score_frame(inference_image, detector, face_detector, preprocessor, threshold)
                    else:
                        fake_probability = score_video(
                            variant_path,
                            detector,
                            face_detector,
                            preprocessor,
                            args.sample_fps,
                            args.max_frames,
                        )

                    prediction = int(fake_probability >= threshold)
                    record = {
                        "sample_id": sample.sample_id,
                        "modality": sample.modality,
                        "variant": variant,
                        "source_path": str(sample.path),
                        "ground_truth": sample.label,
                        "prediction": prediction,
                        "confidence": max(fake_probability, 1.0 - fake_probability),
                        "fake_probability": fake_probability,
                        "status": "measured",
                    }
                    raw_records.append(record)
                    modality_variant_records[f"{sample.modality}/{variant}"].append(record)

        summary: Dict[str, Dict[str, Any]] = {}
        for key, records in modality_variant_records.items():
            summary[key] = {
                "sample_count": len(records),
                **metric_summary(
                    [record["ground_truth"] for record in records],
                    [record["fake_probability"] for record in records],
                    [record["prediction"] for record in records],
                ),
            }

        with args.results_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for record in raw_records:
                metrics = summary[f"{record['modality']}/{record['variant']}"]
                writer.writerow({**record, **metrics, "ground_truth": "FAKE" if record["ground_truth"] else "REAL", "prediction": "FAKE" if record["prediction"] else "REAL"})

        render_chart(summary, args.chart_png)
        report["status"] = "completed"
        report["results_by_modality_and_variant"] = summary
        report["chart"] = str(args.chart_png.resolve())
        report["labels_mutated"] = False
        report["elapsed_seconds"] = round(time.perf_counter() - args.started_at, 3)
        write_json(args.report_json, report)
        return 0
    except Exception as exc:
        report["status"] = "not_run"
        report["blockers"].append(f"Evaluation stopped without publishing partial metrics: {type(exc).__name__}: {exc}")
        write_empty_results(args.results_csv)
        write_json(args.report_json, report)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate image/video robustness using an unchanged labeled test manifest.")
    parser.add_argument("--manifest", type=Path, default=AI_SERVICE_ROOT / "datasets" / "robustness_test_manifest.csv")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path(
            os.environ.get(
                "IMAGE_MODEL_PATH",
                CHECKPOINT_ROOT / "image" / "best_model.pth",
            )
        ),
    )
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--max-frames", type=int, default=16)
    parser.add_argument("--results-csv", type=Path, default=REPORTS_ROOT / "robustness_results.csv")
    parser.add_argument("--report-json", type=Path, default=REPORTS_ROOT / "robustness_report.json")
    parser.add_argument("--config-json", type=Path, default=REPORTS_ROOT / "robustness_config.json")
    parser.add_argument("--chart-png", type=Path, default=REPORTS_ROOT / "robustness_metrics.png")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.started_at = time.perf_counter()
    if args.sample_fps <= 0 or args.max_frames <= 0:
        parser.error("--sample-fps and --max-frames must be positive.")
    if args.threshold is not None and not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1.")
    return run_experiment(args)


if __name__ == "__main__":
    raise SystemExit(main())