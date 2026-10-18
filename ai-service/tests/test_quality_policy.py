import os
import sys
import unittest

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from preprocessing.image_preprocessor import ImagePreprocessor


class TestQualityPolicy(unittest.TestCase):
    def test_quality_warning_is_informational_only(self):
        preprocessor = ImagePreprocessor(target_size=(224, 224), max_dimension=1000)
        quality_path = os.path.join("scratch", "quality_policy_test.jpg")
        os.makedirs("scratch", exist_ok=True)

        dark_image = Image.new("RGB", (64, 64), color=(10, 10, 10))
        dark_image.save(quality_path)

        quality = preprocessor.assess_image_quality(quality_path)

        self.assertEqual(quality["status"], "POOR")
        self.assertIn("Low-quality media may reduce detection reliability.", quality["warning"])
        self.assertNotIn("fake", quality["warning"].lower())
        self.assertNotIn("real", quality["warning"].lower())


if __name__ == "__main__":
    unittest.main()
