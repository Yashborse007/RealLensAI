from typing import Dict, Any
from models.image_model import image_model_manager
from models.video_model import video_model_manager
from models.audio_model import audio_model_manager
from utils.logging_utils import logger


class PredictionService:
    """Central orchestration service checking PyTorch model availability."""

    def check_model_availability(self, modality: str) -> Dict[str, Any]:
        is_available = False

        if modality == "image":
            is_available = image_model_manager.is_available()
        elif modality == "video":
            is_available = image_model_manager.is_available() or video_model_manager.is_available()
        elif modality == "audio":
            is_available = audio_model_manager.is_available()

        if not is_available:
            logger.info(f"Prediction requested for {modality}, but trained model weights are not configured.")
            return {
                "success": False,
                "status": "MODEL_NOT_AVAILABLE",
                "message": "Trained model is not configured."
            }

        return {"success": True, "status": "MODEL_READY"}


prediction_service = PredictionService()
