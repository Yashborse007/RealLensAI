import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.file_utils import validate_uploaded_file, save_temp_file, remove_file_safely
from services.analysis_orchestrator import analysis_orchestrator
from utils.logging_utils import logger

router = APIRouter()

@router.post("/predict/audio")
async def predict_audio(file: UploadFile = File(...)):
    """Backward-compatible audio prediction endpoint."""
    ext, category = validate_uploaded_file(file, expected_category="audio")

    temp_filename = f"temp_aud_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join("scratch", temp_filename)
    await save_temp_file(file, temp_path)

    try:
        return analysis_orchestrator.analyze(temp_path, media_type="audio")
    finally:
        remove_file_safely(temp_path)


@router.post("/api/detect/audio")
async def detect_audio(file: UploadFile = File(...)):
    """Audio deepfake detection endpoint using the AASIST-style pipeline."""
    ext, category = validate_uploaded_file(file, expected_category="audio")
    temp_filename = f"temp_aud_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join("scratch", temp_filename)
    await save_temp_file(file, temp_path)

    try:
        return analysis_orchestrator.analyze(temp_path, media_type="audio")
    finally:
        remove_file_safely(temp_path)
