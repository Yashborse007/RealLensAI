import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.evaluation.cross_dataset import (
    ManifestRow,
    _classification_metrics,
    _identity_state,
    load_manifest,
)


class TestCrossDatasetEvaluation(unittest.TestCase):
    def test_manifest_reads_dataset_split_identity_and_license_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            train_file = root / "train.jpg"
            test_file = root / "test.jpg"
            train_file.write_bytes(b"train-media")
            test_file.write_bytes(b"test-media")
            manifest = root / "manifest.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "sample_id", "dataset", "split", "path", "label", "identity_id",
                    "identity_namespace", "manipulation_type", "dataset_version", "license",
                    "source_url", "preprocessing",
                ])
                writer.writeheader()
                writer.writerow({
                    "sample_id": "train-1", "dataset": "DATASET_A", "split": "train",
                    "path": train_file.name, "label": "REAL", "identity_id": "subject-1",
                    "identity_namespace": "canonical", "manipulation_type": "none",
                    "dataset_version": "v1", "license": "research-only", "source_url": "https://example.invalid/a",
                    "preprocessing": "original frames",
                })
                writer.writerow({
                    "sample_id": "test-1", "dataset": "DATASET_A", "split": "test",
                    "path": test_file.name, "label": "FAKE", "identity_id": "subject-2",
                    "identity_namespace": "canonical", "manipulation_type": "swap",
                    "dataset_version": "v1", "license": "research-only", "source_url": "https://example.invalid/a",
                    "preprocessing": "original frames",
                })

            rows = load_manifest(manifest)

            self.assertEqual([(row.dataset, row.split, row.label) for row in rows], [
                ("DATASET_A", "train", 0),
                ("DATASET_A", "test", 1),
            ])
            self.assertEqual(rows[0].license, "research-only")
            self.assertEqual(rows[0].identity_id, "subject-1")

    def test_identity_overlap_is_detected_and_missing_ids_are_not_verified(self):
        training = [ManifestRow("train", "DATASET_A", "train", Path("train.jpg"), 0, "REAL", "person-1", "global", "none", "", "", "", "")]
        matching_test = [ManifestRow("test", "DATASET_B", "test", Path("test.jpg"), 1, "FAKE", "person-1", "global", "swap", "", "", "", "")]
        missing_test = [ManifestRow("test", "DATASET_B", "test", Path("test.jpg"), 1, "FAKE", "", "global", "swap", "", "", "", "")]

        self.assertEqual(_identity_state(training, matching_test, cross_dataset=True)[0], "overlap")
        self.assertEqual(_identity_state(training, missing_test, cross_dataset=True)[0], "not_verifiable")

    def test_identity_ids_from_unrelated_namespaces_are_not_compared(self):
        training = [ManifestRow("train", "DATASET_A", "train", Path("train.jpg"), 0, "REAL", "1", "source-a", "none", "", "", "", "")]
        testing = [ManifestRow("test", "DATASET_B", "test", Path("test.jpg"), 1, "FAKE", "1", "source-b", "swap", "", "", "", "")]

        self.assertEqual(_identity_state(training, testing, cross_dataset=True)[0], "not_comparable")

    def test_metrics_include_calibration_and_leave_single_class_auc_unavailable(self):
        metrics = _classification_metrics([0, 1], [0.1, 0.8], [0, 1])
        tied_metrics = _classification_metrics([0, 1, 0, 1], [0.2, 0.2, 0.8, 0.8], [0, 0, 1, 1])
        single_class = _classification_metrics([0, 0], [0.1, 0.8], [0, 1])

        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["roc_auc"], 1.0)
        self.assertAlmostEqual(metrics["brier_score"], 0.025)
        self.assertAlmostEqual(metrics["ece"], 0.15)
        self.assertEqual(tied_metrics["roc_auc"], 0.5)
        self.assertIsNone(single_class["roc_auc"])


if __name__ == "__main__":
    unittest.main()