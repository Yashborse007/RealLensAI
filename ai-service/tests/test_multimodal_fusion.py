import unittest

from ml.inference.multimodal_inference import fuse_multimodal_scores


class TestMultimodalFusion(unittest.TestCase):
    def test_audio_unavailable_is_ignored_in_denominator(self):
        result = fuse_multimodal_scores(
            spatial_score=0.82,
            temporal_score=0.79,
            frequency_score=0.58,
            audio_score=None,
            quality_score=0.9,
            modality_availability={
                "spatial": True,
                "temporal": True,
                "frequency": True,
                "audio": False,
            },
            weights={"spatial": 0.45, "temporal": 0.35, "frequency": 0.20, "audio": 0.10},
        )

        self.assertEqual(result["final_label"], "FAKE")
        self.assertIn("audio", result["evidence"])
        self.assertFalse(result["evidence"]["audio"]["available"])
        self.assertNotIn("audio", result["available_modalities"])
        self.assertEqual(result["quality"]["status"], "SUFFICIENT")

    def test_frequency_failure_does_not_stop_fusion(self):
        result = fuse_multimodal_scores(
            spatial_score=0.73,
            temporal_score=0.66,
            frequency_score=None,
            audio_score=0.42,
            quality_score=0.8,
            modality_availability={
                "spatial": True,
                "temporal": True,
                "frequency": False,
                "audio": True,
            },
            weights={"spatial": 0.5, "temporal": 0.3, "frequency": 0.2, "audio": 0.2},
        )

        self.assertIn("frequency", result["evidence"])
        self.assertFalse(result["evidence"]["frequency"]["available"])
        self.assertNotIn("frequency", result["available_modalities"])
        self.assertIn("spatial", result["available_modalities"])
        self.assertIn("temporal", result["available_modalities"])
        self.assertIn("audio", result["available_modalities"])

    def test_low_quality_input_is_not_treated_as_fake(self):
        result = fuse_multimodal_scores(
            spatial_score=0.91,
            temporal_score=0.89,
            frequency_score=0.75,
            audio_score=0.7,
            quality_score=0.2,
            modality_availability={
                "spatial": True,
                "temporal": True,
                "frequency": True,
                "audio": True,
            },
            weights={"spatial": 0.4, "temporal": 0.3, "frequency": 0.2, "audio": 0.1},
        )

        self.assertEqual(result["quality"]["status"], "LOW_QUALITY_INPUT")
        self.assertEqual(result["final_label"], "REAL")
        self.assertEqual(result["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
