from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

from ml.config import (
    CHECKPOINT_ROOT,
    IMAGE_DECISION_THRESHOLD,
    IMAGE_MODEL_PATH,
    get_torch_device,
)


def resolve_image_checkpoint_path(checkpoint_path: Optional[str] = None) -> Optional[str]:
    """Resolve the real checkpoint path, including the local stage-A artifact directory."""
    candidates = []
    if checkpoint_path:
        candidates.append(checkpoint_path)

    candidates.extend([
        IMAGE_MODEL_PATH,
        str(CHECKPOINT_ROOT / "image" / "best_model.pth"),
        str(CHECKPOINT_ROOT / "image" / "last_model.pth"),
        str(Path("scratch") / "stage_a_dataset" / "artifacts" / "best_model.pth"),
        str(Path("scratch") / "stage_a_dataset" / "artifacts" / "last_model.pth"),
    ])

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


class AIDEImageDetector(nn.Module):
    """AIDE-compatible image deepfake detector wrapper.

    This implementation keeps the model interface modular and checkpoint-driven. The
    official AIDE repo/checkpoint should be placed under the configured checkpoint path
    if you are using the original public implementation; otherwise the model acts as a
    robust binary classifier scaffold ready for training.
    """

    def __init__(self, input_channels: int = 3, hidden_dim: int = 64):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        logits = self.classifier(features)
        return logits.squeeze(-1)

    def predict_probability(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            logits = self(x)
            return torch.sigmoid(logits)

    def load_checkpoint(self, checkpoint_path: Optional[str] = None, device: Optional[str] = None) -> Dict[str, Any]:
        path = checkpoint_path or resolve_image_checkpoint_path()
        device_name = device or get_torch_device()
        state = {"success": False, "message": "Checkpoint unavailable"}

        if not path or not os.path.exists(path):
            return state

        try:
            payload = torch.load(path, map_location=device_name)
            if isinstance(payload, dict) and "model_state_dict" in payload:
                self.load_state_dict(payload["model_state_dict"])
                threshold = payload.get("threshold", IMAGE_DECISION_THRESHOLD)
                model_version = payload.get("model_version", "AIDE-CNN-v1.0")
                preprocessing_version = payload.get("preprocessing_version", "image-preprocess-v1.0")
                state = {
                    "success": True,
                    "threshold": float(threshold),
                    "model_version": model_version,
                    "preprocessing_version": preprocessing_version,
                    "payload": payload,
                    "checkpoint_path": path,
                }
            else:
                self.load_state_dict(payload)
                state = {
                    "success": True,
                    "threshold": IMAGE_DECISION_THRESHOLD,
                    "model_version": "AIDE-CNN-v1.0",
                    "preprocessing_version": "image-preprocess-v1.0",
                    "payload": payload,
                    "checkpoint_path": path,
                }
            self.eval()
            return state
        except Exception as exc:  # pragma: no cover - best effort runtime validation
            return {"success": False, "message": f"Could not load checkpoint: {exc}"}

    def save_checkpoint(
        self,
        checkpoint_path: str,
        epoch: int,
        optimizer: Optional[torch.optim.Optimizer] = None,
        best_val_loss: float = float("inf"),
        threshold: float = IMAGE_DECISION_THRESHOLD,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        path = Path(checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "epoch": epoch,
            "model_state_dict": self.state_dict(),
            "optimizer_state_dict": optimizer.state_dict() if optimizer is not None else None,
            "best_val_loss": float(best_val_loss),
            "threshold": float(threshold),
            "model_version": (config or {}).get("model_version", "AIDE-CNN-v1.0"),
            "preprocessing_version": (config or {}).get("preprocessing_version", "image-preprocess-v1.0"),
            "config": config or {},
        }

        torch.save(payload, str(path))
        return str(path)
