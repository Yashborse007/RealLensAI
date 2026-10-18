import os
import torch
import torch.nn as nn
from config import settings
from utils.logging_utils import logger

class AudioSpectrogramClassifier(nn.Module):
    """
    PyTorch 2D CNN Spectrogram classifier for synthetic voice detection.
    """
    def __init__(self):
        super(AudioSpectrogramClassifier, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.AdaptiveAvgPool2d((8, 8))
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(16 * 8 * 8, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        features = self.conv(x)
        out = self.fc(features)
        return out

class AudioModelManager:
    """
    Manages state loading for Audio PyTorch weights.
    """
    def __init__(self):
        self.model = None
        self.is_loaded = False
        self._initialize_model()

    def _initialize_model(self):
        weight_path = settings.AUDIO_MODEL_PATH
        if os.path.exists(weight_path):
            try:
                self.model = AudioSpectrogramClassifier()
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.model.load_state_dict(torch.load(weight_path, map_location=device))
                self.model.eval()
                self.is_loaded = True
                logger.info(f"Audio PyTorch model weights successfully loaded from {weight_path}")
            except Exception as e:
                logger.error(f"Failed to load audio model weights at {weight_path}: {str(e)}")
                self.is_loaded = False
        else:
            logger.info(f"Audio model weights not found at '{weight_path}'. Model marked as NOT_AVAILABLE.")
            self.is_loaded = False

    def is_available(self) -> bool:
        return self.is_loaded

audio_model_manager = AudioModelManager()
