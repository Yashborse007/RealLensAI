from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ml.inference.multimodal_inference import fuse_multimodal_scores

router = APIRouter()


class MultimodalFusionRequest(BaseModel):
    spatial_score: Optional[float] = None
    temporal_score: Optional[float] = None
    frequency_score: Optional[float] = None
    audio_score: Optional[float] = None
    quality_score: float = 1.0
    modality_availability: Dict[str, bool] = Field(
        default_factory=lambda: {
            "spatial": True,
            "temporal": True,
            "frequency": True,
            "audio": True,
        }
    )
    modality_status: Dict[str, str] = Field(default_factory=dict)
    weights: Dict[str, float] = Field(default_factory=dict)
    threshold: float = 0.5


@router.post("/predict/multimodal")
async def predict_multimodal_payload(payload: MultimodalFusionRequest):
    """Fuse modality scores while respecting configuration and availability metadata."""
    return fuse_multimodal_scores(
        spatial_score=payload.spatial_score,
        temporal_score=payload.temporal_score,
        frequency_score=payload.frequency_score,
        audio_score=payload.audio_score,
        quality_score=payload.quality_score,
        modality_availability=payload.modality_availability,
        modality_status=payload.modality_status,
        weights=payload.weights,
        threshold=payload.threshold,
    )


@router.post("/api/detect/multimodal")
async def detect_multimodal_payload(payload: MultimodalFusionRequest):
    """Compatibility wrapper for multimodal evidence fusion."""
    return fuse_multimodal_scores(
        spatial_score=payload.spatial_score,
        temporal_score=payload.temporal_score,
        frequency_score=payload.frequency_score,
        audio_score=payload.audio_score,
        quality_score=payload.quality_score,
        modality_availability=payload.modality_availability,
        modality_status=payload.modality_status,
        weights=payload.weights,
        threshold=payload.threshold,
    )
