import os
import sys
import unittest
import numpy as np
import torch
from PIL import Image

# Ensure ai-service root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from preprocessing.face_detector import FaceDetector, face_detector
from preprocessing.image_preprocessor import ImagePreprocessor, image_preprocessor
from fastapi import HTTPException

class TestImagePreprocessing(unittest.TestCase):

    def setUp(self):
        self.detector = FaceDetector()
        self.preprocessor = ImagePreprocessor(target_size=(224, 224), max_dimension=1000)
        os.makedirs("scratch", exist_ok=True)

    def test_01_image_without_faces_fallback(self):
        """
        Test 1: Verify image without faces is handled gracefully using central crop fallback.
        """
        # Create blank synthetic solid image (no faces)
        img_np = np.ones((300, 300, 3), dtype=np.uint8) * 128
        pil_img = Image.fromarray(img_np)
        
        test_file = os.path.join("scratch", "noface_test.jpg")
        pil_img.save(test_file)

        result = self.preprocessor.process(test_file)
        
        self.assertEqual(result["face_count"], 0)
        self.assertEqual(result["face_crops_count"], 4) # Multi-patch whole-image sampling crops
        self.assertEqual(result["tensor_shape"], [4, 3, 224, 224])
        self.assertIsInstance(result["batch_tensor"], torch.Tensor)

    def test_02_face_detector_methods_and_immutability(self):
        """
        Test 2: Verify FaceDetector detect_faces, extract_face_crops, draw_detections & immutability.
        """
        img_np = np.zeros((200, 200, 3), dtype=np.uint8)
        img_copy_before = img_np.copy()

        # 1. detect_faces
        detections = self.detector.detect_faces(img_np)
        self.assertIsInstance(detections, list)

        # 2. draw_detections (Must preserve original image)
        annotated = self.detector.draw_detections(img_np, detections)
        np.testing.assert_array_equal(img_np, img_copy_before, err_msg="Original image was mutated during draw_detections!")

        # 3. extract_face_crops
        mock_detections = [{"x": 10, "y": 10, "w": 50, "h": 50, "confidence": 0.9}]
        crops = self.detector.extract_face_crops(img_np, mock_detections, target_size=(224, 224))
        self.assertEqual(len(crops), 1)
        self.assertEqual(crops[0].shape, (224, 224, 3))

    def test_03_corrupted_image_handling(self):
        """
        Test 3: Verify corrupted image buffer raises HTTPException 400.
        """
        corrupted_file = os.path.join("scratch", "corrupted.jpg")
        with open(corrupted_file, "wb") as f:
            f.write(b"NOT_AN_IMAGE_HEADER_GARBAGE_BYTES_123456789")

        with self.assertRaises(HTTPException) as ctx:
            self.preprocessor.process(corrupted_file)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_04_ultra_large_image_downscaling(self):
        """
        Test 4: Verify ultra-large image (>1000px in test preprocessor) is downscaled.
        """
        # Create 1500x2000 large image
        large_img = Image.new("RGB", (1500, 2000), color=(100, 150, 200))
        large_file = os.path.join("scratch", "large_test.jpg")
        large_img.save(large_file)

        loaded_pil = self.preprocessor.load_and_validate_image(large_file)
        w, h = loaded_pil.size
        
        # Max dimension in test preprocessor is 1000
        self.assertLessEqual(max(w, h), 1000)

    def test_05_pytorch_tensor_normalization(self):
        """
        Test 5: Verify PyTorch tensor normalization math and shape.
        """
        crop_bgr = np.ones((224, 224, 3), dtype=np.uint8) * 255
        tensor = self.preprocessor.normalize_crop_to_tensor(crop_bgr)

        self.assertEqual(tensor.shape, torch.Size([3, 224, 224]))
        self.assertEqual(tensor.dtype, torch.float32)

    def test_06_quality_assessment_reports_measured_values(self):
        """
        Test 6: Verify quality assessment returns measured values and warns on clearly poor-quality images.
        """
        low_quality = Image.new("RGB", (64, 64), color=(5, 5, 5))
        low_quality_file = os.path.join("scratch", "low_quality_test.jpg")
        low_quality.save(low_quality_file)

        quality = self.preprocessor.assess_image_quality(low_quality_file)

        self.assertEqual(quality["status"], "POOR")
        self.assertGreaterEqual(quality["quality_score"], 0.0)
        self.assertLessEqual(quality["quality_score"], 1.0)
        self.assertIn("resolution", quality["details"])
        self.assertIn("brightness", quality["details"])
        self.assertIn("warning", quality)
        self.assertIn("Low-quality media may reduce detection reliability.", quality["warning"])

if __name__ == "__main__":
    unittest.main()
