"""
[작업 4] 홈페이지 크롤링 - 이메일/팩스 자동 수집
의존: pip install requests beautifulsoup4 openpyxl pandas lxml
실행: python task4_크롤링.py
"""
import re, time, os, csv, warnings
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openpyxl import load_workbook, Workbook

warnings.filterwarnings("ignore")

BASE    = r"C:\Users\user\Desktop\기업수집"
INPUT   = os.path.join(BASE, "기업목록_URL.csv")
OUTPUT  = os.path.join(BASE, "크롤링결과.xlsx")
SAVE_EVERY = 100  # 100건마다 중간 저장

# ── 정규식 패턴 ─────────────────────────────────────────────────
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
FAX_RE = re.compile(
    r"(?:팩스|F(?:AX)?|fax)\s*[:\.]?\s*(0\d{1,2}[-\s]\d{3,4}[-\s]\d{4})|"
    r"(?<!\d)(0\d{1,2}[-\s]\d{3,4}[-\s]\d{4})(?!\d)"
)

# 스팸/시스템 이메일 제외 패턴
SPAM_PATTERNS = re.compile(
    r"@(example|test|naver|daum|nate|gmail|yahoo|hotmail|sentry|"
    r"wix|wordpress|adobe|github|kakao|facebook|google)\.",
    re.I
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

def clean_url(url: str) -> str:
    url = str(url).strip()
    if not url:
        return ""
    if not url.startswith(("http://","https://")):
        url = "https://" + url
    return url

def is_spam_email(email: str) -> bool:
    return bool(SPAM_PATTERNS.search(email))

def extract_from_html(html: str, base_url: str) -> tuple[list, list]:
    """HTML에서 이메일·팩스 추출. (이메일목록, 팩스목록) 반환"""
    soup = BeautifulSoup(html, "lxml")

    # mailto 링크 우선 추출
    emails = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            em = href[7:].split("?")[0].strip()
            if em and not is_spam_email(em):
                emails.append(em)

    # 본문 텍스트에서 이메일 추출
    text = soup.get_text(" ", strip=True)
    for em in EMAIL_RE.findall(text):
        if not is_spam_email(em) and em not in emails:
            emails.append(em)

    # 팩스 번호 추출
    faxes = []
    for m in FAX_RE.finditer(text):
        fax = (m.group(1) or m.group(2) or "").strip()
        if fax and fax not in faxes:
            faxes.append(fax)

    # 정규화 (최대 2개씩)
    emails = list(dict.fromkeys(emails))[:2]
    faxes  = list(dict.fromkeys(faxes))[:2]
    return emails, faxes

def crawl_page(url: str, timeout: int = 8) -> tuple[list, list, str]:
    """단일 페이지 크롤링. (emails, faxes, 상태) 반환"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False, allow_redirects=True)
        r.encoding = r.apparent_encoding or "utf-8"
        if r.status_code != 200:
            return [], [], f"HTTP_{r.status_code}"

        emails, faxes = extract_from_html(r.text, url)

        # 이메일이 없으면 /contact 서브페이지도 시도
        if not emails:
            for sub in ["/contact", "/about", "/contactus", "/연락처", "/회사소개"]:
                try:
                    sub_url = urljoin(url, sub)
                    r2 = requests.get(sub_url, headers=HEADERS, timeout=5, verify=False)
                    if r2.status_code == 200:
                        r2.encoding = r2.apparent_encoding or "utf-8"
                        e2, f2 = extract_from_html(r2.text, sub_url)
                        emails += e2
                        faxes  += f2
                        if emails:
                            break
                except Exception:
                    continue

        status = "성공"
        if not emails and not faxes:
            status = "정보없음"
        return emails[:2], faxes[:2], status

    except requests.exceptions.Timeout:
        return [], [], "타임아웃"
    except requests.exceptions.ConnectionError:
        return [], [], "접속실패"
    except Exception as e:
        return [], [], f"오류:{type(e).__name__}"

def save_results(results: list, path: str):
    cols = ["회사이름","대표자명","업종명","주소","홈페이지",
            "이메일1","이메일2","팩스1","팩스2","상태"]
    df = pd.DataFrame(results, columns=cols)
    df.to_excel(path, index=False, engine="openpyxl")

def find_col(df, candidates):
    for kw in candidates:
        for col in df.columns:
            if kw in str(col):
                return col
    return None

# ── 메인 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*55)
    print("  홈페이지 크롤링 - 이메일/팩스 자동 수집")
    print("="*55)

    # CSV 읽기
    try:
        df_in = pd.read_csv(INPUT, dtype=str, encoding="utf-8-sig").fillna("")
    except UnicodeDecodeError:
        df_in = pd.read_csv(INPUT, dtype=str, encoding="cp949").fillna("")

    print(f"총 {len(df_in):,}건 로드 완료")
    print("컬럼:", list(df_in.columns))

    # 컬럼 자동 탐지
    col_name = find_col(df_in, ["회사이름","회사명","상호","기업명"])
    col_ceo  = find_col(df_in, ["대표자","대표명"])
    col_biz  = find_col(df_in, ["업종","업종명","업태"])
    col_addr = find_col(df_in, ["주소","소재지"])
    col_url  = find_col(df_in, ["홈페이지","URL","url","website","사이트"])

    if not col_url:
        print("❌ URL 컬럼을 찾지 못했습니다. 컬럼명을 확인하세요:", list(df_in.columns))
        exit(1)

    results = []
    total = len(df_in)
    success = fail = no_info = 0

    print(f"\n크롤링 시작 (총 {total:,}건)...\n")

    for i, row in df_in.iterrows():
        url_raw = str(row.get(col_url, "")).strip()
        url     = clean_url(url_raw)
        name    = row.get(col_name, "") if col_name else ""
        ceo     = row.get(col_ceo,  "") if col_ceo  else ""
        biz     = row.get(col_biz,  "") if col_biz  else ""
        addr    = row.get(col_addr, "") if col_addr else ""

        if not url:
            status = "URL없음"
            emails, faxes = [], []
        else:
            emails, faxes, status = crawl_page(url)
            time.sleep(0.3)  # 서버 부하 방지

        if status == "성공":      success += 1
        elif status == "정보없음": no_info += 1
        else:                      fail    += 1

        results.append([
            name, ceo, biz, addr, url_raw,
            emails[0] if len(emails)>0 else "",
            emails[1] if len(emails)>1 else "",
            faxes[0]  if len(faxes)>0  else "",
            faxes[1]  if len(faxes)>1  else "",
            status,
        ])

        num = i+1
        bar = "█"*int(num/total*30)+"░"*(30-int(num/total*30))
        print(f"\r[{bar}] {num:,}/{total:,}  성공:{success}  실패:{fail}  정보없음:{no_info}", end="", flush=True)

        # 중간 저장
        if num % SAVE_EVERY == 0:
            save_results(results, OUTPUT)
            print(f"\n💾 중간저장 완료 ({num:,}건)")

    print()
    save_results(results, OUTPUT)

    print(f"""
{'='*55}
✅ 크롤링 완료! → {OUTPUT}
  총 처리:   {total:,}건
  성공:      {success:,}건
  정보없음:  {no_info:,}건
  실패:      {fail:,}건
  이메일 수집률: {success/(total or 1)*100:.1f}%
{'='*55}
""")
