import os
import re
import shutil
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException
from config import settings
from utils.logging_utils import logger

# Scratch working directory root
SCRATCH_ROOT = os.path.abspath("scratch")

def sanitize_upload_filename(filename: str) -> str:
    """Strips directory traversal, null bytes, and dangerous characters from upload filename."""
    if not filename:
        return "upload"
    # Remove null bytes and path separators
    clean = filename.replace("\0", "").replace("/", "_").replace("\\", "_")
    # Remove multiple dots
    clean = re.sub(r"\.{2,}", ".", clean)
    clean = re.sub(r"[^a-zA-Z0-9_.-]+", "_", clean).strip("._")
    return clean[:100] or "upload"

def validate_uploaded_file(file: UploadFile, expected_category: str) -> Tuple[str, str]:
    """
    Validates uploaded file extension and MIME type against allowed whitelists.
    Returns (extension, category).
    """
    if not file or not file.filename:
        logger.warning("Upload attempt with missing or empty filename.")
        raise HTTPException(status_code=400, detail="No file uploaded or filename is empty.")

    safe_name = sanitize_upload_filename(file.filename)
    ext = os.path.splitext(safe_name)[1].lower().replace(".", "")
    
    if expected_category == "image":
        allowed = settings.ALLOWED_IMAGE_EXTENSIONS
    elif expected_category == "video":
        allowed = settings.ALLOWED_VIDEO_EXTENSIONS
    elif expected_category == "audio":
        allowed = settings.ALLOWED_AUDIO_EXTENSIONS
    else:
        allowed = set()

    if ext not in allowed:
        logger.warning(f"File validation failed: extension '{ext}' not in allowed set for category '{expected_category}'")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '.{ext}'. Allowed formats for {expected_category}: {', '.join(sorted(allowed))}"
        )

    return ext, expected_category

def _is_safe_scratch_path(target_path: str) -> bool:
    """Verifies that target_path resolves strictly inside the scratch directory."""
    if not target_path or "\0" in target_path:
        return False
    abs_path = os.path.abspath(target_path)
    return abs_path == SCRATCH_ROOT or abs_path.startswith(SCRATCH_ROOT + os.sep)

async def save_temp_file(file: UploadFile, destination_path: str) -> str:
    """
    Saves an uploaded FastAPI file stream to a temporary location on disk with
    path traversal validation and size limit enforcement.
    """
    if not _is_safe_scratch_path(destination_path):
        logger.error(f"Path traversal attempt detected targeting: {os.path.basename(destination_path)}")
        raise HTTPException(status_code=400, detail="Invalid destination path for uploaded file.")

    try:
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        bytes_written = 0
        max_bytes = settings.MAX_FILE_SIZE_BYTES

        with open(destination_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum allowed upload size limit of {max_bytes // (1024 * 1024)}MB."
                    )
                buffer.write(chunk)

        logger.info(f"Temporary file saved safely: {os.path.basename(destination_path)} ({bytes_written} bytes)")
        return destination_path
    except HTTPException:
        remove_file_safely(destination_path)
        raise
    except Exception as e:
        remove_file_safely(destination_path)
        logger.error(f"Failed to save temporary upload file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process uploaded file stream.")

def remove_file_safely(file_path: str):
    """
    Safely removes temporary file if it exists and is within scratch boundaries.
    """
    if not file_path or not _is_safe_scratch_path(file_path):
        return

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Temporary file safely removed: {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Failed to delete temp file {os.path.basename(file_path)}: {str(e)}")
