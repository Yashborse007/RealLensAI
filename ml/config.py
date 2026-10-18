from pathlib import Path
import os

import torch

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT_DIR
ML_ROOT = ROOT_DIR / "ml"
DATASET_ROOT = ROOT_DIR / "ai-service" / "datasets"
CHECKPOINT_ROOT = ML_ROOT / "checkpoints"
REPORTS_ROOT = ROOT_DIR / "reports"

RANDOM_SEED = 42

IMAGE_SIZE = 224
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

BATCH_SIZE = 16
NUM_EPOCHS = 20

LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
EARLY_STOPPING_PATIENCE = 5

IMAGE_DECISION_THRESHOLD = 0.5
VIDEO_DECISION_THRESHOLD = 0.5
AUDIO_DECISION_THRESHOLD = 0.5

VIDEO_SAMPLE_FPS = 2.0
VIDEO_MAX_FRAMES = 16
VIDEO_FACE_SIZE = 224
TEMPORAL_SEQUENCE_LENGTH = 12
TEMPORAL_FUSION_WEIGHT_SPATIAL = 0.65
TEMPORAL_FUSION_WEIGHT_TEMPORAL = 0.35
MAX_VIDEO_FRAMES = VIDEO_MAX_FRAMES
FRAME_SAMPLE_RATE = VIDEO_SAMPLE_FPS

MULTIMODAL_DECISION_THRESHOLD = 0.5
MULTIMODAL_QUALITY_THRESHOLD = 0.35
MULTIMODAL_WEIGHTS = {
    "spatial": 0.40,
    "temporal": 0.30,
    "frequency": 0.15,
    "audio": 0.15,
}

AUDIO_SAMPLE_RATE = 16000
MAX_AUDIO_SECONDS = 10

IMAGE_MODEL_PATH = os.getenv("IMAGE_MODEL_PATH", str(CHECKPOINT_ROOT / "image" / "best_model.pth"))
VIDEO_MODEL_PATH = os.getenv("VIDEO_MODEL_PATH", str(CHECKPOINT_ROOT / "video" / "best_model.pth"))
AUDIO_MODEL_PATH = os.getenv("AUDIO_MODEL_PATH", str(CHECKPOINT_ROOT / "audio" / "best_model.pth"))


def get_torch_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_hardware_description() -> str:
    if torch.cuda.is_available():
        return "NVIDIA GPU / CUDA"
    return "CPU"
