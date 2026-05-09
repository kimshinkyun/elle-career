"""
[작업 3] 전국 제조업 DB 정제
수집결과.xlsx → 제조업_이메일발송준비.xlsx
실행: python task3_제조업정제.py
"""
import pandas as pd
import os

BASE = r"C:\Users\user\Desktop\기업수집"
INPUT  = os.path.join(BASE, "수집결과.xlsx")
OUTPUT = os.path.join(BASE, "제조업_이메일발송준비.xlsx")

WANT_COLS = ["업종명", "회사이름", "대표자명", "주소", "이메일", "팩스"]

print("파일 읽는 중...")
df = pd.read_excel(INPUT, dtype=str).fillna("")
print("원본 컬럼:", list(df.columns))
print(f"원본 전체 행수: {len(df):,}")

def find_col(df, candidates):
    for kw in candidates:
        for col in df.columns:
            if kw in str(col):
                return col
    return None

col_map = {
    "업종명":   find_col(df, ["업종명", "업종", "업태", "종목"]),
    "회사이름": find_col(df, ["회사이름", "회사명", "상호", "기업명", "사업장명"]),
    "대표자명": find_col(df, ["대표자", "대표명", "대표이름"]),
    "주소":     find_col(df, ["주소", "사업장주소", "소재지"]),
    "이메일":   find_col(df, ["이메일", "EMAIL", "email", "메일"]),
    "팩스":     find_col(df, ["팩스", "FAX", "fax"]),
}

for key, val in col_map.items():
    if val is None:
        print(f"⚠ '{key}' 컬럼 자동 탐지 실패 → 빈 컬럼으로 처리")

email_col = col_map["이메일"]
if email_col is None:
    print("❌ 이메일 컬럼을 찾지 못했습니다. 스크립트를 종료합니다.")
    exit(1)

# 이메일 있는 행만
df_filtered = df[df[email_col].str.strip() != ""].copy()

result = pd.DataFrame()
for want in WANT_COLS:
    src = col_map.get(want)
    result[want] = df_filtered[src].values if src else ""

result = result.reset_index(drop=True)

# 중복 이메일 제거
before = len(result)
result = result.drop_duplicates(subset=["이메일"]).reset_index(drop=True)
after = len(result)

result.to_excel(OUTPUT, index=False, engine="openpyxl")

print(f"""
✅ 완료! → {OUTPUT}
  원본: {len(df):,}건
  이메일 보유: {before:,}건
  중복 제거 후: {after:,}건
  컬럼: {WANT_COLS}
""")
