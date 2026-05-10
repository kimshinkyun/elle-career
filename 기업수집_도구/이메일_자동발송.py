"""
[방법 C-1] 이메일 자동 발송 스크립트
수집 DB (이메일발송준비.xlsx 또는 크롤링결과.xlsx) → 업종별 맞춤 이메일 자동 발송

설치: pip install pandas openpyxl
실행: python 이메일_자동발송.py
"""

import smtplib, ssl, time, os, csv, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import pandas as pd
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════
# ▼▼▼ 설정 (여기만 수정) ▼▼▼
# ══════════════════════════════════════════════

SMTP_CONFIG = {
    # Gmail 사용 시:
    #   1. Google 계정 → 보안 → 2단계 인증 ON
    #   2. 앱 비밀번호 생성 (16자리) → PASS 에 입력
    "HOST"  : "smtp.gmail.com",
    "PORT"  : 587,
    "USER"  : "tlsrbs3000@gmail.com",
    "PASS"  : "irguvuthntfytoud",
    # Naver 사용 시: HOST = "smtp.naver.com", PORT = 587
}

SENDER_NAME  = "법인전환 전문 컨설턴트"        # 발신자 이름
REPLY_TO     = "tlsrbs3000@gmail.com"
KAKAO_CHANNEL= "[카카오채널명]"                # 카카오채널 이름
PHONE        = "010-0000-0000"               # 연락처

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
LOG_FILE     = os.path.join(BASE_DIR, "발송기록.csv")

DAILY_LIMIT  = 80     # 하루 최대 발송 수 (Gmail 한도: 500, 안전하게 80~100)
DELAY_MIN    = 8      # 발송 간 최소 대기(초) - 스팸 필터 우회
DELAY_MAX    = 20     # 발송 간 최대 대기(초)

# ══════════════════════════════════════════════
# 업종별 이메일 템플릿
# ══════════════════════════════════════════════

