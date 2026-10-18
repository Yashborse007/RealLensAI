from __future__ import annotations

import os
from typing import Optional

import numpy as np
import torch
import torch.nn as nn


class AASISTAudioDetector(nn.Module):
    """AASIST-style audio anti-spoofing detector wrapper.

    The public AASIST checkpoint is to be downloaded manually from the official repo when
    the user's environment permits it. This scaffold keeps the exact inference contract
    and modular checkpoint-loading behavior while remaining honest about not claiming
    measured performance without a dataset-backed evaluation.
    """

    def __init__(self, in_channels: int = 1, hidden_dim: int = 64):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv1d(in_channels, 16, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv1d(16, 32, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, stride=2),
            nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        pooled = self.pool(features)
        return self.classifier(pooled).squeeze(-1)

    def predict_probability(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return torch.sigmoid(self(x))

    def load_checkpoint(self, checkpoint_path: Optional[str] = None):
        if checkpoint_path is None or not os.path.exists(checkpoint_path):
            return {"success": False, "message": "AASIST checkpoint not found"}
        payload = torch.load(checkpoint_path, map_location="cpu")
        if isinstance(payload, dict) and "model_state_dict" in payload:
            self.load_state_dict(payload["model_state_dict"])
        else:
            self.load_state_dict(payload)
        self.eval()
        return {"success": True}
