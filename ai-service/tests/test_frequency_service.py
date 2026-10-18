import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.frequency_service import FrequencyAnalysisService


class TestFrequencyService(unittest.TestCase):
    def setUp(self):
        self.service = FrequencyAnalysisService()
        self.base_image = np.zeros((224, 224, 3), dtype=np.uint8)
        self.base_image[:, :, 0] = 80
        self.base_image[:, :, 1] = 140
        self.base_image[:, :, 2] = 190

        self.face = np.zeros((128, 128, 3), dtype=np.uint8)
        self.face[30:90, 30:90] = 200
        self.face[50:80, 50:80] = 40

    def test_frequency_service_returns_supporting_evidence(self):
        result = self.service.analyze_image(self.face)

        self.assertIn("frequency_score", result)
        self.assertIn("frequency_summary", result)
        self.assertIn("frequency_visualization", result)
        self.assertTrue(0.0 <= float(result["frequency_score"]) <= 1.0)
        self.assertEqual(result["frequency_summary"]["evidence_type"], "supporting_evidence")
        self.assertIn("low_frequency_ratio", result["frequency_summary"])
        self.assertIn("high_frequency_ratio", result["frequency_summary"])

    def test_robustness_summary_tracks_preprocessing_changes(self):
        result = self.service.evaluate_preprocessing_robustness(self.face)

        self.assertIn("baseline", result)
        self.assertIn("test_cases", result)
        self.assertTrue(len(result["test_cases"]) >= 4)
        self.assertIn("jpeg_compression", result["test_cases"][0]["condition"])
        self.assertIn("delta", result["test_cases"][0])


if __name__ == "__main__":
    unittest.main()
