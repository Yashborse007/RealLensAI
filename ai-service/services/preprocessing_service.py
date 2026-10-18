from typing import Dict, Any
from preprocessing.face_detector import face_detector
from preprocessing.frame_extractor import frame_extractor
from preprocessing.audio_processor import audio_processor
from utils.logging_utils import logger

class PreprocessingService:
    """
    Unified preprocessing pipeline dispatcher for image, video, and audio assets.
    """
    def preprocess_image(self, image_bytes: bytes) -> Dict[str, Any]:
        logger.info("Executing image preprocessing tensor pipeline.")
        return {"status": "preprocessed", "size_bytes": len(image_bytes)}

    def preprocess_video(self, video_path: str) -> Dict[str, Any]:
        logger.info(f"Executing video preprocessing pipeline for {video_path}.")
        frames = frame_extractor.extract_uniform_frames(video_path, max_frames=16)
        return {"status": "preprocessed", "extracted_frames_count": len(frames)}

    def preprocess_audio(self, audio_path: str) -> Dict[str, Any]:
        logger.info(f"Executing audio preprocessing pipeline for {audio_path}.")
        features = audio_processor.extract_features(audio_path)
        return {"status": "preprocessed", "features": features}

preprocessing_service = PreprocessingService()
