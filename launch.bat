@echo off
echo 🎵 Local Spotify Music Player
echo =============================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.7 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found
echo.

echo Installing dependencies...
echo Installing pygame, mutagen, pillow...
pip install pygame mutagen pillow
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed
echo.

echo 🚀 Starting Local Spotify Music Player...
echo.
python local_spotify.py

if errorlevel 1 (
    echo.
    echo ❌ Error occurred. Press any key to exit...
    pause >nul
)
