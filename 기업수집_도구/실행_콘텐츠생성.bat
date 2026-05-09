@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python from python.org
    pause
    exit
)
pip install anthropic -q
python "%~dp0자동_콘텐츠생성기.py"
pause
