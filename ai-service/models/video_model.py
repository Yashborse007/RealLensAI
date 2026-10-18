import os
import torch
import torch.nn as nn
from config import settings
from utils.logging_utils import logger


class TemporalSequenceClassifier(nn.Module):
    """A lightweight GRU-based temporal detector for video deepfake analysis.

    Input: a fixed-length sequence of frame embeddings from a CNN feature extractor.
    Output: fake probability for the entire temporal sequence.
    """

    def __init__(self, feature_dim: int = 64, hidden_dim: int = 32, sequence_length: int = 12):
        super().__init__()
        self.feature_dim = feature_dim
        self.sequence_length = sequence_length
        self.encoder = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.gru = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 3:
            raise ValueError(f"Expected tensor of shape [batch, seq_len, feature_dim], got {tuple(x.shape)}")
        encoded = self.encoder(x)
        _, hidden = self.gru(encoded)
        logits = self.head(hidden[-1])
        return logits.squeeze(-1)

    def predict_probability(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return torch.sigmoid(self(x))

    def prepare_sequence(self, feature_sequence, sequence_length: int = None):
        seq_len = self.sequence_length if sequence_length is None else sequence_length
        if seq_len <= 0:
            raise ValueError("sequence_length must be a positive integer.")
        if len(feature_sequence) == 0:
            return torch.zeros((1, seq_len, self.feature_dim), dtype=torch.float32)

        features = [torch.as_tensor(frame, dtype=torch.float32) for frame in feature_sequence]
        for index, feature in enumerate(features):
            if feature.ndim != 1 or feature.numel() != self.feature_dim:
                raise ValueError(
                    f"Frame feature {index} must be a 1D vector of length "
                    f"{self.feature_dim}; got shape {tuple(feature.shape)}."
                )

        if len(features) > seq_len:
            features = features[:seq_len]
        sequence = torch.stack(features, dim=0)
        if sequence.shape[0] < seq_len:
            padding = sequence.new_zeros((seq_len - sequence.shape[0], self.feature_dim))
            sequence = torch.cat((sequence, padding), dim=0)
        return sequence.unsqueeze(0)


class VideoModelManager:
    """Manages state loading for video PyTorch weights."""

    def __init__(self):
        self.model = None
        self.is_loaded = False
        self._initialize_model()

    def _initialize_model(self):
        weight_path = settings.VIDEO_MODEL_PATH
        if os.path.exists(weight_path):
            try:
                self.model = TemporalSequenceClassifier()
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.model.load_state_dict(torch.load(weight_path, map_location=device))
                self.model.eval()
                self.is_loaded = True
                logger.info(f"Video PyTorch model weights successfully loaded from {weight_path}")
            except Exception as e:
                logger.error(f"Failed to load video model weights at {weight_path}: {str(e)}")
                self.is_loaded = False
        else:
            logger.info(f"Video model weights not found at '{weight_path}'. Model marked as NOT_AVAILABLE.")
            self.is_loaded = False

    def is_available(self) -> bool:
        return self.is_loaded


video_model_manager = VideoModelManager()
