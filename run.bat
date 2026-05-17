@echo off
title Job Auto Apply
echo =====================================================
echo  Job Auto Apply — LinkedIn + Indeed + Naukri
echo =====================================================
echo.

if not exist config.yaml (
    echo [ERROR] config.yaml not found!
    echo Run setup.bat first, then fill in config.yaml
    pause
    exit /b 1
)

python main.py
pause
