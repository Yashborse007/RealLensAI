from __future__ import annotations

import io
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import cv2
import numpy as np
import torch
from PIL import Image


class FrequencyAnalysisService:
    """Frequency-domain supporting evidence for image-based deepfake analysis.

    This service intentionally treats frequency information as a supporting signal only.
    It does not claim that frequency artifacts alone prove a deepfake. The score is a
    measurable summary of spectral energy patterns, useful for comparison across
    preprocessing conditions and as one piece of evidence in a multimodal pipeline.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {
            "target_size": (224, 224),
            "resize": True,
            "jpeg_quality": None,
            "blur_ksize": None,
            "noise_sigma": 0.0,
            "use_dct": True,
            "deterministic_noise": True,
            "low_band_fraction": 0.10,
            "mid_band_fraction": 0.35,
            "high_band_fraction": 0.55,
        }
        if config:
            self.config.update(config)

    def _to_uint8_image(self, image: Union[np.ndarray, str, bytes, Image.Image]) -> np.ndarray:
        if isinstance(image, np.ndarray):
            arr = image
        elif isinstance(image, Image.Image):
            arr = np.array(image.convert("RGB"))
        elif isinstance(image, (bytes, bytearray)):
            stream = io.BytesIO(image)
            arr = np.array(Image.open(stream).convert("RGB"))
        else:
            raise ValueError("Unsupported image input. Use a NumPy array, PIL image, or image bytes.")

        if arr.ndim == 2:
            arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
        if arr.shape[-1] == 1:
            arr = np.repeat(arr, 3, axis=-1)
        if arr.shape[-1] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    def _apply_preprocessing(self, image_bgr: np.ndarray, config: Optional[Dict[str, Any]] = None) -> np.ndarray:
        working = image_bgr.copy()
        cfg = deepcopy(self.config)
        if config:
            cfg.update(config)

        if cfg.get("resize"):
            target = tuple(cfg["target_size"])
            if target and working.shape[:2] != target:
                working = cv2.resize(working, target, interpolation=cv2.INTER_AREA)

        if cfg.get("jpeg_quality") is not None:
            quality = int(cfg["jpeg_quality"])
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), max(1, min(100, quality))]
            _, encoded = cv2.imencode(".jpg", working, encode_param)
            working = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

        if cfg.get("blur_ksize"):
            ksize = int(cfg["blur_ksize"])
            if ksize > 1:
                k = max(1, ksize)
                if k % 2 == 0:
                    k += 1
                working = cv2.GaussianBlur(working, (k, k), 0)

        if float(cfg.get("noise_sigma", 0.0)) > 0.0:
            sigma = float(cfg["noise_sigma"])
            rng = np.random.default_rng(0) if cfg.get("deterministic_noise", True) else np.random.default_rng()
            noise = rng.normal(0, sigma * 255.0, working.shape).astype(np.float32)
            working = np.clip(working.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        return working

    def _compute_dct_energy(self, gray: np.ndarray) -> Dict[str, float]:
        gray_f = gray.astype(np.float32)
        dct_matrix = cv2.dct(gray_f)
        magnitude = np.abs(dct_matrix)
        total_energy = float(magnitude.sum())
        if total_energy <= 0:
            return {
                "low_frequency_ratio": 0.0,
                "mid_frequency_ratio": 0.0,
                "high_frequency_ratio": 0.0,
                "energy": 0.0,
                "energy_std": 0.0,
                "sharpness_proxy": 0.0,
            }

        h, w = magnitude.shape
        # Create normalized coordinate grid: (0,0) is DC / lowest frequency at top-left
        # Maximum radius from (0,0) to (h-1, w-1) is sqrt(1^2 + 1^2) = sqrt(2) ~ 1.4142
        u = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        v = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        radius = np.sqrt(u**2 + v**2)

        # Mutually exclusive and exhaustive frequency bands:
        # Low frequency band: radius < 0.15
        # Mid frequency band: 0.15 <= radius < 0.60
        # High frequency band: radius >= 0.60
        low_mask = radius < 0.15
        mid_mask = (radius >= 0.15) & (radius < 0.60)
        high_mask = radius >= 0.60

        low_energy = float(magnitude[low_mask].sum())
        mid_energy = float(magnitude[mid_mask].sum())
        high_energy = float(magnitude[high_mask].sum())

        low_ratio = low_energy / total_energy
        mid_ratio = mid_energy / total_energy
        high_ratio = high_energy / total_energy

        energy = float(magnitude.mean())
        energy_std = float(magnitude.std())
        laplacian = cv2.Laplacian(gray_f, cv2.CV_32F)
        sharpness_proxy = float(np.mean(np.abs(laplacian)))

        return {
            "low_frequency_ratio": float(np.clip(low_ratio, 0.0, 1.0)),
            "mid_frequency_ratio": float(np.clip(mid_ratio, 0.0, 1.0)),
            "high_frequency_ratio": float(np.clip(high_ratio, 0.0, 1.0)),
            "energy": energy,
            "energy_std": energy_std,
            "sharpness_proxy": sharpness_proxy,
        }

    def analyze_image(self, image: Union[np.ndarray, str, bytes, Image.Image], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a single face crop or image in the frequency domain.

        Returns a supporting-evidence score rather than a verified deepfake proof signal.
        """
        image_bgr = self._to_uint8_image(image)
        processed = self._apply_preprocessing(image_bgr, config)

        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        if gray.size == 0:
            return {
                "frequency_score": 0.0,
                "frequency_summary": {
                    "evidence_type": "supporting_evidence",
                    "supporting_evidence": True,
                    "low_frequency_ratio": 0.0,
                    "mid_frequency_ratio": 0.0,
                    "high_frequency_ratio": 0.0,
                    "sharpness_proxy": 0.0,
                    "energy": 0.0,
                    "note": "No valid pixels were available for frequency analysis.",
                },
                "frequency_visualization": {"dct_preview": [], "shape": [0, 0]},
                "config_used": config or self.config,
            }

        dct_stats = self._compute_dct_energy(gray)
        low_ratio = dct_stats["low_frequency_ratio"]
        mid_ratio = dct_stats["mid_frequency_ratio"]
        high_ratio = dct_stats["high_frequency_ratio"]

        # A neutral score based on actual frequency distribution. This is not a forensic value.
        score = float(np.clip(0.5 * (high_ratio + (1.0 - low_ratio)) + 0.25 * mid_ratio, 0.0, 1.0))

        dct_matrix = cv2.dct(gray.astype(np.float32))
        preview = np.abs(dct_matrix[:32, :32])
        normalized_preview = (preview - preview.min()) / (preview.max() - preview.min() + 1e-8)

        summary = {
            "evidence_type": "supporting_evidence",
            "supporting_evidence": True,
            "low_frequency_ratio": float(low_ratio),
            "mid_frequency_ratio": float(mid_ratio),
            "high_frequency_ratio": float(high_ratio),
            "sharpness_proxy": float(dct_stats["sharpness_proxy"]),
            "energy": float(dct_stats["energy"]),
            "energy_std": float(dct_stats["energy_std"]),
            "note": "Frequency-domain output is supporting evidence only; it should not be used alone to prove a deepfake.",
        }

        visualization = {
            "dct_preview": np.round(normalized_preview, 6).tolist(),
            "shape": list(gray.shape),
            "bands": {
                "low": float(low_ratio),
                "mid": float(mid_ratio),
                "high": float(high_ratio),
            },
        }

        return {
            "frequency_score": float(score),
            "frequency_summary": summary,
            "frequency_visualization": visualization,
            "config_used": config or self.config,
        }

    def evaluate_preprocessing_robustness(
        self,
        image: Union[np.ndarray, str, bytes, Image.Image],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Measures how the supporting frequency score changes under common image perturbations."""
        baseline = self.analyze_image(image, config=config)
        baseline_score = float(baseline["frequency_score"])

        scenarios: List[Dict[str, Any]] = []
        perturbations = [
            ("jpeg_compression", {"jpeg_quality": 70}),
            ("resizing", {"resize": True, "target_size": (128, 128)}),
            ("blur", {"blur_ksize": 5}),
            ("noise", {"noise_sigma": 0.02}),
        ]

        for condition, params in perturbations:
            result = self.analyze_image(image, config={**(config or {}), **params})
            score = float(result["frequency_score"])
            delta = score - baseline_score
            direction = "increase" if delta > 0.01 else "decrease" if delta < -0.01 else "stable"
            scenarios.append({
                "condition": condition,
                "score": score,
                "delta": delta,
                "direction": direction,
                "summary": result["frequency_summary"],
            })

        return {
            "baseline": {
                "frequency_score": baseline_score,
                "summary": baseline["frequency_summary"],
            },
            "test_cases": scenarios,
            "summary": "Measured change in frequency support under common preprocessing. Values should be interpreted as supportive context, not forensic proof.",
        }


frequency_service = FrequencyAnalysisService()


__all__ = ["FrequencyAnalysisService", "frequency_service"]
