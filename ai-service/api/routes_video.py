import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.file_utils import validate_uploaded_file, save_temp_file, remove_file_safely
from services.analysis_orchestrator import analysis_orchestrator
from utils.logging_utils import logger

router = APIRouter()

@router.post("/predict/video")
async def predict_video(file: UploadFile = File(...)):
    """Real video prediction endpoint using frame-level sampling and temporal aggregation."""
    ext, category = validate_uploaded_file(file, expected_category="video")

    temp_filename = f"temp_vid_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join("scratch", temp_filename)
    await save_temp_file(file, temp_path)

    try:
        result = analysis_orchestrator.analyze(temp_path, media_type="video")
        return result
    finally:
        remove_file_safely(temp_path)


@router.post("/api/detect/video")
async def detect_video(file: UploadFile = File(...)):
    """Compatibility wrapper for the video deepfake detection endpoint."""
    ext, category = validate_uploaded_file(file, expected_category="video")
    temp_filename = f"temp_vid_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join("scratch", temp_filename)
    await save_temp_file(file, temp_path)

    try:
        return analysis_orchestrator.analyze(temp_path, media_type="video")
    finally:
        remove_file_safely(temp_path)
