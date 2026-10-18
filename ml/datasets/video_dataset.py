from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from torch.utils.data import Dataset


class VideoDeepfakeDataset(Dataset):
    """Placeholder dataset container for video deepfake experiments.

    The real implementation reads video files from datasets/video/real and datasets/video/fake,
    extracts frames, and applies a split strategy while preserving potential source grouping.
    """

    VALID_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.samples: List[Tuple[str, int]] = []
        for label_name, label in (("real", 0), ("fake", 1)):
            label_dir = self.root_dir / label_name
            if not label_dir.exists():
                continue
            for file_path in sorted(label_dir.rglob("*")):
                if file_path.is_file() and file_path.suffix.lower() in self.VALID_EXTENSIONS:
                    self.samples.append((str(file_path), int(label)))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        return self.samples[idx]
