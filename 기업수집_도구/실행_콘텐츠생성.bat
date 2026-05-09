@echo off
chcp 65001 > nul
title SNS 콘텐츠 자동 생성

cd /d "C:\Users\user\Desktop\기업수집"
if errorlevel 1 (
    echo [오류] 폴더를 찾을 수 없습니다: C:\Users\user\Desktop\기업수집
    pause
    exit
)

echo.
echo ========================================
echo   오늘의 SNS 콘텐츠 자동 생성
echo ========================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았습니다.
    pause
    exit
)

if not exist "자동_콘텐츠생성기.py" (
    echo [오류] 자동_콘텐츠생성기.py 파일이 없습니다.
    pause
    exit
)

echo anthropic 설치 확인 중...
pip install anthropic -q
echo.

python 자동_콘텐츠생성기.py
echo.
echo ----------------------------------------
echo 완료! 아무 키나 누르면 창이 닫힙니다.
echo ----------------------------------------
pause > nul