def get_template(industry: str, name: str) -> tuple[str, str]:
    """(제목, 본문HTML) 반환"""

    name_str = name.strip() or "사장"

    industry_lower = str(industry).lower()

    if any(k in industry_lower for k in ["제조", "manufacturing"]):
        subject = f"[{name_str}] 제조업 사장님을 위한 절세 시뮬레이션 (무료)"
        point = "제조업 특성상 설비·인건비 비용 구조를 활용하면 법인 전환 시 절세 효과가 매우 큽니다."

    elif any(k in industry_lower for k in ["도매", "소매", "유통", "retail"]):
        subject = f"[{name_str}] 도소매업 절세 전략 — 법인전환 무료 진단"
        point = "도소매업은 재고·물류 비용을 법인 구조에서 최적화하면 연간 수백만원 절세가 가능합니다."

    elif any(k in industry_lower for k in ["음식", "식당", "카페", "요식", "외식"]):
        subject = f"[{name_str}] 음식업 건보료·세금 합법적으로 줄이는 방법"
        point = "음식업은 건강보험료 절감 효과가 특히 큽니다. 법인 전환 시 직장가입자로 전환되어 보험료가 대폭 줄어듭니다."

    elif any(k in industry_lower for k in ["병원", "의원", "치과", "한의", "의료", "클리닉"]):
        subject = f"[{name_str}] 의원 원장님의 세금 부담을 줄여드립니다 (무료 진단)"
        point = "의원 원장님들의 경우 일반 법인 구조 활용으로 소득세와 건보료를 합법적으로 크게 줄일 수 있습니다."

    elif any(k in industry_lower for k in ["건설", "인테리어", "시공", "건축"]):
        subject = f"[{name_str}] 건설업 법인전환 — 입찰·절세 동시 해결"
        point = "건설업은 법인이어야 유리한 입찰이 많습니다. 절세와 사업 확장을 동시에 해결하는 방법을 안내드립니다."

    else:
        subject = f"[{name_str}] 사장님, 세금 연 1,500만원 절약하는 방법이 있습니다"
        point = "업종에 맞는 법인 구조 설계로 소득세, 건보료, 퇴직금까지 한번에 최적화할 수 있습니다."

    body_html = f"""
<html><body style="font-family:Malgun Gothic,Arial,sans-serif;font-size:14px;color:#1e293b;line-height:1.8;max-width:600px;margin:0 auto;padding:20px;">

<div style="background:linear-gradient(135deg,#0f2d6b,#1b4f9b);color:white;padding:20px 24px;border-radius:10px 10px 0 0;">
  <h2 style="margin:0;font-size:18px;">법인전환 절세 진단 서비스</h2>
  <p style="margin:6px 0 0;font-size:13px;opacity:.85;">연매출 3억 이상 개인사업자를 위한 맞춤 절세 전략</p>
</div>

<div style="background:#ffffff;border:1px solid #e2e8f0;border-top:none;padding:24px;border-radius:0 0 10px 10px;">

  <p>안녕하세요, <strong>{name_str} 사장님</strong>. 😊</p>
  <p>저는 법인전환 전문 컨설턴트로, 지역 내 중소사업자분들의 절세를 돕고 있습니다.</p>
  <p>{point}</p>

  <div style="background:#f0f9ff;border-left:4px solid #1b4f9b;padding:14px 18px;margin:18px 0;border-radius:0 8px 8px 0;">
    <strong>무료 절세 진단 시 제공 내용</strong><br>
    ✅ 현재 세금 부담 분석<br>
    ✅ 법인전환 시 예상 절세액 계산<br>
    ✅ 건강보험료 절감 방법 안내<br>
    ✅ 전환 시기 및 절차 안내
  </div>

  <div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:14px 18px;border-radius:8px;margin:18px 0;text-align:center;">
    <p style="margin:0;font-size:16px;font-weight:700;color:#065f46;">연평균 절세액: 1,500만 ~ 2,500만원</p>
    <p style="margin:4px 0 0;font-size:12px;color:#047857;">상담 후 효과 없으면 진행하지 않으셔도 됩니다.</p>
  </div>

  <p>부담 없이 연락 주시면 <strong>무료로 시뮬레이션</strong> 해드립니다.</p>
  <p>강요 없이 정보만 드리는 방식으로 진행합니다 🙏</p>

  <div style="text-align:center;margin:24px 0 16px;">
    <a href="https://pf.kakao.com/_채널ID"
       style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#ef4444);color:white;padding:14px 32px;border-radius:30px;text-decoration:none;font-weight:700;font-size:15px;">
      💬 무료 상담 신청하기
    </a>
  </div>

  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
  <p style="font-size:12px;color:#64748b;">
    📞 {PHONE} &nbsp;|&nbsp; 💬 카카오채널: {KAKAO_CHANNEL}<br>
    평일 09:00~18:00 운영 | 이 메일을 원하지 않으시면 회신해주세요.
  </p>
</div>

</body></html>"""

    return subject, body_html


# ══════════════════════════════════════════════
# 발송 기록 관리
# ══════════════════════════════════════════════

def load_sent_emails() -> set:
    sent = set()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                sent.add(row.get("이메일", "").strip().lower())
    return sent

def log_sent(email: str, name: str, industry: str, status: str):
    is_new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["발송일시", "이메일", "회사이름", "업종", "상태"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email, name, industry, status])


# ══════════════════════════════════════════════
# 이메일 발송
# ══════════════════════════════════════════════

