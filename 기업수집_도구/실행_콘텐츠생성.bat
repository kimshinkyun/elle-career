@echo off
chcp 65001 > nul
cd /d "C:\Users\user\Desktop\기업수집"
echo.
echo ========================================
echo   오늘의 SNS 콘텐츠 자동 생성
echo ========================================
echo.
pip install anthropic -q
python 자동_콘텐츠생성기.py
echo.
pause
