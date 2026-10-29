@echo off
title Driver Behavior Scoring System - Launcher
echo ========================================================
echo   Starting Driver Behavior Scoring System Backend
echo   Database: MongoDB Atlas (cluster0.irwzdlk.mongodb.net)
echo ========================================================
echo.
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
