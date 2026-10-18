from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import cv2
import numpy as np
from PIL import Image

from ml.config import MULTIMODAL_DECISION_THRESHOLD, MULTIMODAL_WEIGHTS
from ml.inference.multimodal_inference import fuse_multimodal_scores
from models.video_model import video_model_manager
from services.audio_service import audio_service
from services.frequency_service import frequency_service
from services.image_service import image_service
from services.video_service import video_service
from utils.logging_utils import logger


MEDIA_TYPES = {
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "webp": "image",
    "mp4": "video",
    "mov": "video",
    "avi": "video",
    "mkv": "video",
    "webm": "video",
    "mp3": "audio",
    "wav": "audio",
    "m4a": "audio",
    "aac": "audio",
    "flac": "audio",
}
MODALITIES = ("spatial", "temporal", "frequency", "audio")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _probability_from_prediction(result: Dict[str, Any]) -> Optional[float]:
    if result.get("success") is False:
        return None

    direct_probability = result.get("fake_probability")
    if direct_probability is not None:
        try:
            return float(np.clip(float(direct_probability), 0.0, 1.0))
        except (TypeError, ValueError):
            return None

    prediction = result.get("prediction") or {}
    confidence = prediction.get("confidence", result.get("confidence"))
    label = str(prediction.get("label", result.get("label", ""))).upper()
    if confidence is None or label not in {"FAKE", "REAL"}:
        return None
    try:
        confidence_value = float(np.clip(float(confidence), 0.0, 1.0))
    except (TypeError, ValueError):
        return None
    return confidence_value if label == "FAKE" else 1.0 - confidence_value


def _empty_modality(status: str, message: str) -> Dict[str, Any]:
    return {
        "available": False,
        "status": status,
        "score": None,
        "score_type": "fake_probability",
        "label": None,
        "confidence": None,
        "included_in_fusion": False,
        "message": message,
    }


