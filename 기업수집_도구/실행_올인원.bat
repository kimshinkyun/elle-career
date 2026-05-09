@echo off
chcp 65001 > nul
cd /d "C:\Users\user\Desktop\기업수집"
echo.
echo ========================================
echo   DB 분류 + 이메일 추출 (올인원 처리)
echo ========================================
echo.
python 올인원_처리.py
echo.
pause
