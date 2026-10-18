from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageOps
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset

from ml.config import IMAGE_SIZE, RANDOM_SEED, TEST_RATIO, TRAIN_RATIO, VAL_RATIO


class ImageDeepfakeDataset(Dataset):
    """Dataset that reads recursively from datasets/image/real and datasets/image/fake."""

    VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, root_dir: str, transform: Optional[Callable] = None, target_size: int = IMAGE_SIZE):
        self.root_dir = Path(root_dir)
        self.target_size = target_size
        self.transform = transform
        self.samples: List[Tuple[str, int]] = []
        self._discover_samples()

    def _discover_samples(self) -> None:
        label_map = {"real": 0, "fake": 1}
        for label_name, label in label_map.items():
            label_dir = self.root_dir / label_name
            if not label_dir.exists():
                continue
            for file_path in sorted(label_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in self.VALID_EXTENSIONS:
                    continue
                try:
                    with Image.open(file_path) as image:
                        image.verify()
                    self.samples.append((str(file_path), int(label)))
                except Exception:
                    continue

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        file_path, label = self.samples[idx]
        image = Image.open(file_path).convert("RGB")
        image = ImageOps.exif_transpose(image)
        if self.transform is not None:
            image = self.transform(image)
        else:
            image = self._default_transform(image)
        return image, int(label)

    @staticmethod
    def _default_transform(image: Image.Image) -> torch.Tensor:
        image = image.resize((IMAGE_SIZE, IMAGE_SIZE))
        image = np.asarray(image, dtype=np.float32) / 255.0
        image = np.transpose(image, (2, 0, 1))
        return torch.from_numpy(image)


def split_image_dataset(
    root_dir: str,
    train_ratio: float = TRAIN_RATIO,
    val_ratio: float = VAL_RATIO,
    test_ratio: float = TEST_RATIO,
    random_seed: int = RANDOM_SEED,
):
    """Split dataset into train/val/test sets without leaking samples across class partitions."""
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must sum to 1.0")

    dataset = ImageDeepfakeDataset(root_dir=root_dir)
    real_files = [sample for sample in dataset.samples if sample[1] == 0]
    fake_files = [sample for sample in dataset.samples if sample[1] == 1]

    def split_files(files):
        train, remainder = train_test_split(
            files,
            train_size=train_ratio,
            random_state=random_seed,
            shuffle=True,
            stratify=[path[1] if False else "x" for path in []],
        )
        # This helper is intentionally simple and preserves a reproducible split.
        return train, remainder

    real_train, real_rest = train_test_split(real_files, train_size=train_ratio, random_state=random_seed, shuffle=True)
    real_val, real_test = train_test_split(real_rest, train_size=val_ratio / (val_ratio + test_ratio), random_state=random_seed, shuffle=True)

    fake_train, fake_rest = train_test_split(fake_files, train_size=train_ratio, random_state=random_seed, shuffle=True)
    fake_val, fake_test = train_test_split(fake_rest, train_size=val_ratio / (val_ratio + test_ratio), random_state=random_seed, shuffle=True)

    train = real_train + fake_train
    val = real_val + fake_val
    test = real_test + fake_test

    return {
        "train": train,
        "val": val,
        "test": test,
        "train_count": len(train),
        "val_count": len(val),
        "test_count": len(test),
    }
