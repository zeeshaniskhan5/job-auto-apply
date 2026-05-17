@echo off
title Job Auto Apply — Setup
echo =====================================================
echo  Job Auto Apply — One-Time Setup
echo =====================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)
echo [1/4] Python found.

REM Install Python packages
echo [2/4] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

REM Install Playwright browsers
echo [3/4] Installing Playwright browser (Chromium)...
playwright install chromium
if %errorlevel% neq 0 (
    echo [ERROR] Playwright browser install failed.
    pause
    exit /b 1
)

REM Copy example config
echo [4/4] Setting up config...
if not exist config.yaml (
    copy config.example.yaml config.yaml
    echo.
    echo  config.yaml created!
    echo  >>> OPEN config.yaml and fill in your details before running. <<<
) else (
    echo  config.yaml already exists — skipping.
)

echo.
echo =====================================================
echo  Setup complete!
echo  1. Edit config.yaml with your credentials
echo  2. Run: run.bat
echo =====================================================
pause
