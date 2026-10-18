import base64
import io
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps

from ml.models.image.aide_model import AIDEImageDetector
from preprocessing.image_preprocessor import image_preprocessor
from utils.logging_utils import logger


class GradCAM:
    """Gradient-weighted Class Activation Mapping for the image detector."""

    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None

        if self.target_layer is not None:
            self.target_layer.register_forward_hook(self._save_activation)
            self.target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, input_tensor, output):
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate_heatmap(self, input_tensor: torch.Tensor, target_class: Optional[str] = None) -> np.ndarray:
        """Generate a normalized 2D Grad-CAM heatmap for the current model prediction."""
        if self.model is None or self.target_layer is None:
            logger.warning("GradCAM requested without an initialized target layer; returning empty heatmap.")
            return np.zeros((224, 224), dtype=np.float32)

        if input_tensor.dim() == 3:
            input_tensor = input_tensor.unsqueeze(0)

        self.model.zero_grad()
        logits = self.model(input_tensor)
        if logits.ndim == 0:
            score = logits
        else:
            score = logits[0]

        if target_class is None:
            target_class = "FAKE" if torch.sigmoid(score).item() >= 0.5 else "REAL"

        if target_class == "FAKE":
            target_score = score
        else:
            target_score = -score

        target_score.backward(retain_graph=True)

        if self.gradients is None or self.activations is None:
            logger.warning("Grad-CAM gradients or activations are unavailable; returning empty heatmap.")
            return np.zeros((224, 224), dtype=np.float32)

        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)
        cam = torch.relu(cam)
        cam = cam.squeeze(1).squeeze(0).cpu().numpy()

        if cam.size == 0:
            return np.zeros((224, 224), dtype=np.float32)

        cam = cam.astype(np.float32)
        if np.max(cam) > 0:
            cam = cam / np.max(cam)
        return cam

    def overlay_heatmap(self, image_rgb: np.ndarray, heatmap: np.ndarray, alpha: float = 0.5) -> np.ndarray:
        """Blend the Grad-CAM heatmap onto the original image and return an RGB overlay."""
        image_bgr = cv2.cvtColor(np.asarray(image_rgb, dtype=np.uint8), cv2.COLOR_RGB2BGR)
        heatmap_resized = cv2.resize(heatmap, (image_bgr.shape[1], image_bgr.shape[0]))
        heatmap_resized = np.clip(heatmap_resized, 0.0, 1.0)

        heatmap_color = cv2.applyColorMap(np.uint8(255 * heatmap_resized), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(image_bgr, 1.0 - alpha, heatmap_color, alpha, 0)
        return cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)


def _encode_image_to_data_url(image_rgb: np.ndarray) -> str:
    buffer = io.BytesIO()
    Image.fromarray(np.asarray(image_rgb, dtype=np.uint8)).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def explain_image_with_gradcam(file_path: str, threshold: float = 0.5, save_dir: str = "scratch/evidence") -> Dict[str, Any]:
    """Run the real image detector and return a Grad-CAM evidence visualization.

    The returned labels are model evidence visualizations only. They do not claim a causal
    forensic explanation of manipulation.
    """
    os.makedirs(save_dir, exist_ok=True)
    model = AIDEImageDetector()
    checkpoint = model.load_checkpoint()
    if not checkpoint.get("success"):
        return {
            "status": "MODEL_NOT_AVAILABLE",
            "label": "Model Evidence Visualization",
            "target_class": "REAL",
            "prediction_score": 0.0,
            "heatmap": [],
            "overlay_image": "",
            "evidence_path": "",
            "explanation": "The highlighted regions indicate areas that contributed to the model prediction. They are not guaranteed to represent a causal forensic explanation.",
            "message": checkpoint.get("message", "AIDE checkpoint not available."),
        }

    try:
        prep_result = image_preprocessor.process(file_path)
        crop_tensor = prep_result["batch_tensor"][0:1]
        input_tensor = crop_tensor.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
        model.eval()
        logits = model(input_tensor)
        prob = float(torch.sigmoid(logits).squeeze(0).item())

        target_class = "FAKE" if prob >= threshold else "REAL"
        prediction_score = float(prob)

        target_layer = model.backbone[8]
        gradcam = GradCAM(model, target_layer)

        heatmap = gradcam.generate_heatmap(input_tensor, target_class=target_class)
        original_rgb = np.array(Image.open(file_path).convert("RGB"), dtype=np.uint8)
        overlay_image = gradcam.overlay_heatmap(original_rgb, heatmap)

        file_name = f"evidence_{uuid.uuid4().hex}.png"
        evidence_path = os.path.join(save_dir, file_name)
        Image.fromarray(np.asarray(overlay_image, dtype=np.uint8)).save(evidence_path)

        return {
            "status": "COMPLETED",
            "label": "Model Evidence Visualization",
            "target_class": target_class,
            "prediction_score": float(prediction_score),
            "heatmap": np.round(np.clip(heatmap, 0.0, 1.0), 6).tolist(),
            "overlay_image": _encode_image_to_data_url(overlay_image),
            "evidence_path": evidence_path,
            "explanation": "The highlighted regions indicate areas that contributed to the model prediction. They are not guaranteed to represent a causal forensic explanation.",
            "message": "Grad-CAM model evidence visualization generated successfully.",
        }
    except Exception as exc:  # pragma: no cover - runtime fallback path
        logger.exception("Grad-CAM explainability failed for %s", file_path)
        return {
            "status": "FAILED_ANALYSIS",
            "label": "Model Evidence Visualization",
            "target_class": "REAL",
            "prediction_score": 0.0,
            "heatmap": [],
            "overlay_image": "",
            "evidence_path": "",
            "explanation": "The highlighted regions indicate areas that contributed to the model prediction. They are not guaranteed to represent a causal forensic explanation.",
            "message": f"Grad-CAM analysis failed: {exc}",
        }
