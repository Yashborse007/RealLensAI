@echo off
title RealLens AI - MongoDB Server (Port 27017)
cd /d "%~dp0"
echo ====================================================
echo   Starting RealLens AI MongoDB Service on Port 27017
echo ====================================================

rem Check if port 27017 is already in use
netstat -aon | findstr /r ":27017 " >nul 2>&1
if not errorlevel 1 (
    echo MongoDB is already running on port 27017.
    goto :eof
)

if not exist "%USERPROFILE%\.reallens_mongodb_data" mkdir "%USERPROFILE%\.reallens_mongodb_data"

if exist "%USERPROFILE%\scoop\shims\mongod.exe" (
    "%USERPROFILE%\scoop\shims\mongod.exe" --dbpath "%USERPROFILE%\.reallens_mongodb_data" --bind_ip 127.0.0.1,::1 --port 27017
) else if exist "C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" (
    "C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath "%USERPROFILE%\.reallens_mongodb_data" --port 27017
) else (
    mongod --dbpath "%USERPROFILE%\.reallens_mongodb_data" --port 27017
)
