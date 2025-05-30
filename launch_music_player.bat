@echo off
title Local Music Player Launcher
echo 🎵 Local Music Player - Starting...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.6 or higher
    pause
    exit /b 1
)

:: Navigate to the script directory
cd /d "%~dp0"

:: Run the main application
python main.py

:: Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo ❌ Application exited with an error
    pause
)