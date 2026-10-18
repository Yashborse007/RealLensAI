import os
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.datasets.image_dataset import ImageDeepfakeDataset


class TestImageDataset(unittest.TestCase):
    def test_dataset_discovers_valid_images_and_assigns_labels(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            real_dir = os.path.join(tmp_dir, "real")
            fake_dir = os.path.join(tmp_dir, "fake")
            os.makedirs(real_dir, exist_ok=True)
            os.makedirs(fake_dir, exist_ok=True)

            Image.new("RGB", (64, 64), color=(10, 20, 30)).save(os.path.join(real_dir, "real_1.jpg"))
            Image.new("RGB", (64, 64), color=(200, 100, 50)).save(os.path.join(fake_dir, "fake_1.png"))
            with open(os.path.join(fake_dir, "junk.txt"), "wb") as handle:
                handle.write(b"not an image")

            dataset = ImageDeepfakeDataset(tmp_dir)
            self.assertEqual(len(dataset), 2)
            image, label = dataset[0]
            self.assertEqual(image.shape, (3, 224, 224))
            self.assertIn(label, (0, 1))


if __name__ == "__main__":
    unittest.main()
