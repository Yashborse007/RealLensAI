import os
import sys
import unittest

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app


class TestAudioInferenceRoute(unittest.TestCase):
    def test_predict_audio_returns_prediction_and_metadata(self):
        file_path = os.path.join("scratch", "sample_audio_test.wav")
        os.makedirs("scratch", exist_ok=True)
        sr = 16000
        t = np.linspace(0, 1.0, int(sr), endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 220 * t) + 0.2 * np.sin(2 * np.pi * 330 * t)
        sf.write(file_path, signal.astype(np.float32), sr)

        with open(file_path, "rb") as fh:
            payload = fh.read()

        client = TestClient(app)
        response = client.post(
            "/predict/audio",
            files={"file": ("sample_audio.wav", payload, "audio/wav")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result["success"])
        self.assertIn("prediction", result)
        self.assertIn("label", result["prediction"])
        self.assertIn("confidence", result["prediction"])
        self.assertIn("duration", result)
        self.assertIn("sample_rate", result)
        self.assertIn("processing_time_ms", result)
        self.assertIn("audio_available", result)

    def test_missing_audio_is_not_deepfake_evidence(self):
        client = TestClient(app)
        response = client.post(
            "/predict/audio",
            files={"file": ("empty.wav", b"not-real-audio", "audio/wav")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertFalse(payload["audio_available"])
        self.assertIn("message", payload)
        self.assertEqual(payload["label"], "REAL")


if __name__ == "__main__":
    unittest.main()
