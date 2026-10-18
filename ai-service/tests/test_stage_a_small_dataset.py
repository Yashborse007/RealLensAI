import os
import shutil
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.training.train_image import train_image_model


class TestStageASmallDataset(unittest.TestCase):
    def test_stage_a_training_pipeline_works_with_small_dataset(self):
        root = Path("scratch") / "stage_a_dataset"
        if root.exists():
            shutil.rmtree(root)

        for label_name in ["real", "fake"]:
            label_dir = root / label_name
            label_dir.mkdir(parents=True, exist_ok=True)
            for idx in range(2):
                image = np.zeros((32, 32, 3), dtype=np.uint8)
                if label_name == "real":
                    image[:, :, 0] = 30 + idx * 20
                    image[:, :, 1] = 90 + idx * 20
                    image[:, :, 2] = 180 + idx * 20
                else:
                    image[:, :, 0] = 180 + idx * 20
                    image[:, :, 1] = 80 + idx * 20
                    image[:, :, 2] = 40 + idx * 20
                Image.fromarray(image).save(label_dir / f"{label_name}_{idx}.png")

        checkpoint_dir = root / "artifacts"
        result = train_image_model(str(root), checkpoint_dir=str(checkpoint_dir), epochs=1)

        self.assertTrue(Path(result["best_checkpoint"]).exists())
        self.assertTrue(Path(result["last_checkpoint"]).exists())
        self.assertIn("best_val_loss", result)


if __name__ == "__main__":
    unittest.main()
