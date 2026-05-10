"""setup.py - 기업수집 도구 전체 다운로드"""
import urllib.request, os, sys

BASE = r"C:\Users\user\Desktop\기업수집"
RAW  = "https://raw.githubusercontent.com/kimshinkyun/elle-career/claude/utilize-internal-resources-Wldx1/%EA%B8%B0%EC%97%85%EC%88%98%EC%A7%91_%EB%8F%84%EA%B5%AC/"

FILES = [
    ("%EC%98%AC%EC%9D%B8%EC%9B%90_%EC%B2%98%EB%A6%AC.py",          "올인원_처리.py"),
    ("%ED%8C%A8%EC%B9%98.py",                                        "패치.py"),
    ("%EC%9D%B4%EB%A9%94%EC%9D%BC_%EC%9E%90%EB%8F%99%EB%B0%9C%EC%86%A1.py", "이메일_자동발송.py"),
    ("%EC%9E%90%EB%8F%99_%EC%BD%98%ED%85%90%EC%B8%A0%EC%83%9D%EC%84%B1%EA%B8%B0.py", "자동_콘텐츠생성기.py"),
    ("%EC%B9%B4%EC%B9%B4%EC%98%A4_%EB%B0%9C%EC%86%A1.py",           "카카오_발송.py"),
    ("%EC%A0%88%EC%84%B8_%EC%B1%97%EB%B4%87.html",                  "절세_챗봇.html"),
    ("SNS%EB%A7%88%EC%BC%80%ED%8C%85_%EC%BD%98%ED%85%90%EC%B8%A0.html", "SNS마케팅_콘텐츠.html"),
    ("%EC%98%81%EC%97%85%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C.html", "영업대시보드.html"),
    ("%EC%A0%88%EC%84%B8%EC%A7%84%EB%8B%A8.html",                   "절세진단.html"),
]

BAT_ALLINONE = b'@echo off\r\ncd /d "%~dp0"\r\npython \xec\98\ac\xec\9d\xb8\xec\9b\90_\xec\xb2\98\xeb\xa6\xac.py\r\npause\r\n'

os.makedirs(BASE, exist_ok=True)

print("=" * 50)
print("  기업수집 도구 설치 중...")
print("=" * 50)

ok = 0
for url_part, filename in FILES:
    url  = RAW + url_part
    dest = os.path.join(BASE, filename)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  ✓ {filename}")
        ok += 1
    except Exception as e:
        print(f"  ✗ {filename} — {e}")

# bat 파일은 python으로 직접 생성 (한글 파일명 안전하게)
bat_files = {
    "실행_올인원.bat"    : "올인원_처리.py",
    "실행_이메일발송.bat": "이메일_자동발송.py",
    "실행_콘텐츠생성.bat": "자동_콘텐츠생성기.py",
}
for bat_name, py_name in bat_files.items():
    bat_path = os.path.join(BASE, bat_name)
    content  = f'@echo off\r\ncd /d "%~dp0"\r\npython "{py_name}"\r\npause\r\n'
    with open(bat_path, "w", encoding="cp949", errors="ignore") as f:
        f.write(content)
    print(f"  ✓ {bat_name}")

print(f"\n완료! {ok}/{len(FILES)} 파일 다운로드됨")
print(f"폴더: {BASE}")
print("\n다음 단계:")
print("  1. 크롤링결과 엑셀 파일을 위 폴더에 복사")
print("  2. 실행_올인원.bat 더블클릭")
input("\n엔터 누르면 종료...")
