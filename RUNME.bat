@echo off
title Gallery-dl ^& Mobile Image Ranker Launcher
cd /d "%~dp0"

:: Check if virtual environment exists
if not exist ".\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv not found!
    echo Please run: py -3.12 -m venv .venv
    pause
    exit /b 1
)

:MENU
cls
echo ====================================================================
echo             Gallery-dl ^& Mobile Image Ranker Launcher
echo ====================================================================
echo Python: .\.venv\Scripts\python.exe
echo.
echo [1] Start Mobile Image Ranker Server (Tinder Swipe PWA on Port 8000)
echo [2] Start Wallpaper AI Ranker UI (GPU Accelerated)
echo [3] Run Delete Discarded Images Tool (GUI / CLI)
echo [4] Download Media with Gallery-dl
echo [5] Open Command Line with .venv Pre-Activated
echo [0] Exit
echo ====================================================================
echo.

set /p CHOICE="Select an option (0-5): "

if "%CHOICE%"=="1" (
    echo.
    echo Starting Mobile Image Ranker PWA Server...
    ".\.venv\Scripts\python.exe" mobile-image-ranker/serve.py
    pause
    goto MENU
)

if "%CHOICE%"=="2" (
    echo.
    echo Starting Wallpaper AI Ranker Web UI (PyTorch GPU)...
    ".\.venv\Scripts\python.exe" gallery-dl/pickWallpaper_ui.py
    pause
    goto MENU
)

if "%CHOICE%"=="3" (
    echo.
    echo Starting Delete Discarded Images Tool...
    ".\.venv\Scripts\python.exe" delete_discarded.py
    pause
    goto MENU
)

if "%CHOICE%"=="4" (
    echo.
    set /p URL="Enter URL or folder to download: "
    if not "%URL%"=="" (
        ".\.venv\Scripts\gallery-dl.exe" --config gallery-dl.conf "%URL%"
    )
    pause
    goto MENU
)

if "%CHOICE%"=="5" (
    echo.
    echo Launching PowerShell with .venv activated...
    powershell -NoExit -ExecutionPolicy Bypass -Command "& { . .\.venv\Scripts\Activate.ps1 }"
    goto MENU
)

if "%CHOICE%"=="0" (
    exit /b 0
)

echo Invalid choice. Please select 0 to 5.
timeout /t 2 >nul
goto MENU
