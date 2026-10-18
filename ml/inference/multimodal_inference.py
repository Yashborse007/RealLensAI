from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ml.config import MULTIMODAL_DECISION_THRESHOLD, MULTIMODAL_QUALITY_THRESHOLD, MULTIMODAL_WEIGHTS
from ml.inference.audio_inference import predict_audio_probability
from ml.inference.image_inference import predict_image_probability
from ml.inference.video_inference import predict_video_probability


def _coerce_score(value: Optional[float]) -> float:
    if value is None:
        return 0.0
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(score) or math.isinf(score):
        return 0.0
    return max(0.0, min(1.0, score))


def _default_modality_availability() -> Dict[str, bool]:
    return {
        "spatial": True,
        "temporal": True,
        "frequency": True,
        "audio": True,
    }


def _normalize_weights(weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    normalized = dict(MULTIMODAL_WEIGHTS)
    if weights:
        for key, value in weights.items():
            if key in normalized:
                normalized[key] = max(0.0, float(value))
    return normalized


def fuse_multimodal_scores(
    spatial_score: Optional[float] = None,
    temporal_score: Optional[float] = None,
    frequency_score: Optional[float] = None,
    audio_score: Optional[float] = None,
    quality_score: float = 1.0,
    modality_availability: Optional[Dict[str, bool]] = None,
    modality_status: Optional[Dict[str, str]] = None,
    weights: Optional[Dict[str, float]] = None,
    threshold: float = MULTIMODAL_DECISION_THRESHOLD,
) -> Dict[str, Any]:
    """Fuse available modality scores while keeping unavailable/failed evidence separate.

    Missing evidence is never converted into fake evidence. Unavailable or failed signals are
    simply excluded from the denominator. Low-quality inputs suppress a real classification.
    """
    availability = _default_modality_availability()
    if modality_availability:
        availability.update({key: bool(value) for key, value in modality_availability.items()})

    configured_weights = _normalize_weights(weights)
    evidence: Dict[str, Dict[str, Any]] = {}
    available_modalities: List[str] = []
    per_modality_status = modality_status or {}

    for name in ("spatial", "temporal", "frequency", "audio"):
        metric = {
            "spatial": spatial_score,
            "temporal": temporal_score,
            "frequency": frequency_score,
            "audio": audio_score,
        }[name]
        status_override = str(per_modality_status.get(name, "")).upper()
        is_available = bool(availability.get(name, True))
        safe_metric = _coerce_score(metric)

        if status_override == "SUPPORTING_ONLY":
            evidence[name] = {
                "available": is_available and metric is not None,
                "status": "SUPPORTING_ONLY",
                "score": safe_metric,
                "message": (
                    f"{name} output is retained as supporting evidence but was excluded "
                    "from probability fusion because it is not a calibrated fake probability."
                ),
            }
            continue

        if status_override == "NOT_APPLICABLE":
            evidence[name] = {
                "available": False,
                "status": "NOT_APPLICABLE",
                "score": 0.0,
                "message": f"{name} analysis does not apply to this media type.",
            }
            continue

        if status_override == "FAILED_ANALYSIS":
            evidence[name] = {
                "available": False,
                "status": "FAILED_ANALYSIS",
                "score": 0.0,
                "message": f"{name} modality analysis failed and was excluded from fusion.",
            }
            continue

        if not is_available:
            evidence[name] = {
                "available": False,
                "status": "MISSING_EVIDENCE",
                "score": 0.0,
                "message": f"{name} modality is not available.",
            }
            continue

        if metric is None:
            evidence[name] = {
                "available": False,
                "status": "MISSING_EVIDENCE",
                "score": 0.0,
                "message": f"{name} modality was not provided.",
            }
            continue

        if safe_metric <= 0.0 and metric == 0.0:
            evidence[name] = {
                "available": True,
                "status": "AVAILABLE",
                "score": 0.0,
                "message": f"{name} modality is available but produced a neutral score.",
            }
            available_modalities.append(name)
            continue

        evidence[name] = {
            "available": True,
            "status": "AVAILABLE",
            "score": safe_metric,
            "message": f"{name} modality evidence is available.",
        }
        available_modalities.append(name)

    quality_value = _coerce_score(quality_score)
    quality_status = "SUFFICIENT"
    quality_message = "Input quality is sufficient for multimodal fusion."
    if quality_value < MULTIMODAL_QUALITY_THRESHOLD:
        quality_status = "LOW_QUALITY_INPUT"
        quality_message = "Input quality is too low for a reliable fusion decision. Missing or weak evidence is not treated as fake evidence."

    if quality_status == "LOW_QUALITY_INPUT":
        return {
            "final_label": "REAL",
            "confidence": 0.0,
            "evidence": evidence,
            "available_modalities": available_modalities,
            "quality": {
                "quality_score": quality_value,
                "status": quality_status,
                "message": quality_message,
            },
        }

    if not available_modalities:
        return {
            "final_label": "REAL",
            "confidence": 0.0,
            "evidence": evidence,
            "available_modalities": [],
            "quality": {
                "quality_score": quality_value,
                "status": quality_status,
                "message": "No modality evidence was available for fusion.",
            },
        }

    numerator = 0.0
    denominator = 0.0
    for modality in available_modalities:
        weight = configured_weights.get(modality, 1.0)
        numerator += weight * evidence[modality]["score"]
        denominator += weight

    if denominator <= 0.0:
        final_probability = 0.0
    else:
        final_probability = numerator / denominator

    final_probability = _coerce_score(final_probability)
    final_label = "FAKE" if final_probability >= threshold else "REAL"
    confidence = final_probability if final_label == "FAKE" else 1.0 - final_probability

    return {
        "final_label": final_label,
        "confidence": float(max(0.0, min(1.0, confidence))),
        "evidence": evidence,
        "available_modalities": available_modalities,
        "quality": {
            "quality_score": quality_value,
            "status": quality_status,
            "message": quality_message,
        },
    }


def predict_multimodal(file_path: str, media_type: str = "image") -> Dict[str, Any]:
    """Run the modality-appropriate inference and keep modality results separate.

    If the media is a video with an audio track, the function returns both video and audio
    scores as separate entries without fabricating a single forensic truth score.
    """
    if media_type == "image":
        return {"media_type": "image", **predict_image_probability(file_path)}
    if media_type == "video":
        video_result = predict_video_probability(file_path)
        audio_result = predict_audio_probability(file_path)
        return {
            "media_type": "video",
            "video": {"label": video_result.get("label"), "confidence": video_result.get("confidence")},
            "audio": {"label": audio_result.get("label"), "confidence": audio_result.get("confidence")},
        }
    if media_type == "audio":
        return {"media_type": "audio", **predict_audio_probability(file_path)}
    raise ValueError(f"Unsupported media_type '{media_type}'. Use 'image', 'video', or 'audio'.")
