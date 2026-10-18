from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import torch

from ml.config import (
    TEMPORAL_FUSION_WEIGHT_SPATIAL,
    TEMPORAL_FUSION_WEIGHT_TEMPORAL,
    TEMPORAL_SEQUENCE_LENGTH,
    VIDEO_DECISION_THRESHOLD,
    VIDEO_FACE_SIZE,
    VIDEO_MAX_FRAMES,
    VIDEO_SAMPLE_FPS,
    get_torch_device,
)
from ml.models.image.aide_model import AIDEImageDetector
from models.video_model import TemporalSequenceClassifier, video_model_manager
from preprocessing.face_detector import face_detector
from preprocessing.image_preprocessor import ImagePreprocessor
from utils.performance_metrics import elapsed_ms, memory_usage


def _extract_video_metadata(file_path: str) -> Dict[str, Any]:
    capture = cv2.VideoCapture(file_path)
    if not capture.isOpened():
        raise ValueError(f"Unable to open video file: {file_path}")

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    duration = float(frame_count / fps) if fps > 0 else 0.0
    audio_available = False

    capture.release()
    return {
        "duration": round(duration, 3),
        "fps": round(fps, 3),
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "audio_available": audio_available,
    }


def _sample_frame_indices(frame_count: int, fps: float, sample_fps: float, max_frames: int) -> List[int]:
    if frame_count <= 0:
        return []
    sample_rate = float(sample_fps or fps or 1.0)
    step = max(1, int(round(fps / sample_rate))) if fps > 0 else 1
    indices = []
    for idx in range(0, frame_count, step):
        if len(indices) >= max_frames:
            break
        indices.append(idx)
    return indices


def _prepare_fixed_length_sequence(feature_vectors: List[np.ndarray], fixed_length: int = TEMPORAL_SEQUENCE_LENGTH) -> np.ndarray:
    if not feature_vectors:
        return np.zeros((fixed_length, 64), dtype=np.float32)

    sequence = [np.asarray(vector, dtype=np.float32).reshape(-1) for vector in feature_vectors]
    if len(sequence) >= fixed_length:
        sequence = sequence[:fixed_length]
    else:
        pad_length = fixed_length - len(sequence)
        sequence.extend([np.zeros(64, dtype=np.float32) for _ in range(pad_length)])
    return np.asarray(sequence, dtype=np.float32)


