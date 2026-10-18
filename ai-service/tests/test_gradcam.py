import os
import unittest

from PIL import Image
from fastapi.testclient import TestClient

from explainability.gradcam import explain_image_with_gradcam
from main import app


class TestGradCAM(unittest.TestCase):
    def test_explainability_returns_model_evidence_visualization(self):
        image_path = os.path.join("scratch", "gradcam_test.jpg")
        os.makedirs("scratch", exist_ok=True)
        Image.new("RGB", (224, 224), color=(255, 255, 255)).save(image_path)

        result = explain_image_with_gradcam(image_path)

        self.assertIn("heatmap", result)
        self.assertIn("overlay_image", result)
        self.assertIn("target_class", result)
        self.assertIn("prediction_score", result)
        self.assertTrue(os.path.exists(result["evidence_path"]))
        self.assertEqual(result["label"], "Model Evidence Visualization")
        self.assertIn("not guaranteed to represent a causal forensic explanation", result["explanation"].lower())

    def test_image_explain_route_works(self):
        client = TestClient(app)
        image_path = os.path.join("scratch", "gradcam_route_test.jpg")
        Image.new("RGB", (224, 224), color=(120, 150, 200)).save(image_path)

        with open(image_path, "rb") as handle:
            response = client.post(
                "/predict/image/explain",
                files={"file": ("gradcam_route_test.jpg", handle, "image/jpeg")},
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIn("heatmap", payload)
        self.assertIn("overlay_image", payload)
        self.assertIn("target_class", payload)
        self.assertIn("prediction_score", payload)


if __name__ == "__main__":
    unittest.main()
