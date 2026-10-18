from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch
from PIL import Image, ImageOps

from ml.config import IMAGE_DECISION_THRESHOLD, IMAGE_SIZE, get_torch_device
from ml.models.image.aide_model import AIDEImageDetector


def predict_image_probability(file_path: str, model: Optional[AIDEImageDetector] = None, threshold: float = IMAGE_DECISION_THRESHOLD) -> Dict[str, Any]:
    """Return a model-confidence result for a single image.

    The returned label reflects the model's decision under the configured threshold. It
    does not represent forensic certainty or proof of authenticity.
    """
    if model is None:
        model = AIDEImageDetector()
        load_status = model.load_checkpoint()
        if not load_status.get("success"):
            return {
                "media_type": "image",
                "label": "REAL",
                "confidence": 0.0,
                "model": "AIDE",
                "threshold": float(threshold),
                "status": "MODEL_NOT_AVAILABLE",
                "message": "AIDE checkpoint not found. Download the public checkpoint or train a model first.",
            }

    device = torch.device(get_torch_device())
    image = Image.open(file_path).convert("RGB")
    image = ImageOps.exif_transpose(image)
    image = image.resize((IMAGE_SIZE, IMAGE_SIZE))
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = np.transpose(array, (2, 0, 1))
    tensor = torch.from_numpy(array).unsqueeze(0).to(device)

    with torch.no_grad():
        prob = torch.sigmoid(model(tensor)).squeeze(0).item()

    fake_probability = float(prob)
    if fake_probability >= threshold:
        label = "FAKE"
        confidence = fake_probability
    else:
        label = "REAL"
        confidence = 1.0 - fake_probability

    return {
        "media_type": "image",
        "label": label,
        "confidence": float(max(0.0, min(1.0, confidence))),
        "model": "AIDE",
        "threshold": float(threshold),
        "fake_probability": fake_probability,
    }
