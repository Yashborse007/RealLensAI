from __future__ import annotations


class EarlyStopping:
    """Stop training when validation loss fails to improve for the configured patience."""

    def __init__(self, patience: int = 5, min_delta: float = 1e-6):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float("inf")
        self.counter = 0
        self.should_stop = False

    def step(self, val_loss: float) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
        return self.should_stop

    def reset(self) -> None:
        self.best_loss = float("inf")
        self.counter = 0
        self.should_stop = False
