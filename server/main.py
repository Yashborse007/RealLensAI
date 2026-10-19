import os
import sys
from pathlib import Path

# Bridge entry point if executed from server/
AI_SERVICE_DIR = Path(__file__).resolve().parent.parent / "ai-service"
sys.path.insert(0, str(AI_SERVICE_DIR))
os.chdir(AI_SERVICE_DIR)

from main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
