import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from config import settings
from utils.logging_utils import logger
from api.routes_health import router as health_router
from api.routes_image import router as image_router
from api.routes_video import router as video_router
from api.routes_audio import router as audio_router
from api.routes_multimodal import router as multimodal_router

load_dotenv()

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.VERSION,
)

# 1. CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code} on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "path": request.url.path,
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal AI Service Error",
            "message": "An unexpected error occurred during AI processing.",
            "path": request.url.path,
        },
    )

# 3. Root & System Endpoints
@app.get("/")
def root():
    return {
        "success": True,
        "service": "RealLens AI Microservice",
        "status": "online",
        "version": settings.VERSION,
        "docs_url": "/docs",
    }

# 4. Router Mounts
app.include_router(health_router)
app.include_router(health_router, prefix="/api")
app.include_router(image_router)
app.include_router(video_router)
app.include_router(audio_router)
app.include_router(multimodal_router)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting RealLens AI Python Service on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
