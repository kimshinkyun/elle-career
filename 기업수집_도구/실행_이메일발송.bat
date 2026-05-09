@echo off
chcp 65001 > nul
title 이메일 자동 발송

cd /d "C:\Users\user\Desktop\기업수집"
if errorlevel 1 (
    echo [오류] 폴더를 찾을 수 없습니다: C:\Users\user\Desktop\기업수집
    pause
    exit
)

echo.
echo ========================================
echo   이메일 자동 발송 시작
echo ========================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았습니다.
    pause
    exit
)

if not exist "이메일_자동발송.py" (
    echo [오류] 이메일_자동발송.py 파일이 없습니다.
    pause
    exit
)

python 이메일_자동발송.py
echo.
echo ----------------------------------------
echo 완료! 아무 키나 누르면 창이 닫힙니다.
echo ----------------------------------------
pause > nul
