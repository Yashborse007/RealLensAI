from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, random_split

from ml.config import (
    BATCH_SIZE,
    EARLY_STOPPING_PATIENCE,
    IMAGE_DECISION_THRESHOLD,
    LEARNING_RATE,
    NUM_EPOCHS,
    RANDOM_SEED,
    TRAIN_RATIO,
    VAL_RATIO,
    WEIGHT_DECAY,
    CHECKPOINT_ROOT,
    get_torch_device,
)
from ml.datasets.image_dataset import ImageDeepfakeDataset
from ml.models.image.aide_model import AIDEImageDetector
from ml.training.early_stopping import EarlyStopping


def _create_stage_a_demo_dataset(dataset_root: str) -> str:
    """Create a tiny, deterministic synthetic dataset so Stage A can train without external downloads."""
    root = Path(dataset_root)
    root.mkdir(parents=True, exist_ok=True)

    for label_name in ["real", "fake"]:
        label_dir = root / label_name
        label_dir.mkdir(parents=True, exist_ok=True)

        for idx in range(3):
            image = np.zeros((32, 32, 3), dtype=np.uint8)
            yy, xx = np.mgrid[0:32, 0:32]
            if label_name == "real":
                image[:, :, 0] = 35 + (xx * 1.6).astype(np.uint8)
                image[:, :, 1] = 90 + (yy * 1.4).astype(np.uint8)
                image[:, :, 2] = 170 + ((xx + yy) * 0.7).astype(np.uint8)
            else:
                image[:, :, 0] = 180 + ((xx + yy) * 0.8).astype(np.uint8)
                image[:, :, 1] = 80 + (xx * 0.6).astype(np.uint8)
                image[:, :, 2] = 35 + (yy * 0.5).astype(np.uint8)
                image[::2, ::2] = 255
                image[1::2, 1::2] = 25

            Image.fromarray(image, mode="RGB").save(label_dir / f"{label_name}_{idx}.png")

    return str(root)


def ensure_stage_a_dataset(dataset_root: str) -> str:
    root = Path(dataset_root)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)

    dataset = ImageDeepfakeDataset(str(root))
    if len(dataset) > 0:
        return str(root)

    return _create_stage_a_demo_dataset(str(root))


def build_image_dataloaders(dataset_root: str, batch_size: int = BATCH_SIZE):
    dataset_root = ensure_stage_a_dataset(dataset_root)
    dataset = ImageDeepfakeDataset(dataset_root)
    dataset_length = len(dataset)
    if dataset_length == 0:
        raise ValueError(f"No valid image samples were found under '{dataset_root}'.")

    if dataset_length == 1:
        train_size, val_size, test_size = 1, 0, 0
    elif dataset_length == 2:
        train_size, val_size, test_size = 1, 1, 0
    else:
        train_size = max(1, int(dataset_length * TRAIN_RATIO))
        val_size = max(1, int(dataset_length * VAL_RATIO))
        test_size = dataset_length - train_size - val_size
        if test_size < 0:
            delta = abs(test_size)
            train_size = max(1, train_size - delta)
            test_size = dataset_length - train_size - val_size
        if test_size < 1:
            test_size = 0

    split_sizes = [train_size, val_size, test_size]
    if sum(split_sizes) != dataset_length:
        split_sizes[-1] = dataset_length - sum(split_sizes[:-1])
    if split_sizes[0] < 1:
        split_sizes[0] = 1
        split_sizes[1] = max(0, dataset_length - split_sizes[0])

    train_ds, val_ds, test_ds = random_split(
        dataset,
        split_sizes,
        generator=torch.Generator().manual_seed(RANDOM_SEED),
    )

    def safe_loader(ds):
        if len(ds) == 0:
            return None
        return DataLoader(ds, batch_size=max(1, batch_size), shuffle=False)

    return (
        DataLoader(train_ds, batch_size=max(1, batch_size), shuffle=True),
        safe_loader(val_ds),
        safe_loader(test_ds),
    )


def train_image_model(dataset_root: str, checkpoint_dir: Optional[str] = None, epochs: int = NUM_EPOCHS):
    dataset_root = ensure_stage_a_dataset(dataset_root)
    checkpoint_root = Path(checkpoint_dir) if checkpoint_dir else CHECKPOINT_ROOT / "image"
    checkpoint_root.mkdir(parents=True, exist_ok=True)

    best_path = checkpoint_root / "best_model.pth"
    last_path = checkpoint_root / "last_model.pth"

    device = torch.device(get_torch_device())
    train_loader, val_loader, test_loader = build_image_dataloaders(dataset_root)
    model = AIDEImageDetector().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    early_stopping = EarlyStopping(patience=EARLY_STOPPING_PATIENCE)

    best_val_loss = float("inf")

    for epoch in range(1, epochs + 1):
        from ml.training.trainer import train_one_epoch, validate_one_epoch

        train_one_epoch(model, train_loader, device, optimizer)
        val_loss, _, _, _ = validate_one_epoch(model, val_loader, device) if val_loader is not None else (0.0, [], [], [])

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save_checkpoint(str(best_path), epoch=epoch, optimizer=optimizer, best_val_loss=best_val_loss, threshold=IMAGE_DECISION_THRESHOLD, config={"epochs": epochs, "lr": LEARNING_RATE})
        model.save_checkpoint(str(last_path), epoch=epoch, optimizer=optimizer, best_val_loss=best_val_loss, threshold=IMAGE_DECISION_THRESHOLD, config={"epochs": epochs, "lr": LEARNING_RATE})

        if early_stopping.step(val_loss):
            break

    return {"best_checkpoint": str(best_path), "last_checkpoint": str(last_path), "best_val_loss": best_val_loss}
