@echo off
title RealLens AI - Python AI Microservice (Port 8000)
cd /d "%~dp0"
echo ====================================================
echo   Starting RealLens AI Python Service on Port 8000
echo ====================================================

rem Check if port 8000 is already in use and free it
for /f "tokens=5" %%p in ('netstat -aon ^| findstr /r ":8000 "') do (
    if not "%%p"=="0" (
        echo Port 8000 is occupied by PID %%p. Freeing port...
        taskkill /F /PID %%p >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

if exist ".venv\Scripts\python.exe" (
    echo Using project virtual environment (.venv)...
    ".venv\Scripts\python.exe" -m uvicorn --app-dir ai-service main:app --host 127.0.0.1 --port 8000
) else if exist "ai-service\venv\Scripts\python.exe" (
    echo Using ai-service virtual environment (ai-service\venv)...
    "ai-service\venv\Scripts\python.exe" -m uvicorn --app-dir ai-service main:app --host 127.0.0.1 --port 8000
) else (
    echo Using system Python...
    python -m uvicorn --app-dir ai-service main:app --host 127.0.0.1 --port 8000
)

pause
