"""
[작업 1] DB 정제 및 분류
여수_개인사업자_결과.xlsx → DB분류완성.xlsx
실행: python task1_DB분류.py
"""
import pandas as pd
import os

BASE = r"C:\Users\user\Desktop\기업수집"
INPUT = os.path.join(BASE, "여수_개인사업자_결과.xlsx")
OUTPUT = os.path.join(BASE, "DB분류완성.xlsx")

print("파일 읽는 중...")
df = pd.read_excel(INPUT, dtype=str)
df = df.fillna("")

# 팩스·이메일 컬럼 자동 탐지
def find_col(df, keywords):
    for kw in keywords:
        for col in df.columns:
            if kw in str(col):
                return col
    return None

fax_col   = find_col(df, ["팩스", "FAX", "fax"])
email_col = find_col(df, ["이메일", "EMAIL", "email", "메일"])

if not fax_col:
    print("⚠ 팩스 컬럼을 찾지 못했습니다. 컬럼 목록:", list(df.columns))
    exit(1)
if not email_col:
    print("⚠ 이메일 컬럼을 찾지 못했습니다. 컬럼 목록:", list(df.columns))
    exit(1)

print(f"팩스 컬럼: {fax_col}  /  이메일 컬럼: {email_col}")

has_fax   = df[fax_col].str.strip() != ""
has_email = df[email_col].str.strip() != ""

sheet1 = df[has_fax & has_email].reset_index(drop=True)
sheet2 = df[has_fax & ~has_email].reset_index(drop=True)
sheet3 = df[~has_fax & has_email].reset_index(drop=True)
sheet4 = df[~has_fax & ~has_email].reset_index(drop=True)

# 업종별 통계
업종_col = find_col(df, ["업종", "업태", "종목"])
if 업종_col:
    stats = df.groupby(업종_col).agg(
        전체수=(업종_col, "count"),
        팩스이메일둘다=(fax_col, lambda x: ((x.str.strip() != "") & (df.loc[x.index, email_col].str.strip() != "")).sum()),
        팩스만=(fax_col, lambda x: ((x.str.strip() != "") & (df.loc[x.index, email_col].str.strip() == "")).sum()),
        이메일만=(email_col, lambda x: ((x.str.strip() != "") & (df.loc[x.index, fax_col].str.strip() == "")).sum()),
        둘다없음=(fax_col, lambda x: ((x.str.strip() == "") & (df.loc[x.index, email_col].str.strip() == "")).sum()),
    ).reset_index()
else:
    stats = pd.DataFrame({
        "항목": ["팩스+이메일", "팩스만", "이메일만", "둘다없음"],
        "건수": [len(sheet1), len(sheet2), len(sheet3), len(sheet4)],
    })

print("엑셀 저장 중...")
with pd.ExcelWriter(OUTPUT, engine="openpyxl") as w:
    sheet1.to_excel(w, sheet_name="팩스+이메일", index=False)
    sheet2.to_excel(w, sheet_name="팩스만", index=False)
    sheet3.to_excel(w, sheet_name="이메일만", index=False)
    sheet4.to_excel(w, sheet_name="둘다없음", index=False)
    stats.to_excel(w, sheet_name="업종별통계", index=False)

print(f"""
✅ 완료! → {OUTPUT}
  시트1 (팩스+이메일): {len(sheet1)}건
  시트2 (팩스만):      {len(sheet2)}건
  시트3 (이메일만):    {len(sheet3)}건
  시트4 (둘다없음):    {len(sheet4)}건
  시트5 (업종별통계):  저장완료
""")
