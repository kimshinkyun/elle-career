"""
[작업 2] 병원 DB 정제
병원_이메일팩스.xlsx → 병원_발송준비완성.xlsx
실행: python task2_병원정제.py
"""
import pandas as pd
import os

BASE = r"C:\Users\user\Desktop\기업수집"
INPUT  = os.path.join(BASE, "병원_이메일팩스.xlsx")
OUTPUT = os.path.join(BASE, "병원_발송준비완성.xlsx")

WANT_COLS = ["병원종류", "시도", "병원명", "이메일", "팩스", "전화번호"]

print("파일 읽는 중...")
df = pd.read_excel(INPUT, dtype=str).fillna("")

print("원본 컬럼:", list(df.columns))

def find_col(df, candidates):
    for kw in candidates:
        for col in df.columns:
            if kw in str(col):
                return col
    return None

col_map = {
    "병원종류": find_col(df, ["병원종류", "종별", "의원종류", "기관종류", "유형"]),
    "시도":     find_col(df, ["시도", "광역시", "지역", "시·도"]),
    "병원명":   find_col(df, ["병원명", "기관명", "사업장명", "상호"]),
    "이메일":   find_col(df, ["이메일", "EMAIL", "email", "메일"]),
    "팩스":     find_col(df, ["팩스", "FAX", "fax"]),
    "전화번호": find_col(df, ["전화", "TEL", "tel", "연락처", "전화번호"]),
}

for key, val in col_map.items():
    if val is None:
        print(f"⚠ '{key}' 컬럼 자동 탐지 실패 → 빈 컬럼으로 처리")

# 이메일 있는 행만
email_col = col_map["이메일"]
if email_col is None:
    print("❌ 이메일 컬럼을 찾지 못했습니다. 스크립트를 종료합니다.")
    exit(1)

df_filtered = df[df[email_col].str.strip() != ""].copy()

# 원하는 컬럼 추출 (없으면 빈 컬럼 추가)
result = pd.DataFrame()
for want in WANT_COLS:
    src = col_map.get(want)
    result[want] = df_filtered[src].values if src else ""

result = result.reset_index(drop=True)

result.to_excel(OUTPUT, index=False, engine="openpyxl")

print(f"""
✅ 완료! → {OUTPUT}
  이메일 보유 병원: {len(result)}건 추출
  컬럼: {WANT_COLS}
""")
