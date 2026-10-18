import csv
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.evaluation.robustness import load_test_manifest, metric_summary, parse_label


class TestRobustnessEvaluation(unittest.TestCase):
    def test_manifest_keeps_test_labels_and_ignores_non_test_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_image = root / "real.jpg"
            fake_image = root / "fake.png"
            real_image.write_bytes(b"original-real-media")
            fake_image.write_bytes(b"original-fake-media")
            original_hashes = {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (real_image, fake_image)
            }
            manifest = root / "test.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id", "path", "label", "split"])
                writer.writeheader()
                writer.writerow({"sample_id": "real-case", "path": real_image.name, "label": "REAL", "split": "test"})
                writer.writerow({"sample_id": "fake-case", "path": fake_image.name, "label": "FAKE", "split": "test"})
                writer.writerow({"sample_id": "train-case", "path": "missing.jpg", "label": "REAL", "split": "train"})

            samples, split_source = load_test_manifest(manifest)

            self.assertEqual(split_source, "split=test column")
            self.assertEqual([(sample.sample_id, sample.label, sample.source_label) for sample in samples], [
                ("real-case", 0, "REAL"),
                ("fake-case", 1, "FAKE"),
            ])
            for path in (real_image, fake_image):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original_hashes[str(path)])

    def test_metrics_report_auc_as_unavailable_for_single_class(self):
        metrics = metric_summary([0, 0], [0.1, 0.8], [0, 1])

        self.assertEqual(metrics["accuracy"], 0.5)
        self.assertEqual(metrics["precision"], 0.0)
        self.assertEqual(metrics["recall"], 0.0)
        self.assertEqual(metrics["f1"], 0.0)
        self.assertIsNone(metrics["auc"])

    def test_unknown_ground_truth_label_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_label("uncertain")

    def test_manifest_rejects_duplicate_sample_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            media = root / "sample.png"
            media.write_bytes(b"unchanged")
            manifest = root / "test.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id", "path", "label"])
                writer.writeheader()
                writer.writerow({"sample_id": "duplicate", "path": media.name, "label": "REAL"})
                writer.writerow({"sample_id": "duplicate", "path": media.name, "label": "FAKE"})

            with self.assertRaisesRegex(ValueError, "duplicates sample_id"):
                load_test_manifest(manifest)


if __name__ == "__main__":
    unittest.main()