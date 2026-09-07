@echo off
title Quantive Desktop
echo.
echo   ╔══════════════════════════════════════════╗
echo   ║    QUANTIVE DESKTOP  v2.1.0              ║
echo   ║    Native Glassmorphism Edition           ║
echo   ╚══════════════════════════════════════════╝
echo.
echo   Starting...
echo.
python desktop.py %*
if errorlevel 1 (
    echo.
    echo   [ERROR] Failed to start. Make sure Python is installed.
    echo   Download: https://www.python.org/downloads/
    echo.
    pause
)
