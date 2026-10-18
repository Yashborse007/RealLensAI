from __future__ import annotations

import time
from typing import Any, Dict


def elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


def memory_usage() -> Dict[str, Any]:
    metrics: Dict[str, Any] = {
        "ram_rss_mb": None,
        "gpu_memory_allocated_mb": None,
        "gpu_memory_reserved_mb": None,
    }

    try:
        import psutil

        metrics["ram_rss_mb"] = round(
            psutil.Process().memory_info().rss / (1024 * 1024), 2
        )
    except (ImportError, OSError):
        pass

    try:
        import torch

        if torch.cuda.is_available():
            metrics["gpu_memory_allocated_mb"] = round(
                torch.cuda.memory_allocated() / (1024 * 1024), 2
            )
            metrics["gpu_memory_reserved_mb"] = round(
                torch.cuda.memory_reserved() / (1024 * 1024), 2
            )
    except (ImportError, RuntimeError):
        pass

    return metrics