def send_email(smtp, sender_email: str, to_email: str, subject: str, body_html: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"]    = f"{SENDER_NAME} <{sender_email}>"
        msg["To"]      = to_email
        msg["Reply-To"]= REPLY_TO
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        smtp.sendmail(sender_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  ❌ 발송 실패: {e}")
        return False


# ══════════════════════════════════════════════
# 입력 파일 자동 탐지
# ══════════════════════════════════════════════

def find_input_file() -> str | None:
    candidates = [
        "이메일발송준비.xlsx",
        "이메일발송준비_*.xlsx",
        "크롤링결과*.xlsx",
        "DB분류완성.xlsx",
    ]
    from glob import glob
    for pattern in candidates:
        matches = glob(os.path.join(BASE_DIR, pattern))
        if matches:
            return sorted(matches)[-1]
    return None


# ══════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════

def main():
    print("=" * 55)
    print("  이메일 자동 발송 스크립트")
    print("=" * 55)

    if "여기에" in SMTP_CONFIG["USER"]:
        print("""
❌ 이메일 설정이 필요합니다.

▶ Gmail 앱 비밀번호 발급:
  1. Google 계정 → 보안 → 2단계 인증 ON
  2. Google 계정 → 보안 → 앱 비밀번호
  3. 앱: 메일 / 기기: Windows → 생성
  4. 이 파일 상단 SMTP_CONFIG 에 붙여넣기

▶ Naver 사용 시:
  HOST: smtp.naver.com / PORT: 587
  PASS: 네이버 로그인 비밀번호
""")
        return

    # 입력 파일 탐지
    input_file = find_input_file()
    if not input_file:
        print(f"❌ 발송할 엑셀 파일을 찾지 못했습니다.\n   {BASE_DIR} 폴더에 이메일발송준비.xlsx 또는 크롤링결과.xlsx 가 있어야 합니다.")
        return

    print(f"📂 입력 파일: {os.path.basename(input_file)}")

    # 데이터 로드
    try:
        df = pd.read_excel(input_file, dtype=str).fillna("")
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")
        return

    # 컬럼 탐지
    def find_col(keywords):
        for kw in keywords:
            for c in df.columns:
                if kw in str(c):
                    return c
        return None

    c_email   = find_col(["이메일1", "이메일", "EMAIL"])
    c_email2  = find_col(["이메일2"])
    c_name    = find_col(["회사이름", "회사명", "상호"])
    c_biz     = find_col(["업종명", "업종", "업태"])

    if not c_email:
        print("❌ 이메일 컬럼을 찾지 못했습니다.")
        return

    print(f"총 {len(df):,}건 로드 완료")

    # 이미 발송한 이메일 로드
    sent_set = load_sent_emails()
    print(f"이미 발송: {len(sent_set):,}건 (중복 제외)")

    # 발송 대상 필터
    rows = []
    for _, row in df.iterrows():
        emails = []
        for col in [c_email, c_email2]:
            if col and row.get(col, "").strip():
                emails.append(row[col].strip())
        for em in emails:
            if em.lower() not in sent_set and "@" in em:
                rows.append({
                    "email"   : em,
                    "name"    : row.get(c_name, "") if c_name else "",
                    "industry": row.get(c_biz,  "") if c_biz  else "",
                })

    if not rows:
        print("\n✅ 모든 업체에 이미 발송 완료되었습니다.")
        return

    today_limit = min(DAILY_LIMIT, len(rows))
    print(f"발송 예정: {today_limit:,}건 (오늘 한도: {DAILY_LIMIT})\n")

    # SMTP 연결
    try:
        context = ssl.create_default_context()
        smtp = smtplib.SMTP(SMTP_CONFIG["HOST"], SMTP_CONFIG["PORT"], timeout=15)
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.login(SMTP_CONFIG["USER"], SMTP_CONFIG["PASS"])
        print("📧 SMTP 연결 성공!\n")
    except Exception as e:
        print(f"❌ SMTP 연결 실패: {e}\n앱 비밀번호와 계정 설정을 확인하세요.")
        return

    success = fail = 0

    try:
        for i, item in enumerate(rows[:today_limit]):
            em       = item["email"]
            name     = item["name"]
            industry = item["industry"]

            subject, body_html = get_template(industry, name)

            ok = send_email(smtp, SMTP_CONFIG["USER"], em, subject, body_html)
            status = "성공" if ok else "실패"
            log_sent(em, name, industry, status)

            if ok:
                success += 1
                print(f"  ✅ [{i+1}/{today_limit}] {em[:30]:<32} ({industry or '업종불명'})")
            else:
                fail += 1
                print(f"  ❌ [{i+1}/{today_limit}] {em[:30]:<32} 실패")

            # 마지막 발송이 아니면 랜덤 대기
            if i < today_limit - 1:
                wait = random.uniform(DELAY_MIN, DELAY_MAX)
                time.sleep(wait)

    finally:
        smtp.quit()

    print(f"""
{'='*55}
✅ 발송 완료
  성공: {success:,}건
  실패: {fail:,}건
  기록: {LOG_FILE}
{'='*55}

내일 다시 실행하면 남은 업체들에게 이어서 발송합니다.
""")


if __name__ == "__main__":
    main()
