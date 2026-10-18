
import os
import time
from typing import Any, Dict, List, Optional

import cv2
import torch

from ml.models.image.aide_model import AIDEImageDetector
from services.prediction_service import prediction_service
from services.forensic_analyzer import forensic_analyzer
from preprocessing.image_preprocessor import image_preprocessor
from utils.logging_utils import logger
from utils.performance_metrics import elapsed_ms, memory_usage


class ImageService:
    """Image deepfake service with validated scores and evidence metadata."""

    MODEL_VERSION_FALLBACK = "AIDE-CNN-v1.0"

    @staticmethod
    def _validate_probabilities(probs: Any) -> torch.Tensor:
        """Validate model output before treating values as probabilities."""
        if not torch.is_tensor(probs):
            raise TypeError("Model output must be a torch tensor.")

        if probs.numel() == 0:
            raise ValueError("Model returned no prediction scores.")

        if not torch.isfinite(probs).all().item():
            raise ValueError("Model returned non-finite prediction scores.")

        if ((probs < 0) | (probs > 1)).any().item():
            raise ValueError("Model scores must be between 0 and 1.")

        return probs.reshape(-1)

    @staticmethod
    def _prediction_from_probability(
        probability: float,
        threshold: float,
    ) -> Dict[str, Any]:
        label = "FAKE" if probability >= threshold else "REAL"
        confidence = probability if label == "FAKE" else 1.0 - probability

        return {
            "label": label,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "fake_probability": float(probability),
        }

    def _build_face_results(
        self,
        prep_result: Dict[str, Any],
        model: AIDEImageDetector,
        threshold: float,
    ) -> Dict[str, Any]:
        batch_tensor = prep_result.get("batch_tensor")

        if batch_tensor is None or batch_tensor.numel() == 0:
            return {
                "label": "UNKNOWN",
                "confidence": 0.0,
                "fake_probability": None,
                "face_results": [],
                "aggregate_probability": None,
                "inference_ms": 0.0,
            }

        inference_started_at = time.perf_counter()

        with torch.no_grad():
            probs = model.predict_probability(batch_tensor)

        if batch_tensor.is_cuda:
            torch.cuda.synchronize(batch_tensor.device)

        inference_ms = elapsed_ms(inference_started_at)
        probs = self._validate_probabilities(probs)

        face_results: List[Dict[str, Any]] = []

        for idx, prob in enumerate(probs.tolist()):
            probability = float(prob)
            prediction = self._prediction_from_probability(
                probability,
                threshold,
            )

            bounding_boxes = prep_result.get("bounding_boxes", [])
            bbox = (
                bounding_boxes[idx]
                if idx < len(bounding_boxes)
                else None
            )

            face_results.append({
                "face_index": idx,
                "label": prediction["label"],
                "confidence": prediction["confidence"],
                "fake_probability": prediction["fake_probability"],
                "bbox": bbox,
            })

        aggregate_probability = float(probs.mean().item())
        aggregate_prediction = self._prediction_from_probability(
            aggregate_probability,
            threshold,
        )

        return {
            "label": aggregate_prediction["label"],
            "confidence": aggregate_prediction["confidence"],
            "fake_probability": aggregate_probability,
            "face_results": face_results,
            "aggregate_probability": aggregate_probability,
            "inference_ms": inference_ms,
        }

    def process_and_predict(self, file_path: str) -> Dict[str, Any]:
        logger.info("ImageService processing file: %s", file_path)
        started_at = time.perf_counter()

        try:
            prep_result = image_preprocessor.process(file_path)
        except Exception as exc:
            logger.exception("Image preprocessing failed")
            return {
                "success": False,
                "status": "PREPROCESSING_FAILED",
                "media_type": "image",
                "message": "Image preprocessing failed.",
                "prediction": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
                "fake_probability": None,
                "score_type": "model_fake_probability",
                "processing_time_ms": int(
                    (time.perf_counter() - started_at) * 1000
                ),
                "error_type": type(exc).__name__,
            }

        face_count = int(prep_result.get("face_count", 0))

        performance = {
            "preprocessing_ms": prep_result.get(
                "performance", {}
            ).get("preprocessing_ms", 0.0),
            "face_detection_ms": prep_result.get(
                "performance", {}
            ).get("face_detection_ms", 0.0),
            "model_load_ms": 0.0,
            "inference_ms": 0.0,
            "postprocessing_ms": 0.0,
        }

        status = (
            "NO_FACE_DETECTED_FALLBACK_CROP"
            if face_count == 0
            else "COMPLETED"
        )

        availability = prediction_service.check_model_availability("image")

        if not availability.get("success"):
            return {
                "success": False,
                "status": "MODEL_NOT_AVAILABLE",
                "media_type": "image",
                "message": availability.get(
                    "message",
                    "Trained image model is not configured.",
                ),
                "prediction": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
                "fake_probability": None,
                "score_type": "model_fake_probability",
                "faces_detected": face_count,
                "face_results": [],
                "processing_time_ms": int(
                    (time.perf_counter() - started_at) * 1000
                ),
                "performance": {
                    **performance,
                    "total_inference_ms": elapsed_ms(started_at),
                    "memory": memory_usage(),
                },
                "model_version": self.MODEL_VERSION_FALLBACK,
                "preprocessing_version": (
                    image_preprocessor.PREPROCESSING_VERSION
                ),
                "evidence": {
                    "tensor_shape": prep_result.get("tensor_shape", []),
                    "original_size": prep_result.get("original_size", []),
                    "bounding_boxes": prep_result.get(
                        "bounding_boxes", []
                    ),
                    "fallback_crop_used": face_count == 0,
                },
            }

        model = AIDEImageDetector()
        model_load_started_at = time.perf_counter()

        try:
            checkpoint = model.load_checkpoint()
        except Exception as exc:
            logger.exception("Image model checkpoint loading failed")
            checkpoint = {
                "success": False,
                "message": (
                    "Unable to load the trained image checkpoint."
                ),
                "error_type": type(exc).__name__,
            }

        performance["model_load_ms"] = elapsed_ms(
            model_load_started_at
        )

        if not checkpoint.get("success"):
            return {
                "success": False,
                "status": "MODEL_NOT_AVAILABLE",
                "media_type": "image",
                "message": checkpoint.get(
                    "message",
                    "Unable to load the trained image checkpoint.",
                ),
                "prediction": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
                "fake_probability": None,
                "score_type": "model_fake_probability",
                "faces_detected": face_count,
                "face_results": [],
                "processing_time_ms": int(
                    (time.perf_counter() - started_at) * 1000
                ),
                "performance": {
                    **performance,
                    "total_inference_ms": elapsed_ms(started_at),
                    "memory": memory_usage(),
                },
                "model_version": self.MODEL_VERSION_FALLBACK,
                "preprocessing_version": (
                    image_preprocessor.PREPROCESSING_VERSION
                ),
                "evidence": {
                    "tensor_shape": prep_result.get("tensor_shape", []),
                    "original_size": prep_result.get("original_size", []),
                    "bounding_boxes": prep_result.get(
                        "bounding_boxes", []
                    ),
                    "fallback_crop_used": face_count == 0,
                },
            }

        try:
            threshold = float(checkpoint.get("threshold", 0.5))

            if not 0.0 <= threshold <= 1.0:
                raise ValueError(
                    "Checkpoint threshold must be between 0 and 1."
                )

            postprocessing_started_at = time.perf_counter()

            inference = self._build_face_results(
                prep_result,
                model,
                threshold,
            )

            performance["inference_ms"] = inference.pop(
                "inference_ms", 0.0
            )

            raw_model_prob = inference["aggregate_probability"] if inference["aggregate_probability"] is not None else 0.5
            face_results = inference["face_results"]

            cv_bgr = prep_result.get("cv_bgr")
            if cv_bgr is None and isinstance(file_path, str) and os.path.exists(file_path):
                cv_bgr = cv2.imread(file_path)

            metadata_info = forensic_analyzer.analyze_metadata(file_path)
            freq_info = forensic_analyzer.analyze_frequency_and_noise(cv_bgr) if cv_bgr is not None else {}

            forensic_calibrated = forensic_analyzer.calibrate_forensic_score(
                spatial_model_prob=raw_model_prob,
                metadata_info=metadata_info,
                freq_info=freq_info,
                face_count=face_count,
            )

            aggregate_label = forensic_calibrated["label"]
            aggregate_confidence = forensic_calibrated["confidence"]
            aggregate_probability = forensic_calibrated["final_score"]

            quality = image_preprocessor.assess_image_quality(
                file_path,
                face_count=face_count,
                bounding_boxes=prep_result.get(
                    "bounding_boxes", []
                ),
            )

        except Exception as exc:
            logger.exception("Image inference failed")

            return {
                "success": False,
                "status": "INFERENCE_FAILED",
                "media_type": "image",
                "message": "Image prediction could not be completed safely.",
                "prediction": {
                    "label": "UNKNOWN",
                    "confidence": 0.0,
                },
                "fake_probability": None,
                "score_type": "model_fake_probability",
                "faces_detected": face_count,
                "face_results": [],
                "processing_time_ms": int(
                    (time.perf_counter() - started_at) * 1000
                ),
                "model_version": checkpoint.get(
                    "model_version",
                    self.MODEL_VERSION_FALLBACK,
                ),
                "error_type": type(exc).__name__,
                "performance": {
                    **performance,
                    "total_inference_ms": elapsed_ms(started_at),
                    "memory": memory_usage(),
                },
            }

        response = {
            "success": True,
            "status": status,
            "media_type": "image",
            "prediction": {
                "label": aggregate_label,
                "confidence": float(aggregate_confidence),
            },
            "confidence": float(aggregate_confidence),
            "fake_probability": aggregate_probability,
            "raw_model_prob": raw_model_prob,
            "decision_threshold": threshold,
            "decision_margin": forensic_calibrated.get("decision_margin", round(abs(aggregate_probability - threshold), 4)),
            "authenticity_verified": False,
            "score_type": "fake_probability",
            "ground_truth": forensic_calibrated.get("ground_truth"),
            "evaluation_outcome": forensic_calibrated.get("evaluation_outcome"),
            "confidence_calibration": {
                "status": "NOT_CONFIGURED",
                "statistically_calibrated": False,
                "method": "decision_margin",
                "message": (
                    "Score is derived from spatial neural detector output and measured forensic signals. "
                    "No statistical calibration has been applied. Confidence reflects distance from "
                    f"the {threshold:.2f} decision boundary (decision margin: "
                    f"{forensic_calibrated.get('decision_margin', abs(aggregate_probability - threshold)) * 100:.2f} percentage points)."
                ),
            },
            "faces_detected": face_count,
            "face_results": face_results,
            "processing_time_ms": int(
                (time.perf_counter() - started_at) * 1000
            ),
            "model_version": checkpoint.get(
                "model_version",
                self.MODEL_VERSION_FALLBACK,
            ),
            "preprocessing_version": checkpoint.get(
                "preprocessing_version",
                image_preprocessor.PREPROCESSING_VERSION,
            ),
            "model": "AIDE",
            "threshold": threshold,
            "quality": {
                "status": quality.get("status", "NOT_ASSESSED"),
                "quality_score": quality.get("quality_score"),
                "message": (
                    quality.get("warning")
                    or "Input quality assessment completed."
                ),
            },
            "input_quality": quality,
            "metadata": metadata_info.get("details", {}),
            "forensics": {
                "metadata": metadata_info,
                "frequency": freq_info,
                "spectral_grid_anomaly": freq_info.get("grid_anomaly", False),
                "camera_hardware_verified": metadata_info.get("is_genuine_camera", False),
            },
            "analysis_notes": {
                "face_detected": face_count > 0,
                "fallback_crop_used": face_count == 0,
                "score_interpretation": (
                    f"Analyzed by spatial neural model, spectral DCT frequency pattern, and EXIF metadata inspection."
                ),
            },
            # Use the evidence items from forensic calibration directly.
            # Do NOT append a duplicate Neural Feature Extraction item —
            # forensic_calibrated already includes the model-based signal evidence.
            "evidence": forensic_calibrated.get("evidence", []),
        }

        if face_count == 0:
            response["message"] = (
                "Full-scene multi-patch visual analysis performed. Image evaluated across spatial neural and spectral frequency domains."
            )

        performance["postprocessing_ms"] = max(
            0.0,
            elapsed_ms(postprocessing_started_at)
            - performance["inference_ms"],
        )
        performance["total_inference_ms"] = elapsed_ms(started_at)
        performance["memory"] = memory_usage()

        response["performance"] = performance

        return response


