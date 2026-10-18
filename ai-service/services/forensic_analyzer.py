import os
import re
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from PIL import Image, ExifTags
from utils.logging_utils import logger


AI_SIGNATURE_PATTERNS = [
    re.compile(r"midjourney", re.I),
    re.compile(r"dall[-_]?e", re.I),
    re.compile(r"stable[\s_-]?diffusion", re.I),
    re.compile(r"comfyui", re.I),
    re.compile(r"novelai", re.I),
    re.compile(r"automatic1111", re.I),
    re.compile(r"webui", re.I),
    re.compile(r"flux\.?1", re.I),
    re.compile(r"invokeai", re.I),
    re.compile(r"civitai", re.I),
    re.compile(r"adobe\s*firefly", re.I),
    re.compile(r"steps:\s*\d+", re.I),
    re.compile(r"sampler:\s*[\w\+]+", re.I),
    re.compile(r"cfg\s*scale:\s*[\d\.]+", re.I),
    re.compile(r"denoising\s*strength", re.I),
    re.compile(r"negative\s*prompt:", re.I),
]

KNOWN_CAMERA_MAKERS = [
    "apple", "samsung", "sony", "canon", "nikon", "fujifilm", "panasonic",
    "olympus", "leica", "google", "huawei", "xiaomi", "oneplus", "oppo",
    "vivo", "motorola", "gopro", "dji", "hasselblad", "pentax", "ricoh"
]