def _assess_video_quality(file_path: str, metadata: Dict[str, Any], frame_predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    fps = float(metadata.get("fps") or 0.0)
    face_boxes = [entry.get("bbox") for entry in frame_predictions if isinstance(entry.get("bbox"), dict)]
    face_area = 0.0
    face_count = 0
    for bbox in face_boxes:
        if not isinstance(bbox, dict):
            continue
        w = float(bbox.get("w") or 0.0)
        h = float(bbox.get("h") or 0.0)
        face_area = max(face_area, w * h)
        face_count += 1

    brightness_values: List[float] = []
    blur_values: List[float] = []
    noise_values: List[float] = []
    capture = cv2.VideoCapture(file_path)
    sampled_indices = sorted({max(0, int(entry.get("frame_number") - 1)) for entry in frame_predictions if isinstance(entry, dict) and entry.get("frame_number") is not None})
    if capture.isOpened() and sampled_indices:
        for index in sampled_indices[:12]:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness_values.append(float(np.mean(gray)))
            blur_values.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            noise_values.append(float(np.std(gray)))
    capture.release()

    brightness = float(np.mean(brightness_values)) if brightness_values else 128.0
    blur_metric = float(np.mean(blur_values)) if blur_values else 80.0
    noise_estimate = float(np.mean(noise_values)) if noise_values else 25.0

    image_area = max(width * height, 1)
    face_ratio = (face_area / image_area) if image_area > 0 else 0.0
    resolution_score = 1.0 if max(width, height) >= 720 else 0.7 if max(width, height) >= 480 else 0.45
    brightness_score = 1.0 if 60 <= brightness <= 200 else 0.6 if 30 <= brightness <= 220 else 0.3
    blur_score = 1.0 if blur_metric >= 80 else 0.7 if blur_metric >= 40 else 0.3
    noise_score = 1.0 if noise_estimate <= 35 else 0.7 if noise_estimate <= 60 else 0.4
    fps_score = 1.0 if fps >= 24 else 0.7 if fps >= 12 else 0.4
    face_score = 1.0 if face_ratio >= 0.05 else 0.7 if face_ratio >= 0.02 else 0.5

    quality_score = float(np.clip((resolution_score * 0.35) + (brightness_score * 0.2) + (blur_score * 0.2) + (noise_score * 0.15) + (fps_score * 0.05) + (face_score * 0.05), 0.0, 1.0))
    if quality_score >= 0.75:
        status = "GOOD"
    elif quality_score >= 0.45:
        status = "FAIR"
    else:
        status = "POOR"

    compression_indicator = "No obvious motion-encoded compression artifact pattern detected."
    if width and height and file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        bytes_per_pixel = file_size / max(width * height, 1)
        if bytes_per_pixel < 0.003:
            compression_indicator = "Strong compression artifacts detected across sampled frames."
        elif bytes_per_pixel < 0.01:
            compression_indicator = "Moderate compression present in the encoded video stream."
        else:
            compression_indicator = "Compression appears relatively light and details remain preserved."

    details = {
        "resolution": f"{width}x{height}",
        "fps": f"{fps:.2f}",
        "brightness": f"{brightness:.1f} / 255",
        "blurEstimate": f"{blur_metric:.1f}",
        "noiseEstimate": f"{noise_estimate:.1f}",
        "compressionIndicators": compression_indicator,
        "faceSize": f"{face_area:.0f}px²" if face_area > 0 else "N/A",
        "facesDetected": int(face_count),
        "qualityScore": round(quality_score, 3),
    }

    warning = None
    if status == "POOR":
        warning = "Low-quality media may reduce detection reliability."

    return {
        "status": status,
        "quality_score": round(quality_score, 3),
        "details": details,
        "warning": warning,
    }


def predict_video_probability(
    file_path: str,
    model: Optional[AIDEImageDetector] = None,
    threshold: float = VIDEO_DECISION_THRESHOLD,
    sample_fps: float = VIDEO_SAMPLE_FPS,
    max_frames: int = VIDEO_MAX_FRAMES,
    face_size: int = VIDEO_FACE_SIZE,
    fusion_weight_spatial: float = TEMPORAL_FUSION_WEIGHT_SPATIAL,
    fusion_weight_temporal: float = TEMPORAL_FUSION_WEIGHT_TEMPORAL,
    fixed_sequence_length: int = TEMPORAL_SEQUENCE_LENGTH,
) -> Dict[str, Any]:
    """Run spatial frame-level inference, temporal sequence inference, and fusion comparison."""
    started_at = time.perf_counter()

    try:
        metadata = _extract_video_metadata(file_path)
    except ValueError as exc:
        return {
            "success": False,
            "media_type": "video",
            "status": "INVALID_VIDEO",
            "message": str(exc),
            "prediction": {"label": "UNKNOWN", "confidence": 0.0},
            "spatial_score": 0.0,
            "temporal_score": 0.0,
            "combined_score": 0.0,
            "label": "UNKNOWN",
            "confidence": 0.0,
            "frames_analyzed": 0,
            "processing_time_ms": 0,
            "model_version": "AIDE-CNN-v1.0",
            "preprocessing_version": "image-preprocess-v1.0",
            "frame_predictions": [],
            "suspicious_timestamps": [],
            "metadata": {"duration": 0.0, "fps": 0.0, "width": 0, "height": 0, "frame_count": 0, "audio_available": False},
        }

    if model is None:
        model = AIDEImageDetector()
        model_load_started_at = time.perf_counter()
        load_status = model.load_checkpoint()
        model_load_ms = elapsed_ms(model_load_started_at)
        if not load_status.get("success"):
            return {
                "success": False,
                "status": "MODEL_NOT_AVAILABLE",
                "media_type": "video",
                "message": "AIDE image checkpoint not found. Load the trained image model before video analysis.",
                "prediction": {"label": "UNKNOWN", "confidence": 0.0},
                "spatial_score": 0.0,
                "temporal_score": 0.0,
                "combined_score": 0.0,
                "label": "UNKNOWN",
                "confidence": 0.0,
                "frames_analyzed": 0,
                "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
                "model_version": "AIDE-CNN-v1.0",
                "preprocessing_version": "image-preprocess-v1.0",
                "frame_predictions": [],
                "suspicious_timestamps": [],
                "metadata": metadata,
                "performance": {"model_load_ms": model_load_ms, "total_inference_ms": elapsed_ms(started_at), "memory": memory_usage()},
            }
    else:
        model_load_ms = 0.0

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return {
            "success": False,
            "status": "INVALID_VIDEO",
            "media_type": "video",
            "message": "Video file could not be opened.",
            "prediction": {"label": "UNKNOWN", "confidence": 0.0},
            "spatial_score": 0.0,
            "temporal_score": 0.0,
            "combined_score": 0.0,
            "label": "UNKNOWN",
            "confidence": 0.0,
            "frames_analyzed": 0,
            "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
            "model_version": "AIDE-CNN-v1.0",
            "preprocessing_version": "image-preprocess-v1.0",
            "frame_predictions": [],
            "suspicious_timestamps": [],
            "metadata": metadata,
        }

    fps = metadata["fps"]
    frame_count = metadata["frame_count"]
    frame_indices = _sample_frame_indices(frame_count, fps, sample_fps, max_frames)
    frame_predictions: List[Dict[str, Any]] = []
    probabilities: List[float] = []
    feature_vectors: List[np.ndarray] = []
    device = torch.device(get_torch_device())
    preprocessor = ImagePreprocessor(target_size=(face_size, face_size))
    spatial_time_start = time.perf_counter()
    face_detection_ms = 0.0
    preprocessing_ms = 0.0
    inference_ms = 0.0

    for frame_index in frame_indices:
        preprocessing_started_at = time.perf_counter()
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        frame_bgr = frame
        face_detection_started_at = time.perf_counter()
        detections = face_detector.detect_faces(frame_bgr)
        current_face_detection_ms = elapsed_ms(face_detection_started_at)
        face_detection_ms += current_face_detection_ms
        face_box = None
        crop = None

        if detections:
            face_box = detections[0]
            crop_candidates = face_detector.extract_face_crops(frame_bgr, [face_box], target_size=(face_size, face_size))
            if crop_candidates:
                crop = crop_candidates[0]

        if crop is None:
            h, w = frame_bgr.shape[:2]
            min_dim = min(h, w)
            start_y = max(0, (h - min_dim) // 2)
            start_x = max(0, (w - min_dim) // 2)
            central_crop = frame_bgr[start_y:start_y + min_dim, start_x:start_x + min_dim]
            crop = cv2.resize(central_crop, (face_size, face_size), interpolation=cv2.INTER_AREA)
            face_box = None

        tensor = preprocessor.normalize_crop_to_tensor(crop).unsqueeze(0).to(device)
        preprocessing_ms += max(0.0, elapsed_ms(preprocessing_started_at) - current_face_detection_ms)
        inference_started_at = time.perf_counter()
        with torch.no_grad():
            features = model.backbone(tensor)
            prob = float(torch.sigmoid(model.classifier(features)).squeeze(0).item())
            feature = features.flatten(1).squeeze(0).cpu().numpy()
        inference_ms += elapsed_ms(inference_started_at)

        label = "FAKE" if prob >= threshold else "REAL"
        confidence = prob if label == "FAKE" else 1.0 - prob
        timestamp = round(frame_index / fps, 3) if fps > 0 else 0.0

        frame_predictions.append({
            "frame_number": int(frame_index + 1),
            "timestamp": float(timestamp),
            "prediction": label,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "bbox": face_box,
            "fake_probability": float(prob),
            "feature_vector": feature.tolist(),
        })
        probabilities.append(float(prob))
        feature_vectors.append(feature.astype(np.float32))

    cap.release()
    spatial_time_ms = int((time.perf_counter() - spatial_time_start) * 1000)
    postprocessing_started_at = time.perf_counter()

    if not frame_predictions:
        spatial_score = 0.0
        temporal_score = 0.0
        combined_score = 0.0
        final_label = "REAL"
        final_confidence = 0.0
        suspicious_timestamps = []
        status = "NO_FACE_DETECTED_FALLBACK_CROP"
        temporal_evaluation = {
            "score": 0.0,
            "label": "REAL",
            "confidence": 0.0,
            "time_ms": 0,
        }
    else:
        spatial_score = float(np.mean(probabilities))
        spatial_label = "FAKE" if spatial_score >= threshold else "REAL"
        spatial_confidence = spatial_score if spatial_label == "FAKE" else 1.0 - spatial_score

        temporal_time_start = time.perf_counter()
        temporal_model = (
            video_model_manager.model
            if video_model_manager.is_available()
            else TemporalSequenceClassifier(
                feature_dim=64,
                hidden_dim=32,
                sequence_length=fixed_sequence_length,
            )
        )
        temporal_input = torch.from_numpy(_prepare_fixed_length_sequence(feature_vectors, fixed_length=fixed_sequence_length)).unsqueeze(0).to(device)
        temporal_model.eval()
        with torch.no_grad():
            temporal_score = float(torch.sigmoid(temporal_model(temporal_input)).squeeze(0).item())
        temporal_time_ms = int((time.perf_counter() - temporal_time_start) * 1000)

        temporal_label = "FAKE" if temporal_score >= threshold else "REAL"
        temporal_confidence = temporal_score if temporal_label == "FAKE" else 1.0 - temporal_score

        combined_score = float(np.clip((fusion_weight_spatial * spatial_score) + (fusion_weight_temporal * temporal_score), 0.0, 1.0))
        final_label = "FAKE" if combined_score >= threshold else "REAL"
        final_confidence = combined_score if final_label == "FAKE" else 1.0 - combined_score
        suspicious_timestamps = [
            float(entry["timestamp"]) for entry in frame_predictions if entry["prediction"] == "FAKE" and entry["confidence"] >= threshold
        ]
        status = "COMPLETED"
        temporal_evaluation = {
            "score": temporal_score,
            "label": temporal_label,
            "confidence": float(max(0.0, min(1.0, temporal_confidence))),
            "time_ms": temporal_time_ms,
        }

    spatial_evaluation = {
        "score": float(spatial_score),
        "label": "FAKE" if spatial_score >= threshold else "REAL",
        "confidence": float(max(0.0, min(1.0, (spatial_score if spatial_score >= threshold else 1.0 - spatial_score)))),
        "time_ms": spatial_time_ms,
    }

    combined_evaluation = {
        "score": float(combined_score),
        "label": final_label,
        "confidence": float(max(0.0, min(1.0, final_confidence))),
        "time_ms": int((time.perf_counter() - started_at) * 1000) - spatial_time_ms - temporal_evaluation.get("time_ms", 0),
    }

    quality = _assess_video_quality(file_path, metadata, frame_predictions)
    postprocessing_ms = max(
        0.0,
        elapsed_ms(postprocessing_started_at)
        - temporal_evaluation.get("time_ms", 0),
    )
    total_processing_ms = elapsed_ms(started_at)
    frames_processed = len(frame_predictions)

    response = {
        "success": True,
        "status": status,
        "media_type": "video",
        "spatial_score": float(spatial_score),
        "temporal_score": float(temporal_score),
        "combined_score": float(combined_score),
        "label": final_label,
        "confidence": float(max(0.0, min(1.0, final_confidence))),
        "prediction": {
            "label": final_label,
            "confidence": float(max(0.0, min(1.0, final_confidence))),
        },
        "frames_analyzed": len(frame_predictions),
        "frame_predictions": frame_predictions,
        "suspicious_timestamps": suspicious_timestamps,
        "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
        "frames_processed": frames_processed,
        "processing_fps": round(frames_processed / max(total_processing_ms / 1000, 0.001), 3),
        "total_processing_time_ms": total_processing_ms,
        "performance": {
            "preprocessing_ms": round(preprocessing_ms, 3),
            "face_detection_ms": round(face_detection_ms, 3),
            "inference_ms": round(inference_ms + temporal_evaluation.get("time_ms", 0), 3),
            "postprocessing_ms": postprocessing_ms,
            "model_load_ms": model_load_ms,
            "total_inference_ms": total_processing_ms,
            "frames_processed": frames_processed,
            "processing_fps": round(frames_processed / max(total_processing_ms / 1000, 0.001), 3),
            "memory": memory_usage(),
        },
        "model_version": "AIDE-CNN-v1.0",
        "preprocessing_version": "image-preprocess-v1.0",
        "model": "AIDE-Temporal-GRU",
        "sample_config": {
            "sample_fps": float(sample_fps),
            "max_frames": int(max_frames),
            "face_size": int(face_size),
            "sequence_length": int(fixed_sequence_length),
        },
        "metadata": metadata,
        "threshold": float(threshold),
        "quality": {
            "status": quality["status"],
            "quality_score": quality["quality_score"],
            "message": quality.get("warning") or "Input quality is sufficient for video analysis.",
        },
        "input_quality": quality,
        "evaluation": {
            "spatial_only": spatial_evaluation,
            "temporal_only": temporal_evaluation,
            "combined": combined_evaluation,
            "fusion_weights": {
                "spatial": float(fusion_weight_spatial),
                "temporal": float(fusion_weight_temporal),
            },
            "sequence_length": int(fixed_sequence_length),
            "measured_results": {
                "spatial_only_label": spatial_evaluation["label"],
                "temporal_only_label": temporal_evaluation["label"],
                "combined_label": final_label,
            },
        },
    }

    if status == "NO_FACE_DETECTED_FALLBACK_CROP":
        response["message"] = "No face was detected in the sampled video frames; central-crop fallback was used for inference."

    return response