class AnalysisOrchestrator:
    """Runs media-specific detectors and returns an explainable, stable result contract."""

    def __init__(
        self,
        image_runner: Callable[[str], Dict[str, Any]] = image_service.process_and_predict,
        video_runner: Callable[[str], Dict[str, Any]] = video_service.process_and_predict,
        audio_runner: Callable[[str], Dict[str, Any]] = audio_service.process_and_predict,
        frequency_runner: Callable[..., Dict[str, Any]] = frequency_service.analyze_image,
    ):
        self.image_runner = image_runner
        self.video_runner = video_runner
        self.audio_runner = audio_runner
        self.frequency_runner = frequency_runner

    def determine_media_type(self, file_path: str, media_type: Optional[str] = None) -> str:
        detected = MEDIA_TYPES.get(os.path.splitext(file_path)[1].lower().lstrip("."))
        if detected is None:
            raise ValueError("Unsupported media format.")
        if media_type and media_type != detected:
            raise ValueError("The supplied media type does not match the file extension.")
        return detected

    def _run_module(
        self,
        name: str,
        runner: Callable[[], Dict[str, Any]],
        processing: Dict[str, Any],
        modalities: Dict[str, Dict[str, Any]],
        input_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            result = runner()
            if not isinstance(result, dict):
                raise TypeError(f"{name} analyzer returned an invalid result.")
            if result.get("message") and input_path:
                result["message"] = str(result["message"]).replace(
                    input_path,
                    os.path.basename(input_path),
                )
            processing["modules"][name] = {
                "status": "SUCCEEDED" if result.get("success", True) else "FAILED",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            if result.get("success") is False:
                processing["modules"][name]["message"] = str(
                    result.get("message") or result.get("status") or "Analysis failed."
                )
            return result
        except Exception as exc:
            logger.exception("%s analysis failed", name)
            processing["modules"][name] = {
                "status": "FAILED",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "error": type(exc).__name__,
                "message": f"{name.capitalize()} analysis failed ({type(exc).__name__}).",
            }
            modalities[name] = _empty_modality(
                "FAILED_ANALYSIS",
                processing["modules"][name]["message"],
            )
            return {"success": False, "status": "FAILED", "message": processing["modules"][name]["message"]}

    def _frequency_for_image(self, file_path: str) -> Dict[str, Any]:
        with Image.open(file_path) as image:
            return self.frequency_runner(image.convert("RGB"))

    def _frequency_for_video(self, file_path: str, max_frames: int = 8) -> Dict[str, Any]:
        capture = cv2.VideoCapture(file_path)
        if not capture.isOpened():
            raise ValueError("Unable to open video for frequency analysis.")
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            capture.release()
            raise ValueError("Video has no decodable frames for frequency analysis.")

        frame_indices = np.linspace(0, frame_count - 1, min(frame_count, max_frames), dtype=int)
        scores = []
        summaries = []
        try:
            for frame_index in frame_indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = self.frequency_runner(rgb_frame)
                scores.append(float(result["frequency_score"]))
                summaries.append(result.get("frequency_summary", {}))
        finally:
            capture.release()

        if not scores:
            raise ValueError("No video frames could be decoded for frequency analysis.")
        return {
            "frequency_score": float(np.mean(scores)),
            "frequency_summary": {
                "evidence_type": "supporting_evidence",
                "supporting_evidence": True,
                "sampled_frames": len(scores),
                "frame_summaries": summaries,
                "note": "Video frequency score is a supporting metric, not a fake probability.",
            },
        }

    def _extract_video_audio(self, file_path: str, analysis_id: str) -> Optional[str]:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None

        os.makedirs("scratch", exist_ok=True)
        output_path = os.path.join("scratch", f"analysis_{analysis_id}.wav")
        try:
            completed = subprocess.run(
                [
                    ffmpeg,
                    "-nostdin",
                    "-v",
                    "error",
                    "-i",
                    file_path,
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-y",
                    output_path,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if completed.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
                if os.path.exists(output_path):
                    os.remove(output_path)
                return None
            return output_path
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Video audio extraction failed (%s)", type(exc).__name__)
            if os.path.exists(output_path):
                os.remove(output_path)
            return None

    def analyze(
        self,
        file_path: str,
        media_type: Optional[str] = None,
        ground_truth: Optional[str] = None,
    ) -> Dict[str, Any]:
        analysis_id = uuid.uuid4().hex
        started_at = _utc_now()
        started = time.perf_counter()
        try:
            resolved_type = self.determine_media_type(file_path, media_type)
        except ValueError as exc:
            return {
                "analysis_id": analysis_id,
                "media_type": media_type or "unknown",
                "status": "FAILED",
                "prediction": {"label": "UNKNOWN", "confidence": 0.0},
                "confidence": 0.0,
                "quality": {"status": "NOT_ASSESSED", "score": None, "details": {}, "warning": None},
                "modalities": {
                    name: _empty_modality("NOT_APPLICABLE", "Media validation failed.")
                    for name in MODALITIES
                },
                "evidence": [],
                "timestamps": {"started_at": started_at, "completed_at": _utc_now()},
                "processing": {
                    "total_ms": 0.0,
                    "modules": {
                        "media_validation": {
                            "status": "FAILED",
                            "message": str(exc),
                        }
                    },
                },
                "model_versions": {},
                "message": str(exc),
            }

        modalities = {
            name: _empty_modality("NOT_APPLICABLE", f"{name.capitalize()} analysis does not apply to {resolved_type} media.")
            for name in MODALITIES
        }
        processing: Dict[str, Any] = {
            "modules": {
                "media_validation": {
                    "status": "SUCCEEDED",
                    "media_type": resolved_type,
                }
            }
        }
        evidence = []
        model_versions: Dict[str, str] = {}
        raw_result: Dict[str, Any] = {}
        audio_path: Optional[str] = None

        if resolved_type == "image":
            raw_result = self._run_module(
                "spatial",
                lambda: self.image_runner(file_path),
                processing,
                modalities,
                input_path=file_path,
            )
            spatial_probability = _probability_from_prediction(raw_result)
            modalities["spatial"] = self._probability_modality(
                spatial_probability,
                raw_result,
                "AIDE spatial image fake probability",
            )
            model_versions["spatial"] = str(raw_result.get("model_version") or raw_result.get("model") or "unknown")
            modalities["spatial"]["model"] = model_versions["spatial"]
            frequency_result = self._run_module(
                "frequency",
                lambda: self._frequency_for_image(file_path),
                processing,
                modalities,
                input_path=file_path,
            )
            modalities["frequency"] = self._supporting_modality(
                frequency_result.get("frequency_score"),
                "frequency_support_metric",
                "DCT frequency distribution support metric",
            )
            model_versions["frequency"] = "DCT-frequency-v1"
            model_versions["preprocessing"] = str(
                raw_result.get("preprocessing_version") or "image-preprocess-v1.0"
            )
            quality = self._quality_result(raw_result)
            processing["modules"]["face_extraction"] = {
                "status": "SUCCEEDED",
                "faces_detected": int(raw_result.get("faces_detected", 0)),
            } if processing["modules"]["spatial"]["status"] == "SUCCEEDED" else {
                "status": "FAILED",
                "message": "Face/frame preprocessing did not complete.",
            }
            if raw_result.get("evidence"):
                evidence.append({"type": "spatial_preprocessing", "details": raw_result["evidence"]})
            if raw_result.get("face_results"):
                evidence.append({
                    "type": "face_predictions",
                    "details": raw_result["face_results"],
                })
            evidence.append({
                "type": "frequency_analysis",
                "details": frequency_result.get("frequency_summary", {}),
            })
        elif resolved_type == "video":
            raw_result = self._run_module(
                "spatial",
                lambda: self.video_runner(file_path),
                processing,
                modalities,
                input_path=file_path,
            )
            if raw_result.get("frame_predictions"):
                raw_result["frame_predictions"] = [
                    {
                        key: value
                        for key, value in frame.items()
                        if key != "feature_vector"
                    }
                    for frame in raw_result["frame_predictions"]
                ]
            modalities["spatial"] = self._probability_modality(
                _score_probability(raw_result.get("spatial_score"))
                if raw_result.get("success") is not False
                else None,
                raw_result,
                "AIDE frame-level fake probability",
            )
            model_versions["spatial"] = str(raw_result.get("model_version") or raw_result.get("model") or "unknown")
            modalities["spatial"]["model"] = model_versions["spatial"]

            temporal_probability = _score_probability(raw_result.get("temporal_score"))
            temporal_available = bool(video_model_manager.is_available()) and raw_result.get("success") is not False
            if temporal_available:
                modalities["temporal"] = self._probability_modality(
                    temporal_probability,
                    raw_result,
                    "trained temporal model fake probability",
                )
                model_versions["temporal"] = "TemporalSequenceClassifier"
                processing["modules"]["temporal"] = {
                    "status": "SUCCEEDED" if temporal_probability is not None else "FAILED",
                }
            else:
                modalities["temporal"] = _empty_modality(
                    "MODEL_NOT_AVAILABLE",
                    "A trained temporal checkpoint is not available; the untrained temporal output was excluded.",
                )
                processing["modules"]["temporal"] = {
                    "status": "UNAVAILABLE",
                    "message": modalities["temporal"]["message"],
                }

            frequency_result = self._run_module(
                "frequency",
                lambda: self._frequency_for_video(file_path),
                processing,
                modalities,
                input_path=file_path,
            )
            modalities["frequency"] = self._supporting_modality(
                frequency_result.get("frequency_score"),
                "frequency_support_metric",
                "Mean sampled-frame DCT frequency distribution support metric",
            )
            quality = self._quality_result(raw_result)
            model_versions["frequency"] = "DCT-frequency-v1"
            model_versions["preprocessing"] = str(
                raw_result.get("preprocessing_version") or "image-preprocess-v1.0"
            )
            processing["modules"]["frame_extraction"] = {
                "status": "SUCCEEDED" if raw_result.get("frames_analyzed", 0) else "FAILED",
                "frames_analyzed": int(raw_result.get("frames_analyzed", 0)),
            }
            if raw_result.get("frame_predictions"):
                evidence.append({
                    "type": "frame_predictions",
                    "details": raw_result["frame_predictions"],
                })
            evidence.append({
                "type": "frequency_analysis",
                "details": frequency_result.get("frequency_summary", {}),
            })

            audio_path = self._extract_video_audio(file_path, analysis_id)
            raw_result["audio_available"] = bool(audio_path)
            if isinstance(raw_result.get("metadata"), dict):
                raw_result["metadata"]["audio_available"] = bool(audio_path)
            if audio_path:
                audio_result = self._run_module(
                    "audio",
                    lambda: self.audio_runner(audio_path),
                    processing,
                    modalities,
                    input_path=audio_path,
                )
                self._set_audio_modality(modalities, audio_result, model_versions)
                if audio_result.get("message"):
                    evidence.append({"type": "audio_analysis", "details": audio_result.get("message")})
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                audio_path = None
            else:
                modalities["audio"] = _empty_modality(
                    "UNAVAILABLE",
                    "No audio track was extracted. FFmpeg may be unavailable or the video may have no audio stream.",
                )
                processing["modules"]["audio"] = {
                    "status": "UNAVAILABLE",
                    "message": modalities["audio"]["message"],
                }
        else:
            raw_result = self._run_module(
                "audio",
                lambda: self.audio_runner(file_path),
                processing,
                modalities,
                input_path=file_path,
            )
            self._set_audio_modality(modalities, raw_result, model_versions)
            quality = {
                "status": "NOT_ASSESSED",
                "score": None,
                "details": {},
                "warning": "Audio input quality metrics are not implemented; no quality score was inferred.",
            }
            processing["modules"]["audio_extraction"] = {
                "status": "SUCCEEDED"
                if raw_result.get("audio_available")
                else "FAILED",
                "duration_seconds": raw_result.get("duration"),
            }
            evidence.append({
                "type": "audio_analysis",
                "details": {
                    "model": raw_result.get("model"),
                    "duration": raw_result.get("duration"),
                    "sample_rate": raw_result.get("sample_rate"),
                    "message": raw_result.get("message"),
                },
            })

        for name in ("spatial", "temporal", "frequency"):
            if modalities[name]["status"] == "NOT_APPLICABLE":
                processing["modules"][name] = {"status": "NOT_APPLICABLE"}
        processing["modules"]["quality_analysis"] = {
            "status": "SUCCEEDED" if quality.get("score") is not None else "UNAVAILABLE",
            "quality_status": quality.get("status"),
        }
        for name, modality in modalities.items():
            if modality["status"] == "FAILED_ANALYSIS":
                modality["available"] = False

        score_args = {
            "spatial_score": modalities["spatial"].get("score"),
            "temporal_score": modalities["temporal"].get("score"),
            "frequency_score": modalities["frequency"].get("score"),
            "audio_score": modalities["audio"].get("score"),
            "quality_score": quality.get("score") if quality.get("score") is not None else 1.0,
            "modality_availability": {
                name: bool(value.get("available")) for name, value in modalities.items()
            },
            "modality_status": {
                name: (
                    "SUPPORTING_ONLY"
                    if value.get("score_type") != "fake_probability" and value.get("available")
                    else value.get("status", "")
                )
                for name, value in modalities.items()
            },
            "threshold": MULTIMODAL_DECISION_THRESHOLD,
        }
        fusion = fuse_multimodal_scores(**score_args)
        included = set(fusion.get("available_modalities", []))
        for name, modality in modalities.items():
            modality["included_in_fusion"] = name in included
            if name in fusion.get("evidence", {}):
                modality["fusion_status"] = fusion["evidence"][name]["status"]
                modality["fusion_message"] = fusion["evidence"][name]["message"]

        has_classifying_evidence = bool(included)
        quality_is_low = quality.get("score") is not None and quality["score"] < 0.35
        if not has_classifying_evidence or quality_is_low:
            prediction = {"label": "UNCERTAIN", "confidence": 0.0}
        else:
            prediction = {
                "label": fusion["final_label"],
                "confidence": round(float(fusion["confidence"]), 6),
            }
        for name in included:
            modalities[name]["fusion_weight"] = MULTIMODAL_WEIGHTS.get(name, 1.0)
        weight_total = sum(MULTIMODAL_WEIGHTS.get(name, 1.0) for name in included)
        normalized_weights = {}
        for name in included:
            effective_weight = (
                MULTIMODAL_WEIGHTS.get(name, 1.0) / weight_total
                if weight_total > 0
                else 0.0
            )
            normalized_weights[name] = effective_weight
            modalities[name]["normalized_fusion_weight"] = effective_weight
            modalities[name]["weighted_contribution"] = (
                float(modalities[name]["score"]) * effective_weight
            )
        processing["modules"]["fusion"] = {
            "status": "SUCCEEDED" if has_classifying_evidence else "UNAVAILABLE",
            "available_modalities": sorted(included),
        }
        processing["modules"]["confidence_calibration"] = {
            "status": "NOT_CONFIGURED",
            "method": "decision_margin",
        }
        processing["modules"]["explainability"] = {
            "status": "SUCCEEDED",
            "evidence_items": len(evidence),
        }

        fused_fake_prob = (
            1.0 - fusion["confidence"] if prediction["label"] == "REAL"
            else fusion["confidence"] if prediction["label"] == "FAKE"
            else None
        )
        decision_margin = (
            round(abs(fused_fake_prob - MULTIMODAL_DECISION_THRESHOLD), 4)
            if fused_fake_prob is not None
            else 0.0
        )

        evaluation_outcome = None
        resolved_ground_truth = ground_truth or raw_result.get("ground_truth")
        if resolved_ground_truth and prediction.get("label") in {"REAL", "FAKE"}:
            gt_norm = str(resolved_ground_truth).strip().upper()
            is_gt_fake = gt_norm in {"FAKE", "AI_GENERATED", "SYNTHETIC", "DEEPFAKE", "MANIPULATED"}
            is_pred_fake = (prediction["label"] == "FAKE")
            if is_gt_fake and is_pred_fake:
                evaluation_outcome = "TRUE_POSITIVE"
            elif not is_gt_fake and not is_pred_fake:
                evaluation_outcome = "TRUE_NEGATIVE"
            elif not is_gt_fake and is_pred_fake:
                evaluation_outcome = "FALSE_POSITIVE"
            elif is_gt_fake and not is_pred_fake:
                evaluation_outcome = "FALSE_NEGATIVE"

        processing["fusion"] = {
            "method": "weighted_mean_of_available_fake_probabilities",
            "weights": {
                name: MULTIMODAL_WEIGHTS.get(name, 1.0)
                for name in included
            },
            "normalized_weights": normalized_weights,
            "threshold": MULTIMODAL_DECISION_THRESHOLD,
            "decision_margin": decision_margin,
            "available_modalities": sorted(included),
            "excluded_modalities": {
                name: value.get("fusion_message")
                for name, value in modalities.items()
                if not value.get("included_in_fusion")
            },
            "fake_probability": fused_fake_prob,
            "confidence_calibration": {
                "method": "decision_margin",
                "statistically_calibrated": False,
                "description": (
                    f"Confidence is the distance from the 0.50 decision boundary (decision margin: {decision_margin * 100:.2f} percentage points); "
                    "no held-out calibration model is configured."
                ),
            },
        }

        module_states = [entry.get("status") for entry in processing["modules"].values()]
        if not has_classifying_evidence:
            status = "FAILED" if raw_result.get("success") is False else "PARTIAL"
        elif any(state in {"FAILED", "UNAVAILABLE"} for state in module_states):
            status = "PARTIAL"
        else:
            status = "COMPLETED"
        processing["total_ms"] = round((time.perf_counter() - started) * 1000, 3)
        completed_at = _utc_now()
        processing["module_success"] = {
            name: entry.get("status") == "SUCCEEDED"
            for name, entry in processing["modules"].items()
        }
        processing["unavailable_modalities"] = [
            name
            for name, value in modalities.items()
            if not value.get("available") and value.get("status") != "NOT_APPLICABLE"
        ]

        response = {
            "analysis_id": analysis_id,
            "media_type": resolved_type,
            "status": status,
            "prediction": prediction,
            "confidence": prediction["confidence"],
            "fake_probability": fused_fake_prob,
            "decision_threshold": MULTIMODAL_DECISION_THRESHOLD,
            "decision_margin": decision_margin,
            "authenticity_verified": False,
            "ground_truth": resolved_ground_truth,
            "evaluation_outcome": evaluation_outcome,
            "calibration_status": "NOT_CONFIGURED",
            "statistically_calibrated": False,
            "quality": quality,
            "modalities": modalities,
            "evidence": evidence,
            "timestamps": {"started_at": started_at, "completed_at": completed_at},
            "processing": processing,
            "model_versions": model_versions,
            "success": status != "FAILED",
            "processing_time_ms": round(processing["total_ms"]),
            "model_version": ", ".join(sorted(set(model_versions.values()))) or "unknown",
            "message": self._result_message(status, prediction, quality, processing),
        }

        # Keep detector-specific fields available to existing API consumers and reports.
        for key in (
            "faces_detected",
            "face_results",
            "frames_analyzed",
            "frame_predictions",
            "suspicious_timestamps",
            "metadata",
            "performance",
            "input_quality",
            "model",
            "threshold",
            "duration",
            "sample_rate",
            "audio_available",
            "label",
            "confidence",
            "preprocessing_version",
            "evaluation",
            "raw_model_prob",
        ):
            if key in raw_result:
                response[key] = raw_result[key]
        response["confidence"] = prediction["confidence"]
        response["authenticity_verified"] = False
        if resolved_type == "video" and raw_result.get("spatial_score") is not None:
            response["spatial_score"] = raw_result["spatial_score"]
            response["temporal_score"] = modalities["temporal"].get("score")
            response["combined_score"] = processing["fusion"]["fake_probability"]
            if isinstance(response.get("evaluation"), dict):
                response["evaluation"]["temporal_only"] = {
                    **response["evaluation"].get("temporal_only", {}),
                    "score": modalities["temporal"].get("score"),
                    "status": modalities["temporal"].get("status"),
                }
                response["evaluation"]["combined"] = {
                    "score": processing["fusion"]["fake_probability"],
                    "label": prediction["label"],
                    "confidence": prediction["confidence"],
                }

        return response

    @staticmethod
    def _probability_modality(
        probability: Optional[float],
        result: Dict[str, Any],
        description: str,
    ) -> Dict[str, Any]:
        if probability is None:
            return _empty_modality(
                "FAILED_ANALYSIS"
                if result.get("success") is False
                else str(result.get("status") or "UNAVAILABLE"),
                str(result.get("message") or "No usable probability score was returned."),
            )
        label = "FAKE" if probability >= MULTIMODAL_DECISION_THRESHOLD else "REAL"
        return {
            "available": True,
            "status": "AVAILABLE",
            "score": probability,
            "score_type": "fake_probability",
            "label": label,
            "confidence": probability if label == "FAKE" else 1.0 - probability,
            "included_in_fusion": False,
            "model": result.get("model") or result.get("model_version"),
            "description": description,
            "message": result.get("message"),
        }

    @staticmethod
    def _supporting_modality(
        score: Optional[float],
        score_type: str,
        description: str,
    ) -> Dict[str, Any]:
        if score is None:
            return _empty_modality("FAILED_ANALYSIS", "No supporting score was returned.")
        return {
            "available": True,
            "status": "AVAILABLE",
            "score": float(np.clip(float(score), 0.0, 1.0)),
            "score_type": score_type,
            "label": None,
            "confidence": None,
            "included_in_fusion": False,
            "description": description,
            "message": "Supporting metric only; not interpreted as fake probability.",
        }

    @staticmethod
    def _quality_result(result: Dict[str, Any]) -> Dict[str, Any]:
        quality = result.get("input_quality") or result.get("quality") or {}
        if isinstance(quality, str):
            return {"status": quality, "score": None, "details": {}, "warning": None}
        score = quality.get("quality_score", quality.get("qualityScore"))
        return {
            "status": str(quality.get("status") or "NOT_ASSESSED"),
            "score": float(score) if score is not None else None,
            "details": quality.get("details", {}),
            "warning": quality.get("warning") or quality.get("message"),
        }

    def _set_audio_modality(
        self,
        modalities: Dict[str, Dict[str, Any]],
        result: Dict[str, Any],
        model_versions: Dict[str, str],
    ) -> None:
        probability = _probability_from_prediction(result)
        if probability is None:
            modalities["audio"] = _empty_modality(
                str(result.get("status") or "UNAVAILABLE"),
                str(result.get("message") or "No usable audio score was returned."),
            )
            return

        model = str(result.get("model") or "unknown")
        model_versions["audio"] = model
        if model == "mel-mfcc-supporting-evidence":
            modalities["audio"] = self._supporting_modality(
                probability,
                "audio_support_probability_proxy",
                "Heuristic mel/MFCC audio score",
            )
            modalities["audio"]["status"] = "SUPPORTING_ONLY"
            modalities["audio"]["model"] = model
            modalities["audio"]["label"] = result.get("label")
            modalities["audio"]["confidence"] = result.get("confidence")
            modalities["audio"]["message"] = (
                "Heuristic audio output is preserved but excluded from fusion because no trained AASIST checkpoint is loaded."
            )
            return

        modalities["audio"] = self._probability_modality(
            probability,
            result,
            "AASIST audio fake probability",
        )
        modalities["audio"]["model"] = model

    @staticmethod
    def _result_message(
        status: str,
        prediction: Dict[str, Any],
        quality: Dict[str, Any],
        processing: Dict[str, Any],
    ) -> str:
        if status == "FAILED":
            return "Media could not be analyzed by an available detection module."
        if prediction["label"] == "UNCERTAIN":
            return "No reliable fake-probability evidence was available for a final classification."
        if quality.get("status") == "POOR":
            return "Input quality is too low for a reliable decision; review the preserved modality scores with caution."
        if status == "PARTIAL":
            return "A partial result was produced. See module statuses and unavailable modalities before interpreting the classification."
        return "Classification is based on the listed available fake-probability modalities. Supporting metrics are shown separately."

def _score_probability(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(score):
        return None
    return float(np.clip(score, 0.0, 1.0))


analysis_orchestrator = AnalysisOrchestrator()


__all__ = ["AnalysisOrchestrator", "analysis_orchestrator"]
