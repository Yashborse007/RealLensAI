import glob
import os
from pathlib import Path

import torch

from config import settings
from ml.config import CHECKPOINT_ROOT
from ml.models.image.aide_model import AIDEImageDetector
from utils.logging_utils import logger


class ImageModelManager:
    """Manages state loading for the trained image model checkpoint."""

    def __init__(self):
        self.model = None
        self.is_loaded = False
        self._initialize_model()

    def _resolve_model_path(self) -> str:
        candidates = []
        env_path = os.getenv("IMAGE_MODEL_PATH")
        if env_path:
            candidates.append(env_path)
        candidates.extend([
            settings.IMAGE_MODEL_PATH,
            str(CHECKPOINT_ROOT / "image" / "best_model.pth"),
            str(CHECKPOINT_ROOT / "image" / "last_model.pth"),
            "scratch/stage_a_dataset/artifacts/best_model.pth",
            "scratch/stage_a_dataset/artifacts/last_model.pth",
        ])

        for pattern in [
            "scratch/**/best_model.pth",
            "scratch/**/last_model.pth",
            "**/best_model.pth",
            "**/last_model.pth",
        ]:
            for match in glob.glob(pattern, recursive=True):
                candidates.append(match)

        seen = set()
        for candidate in candidates:
            normalized = os.path.normpath(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            if os.path.exists(normalized):
                return normalized

        # Fallback to the legacy configured path if no trained checkpoint exists
        return os.path.normpath(settings.IMAGE_MODEL_PATH)

    def _initialize_model(self):
        weight_path = self._resolve_model_path()
        if os.path.exists(weight_path):
            try:
                self.model = AIDEImageDetector()
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                payload = torch.load(weight_path, map_location=device)
                if isinstance(payload, dict) and "model_state_dict" in payload:
                    self.model.load_state_dict(payload["model_state_dict"])
                else:
                    self.model.load_state_dict(payload)
                self.model.eval()
                self.is_loaded = True
                logger.info(f"Image PyTorch model weights successfully loaded from {weight_path}")
            except Exception as exc:
                logger.error(f"Failed to load image model weights at {weight_path}: {exc}")
                self.is_loaded = False
        else:
            logger.info(f"Image model weights not found at '{weight_path}'. Model marked as NOT_AVAILABLE.")
            self.is_loaded = False

    def is_available(self) -> bool:
        return self.is_loaded


image_model_manager = ImageModelManager()
