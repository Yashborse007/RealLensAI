import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

CHECKPOINT_ROOT = Path(__file__).resolve().parents[1] / "ml" / "checkpoints"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_TITLE: str = "RealLens AI - Python AI Service"
    APP_DESCRIPTION: str = "Multi-Modal AI Deepfake Detection Engine"
    VERSION: str = "1.0.0"
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Model Weights Storage Configuration
    MODEL_WEIGHTS_DIR: str = os.getenv("MODEL_WEIGHTS_DIR", str(CHECKPOINT_ROOT))
    IMAGE_MODEL_PATH: str = os.getenv("IMAGE_MODEL_PATH", str(CHECKPOINT_ROOT / "image" / "best_model.pth"))
    VIDEO_MODEL_PATH: str = os.getenv("VIDEO_MODEL_PATH", str(CHECKPOINT_ROOT / "video" / "best_model.pth"))
    AUDIO_MODEL_PATH: str = os.getenv("AUDIO_MODEL_PATH", str(CHECKPOINT_ROOT / "audio" / "best_model.pth"))

    # Upload & Preprocessing Limits
    MAX_FILE_SIZE_BYTES: int = 200 * 1024 * 1024  # 200MB
    ALLOWED_IMAGE_EXTENSIONS: set = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_VIDEO_EXTENSIONS: set = {"mp4", "mov", "avi", "mkv", "webm"}
    ALLOWED_AUDIO_EXTENSIONS: set = {"mp3", "wav", "m4a", "aac", "flac"}

settings = Settings()
