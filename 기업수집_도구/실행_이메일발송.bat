@echo off
chcp 65001 > nul
cd /d "C:\Users\user\Desktop\기업수집"
echo.
echo ========================================
echo   이메일 자동 발송 시작
echo ========================================
echo.
python 이메일_자동발송.py
echo.
pause
