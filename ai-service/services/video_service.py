from typing import Dict, Any

from ml.inference.video_inference import predict_video_probability
from services.prediction_service import prediction_service
from utils.logging_utils import logger


class VideoService:
    """Video deepfake analysis service using sampled frame inference and temporal aggregation."""

    def process_and_predict(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"VideoService processing file: {file_path}")

        availability = prediction_service.check_model_availability("video")
        if not availability["success"]:
            inference = predict_video_probability(file_path)
            inference["media_type"] = "video"
            inference["modality"] = "video"
            return inference

        inference = predict_video_probability(file_path)
        inference["media_type"] = "video"
        inference["modality"] = "video"
        return inference


video_service = VideoService()
