import os
import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Tuple, Union
from utils.logging_utils import logger

class FaceDetector:
    """
    Modular OpenCV Haar Cascade / DNN Face Detector.
    Designed for plug-and-play replacement with MTCNN / RetinaFace in future iterations.
    """
    def __init__(self, cascade_path: str = None):
        self.cascade_path = cascade_path
        self.face_cascade = None
        self.yunet_detector = None

        # 1. Try modern YuNet deep-learning detector
        yunet_path = os.path.join(os.path.dirname(__file__), 'face_detection_yunet.onnx')
        if os.path.exists(yunet_path) and hasattr(cv2, "FaceDetectorYN_create"):
            try:
                self.yunet_detector = cv2.FaceDetectorYN_create(yunet_path, "", (300, 300), score_threshold=0.6, nms_threshold=0.3)
                logger.info("Modular FaceDetector initialized using YuNet deep learning detector.")
                return
            except Exception as exc:
                logger.warning(f"YuNet initialization failed: {exc}")

        # 2. Fallback to Haar Cascade
        if hasattr(cv2, "CascadeClassifier"):
            candidates = []
            if cascade_path:
                candidates.append(cascade_path)
            candidates.append(os.path.join(os.path.dirname(__file__), 'haarcascade_frontalface_default.xml'))
            cascade_base = getattr(cv2, "data", None)
            if cascade_base is not None and hasattr(cascade_base, "haarcascades"):
                candidates.append(os.path.join(cascade_base.haarcascades, 'haarcascade_frontalface_default.xml'))
            if os.environ.get('OPENCV_HAAR_FACE_CASCADE'):
                candidates.append(os.environ.get('OPENCV_HAAR_FACE_CASCADE'))

            for candidate in candidates:
                if candidate and os.path.exists(candidate):
                    try:
                        self.face_cascade = cv2.CascadeClassifier(candidate)
                        self.cascade_path = candidate
                        logger.info(f"Modular FaceDetector initialized using cascade: {self.cascade_path}")
                        return
                    except Exception as exc:
                        logger.warning(f"Failed to load OpenCV Haar cascade from {candidate}: {exc}")

        logger.info("Modular FaceDetector initialized with fallback crop strategy.")

    def _to_cv2_image(self, image: Union[np.ndarray, Image.Image]) -> np.ndarray:
        """
        Helper converting PIL Image or NumPy array into standard BGR OpenCV NumPy array.
        """
        if isinstance(image, Image.Image):
            rgb = np.array(image.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        elif isinstance(image, np.ndarray):
            # If RGB (3 channels), copy to avoid mutating original
            return image.copy()
        else:
            raise ValueError("Unsupported image type. Input must be a PIL Image or NumPy ndarray.")

    def detect_faces(self, image: Union[np.ndarray, Image.Image]) -> List[Dict[str, Any]]:
        """
        Detect faces in image.
        Returns list of detection dicts: [{'x': x, 'y': y, 'w': w, 'h': h, 'confidence': float}, ...]
        """
        cv_img = self._to_cv2_image(image)
        try:
            if cv_img is None or cv_img.size == 0:
                logger.warning("Empty or null image provided to detect_faces.")
                return []

            h_img, w_img = cv_img.shape[:2]

            # 1. Prefer YuNet detector
            if self.yunet_detector is not None:
                try:
                    self.yunet_detector.setInputSize((int(w_img), int(h_img)))
                    ret, faces = self.yunet_detector.detect(cv_img)
                    if faces is not None and len(faces) > 0:
                        detections = []
                        for face in faces:
                            fx, fy, fw, fh = face[:4]
                            conf = float(face[-1]) if len(face) > 4 else 0.95
                            detections.append({
                                "x": max(0, int(fx)),
                                "y": max(0, int(fy)),
                                "w": min(int(w_img), int(fw)),
                                "h": min(int(h_img), int(fh)),
                                "confidence": round(conf, 4),
                            })
                        logger.info(f"FaceDetector.detect_faces (YuNet) found {len(detections)} face(s).")
                        return detections
                except Exception as y_err:
                    logger.warning(f"YuNet detect error: {y_err}")

            # 2. Fallback to Haar Cascade
            if self.face_cascade is not None:
                gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )

                detections = []
                for (x, y, w, h) in faces:
                    detections.append({
                        "x": int(x),
                        "y": int(y),
                        "w": int(w),
                        "h": int(h),
                        "confidence": 0.95,
                    })

                logger.info(f"FaceDetector.detect_faces (Haar) found {len(detections)} face(s).")
                return detections

            return []
        except Exception as e:
            logger.error(f"Error during FaceDetector.detect_faces: {str(e)}")
            return []

    def extract_face_crops(
        self,
        image: Union[np.ndarray, Image.Image],
        detections: List[Dict[str, Any]],
        target_size: Tuple[int, int] = (224, 224),
        margin_ratio: float = 0.2
    ) -> List[np.ndarray]:
        """
        Extract and crop faces from input image based on detection bounding boxes.
        Adds proportional boundary padding margin and resizes to target_size.
        """
        crops = []
        cv_img = self._to_cv2_image(image)
        if cv_img is None or cv_img.size == 0 or not detections:
            return crops

        h_img, w_img = cv_img.shape[:2]

        for det in detections:
            x, y, w, h = det["x"], det["y"], det["w"], det["h"]
            
            # Calculate boundary expansion padding
            margin_w = int(w * margin_ratio)
            margin_h = int(h * margin_ratio)
            
            x1 = max(0, x - margin_w)
            y1 = max(0, y - margin_h)
            x2 = min(w_img, x + w + margin_w)
            y2 = min(h_img, y + h + margin_h)

            crop = cv_img[y1:y2, x1:x2]
            
            if crop.size > 0:
                resized_crop = cv2.resize(crop, target_size, interpolation=cv2.INTER_AREA)
                crops.append(resized_crop)

        logger.info(f"FaceDetector.extract_face_crops generated {len(crops)} crop(s) of size {target_size}.")
        return crops

    def draw_detections(
        self,
        image: Union[np.ndarray, Image.Image],
        detections: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Draw bounding boxes and face labels on a copy of the input image.
        Original input image is strictly preserved (never mutated).
        """
        annotated = self._to_cv2_image(image)
        
        for idx, det in enumerate(detections):
            x, y, w, h = det["x"], det["y"], det["w"], det["h"]
            # Draw bounding box (Cyan)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 240, 0), 2)
            # Draw label banner
            label = f"Face #{idx + 1}"
            cv2.putText(
                annotated,
                label,
                (x, max(15, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 240, 0),
                2,
                cv2.LINE_AA
            )

        return annotated

face_detector = FaceDetector()