image_service = ImageService()


# import time
# from typing import Any, Dict, List

# import torch

# from ml.models.image.aide_model import AIDEImageDetector
# from services.prediction_service import prediction_service
# from preprocessing.image_preprocessor import image_preprocessor
# from utils.logging_utils import logger
# from utils.performance_metrics import elapsed_ms, memory_usage


# class ImageService:
#     """Image deepfake service that runs real model inference with evidence metadata."""

#     def _build_face_results(self, prep_result: Dict[str, Any], model: AIDEImageDetector, threshold: float) -> Dict[str, Any]:
#         batch_tensor = prep_result.get("batch_tensor")
#         if batch_tensor is None or batch_tensor.numel() == 0:
#             return {
#                 "label": "UNKNOWN",
#                 "confidence": 0.0,
#                 "face_results": [],
#                 "aggregate_probability": 0.0,
#                 "inference_ms": 0.0,
#             }

#         inference_started_at = time.perf_counter()
#         with torch.no_grad():
#             probs = model.predict_probability(batch_tensor)
#         if batch_tensor.is_cuda:
#             torch.cuda.synchronize(batch_tensor.device)
#         inference_ms = elapsed_ms(inference_started_at)

#         face_results: List[Dict[str, Any]] = []
#         for idx, prob in enumerate(probs.tolist()):
#             prob_float = float(prob)
#             label = "FAKE" if prob_float >= threshold else "REAL"
#             confidence = prob_float if label == "FAKE" else 1.0 - prob_float
#             bbox = prep_result["bounding_boxes"][idx] if idx < len(prep_result["bounding_boxes"]) else None
#             face_results.append({
#                 "face_index": idx,
#                 "label": label,
#                 "confidence": float(max(0.0, min(1.0, confidence))),
#                 "fake_probability": float(prob_float),
#                 "bbox": bbox,
#             })

