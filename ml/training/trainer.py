from __future__ import annotations

from typing import Dict, List, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader


def train_one_epoch(model: nn.Module, loader: DataLoader, device: torch.device, optimizer: torch.optim.Optimizer):
    model.train()
    total_loss = 0.0
    total_examples = 0
    for inputs, targets in loader:
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True).float()
        optimizer.zero_grad()
        logits = model(inputs)
        loss_fn = nn.BCEWithLogitsLoss()
        loss = loss_fn(logits, targets)
        loss.backward()
        optimizer.step()
        total_loss += float(loss.item()) * inputs.size(0)
        total_examples += inputs.size(0)
    return total_loss / max(total_examples, 1)


def validate_one_epoch(model: nn.Module, loader: DataLoader, device: torch.device):
    model.eval()
    total_loss = 0.0
    total_examples = 0
    predictions: List[int] = []
    labels: List[int] = []
    scores: List[float] = []
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True).float()
            logits = model(inputs)
            loss = nn.BCEWithLogitsLoss()(logits, targets)
            total_loss += float(loss.item()) * inputs.size(0)
            total_examples += inputs.size(0)
            probs = torch.sigmoid(logits)
            predictions.extend((probs >= 0.5).long().cpu().tolist())
            labels.extend(targets.long().cpu().tolist())
            scores.extend(probs.cpu().tolist())
    return total_loss / max(total_examples, 1), labels, predictions, scores
