@echo off
title Job Auto Apply — Setup
echo =====================================================
echo  Job Auto Apply — One-Time Setup
echo =====================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [1/3] Python found.

REM Install dependencies
echo [2/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM Copy config if not exists
echo [3/3] Setting up config...
if not exist config.yaml (
    copy config.example.yaml config.yaml
    echo.
    echo  config.yaml created!
    echo  >>> OPEN config.yaml and fill in your details before running. <<<
) else (
    echo  config.yaml already exists - skipping copy.
)

echo.
echo =====================================================
echo  Setup complete!
echo  Next step: Edit config.yaml with your credentials
echo  Then run:  run.bat
echo =====================================================
pause
