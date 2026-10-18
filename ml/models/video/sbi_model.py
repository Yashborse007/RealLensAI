from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn


class SBIVideoDetector(nn.Module):
    """Self-Blended Images (SBI) style video detector wrapper.

    This module keeps the detection pipeline modular and checkpoint-driven. The public
    SBI implementation and public pretrained checkpoint should be downloaded manually if
    you want to reproduce the official detector instead of the lightweight training scaffold.
    """

    def __init__(self, input_channels: int = 3, hidden_dim: int = 64):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, hidden_dim, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.backbone(x)).squeeze(-1)

    def predict_probability(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return torch.sigmoid(self(x))

    def load_checkpoint(self, checkpoint_path: Optional[str] = None):
        if checkpoint_path is None or not os.path.exists(checkpoint_path):
            return {"success": False, "message": "SBI checkpoint not found"}
        payload = torch.load(checkpoint_path, map_location="cpu")
        if isinstance(payload, dict) and "model_state_dict" in payload:
            self.load_state_dict(payload["model_state_dict"])
        else:
            self.load_state_dict(payload)
        self.eval()
        return {"success": True}

    def aggregate_frame_probabilities(self, probabilities: List[float], strategy: str = "mean") -> float:
        values = np.asarray(probabilities, dtype=np.float32)
        if values.size == 0:
            return 0.0
        if strategy == "median":
            return float(np.median(values))
        return float(np.mean(values))
