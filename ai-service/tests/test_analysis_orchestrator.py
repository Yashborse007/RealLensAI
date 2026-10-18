import tempfile
import unittest
from pathlib import Path

from PIL import Image

from services.analysis_orchestrator import AnalysisOrchestrator


class TestAnalysisOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _frequency_result(_image):
        return {
            "frequency_score": 0.74,
            "frequency_summary": {"high_frequency_ratio": 0.2},
        }

    def test_image_result_preserves_supporting_score_and_fusion_explanation(self):
        image_path = self.temp_path / "sample.png"
        Image.new("RGB", (32, 32), (100, 120, 140)).save(image_path)

        orchestrator = AnalysisOrchestrator(
            image_runner=lambda _: {
                "success": True,
                "status": "COMPLETED",
                "prediction": {"label": "FAKE", "confidence": 0.81},
                "fake_probability": 0.81,
                "model_version": "aide-test",
                "preprocessing_version": "preprocess-test",
                "faces_detected": 1,
                "face_results": [{"fake_probability": 0.81}],
                "quality": {"status": "GOOD", "quality_score": 0.9},
                "input_quality": {
                    "status": "GOOD",
                    "quality_score": 0.9,
                    "details": {"resolution": "32x32"},
                },
                "evidence": {"fallback_crop_used": False},
            },
            frequency_runner=self._frequency_result,
        )

        result = orchestrator.analyze(str(image_path))

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["prediction"], {"label": "FAKE", "confidence": 0.81})
        self.assertEqual(result["modalities"]["spatial"]["score"], 0.81)
        self.assertTrue(result["modalities"]["spatial"]["included_in_fusion"])
        self.assertEqual(result["modalities"]["frequency"]["score"], 0.74)
        self.assertFalse(result["modalities"]["frequency"]["included_in_fusion"])
        self.assertEqual(
            result["modalities"]["frequency"]["score_type"],
            "frequency_support_metric",
        )
        self.assertEqual(result["processing"]["fusion"]["available_modalities"], ["spatial"])
        self.assertFalse(
            result["processing"]["fusion"]["confidence_calibration"]["statistically_calibrated"]
        )
        self.assertEqual(result["model_versions"]["spatial"], "aide-test")
        self.assertEqual(result["model_versions"]["frequency"], "DCT-frequency-v1")
        self.assertTrue(result["evidence"])

    def test_audio_heuristic_score_is_retained_but_not_used_as_final_evidence(self):
        audio_path = self.temp_path / "sample.wav"
        audio_path.write_bytes(b"test")
        orchestrator = AnalysisOrchestrator(
            audio_runner=lambda _: {
                "success": True,
                "audio_available": True,
                "prediction": {"label": "FAKE", "confidence": 0.8},
                "label": "FAKE",
                "confidence": 0.8,
                "model": "mel-mfcc-supporting-evidence",
                "duration": 1.0,
                "sample_rate": 16000,
            },
        )

        result = orchestrator.analyze(str(audio_path))

        self.assertEqual(result["prediction"]["label"], "UNCERTAIN")
        self.assertEqual(result["modalities"]["audio"]["score"], 0.8)
        self.assertEqual(result["modalities"]["audio"]["status"], "SUPPORTING_ONLY")
        self.assertFalse(result["modalities"]["audio"]["included_in_fusion"])
        self.assertEqual(result["processing"]["fusion"]["available_modalities"], [])
        self.assertEqual(result["quality"]["status"], "NOT_ASSESSED")

    def test_module_failure_is_reported_and_does_not_disappear(self):
        image_path = self.temp_path / "sample.png"
        Image.new("RGB", (32, 32), (100, 120, 140)).save(image_path)

        def fail_spatial(_):
            raise RuntimeError("detector unavailable")

        orchestrator = AnalysisOrchestrator(
            image_runner=fail_spatial,
            frequency_runner=self._frequency_result,
        )

        result = orchestrator.analyze(str(image_path))

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["prediction"]["label"], "UNCERTAIN")
        self.assertEqual(result["processing"]["modules"]["spatial"]["status"], "FAILED")
        self.assertEqual(result["modalities"]["spatial"]["status"], "FAILED_ANALYSIS")
        self.assertEqual(result["modalities"]["frequency"]["score"], 0.74)
        self.assertIn("spatial", result["processing"]["unavailable_modalities"])

    def test_media_type_is_inferred_and_mismatch_is_rejected(self):
        orchestrator = AnalysisOrchestrator()

        self.assertEqual(orchestrator.determine_media_type(str(Path("clip.mp4"))), "video")
        with self.assertRaisesRegex(ValueError, "does not match"):
            orchestrator.determine_media_type("clip.mp4", media_type="image")
