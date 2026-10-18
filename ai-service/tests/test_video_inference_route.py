import os
import sys
import unittest
from io import BytesIO

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app


class TestVideoInferenceRoute(unittest.TestCase):
    def test_predict_video_returns_metadata_and_temporal_predictions(self):
        video_path = os.path.join("scratch", "sample_video_test.mp4")
        os.makedirs("scratch", exist_ok=True)

        width, height, fps = 160, 120, 5
        writer = cv2.VideoWriter(
            video_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        self.assertIsNotNone(writer)

        frame_count = 10
        for idx in range(frame_count):
            frame = np.full((height, width, 3), 128, dtype=np.uint8)
            if idx % 2 == 0:
                frame[:, :, 0] = 40
                frame[:, :, 1] = 95
                frame[:, :, 2] = 170
            else:
                frame[:, :, 0] = 180
                frame[:, :, 1] = 85
                frame[:, :, 2] = 40
            writer.write(frame)
        writer.release()

        with open(video_path, "rb") as fh:
            payload = fh.read()

        client = TestClient(app)
        response = client.post(
            "/predict/video",
            files={"file": ("sample_video.mp4", payload, "video/mp4")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result["success"])
        self.assertIn("spatial_score", result)
        self.assertIn("temporal_score", result)
        self.assertIn("combined_score", result)
        self.assertIn("label", result)
        self.assertIn("confidence", result)
        self.assertIn("prediction", result)
        self.assertIn("frames_analyzed", result)
        self.assertIn("frame_predictions", result)
        self.assertIn("processing_time_ms", result)
        self.assertIn("metadata", result)
        self.assertIn("evaluation", result)
        self.assertIn("spatial_only", result["evaluation"])
        self.assertIn("temporal_only", result["evaluation"])
        self.assertIn("combined", result["evaluation"])
        self.assertTrue(result["metadata"]["frame_count"] > 0)
        self.assertTrue(result["model_version"])
        self.assertTrue(result["preprocessing_version"])

    def test_predict_video_no_valid_video_returns_clear_failure(self):
        client = TestClient(app)
        response = client.post(
            "/predict/video",
            files={"file": ("bad.mp4", b"not-a-video", "video/mp4")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertFalse(payload.get("success", True))
        self.assertIn("status", payload)


if __name__ == "__main__":
    unittest.main()
