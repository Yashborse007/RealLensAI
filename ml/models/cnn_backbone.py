import torch
import torch.nn as nn
import torch.nn.functional as F

class ConvBlock(nn.Module):
    """
    Modular Convolutional Block: Conv2D -> BatchNorm -> ReLU -> MaxPool2D
    """
    def __init__(self, in_channels: int, out_channels: int, pool: bool = True):
        super(ConvBlock, self).__init__()
        layers = [
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        ]
        if pool:
            layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
        self.block = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)

class SpatialDeepfakeDetector(nn.Module):
    """
    Lightweight PyTorch CNN Backbone & Binary Classifier for Image Deepfake Detection.
    Inputs normalized face crop tensors (N, 3, 224, 224).
    Outputs raw binary logits or probability scores (N, 1).
    """
    def __init__(self, in_channels: int = 3, num_classes: int = 1, dropout_rate: float = 0.5):
        super(SpatialDeepfakeDetector, self).__init__()
        
        # 4-Stage Feature Extractor Backbone
        self.backbone = nn.Sequential(
            ConvBlock(in_channels, 32, pool=True),   # Output: (N, 32, 112, 112)
            ConvBlock(32, 64, pool=True),            # Output: (N, 64, 56, 56)
            ConvBlock(64, 128, pool=True),           # Output: (N, 128, 28, 28)
            ConvBlock(128, 256, pool=True),          # Output: (N, 256, 14, 14)
        )
        
        # Adaptive pooling to fixed spatial grid size
        self.avgpool = nn.AdaptiveAvgPool2d((7, 7))  # Output: (N, 256, 7, 7)
        
        # Binary Classification Head
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 7 * 7, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate * 0.5),
            nn.Linear(64, num_classes)  # Raw Logits output (use BCEWithLogitsLoss or torch.sigmoid)
        )

    def forward(self, x: torch.Tensor, return_probability: bool = False) -> torch.Tensor:
        features = self.backbone(x)
        pooled = self.avgpool(features)
        logits = self.classifier(pooled)
        
        if return_probability:
            return torch.sigmoid(logits)
        return logits

def get_model(pretrained_path: str = None) -> SpatialDeepfakeDetector:
    """
    Factory function instantiating SpatialDeepfakeDetector. Loads weights if path is provided.
    """
    model = SpatialDeepfakeDetector()
    if pretrained_path:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch.load(pretrained_path, map_location=device)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        model.load_state_dict(state_dict)
    return model
