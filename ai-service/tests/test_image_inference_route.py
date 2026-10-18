import os
import sys
import unittest
from io import BytesIO

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app


class TestImageInferenceRoute(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_predict_image_uses_actual_model_and_returns_metadata(self):
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        image[:, :, 0] = 20
        image[:, :, 1] = 100
        image[:, :, 2] = 180
        buffer = BytesIO()
        Image.fromarray(image, mode="RGB").save(buffer, format="PNG")
        buffer.seek(0)

        response = self.client.post(
            "/predict/image",
            files={"file": ("sample.png", buffer.getvalue(), "image/png")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("prediction", payload)
        self.assertIn(payload["prediction"]["label"], {"REAL", "FAKE"})
        self.assertGreaterEqual(float(payload["prediction"]["confidence"]), 0.0)
        self.assertLessEqual(float(payload["prediction"]["confidence"]), 1.0)
        self.assertIn("processing_time_ms", payload)
        self.assertTrue(payload["model_version"])
        self.assertTrue(payload["preprocessing_version"])
        self.assertIsInstance(payload["face_results"], list)

    def test_predict_image_no_face_returns_meaningful_status(self):
        image = np.full((96, 96, 3), 128, dtype=np.uint8)
        buffer = BytesIO()
        Image.fromarray(image, mode="RGB").save(buffer, format="PNG")
        buffer.seek(0)

        response = self.client.post(
            "/predict/image",
            files={"file": ("blank.png", buffer.getvalue(), "image/png")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIn("status", payload)
        self.assertTrue("NO_FACE" in payload["status"] or payload["status"] == "COMPLETED")
        self.assertIn("prediction", payload)
        self.assertIn("confidence", payload["prediction"])


if __name__ == "__main__":
    unittest.main()