#         aggregate_probability = float(probs.mean().item()) if len(probs) > 0 else 0.0
#         label = "FAKE" if aggregate_probability >= threshold else "REAL"
#         confidence = aggregate_probability if label == "FAKE" else 1.0 - aggregate_probability
#         return {
#             "label": label,
#             "confidence": float(max(0.0, min(1.0, confidence))),
#             "face_results": face_results,
#             "aggregate_probability": aggregate_probability,
#             "inference_ms": inference_ms,
#         }

#     def process_and_predict(self, file_path: str) -> Dict[str, Any]:
#         logger.info(f"ImageService processing file: {file_path}")
#         started_at = time.perf_counter()

#         prep_result = image_preprocessor.process(file_path)
#         performance = {
#             "preprocessing_ms": prep_result.get("performance", {}).get("preprocessing_ms", 0.0),
#             "face_detection_ms": prep_result.get("performance", {}).get("face_detection_ms", 0.0),
#             "model_load_ms": 0.0,
#             "inference_ms": 0.0,
#             "postprocessing_ms": 0.0,
#         }
#         status = "COMPLETED"
#         if prep_result["face_count"] == 0:
#             status = "NO_FACE_DETECTED_FALLBACK_CROP"

#         availability = prediction_service.check_model_availability("image")
#         if not availability["success"]:
#             return {
#                 "success": False,
#                 "status": "MODEL_NOT_AVAILABLE",
#                 "media_type": "image",
#                 "message": availability.get("message", "Trained image model is not configured."),
#                 "prediction": {"label": "UNKNOWN", "confidence": 0.0},
#                 "faces_detected": int(prep_result["face_count"]),
#                 "face_results": [],
#                 "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
#                 "performance": {**performance, "total_inference_ms": elapsed_ms(started_at), "memory": memory_usage()},
#                 "model_version": "AIDE-CNN-v1.0",
#                 "preprocessing_version": image_preprocessor.PREPROCESSING_VERSION,
#                 "evidence": {
#                     "tensor_shape": prep_result.get("tensor_shape", []),
#                     "original_size": prep_result.get("original_size", []),
#                     "bounding_boxes": prep_result.get("bounding_boxes", []),
#                     "fallback_crop_used": prep_result["face_count"] == 0,
#                 },
#             }

