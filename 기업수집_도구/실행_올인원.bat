@echo off
chcp 65001 > nul
title DB 분류 + 이메일 추출

cd /d "C:\Users\user\Desktop\기업수집"
if errorlevel 1 (
    echo [오류] 폴더를 찾을 수 없습니다: C:\Users\user\Desktop\기업수집
    echo 폴더가 있는지 확인하세요.
    pause
    exit
)

echo.
echo ========================================
echo   DB 분류 + 이메일 추출 (올인원 처리)
echo ========================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았습니다.
    echo https://python.org 에서 Python 설치 후 다시 실행하세요.
    pause
    exit
)

if not exist "올인원_처리.py" (
    echo [오류] 올인원_처리.py 파일이 없습니다.
    echo 먼저 파일을 다운받아야 합니다.
    pause
    exit
)

python 올인원_처리.py
echo.
echo ----------------------------------------
echo 완료! 아무 키나 누르면 창이 닫힙니다.
echo ----------------------------------------
pause > nul
