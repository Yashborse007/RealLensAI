import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Dict, Any, Tuple
import numpy as np

from evaluation.evaluator import evaluator

class EarlyStopping:
    """
    Early stopping monitor tracking validation loss to prevent overfitting.
    """
    def __init__(self, patience: int = 5, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float("inf")
        self.should_stop = False

    def __call__(self, val_loss: float) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
            return True # Improved
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
            return False # Not improved

class ModelTrainer:
    """
    Training and Validation Loop orchestrator with Checkpoint Saving and Early Stopping.
    """
    def __init__(
        self,
        model: nn.Module,
        checkpoint_dir: str = "ml/checkpoints",
        device: torch.device = None,
        lr: float = 1e-3,
        patience: int = 5
    ):
        self.model = model
        self.checkpoint_dir = checkpoint_dir
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        self.criterion = nn.BCEWithLogitsLoss()
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode="min", factor=0.5, patience=2)
        self.early_stopping = EarlyStopping(patience=patience)

        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def train_epoch(self, dataloader: DataLoader) -> Tuple[float, float]:
        """
        Execute 1 training epoch over train dataloader.
        Returns (average_loss, accuracy).
        """
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in dataloader:
            images = images.to(self.device)
            labels = labels.to(self.device).float().unsqueeze(1)

            self.optimizer.zero_grad()
            logits = self.model(images)
            loss = self.criterion(logits, labels)
            loss.backward()
            self.optimizer.step()

            running_loss += loss.item() * images.size(0)
            probs = torch.sigmoid(logits)
            preds = (probs >= 0.5).float()
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        epoch_loss = running_loss / max(1, total)
        epoch_acc = correct / max(1, total)
        return epoch_loss, epoch_acc

    def validate_epoch(self, dataloader: DataLoader) -> Tuple[float, float, np.ndarray, np.ndarray]:
        """
        Execute 1 validation/testing epoch over val dataloader.
        Returns (average_loss, accuracy, y_true, y_probs).
        """
        self.model.eval()
        running_loss = 0.0
        correct = 0
        total = 0
        all_labels = []
        all_probs = []

        with torch.no_grad():
            for images, labels in dataloader:
                images = images.to(self.device)
                labels = labels.to(self.device).float().unsqueeze(1)

                logits = self.model(images)
                loss = self.criterion(logits, labels)

                running_loss += loss.item() * images.size(0)
                probs = torch.sigmoid(logits)
                preds = (probs >= 0.5).float()

                correct += (preds == labels).sum().item()
                total += labels.size(0)

                all_labels.extend(labels.cpu().numpy().flatten())
                all_probs.extend(probs.cpu().numpy().flatten())

        val_loss = running_loss / max(1, total)
        val_acc = correct / max(1, total)
        return val_loss, val_acc, np.array(all_labels), np.array(all_probs)

    def save_checkpoint(self, epoch: int, metrics: Dict[str, Any], filename: str = "best_model.pth"):
        """
        Save PyTorch state dict and training metadata checkpoint.
        """
        filepath = os.path.join(self.checkpoint_dir, filename)
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "metrics": metrics,
        }
        torch.save(checkpoint, filepath)
        return filepath

    def fit(self, dataloaders: Dict[str, DataLoader], epochs: int = 10) -> Dict[str, Any]:
        """
        Complete Training & Validation Loop with Checkpointing and Early Stopping.
        """
        print(f"[Training] Starting model training for {epochs} epochs on device: {self.device}")
        best_val_loss = float("inf")
        best_metrics = {}

        for epoch in range(1, epochs + 1):
            train_loss, train_acc = self.train_epoch(dataloaders["train"])
            val_loss, val_acc, y_true, y_probs = self.validate_epoch(dataloaders["val"])

            self.scheduler.step(val_loss)

            print(f"Epoch [{epoch}/{epochs}] - Train Loss: {train_loss:.4f} | Train Acc: {train_acc*100:.2f}% | Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:.2f}%")

            is_improved = self.early_stopping(val_loss)
            if is_improved:
                best_val_loss = val_loss
                # Evaluate full validation metrics
                best_metrics = evaluator.compute_metrics(y_true, y_probs)
                self.save_checkpoint(epoch, best_metrics, "best_model.pth")

            if self.early_stopping.should_stop:
                print(f"[Early Stopping] Training stopped early at epoch {epoch} due to non-improving val loss.")
                break

        # Save final metrics report to JSON
        evaluator.save_metrics_report(best_metrics, os.path.join(self.checkpoint_dir, "metrics_report.json"))
        return best_metrics
