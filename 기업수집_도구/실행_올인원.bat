@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python from python.org
    pause
    exit
)
python "%~dp0올인원_처리.py"
pause
