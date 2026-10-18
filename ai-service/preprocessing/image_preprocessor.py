import os
import time
import cv2
import numpy as np
import torch
from PIL import Image, ImageOps, UnidentifiedImageError
from typing import Dict, Any, Tuple, List, Optional, Union
from fastapi import HTTPException
from preprocessing.face_detector import face_detector
from utils.logging_utils import logger

class ImagePreprocessor:
    """
    Image Preprocessing Pipeline.
    Validates, loads, detects faces, crops, resizes, normalizes, and prepares PyTorch tensors.
    """
    PREPROCESSING_VERSION = "image-preprocess-v1.0"

    def __init__(self, target_size: Tuple[int, int] = (224, 224), max_dimension: int = 4096):
        self.target_size = target_size
        self.max_dimension = max_dimension
        # Standard ImageNet Normalization Parameters
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def load_and_validate_image(self, file_path_or_bytes: Union[str, bytes]) -> Image.Image:
        """
        Loads image safely from file path or bytes, handles EXIF orientation, 
        downscales ultra-large images, and raises errors for corrupted formats.
        """
        try:
            if isinstance(file_path_or_bytes, str):
                if not os.path.exists(file_path_or_bytes):
                    raise HTTPException(status_code=404, detail=f"Image file not found at path: {file_path_or_bytes}")
                pil_img = Image.open(file_path_or_bytes)
            elif isinstance(file_path_or_bytes, bytes):
                import io
                pil_img = Image.open(io.BytesIO(file_path_or_bytes))
            else:
                raise ValueError("Input must be a file path string or bytes buffer.")

            # Verify image file integrity
            pil_img.verify()
            
            # Re-open after verify() as verify() invalidates the image object
            if isinstance(file_path_or_bytes, str):
                pil_img = Image.open(file_path_or_bytes)
            else:
                import io
                pil_img = Image.open(io.BytesIO(file_path_or_bytes))

            # Auto-rotate based on EXIF tag if present
            pil_img = ImageOps.exif_transpose(pil_img)
            
            # Convert RGBA/Palette images to RGB
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            # Handle very large images: downscale if max dimension exceeds max_dimension
            w, h = pil_img.size
            if max(w, h) > self.max_dimension:
                scale = self.max_dimension / float(max(w, h))
                new_w = int(w * scale)
                new_h = int(h * scale)
                pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                logger.info(f"Ultra-large image ({w}x{h}) downscaled to ({new_w}x{new_h}).")

            return pil_img
        except UnidentifiedImageError:
            logger.error("Failed to load image: Corrupted or unidentified image format.")
            raise HTTPException(status_code=400, detail="Corrupted or invalid image file. Unable to decode pixels.")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.error(f"Error loading image: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to read image buffer: {str(e)}")

    def normalize_crop_to_tensor(self, crop_bgr: np.ndarray) -> torch.Tensor:
        """
        Converts BGR NumPy array crop to RGB normalized PyTorch Tensor (3, H, W).
        """
        # Convert BGR to RGB float32 in range [0.0, 1.0]
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        
        # Apply standard ImageNet mean & std normalization
        normalized = (rgb - self.mean) / self.std
        
        # Transpose from (H, W, C) to (C, H, W) PyTorch layout
        tensor = torch.from_numpy(normalized.transpose(2, 0, 1)).float()
        return tensor

    def assess_image_quality(
        self,
        file_path_or_bytes: Union[str, bytes],
        face_count: int = 0,
        bounding_boxes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Measure practical image-quality signals without using quality as a fake signal."""
        pil_img = self.load_and_validate_image(file_path_or_bytes)
        gray = np.array(pil_img.convert("L"), dtype=np.float32)
        height, width = gray.shape
        brightness = float(np.mean(gray))
        blur_metric = float(cv2.Laplacian(gray.astype(np.uint8), cv2.CV_64F).var())
        noise_estimate = float(np.std(gray))

        estimated_face_size = 0.0
        if bounding_boxes:
            estimated_face_size = max(
                (
                    float(box.get("w", 0) or 0) * float(box.get("h", 0) or 0)
                    for box in bounding_boxes
                ),
                default=0.0,
            )

        image_area = max(width * height, 1)
        face_ratio = (estimated_face_size / image_area) if image_area > 0 else 0.0
        resolution_score = 1.0 if max(width, height) >= 720 else 0.7 if max(width, height) >= 480 else 0.45
        brightness_score = 1.0 if 60 <= brightness <= 200 else 0.6 if 30 <= brightness <= 220 else 0.3
        blur_score = 1.0 if blur_metric >= 80 else 0.7 if blur_metric >= 40 else 0.3
        noise_score = 1.0 if noise_estimate <= 35 else 0.7 if noise_estimate <= 60 else 0.4
        face_score = 1.0 if face_count == 0 else (1.0 if face_ratio >= 0.05 else 0.7 if face_ratio >= 0.02 else 0.4)

        quality_score = float(np.clip((resolution_score * 0.25) + (brightness_score * 0.2) + (blur_score * 0.25) + (noise_score * 0.15) + (face_score * 0.15), 0.0, 1.0))

        # Strongly penalize nearly invisible or textureless media so weak inputs are marked as low quality
        # without ever using quality as a fake-positive signal.
        if brightness < 20 or blur_metric < 10 or noise_estimate < 5:
            quality_score = min(quality_score, 0.35)

        if quality_score >= 0.75:
            status = "GOOD"
        elif quality_score >= 0.45:
            status = "FAIR"
        else:
            status = "POOR"

        file_size = None
        if isinstance(file_path_or_bytes, str) and os.path.exists(file_path_or_bytes):
            file_size = os.path.getsize(file_path_or_bytes)
        elif isinstance(file_path_or_bytes, (bytes, bytearray)):
            file_size = len(file_path_or_bytes)

        compression_indicator = "No obvious JPEG artifact pattern detected."
        if file_size and image_area > 0:
            bytes_per_pixel = file_size / image_area
            if bytes_per_pixel < 0.003:
                compression_indicator = "Strong compression pattern detected; image detail may be degraded."
            elif bytes_per_pixel < 0.01:
                compression_indicator = "Moderate compression present in the encoded image."
            else:
                compression_indicator = "Fine detail preservation appears acceptable for this file size."

        details = {
            "resolution": f"{width}x{height}",
            "brightness": f"{brightness:.1f} / 255",
            "blurEstimate": f"{blur_metric:.1f}",
            "noiseEstimate": f"{noise_estimate:.1f}",
            "compressionIndicators": compression_indicator,
            "faceSize": f"{estimated_face_size:.0f}px" if estimated_face_size > 0 else "N/A",
            "facesDetected": int(face_count),
            "qualityScore": round(quality_score, 3),
        }

        warning = None
        if status == "POOR":
            warning = "Low-quality media may reduce detection reliability."

        return {
            "status": status,
            "quality_score": round(quality_score, 3),
            "details": details,
            "warning": warning,
        }

    def process(self, file_path_or_bytes: Union[str, bytes]) -> Dict[str, Any]:
        """
        Full Image Preprocessing Execution:
        Load -> Detect -> Crop -> Resize -> Normalize -> Prepare Batch Tensor.
        """
        preprocessing_started_at = time.perf_counter()

        # 1. Load and validate image (Preserves original file/data)
        original_pil = self.load_and_validate_image(file_path_or_bytes)
        
        # Convert to OpenCV BGR numpy array copy for face detector
        np_img = np.array(original_pil)
        cv_bgr = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

        # 2. Detect faces
        face_detection_started_at = time.perf_counter()
        detections = face_detector.detect_faces(cv_bgr)
        face_detection_ms = (time.perf_counter() - face_detection_started_at) * 1000
        face_count = len(detections)

        # 3. Crop faces or handle fallback if 0 faces found
        crops_bgr = []
        if face_count > 0:
            crops_bgr = face_detector.extract_face_crops(
                cv_bgr,
                detections,
                target_size=self.target_size
            )
        else:
            # Multi-patch full image sampling for non-face / scene / object media
            logger.info("No faces detected in image. Applying multi-patch whole-image sampling.")
            h, w = cv_bgr.shape[:2]
            
            # Patch 1: Global resized image
            global_resized = cv2.resize(cv_bgr, self.target_size, interpolation=cv2.INTER_AREA)
            crops_bgr.append(global_resized)

            # Patch 2: Central crop
            crop_dim = min(h, w)
            start_x = (w - crop_dim) // 2
            start_y = (h - crop_dim) // 2
            central_crop = cv_bgr[start_y:start_y + crop_dim, start_x:start_x + crop_dim]
            crops_bgr.append(cv2.resize(central_crop, self.target_size, interpolation=cv2.INTER_AREA))

            # Patch 3 & 4: Upper and lower / left and right regions
            if w > h:
                left_crop = cv_bgr[:, :h]
                right_crop = cv_bgr[:, w - h:]
                crops_bgr.append(cv2.resize(left_crop, self.target_size, interpolation=cv2.INTER_AREA))
                crops_bgr.append(cv2.resize(right_crop, self.target_size, interpolation=cv2.INTER_AREA))
            else:
                top_crop = cv_bgr[:w, :]
                bottom_crop = cv_bgr[h - w:, :]
                crops_bgr.append(cv2.resize(top_crop, self.target_size, interpolation=cv2.INTER_AREA))
                crops_bgr.append(cv2.resize(bottom_crop, self.target_size, interpolation=cv2.INTER_AREA))

        # 4. Normalize crops & prepare PyTorch Batch Tensor (N, 3, H, W)
        tensors_list = [self.normalize_crop_to_tensor(c) for c in crops_bgr]
        batch_tensor = torch.stack(tensors_list, dim=0)

        # Format metadata response
        bounding_boxes = [
            {"x": d["x"], "y": d["y"], "w": d["w"], "h": d["h"], "confidence": d["confidence"]}
            for d in detections
        ]

        logger.info(f"ImagePreprocessor finished: face_count={face_count}, batch_tensor_shape={list(batch_tensor.shape)}")

        return {
            "face_count": face_count,
            "bounding_boxes": bounding_boxes,
            "face_crops_count": len(crops_bgr),
            "batch_tensor": batch_tensor,
            "tensor_shape": list(batch_tensor.shape),
            "original_size": list(original_pil.size),
            "cv_bgr": cv_bgr,
            "quality": self.assess_image_quality(file_path_or_bytes, face_count, bounding_boxes),
            "performance": {
                "preprocessing_ms": round((time.perf_counter() - preprocessing_started_at) * 1000, 3),
                "face_detection_ms": round(face_detection_ms, 3),
            },
        }

image_preprocessor = ImagePreprocessor()
