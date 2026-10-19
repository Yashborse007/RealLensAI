@echo off
title RealLens AI - Service Launcher
cd /d "%~dp0"
set "PATH=%USERPROFILE%\scoop\apps\nodejs-lts\current\bin;%USERPROFILE%\scoop\apps\nodejs-lts\current;%USERPROFILE%\scoop\shims;%PATH%"
echo ====================================================
echo      Starting RealLens AI Complete System
echo ====================================================
echo 1. Launching MongoDB Server on http://127.0.0.1:27017 ...
start "RealLens AI - MongoDB (27017)" start_mongodb.bat

timeout /t 2 /nobreak >nul

echo 2. Launching Python AI Service on http://127.0.0.1:8000 ...
start "RealLens AI - Python Service (8000)" start_ai_service.bat

timeout /t 3 /nobreak >nul

echo 3. Launching Backend Gateway on http://localhost:5000 ...
start "RealLens AI - Backend Gateway (5000)" cmd /k "cd /d \"%~dp0server\" && npm run dev"

timeout /t 2 /nobreak >nul

echo 4. Launching Frontend Client on http://localhost:5173 ...
start "RealLens AI - Web Client (5173)" cmd /k "cd /d \"%~dp0client\" && npm run dev"

echo.
echo ====================================================
echo   All 4 RealLens AI Services have been initiated!
echo   - Web UI:         http://localhost:5173
echo   - API Gateway:    http://localhost:5000
echo   - AI Service:     http://localhost:8000
echo   - Database:       mongodb://127.0.0.1:27017/reallens_ai
echo ====================================================
echo You may close this launcher window.
pause
