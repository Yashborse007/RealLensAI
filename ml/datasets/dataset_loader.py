import os
import random
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from typing import List, Tuple, Dict, Any

class DeepfakeDataset(Dataset):
    """
    PyTorch Dataset for binary Image Deepfake Detection (0: REAL, 1: FAKE).
    """
    def __init__(self, samples: List[Tuple[str, int]], transform=None):
        """
        :param samples: List of (image_file_path, label_int) tuples
        :param transform: torchvision.transforms pipeline
        """
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        image_path, label = self.samples[idx]
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            # Fallback for corrupted test images
            image = Image.new("RGB", (224, 224), color=(0, 0, 0))

        if self.transform:
            image = self.transform(image)

        return image, label

def get_data_transforms() -> Dict[str, transforms.Compose]:
    """
    Build training augmentations and validation/test transforms.
    """
    # Standard ImageNet Mean and Standard Deviation
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    return {"train": train_transform, "eval": eval_transform}

def create_train_val_test_split(
    samples: List[Tuple[str, int]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Dict[str, List[Tuple[str, int]]]:
    """
    Split a list of dataset samples into Train, Validation, and Test sets.
    """
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Ratios must sum to 1.0"
    
    random.seed(seed)
    shuffled = samples.copy()
    random.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_samples = shuffled[:n_train]
    val_samples = shuffled[n_train:n_train + n_val]
    test_samples = shuffled[n_train + n_val:]

    return {
        "train": train_samples,
        "val": val_samples,
        "test": test_samples,
    }

def build_dataloaders(
    split_samples: Dict[str, List[Tuple[str, int]]],
    batch_size: int = 16,
    num_workers: int = 0
) -> Dict[str, DataLoader]:
    """
    Instantiate PyTorch DataLoaders for train, val, and test splits.
    """
    tf = get_data_transforms()

    train_dataset = DeepfakeDataset(split_samples["train"], transform=tf["train"])
    val_dataset = DeepfakeDataset(split_samples["val"], transform=tf["eval"])
    test_dataset = DeepfakeDataset(split_samples["test"], transform=tf["eval"])

    dataloaders = {
        "train": DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers),
        "val": DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers),
        "test": DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers),
    }

    return dataloaders