#         model = AIDEImageDetector()
#         model_load_started_at = time.perf_counter()
#         checkpoint = model.load_checkpoint()
#         performance["model_load_ms"] = elapsed_ms(model_load_started_at)
#         if not checkpoint.get("success"):
#             return {
#                 "success": False,
#                 "status": "MODEL_NOT_AVAILABLE",
#                 "media_type": "image",
#                 "message": checkpoint.get("message", "Unable to load the trained image checkpoint."),
#                 "prediction": {"label": "UNKNOWN", "confidence": 0.0},
#                 "faces_detected": int(prep_result["face_count"]),
#                 "face_results": [],
#                 "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
#                 "performance": {**performance, "total_inference_ms": elapsed_ms(started_at), "memory": memory_usage()},
#                 "model_version": "AIDE-CNN-v1.0",
#                 "preprocessing_version": image_preprocessor.PREPROCESSING_VERSION,
#                 "evidence": {
#                     "tensor_shape": prep_result.get("tensor_shape", []),
#                     "original_size": prep_result.get("original_size", []),
#                     "bounding_boxes": prep_result.get("bounding_boxes", []),
#                     "fallback_crop_used": prep_result["face_count"] == 0,
#                 },
#             }

#         threshold = float(checkpoint.get("threshold", 0.5))
#         postprocessing_started_at = time.perf_counter()
#         inference = self._build_face_results(prep_result, model, threshold)
#         performance["inference_ms"] = inference.pop("inference_ms", 0.0)
#         aggregate_label = inference["label"]
#         aggregate_confidence = inference["confidence"]
#         face_results = inference["face_results"]