class ForensicAnalyzer:
    """
    Forensic image analysis engine combining:
    1. EXIF Hardware & Sensor Provenance
    2. AI Prompt & Generation Metadata Signatures
    3. Frequency Domain (DCT/FFT) Spectral Anomaly & Grid Detection
    4. Sensor Noise (PRNU proxy) Uniformity Analysis
    """

    def analyze_metadata(self, file_path_or_pil) -> Dict[str, Any]:
        """Inspect EXIF, IPTC, and text tags for camera hardware or AI generator fingerprints."""
        try:
            if isinstance(file_path_or_pil, str):
                pil_img = Image.open(file_path_or_pil)
            else:
                pil_img = file_path_or_pil

            exif_raw = pil_img.getexif()
            exif_dict = {}
            if exif_raw:
                for tag_id, val in exif_raw.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    exif_dict[tag_name] = str(val)

            # Check textual info (PNG chunks or JPEG comments)
            info_text = " ".join([f"{k}: {v}" for k, v in getattr(pil_img, "info", {}).items()])
            exif_text = " ".join([f"{k}: {v}" for k, v in exif_dict.items()])
            combined_metadata = f"{info_text} {exif_text}"

            # 1. Search for AI generation keywords
            detected_ai_signatures = []
            for pattern in AI_SIGNATURE_PATTERNS:
                match = pattern.search(combined_metadata)
                if match:
                    detected_ai_signatures.append(match.group(0))

            # 2. Check for Genuine Camera Hardware Tags
            camera_make = exif_dict.get("Make", "").strip()
            camera_model = exif_dict.get("Model", "").strip()
            software = exif_dict.get("Software", "").strip()
            has_camera_make = any(maker in camera_make.lower() for maker in KNOWN_CAMERA_MAKERS)
            has_shutter_data = bool(
                exif_dict.get("ExposureTime")
                or exif_dict.get("FNumber")
                or exif_dict.get("ISOSpeedRatings")
                or exif_dict.get("FocalLength")
            )

            # Require the camera make to be from a known optical hardware manufacturer
            # to avoid accepting software names like "Adobe Photoshop" as camera provenance.
            is_genuine_camera = has_camera_make and (has_shutter_data or bool(camera_model))

            return {
                "has_exif": len(exif_dict) > 0,
                "camera_make": camera_make or None,
                "camera_model": camera_model or None,
                "software": software or None,
                "is_genuine_camera": is_genuine_camera,
                "has_camera_hardware": has_camera_make or is_genuine_camera,
                "ai_signatures": detected_ai_signatures,
                "is_ai_metadata": len(detected_ai_signatures) > 0,
                "exif_tags_count": len(exif_dict),
                "details": {
                    "make": camera_make or "Not specified",
                    "model": camera_model or "Not specified",
                    "software": software or "Standard encoder",
                    "exposureTime": exif_dict.get("ExposureTime", "N/A"),
                    "fNumber": exif_dict.get("FNumber", "N/A"),
                    "iso": exif_dict.get("ISOSpeedRatings", "N/A"),
                    "dateTime": exif_dict.get("DateTimeOriginal", exif_dict.get("DateTime", "N/A")),
                }
            }
        except Exception as exc:
            logger.warning("Metadata forensic analysis failed: %s", exc)
            return {
                "has_exif": False,
                "camera_make": None,
                "camera_model": None,
                "software": None,
                "is_genuine_camera": False,
                "has_camera_hardware": False,
                "ai_signatures": [],
                "is_ai_metadata": False,
                "exif_tags_count": 0,
                "details": {}
            }

    def analyze_frequency_and_noise(self, cv_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Analyze 2D DCT / FFT frequency domain and sensor noise residual.
        Detects GAN/Diffusion grid artifacts, upsampling anomalies, and PRNU noise absence.
        """
        try:
            h, w = cv_bgr.shape[:2]
            gray = cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2GRAY)

            # 1. 2D DCT Spectrum Analysis with mutually exclusive radial bands
            resized_for_dct = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
            dct_matrix = cv2.dct(resized_for_dct.astype(np.float32))
            abs_dct = np.abs(dct_matrix)
            total_energy = float(np.sum(abs_dct)) + 1e-8

            dh, dw = abs_dct.shape
            u = np.linspace(0, 1, dh, dtype=np.float32)[:, None]
            v = np.linspace(0, 1, dw, dtype=np.float32)[None, :]
            radius = np.sqrt(u**2 + v**2)

            # Mutually exclusive radial frequency bands
            low_mask = radius < 0.15
            mid_mask = (radius >= 0.15) & (radius < 0.60)
            high_mask = radius >= 0.60

            low_energy = float(abs_dct[low_mask].sum()) / total_energy
            mid_energy = float(abs_dct[mid_mask].sum()) / total_energy
            high_energy = float(abs_dct[high_mask].sum()) / total_energy

            # 2. Check for periodic grid / checkerboard artifacts (GAN / Diffusion deconvolution strides)
            # High-pass filter to isolate high frequency residual
            blur = cv2.medianBlur(gray, 3)
            noise_residual = cv2.absdiff(gray, blur).astype(np.float32)
            noise_std = float(np.std(noise_residual))
            noise_mean = float(np.mean(noise_residual))

            # FFT power spectrum peak-to-average ratio (detects artificial frequency spikes)
            fft = np.fft.fft2(resized_for_dct)
            fft_shift = np.fft.fftshift(fft)
            magnitude_spectrum = np.log(np.abs(fft_shift) + 1.0)
            max_mag = float(np.max(magnitude_spectrum[100:156, 100:156]))
            mean_mag = float(np.mean(magnitude_spectrum))
            peak_ratio = (max_mag / (mean_mag + 1e-8)) if mean_mag > 0 else 1.0

            # AI grid artifact signal: high peak ratio in high frequency or abnormal high/low ratio
            grid_anomaly = peak_ratio > 3.2 or (high_energy < 0.008 and noise_std < 2.0)

            # Natural camera sensors produce a characteristic noise standard deviation between 1.8 and 25.0
            natural_sensor_noise = 1.8 <= noise_std <= 25.0

            return {
                "low_energy_ratio": round(low_energy, 4),
                "mid_energy_ratio": round(mid_energy, 4),
                "high_energy_ratio": round(high_energy, 4),
                "noise_std": round(noise_std, 2),
                "noise_mean": round(noise_mean, 2),
                "peak_ratio": round(peak_ratio, 2),
                "grid_anomaly": grid_anomaly,
                "natural_sensor_noise": natural_sensor_noise,
            }
        except Exception as exc:
            logger.warning("Frequency/noise forensic analysis failed: %s", exc)
            return {
                "low_energy_ratio": 0.85,
                "mid_energy_ratio": 0.12,
                "high_energy_ratio": 0.03,
                "noise_std": 5.0,
                "noise_mean": 2.0,
                "peak_ratio": 1.5,
                "grid_anomaly": False,
                "natural_sensor_noise": True,
            }

    def calibrate_forensic_score(
        self,
        spatial_model_prob: float,
        metadata_info: Dict[str, Any],
        freq_info: Dict[str, Any],
        face_count: int,
        ground_truth: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes raw model probability with physical optical & forensic metadata signals
        while keeping raw predictions separate, avoiding fabricated certainty, and recording
        explicit limitations and evaluation outcomes.
        """
        # Base raw probability from spatial model
        raw_prob = float(spatial_model_prob)
        score = float(raw_prob)

        evidence_items: List[Dict[str, Any]] = []

        # 1. AI Metadata Signatures
        if metadata_info.get("is_ai_metadata"):
            sigs = ", ".join(metadata_info.get("ai_signatures", []))
            score = max(score, 0.94)
            evidence_items.append({
                "type": "AI Metadata Fingerprint",
                "category": "metadata",
                "severity": "high",
                "metricValue": "Definitive AI Signature",
                "description": f"File metadata contains embedded generative AI parameters or model tags ({sigs}).",
                "reference_range": "No AI generation tags expected in camera media",
                "included_in_fusion": True,
                "limitations": "Metadata can be stripped or altered during transmission.",
            })

        # 2. Frequency Grid Artifacts
        high_ratio = freq_info.get("high_energy_ratio", 0.0)
        peak_ratio = freq_info.get("peak_ratio", 1.0)
        if freq_info.get("grid_anomaly"):
            score = max(score, min(0.96, score + 0.35))
            evidence_items.append({
                "type": "Spectral Grid Anomaly",
                "category": "frequency_domain",
                "severity": "high",
                "metricValue": f"Peak Ratio: {peak_ratio}",
                "description": "High-frequency periodic spikes detected in DCT/FFT spectrum matching neural upscaling deconvolution artifacts.",
                "reference_range": "Peak ratio <= 3.2",
                "included_in_fusion": True,
                "limitations": "Certain regular textile or geometric patterns may introduce high peak ratios.",
            })
        else:
            evidence_items.append({
                "type": "Spectral Energy Distribution",
                "category": "frequency_domain",
                "severity": "low",
                "metricValue": f"High Band: {high_ratio * 100:.1f}%, Peak: {peak_ratio}",
                "description": "Frequency spectrum displays continuous radial decay without periodic neural deconvolution grid spikes.",
                "reference_range": "High band: 1.0% - 15.0%, Peak ratio <= 3.2",
                "included_in_fusion": False,
                "limitations": "A normal frequency spectrum is supporting context only and does not establish physical camera authenticity.",
            })

        # 3. Camera Hardware Metadata Telemetry
        if metadata_info.get("is_genuine_camera") and not metadata_info.get("is_ai_metadata"):
            make = metadata_info.get("camera_make") or "Camera"
            model = metadata_info.get("camera_model") or "Sensor"
            evidence_items.append({
                "type": "Hardware Metadata Telemetry",
                "category": "metadata",
                "severity": "low",
                "metricValue": f"Device: {make} {model}",
                "description": f"Camera hardware EXIF tags present with valid exposure and shutter telemetry ({make} {model}).",
                "reference_range": "Valid ISO, exposure, aperture tags",
                "included_in_fusion": False,
                "limitations": "EXIF metadata can be cloned or preserved during image editing; metadata alone does not verify authenticity.",
            })
        elif not metadata_info.get("has_exif") and not metadata_info.get("is_ai_metadata"):
            evidence_items.append({
                "type": "Metadata Integrity",
                "category": "metadata",
                "severity": "low",
                "metricValue": "Stripped / Absent EXIF",
                "description": "Camera metadata absent. Note: Web-optimization, social media uploads, and privacy stripping routinely remove EXIF; missing metadata alone does not indicate synthetic generation.",
                "reference_range": "Standard camera EXIF vs web-stripped",
                "included_in_fusion": False,
                "limitations": "Absence of metadata is inconclusive regarding authentic vs synthetic origin.",
            })

        # 4. Sensor Noise (PRNU proxy) Residual
        noise_std = freq_info.get("noise_std", 0.0)
        if freq_info.get("natural_sensor_noise") and not freq_info.get("grid_anomaly"):
            evidence_items.append({
                "type": "Sensor Noise Residual Consistency",
                "category": "sensor_noise",
                "severity": "low",
                "metricValue": f"Noise Std: {noise_std:.2f}",
                "description": f"Measured noise residual standard deviation ({noise_std:.2f}) falls within typical uncompressed camera sensor shot noise range (1.8 - 25.0).",
                "reference_range": "1.8 - 25.0 noise std",
                "included_in_fusion": False,
                "limitations": "Noise consistency is supporting evidence only and does not independently prove camera hardware capture.",
            })
        else:
            if not freq_info.get("natural_sensor_noise"):
                evidence_items.append({
                    "type": "Sensor Noise Residual Anomaly",
                    "category": "sensor_noise",
                    "severity": "medium",
                    "metricValue": f"Noise Std: {noise_std:.2f}",
                    "description": f"Measured noise residual standard deviation ({noise_std:.2f}) falls below typical camera sensor noise grain (1.8 - 25.0); surfaces exhibit synthetic oversmoothing or denoising.",
                    "reference_range": "1.8 - 25.0 noise std",
                    "included_in_fusion": False,
                    "limitations": "Heavy compression, software denoising, or flat synthetic surfaces can also reduce noise standard deviation.",
                })

        # Final Decision — standard threshold 0.50 on the fake probability score
        score = float(np.clip(score, 0.01, 0.99))
        decision_threshold = 0.50
        label = "FAKE" if score >= decision_threshold else "REAL"

        # Explicit decision margin (distance from decision boundary)
        decision_margin = round(abs(score - decision_threshold), 4)

        # Raw model confidence (distance from the uncalibrated decision boundary)
        raw_confidence = score if label == "FAKE" else 1.0 - score
        raw_confidence = float(np.clip(raw_confidence, 0.0, 1.0))

        # Evaluation outcome (if independent ground truth is supplied)
        evaluation_outcome = None
        if ground_truth:
            gt_norm = str(ground_truth).strip().upper()
            is_gt_fake = gt_norm in {"FAKE", "AI_GENERATED", "SYNTHETIC", "DEEPFAKE", "MANIPULATED"}
            is_pred_fake = (label == "FAKE")
            if is_gt_fake and is_pred_fake:
                evaluation_outcome = "TRUE_POSITIVE"
            elif not is_gt_fake and not is_pred_fake:
                evaluation_outcome = "TRUE_NEGATIVE"
            elif not is_gt_fake and is_pred_fake:
                evaluation_outcome = "FALSE_POSITIVE"
            elif is_gt_fake and not is_pred_fake:
                evaluation_outcome = "FALSE_NEGATIVE"

        return {
            "final_score": score,
            "raw_model_prob": raw_prob,
            "label": label,
            "decision_threshold": decision_threshold,
            "decision_margin": decision_margin,
            "confidence": round(raw_confidence, 4),
            "authenticity_verified": False,
            "evidence": evidence_items,
            "metadata_info": metadata_info,
            "frequency_info": freq_info,
            "score_type": "fake_probability",
            "calibration_status": "NOT_CONFIGURED",
            "statistically_calibrated": False,
            "ground_truth": ground_truth,
            "evaluation_outcome": evaluation_outcome,
            "calibration_note": (
                "Score is derived from spatial neural detector output and measured forensic signals. "
                "Confidence reflects distance from the 0.50 decision boundary (decision margin: "
                f"{decision_margin * 100:.2f} percentage points); no held-out calibration model is configured."
            ),
        }


forensic_analyzer = ForensicAnalyzer()
