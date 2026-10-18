import time
from typing import Any, Dict

from ml.inference.audio_inference import predict_audio_probability
from utils.logging_utils import logger


class AudioService:
    """Audio analysis service using resampled waveform + mel/MFCC feature extraction."""

    def process_and_predict(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"AudioService processing file: {file_path}")
        started_at = time.perf_counter()

        inference = predict_audio_probability(file_path)
        result = {
            "success": bool(inference.get("success", False)),
            "audio_available": bool(inference.get("audio_available", False)),
            "media_type": "audio",
            "prediction": inference.get("prediction", {"label": "REAL", "confidence": 0.0}),
            "label": inference.get("label", "REAL"),
            "confidence": float(inference.get("confidence", 0.0)),
            "duration": float(inference.get("duration", 0.0)),
            "sample_rate": int(inference.get("sample_rate", 0)),
            "processing_time_ms": int((time.perf_counter() - started_at) * 1000),
            "status": inference.get("status", "INVALID_AUDIO"),
            "model": inference.get("model", "mel-mfcc-supporting-evidence"),
            "threshold": float(inference.get("threshold", 0.5)),
        }

        if "message" in inference:
            result["message"] = inference["message"]

        if not result["audio_available"]:
            result["prediction"] = {"label": "REAL", "confidence": 0.0}
            result["label"] = "REAL"
            result["confidence"] = 0.0
            result["success"] = False
            result["status"] = "AUDIO_NOT_AVAILABLE"
            result["message"] = inference.get("message", "No usable audio signal was found. Missing audio is not evidence of a deepfake.")

        return result


audio_service = AudioService()