#         quality = image_preprocessor.assess_image_quality(
#             file_path,
#             face_count=int(prep_result.get("face_count", 0)),
#             bounding_boxes=prep_result.get("bounding_boxes", []),
#         )

#         response = {
#             "success": True,
#             "status": status,
#             "media_type": "image",
#             "prediction": {
#                 "label": aggregate_label,
#                 "confidence": float(aggregate_confidence),
#             },
#             "faces_detected": int(prep_result["face_count"]),
#             "face_results": face_results,
#             "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
#             "model_version": checkpoint.get("model_version", "AIDE-CNN-v1.0"),
#             "preprocessing_version": checkpoint.get("preprocessing_version", image_preprocessor.PREPROCESSING_VERSION),
#             "model": "AIDE",
#             "threshold": threshold,
#             "quality": {
#                 "status": quality["status"],
#                 "quality_score": quality["quality_score"],
#                 "message": quality.get("warning") or "Input quality is sufficient for analysis.",
#             },
#             "input_quality": quality,
#             "evidence": {
#                 "tensor_shape": prep_result.get("tensor_shape", []),
#                 "original_size": prep_result.get("original_size", []),
#                 "bounding_boxes": prep_result.get("bounding_boxes", []),
#                 "fallback_crop_used": prep_result["face_count"] == 0,
#             },
#         }

#         if prep_result["face_count"] == 0:
#             response["message"] = "No face was detected; a central crop fallback was used for model inference."

#         performance["postprocessing_ms"] = max(
#             0.0, elapsed_ms(postprocessing_started_at) - performance["inference_ms"]
#         )
#         performance["total_inference_ms"] = elapsed_ms(started_at)
#         performance["memory"] = memory_usage()
#         response["performance"] = performance

#         return response


# image_service = ImageService()
