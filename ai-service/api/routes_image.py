import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.file_utils import validate_uploaded_file, save_temp_file, remove_file_safely
from services.analysis_orchestrator import analysis_orchestrator
from explainability.gradcam import explain_image_with_gradcam
from utils.logging_utils import logger

router = APIRouter()

@router.post("/predict/image")
async def predict_image(file: UploadFile = File(...)):
    """Real image prediction endpoint using the trained AIDE checkpoint."""
    ext, category = validate_uploaded_file(file, expected_category="image")

    temp_filename = f"temp_img_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join("scratch", temp_filename)
    await save_temp_file(file, temp_path)

    try:
        result = analysis_orchestrator.analyze(temp_path, media_type="image")
        return result
    finally:
        remove_file_safely(temp_path)


@router.post("/api/detect/image")
async def detect_image(file: UploadFile = File(...)):
    """Compatibility wrapper for the image detection endpoint."""
    ext, category = validate_uploaded_file(file, expected_category="image")
    temp_filename = f"temp_img_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join("scratch", temp_filename)
    await save_temp_file(file, temp_path)

    try:
        return analysis_orchestrator.analyze(temp_path, media_type="image")
    finally:
        remove_file_safely(temp_path)


@router.post("/predict/image/explain")
async def explain_image(file: UploadFile = File(...)):
    """Return a Grad-CAM evidence visualization for a single uploaded image."""
    ext, category = validate_uploaded_file(file, expected_category="image")
    temp_filename = f"temp_img_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join("scratch", temp_filename)
    await save_temp_file(file, temp_path)

    try:
        return explain_image_with_gradcam(temp_path)
    finally:
        remove_file_safely(temp_path)
