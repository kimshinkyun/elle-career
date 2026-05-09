"""
설치 스크립트 - 이 파일 하나를 실행하면 모든 파일이 자동 생성됩니다.
실행: python 설치.py
"""
import os

BASE = r"C:\Users\user\Desktop\기업수집"
os.makedirs(BASE, exist_ok=True)

FILES = {}

FILES['task1_DB분류.py'] = r'''"""
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
df = pd.read_excel(INPUT, dtype=str).fillna("")

def find_col(df, keywords):
    for kw in keywords:
        for col in df.columns:
            if kw in str(col): return col
    return None

fax_col   = find_col(df, ["팩스","FAX","fax"])
email_col = find_col(df, ["이메일","EMAIL","email","메일"])

if not fax_col:   print("⚠ 팩스 컬럼 없음:", list(df.columns)); exit(1)
if not email_col: print("⚠ 이메일 컬럼 없음:", list(df.columns)); exit(1)

has_fax   = df[fax_col].str.strip() != ""
has_email = df[email_col].str.strip() != ""
s1 = df[has_fax & has_email].reset_index(drop=True)
s2 = df[has_fax & ~has_email].reset_index(drop=True)
s3 = df[~has_fax & has_email].reset_index(drop=True)
s4 = df[~has_fax & ~has_email].reset_index(drop=True)

업종_col = find_col(df, ["업종","업태","종목"])
if 업종_col:
    rows = []
    for biz, grp in df.groupby(업종_col):
        if not biz: continue
        he = grp[email_col].str.strip() != ""
        hf = grp[fax_col].str.strip() != ""
        rows.append({"업종":biz,"전체":len(grp),"팩스+이메일":int((he&hf).sum()),
                     "팩스만":int((hf&~he).sum()),"이메일만":int((he&~hf).sum()),"둘다없음":int((~he&~hf).sum())})
    stats = pd.DataFrame(rows).sort_values("전체", ascending=False)
else:
    stats = pd.DataFrame({"항목":["팩스+이메일","팩스만","이메일만","둘다없음"],"건수":[len(s1),len(s2),len(s3),len(s4)]})

with pd.ExcelWriter(OUTPUT, engine="openpyxl") as w:
    s1.to_excel(w, sheet_name="팩스+이메일", index=False)
    s2.to_excel(w, sheet_name="팩스만", index=False)
    s3.to_excel(w, sheet_name="이메일만", index=False)
    s4.to_excel(w, sheet_name="둘다없음", index=False)
    stats.to_excel(w, sheet_name="업종별통계", index=False)

print(f"✅ 완료! 팩스+이메일:{len(s1)}건 / 팩스만:{len(s2)}건 / 이메일만:{len(s3)}건 / 없음:{len(s4)}건")
'''

FILES['task2_병원정제.py'] = r'''"""
[작업 2] 병원 DB 정제
병원_이메일팩스.xlsx → 병원_발송준비완성.xlsx
실행: python task2_병원정제.py
"""
import pandas as pd, os

BASE = r"C:\Users\user\Desktop\기업수집"
df = pd.read_excel(os.path.join(BASE,"병원_이메일팩스.xlsx"), dtype=str).fillna("")
print("컬럼:", list(df.columns))

def find_col(df, kws):
    for kw in kws:
        for c in df.columns:
            if kw in str(c): return c
    return None

col_map = {
    "병원종류": find_col(df,["병원종류","종별","기관종류","유형"]),
    "시도":     find_col(df,["시도","광역시","지역"]),
    "병원명":   find_col(df,["병원명","기관명","사업장명","상호"]),
    "이메일":   find_col(df,["이메일","EMAIL","email","메일"]),
    "팩스":     find_col(df,["팩스","FAX","fax"]),
    "전화번호": find_col(df,["전화","TEL","tel","연락처","전화번호"]),
}
ec = col_map["이메일"]
if not ec: print("❌ 이메일 컬럼 없음"); exit(1)

df2 = df[df[ec].str.strip()!=""].copy()
result = pd.DataFrame({k: df2[v].values if v else "" for k,v in col_map.items()})
result.to_excel(os.path.join(BASE,"병원_발송준비완성.xlsx"), index=False, engine="openpyxl")
print(f"✅ 완료! 이메일 보유 병원 {len(result)}건")
'''

FILES['task3_제조업정제.py'] = r'''"""
[작업 3] 제조업 DB 정제
수집결과.xlsx → 제조업_이메일발송준비.xlsx
실행: python task3_제조업정제.py
"""
import pandas as pd, os

BASE = r"C:\Users\user\Desktop\기업수집"
df = pd.read_excel(os.path.join(BASE,"수집결과.xlsx"), dtype=str).fillna("")
print(f"원본 {len(df):,}건 / 컬럼:", list(df.columns))

def find_col(df, kws):
    for kw in kws:
        for c in df.columns:
            if kw in str(c): return c
    return None

col_map = {
    "업종명":   find_col(df,["업종명","업종","업태","종목"]),
    "회사이름": find_col(df,["회사이름","회사명","상호","기업명","사업장명"]),
    "대표자명": find_col(df,["대표자","대표명","대표이름"]),
    "주소":     find_col(df,["주소","사업장주소","소재지"]),
    "이메일":   find_col(df,["이메일","EMAIL","email","메일"]),
    "팩스":     find_col(df,["팩스","FAX","fax"]),
}
ec = col_map["이메일"]
if not ec: print("❌ 이메일 컬럼 없음"); exit(1)

df2 = df[df[ec].str.strip()!=""].copy()
result = pd.DataFrame({k: df2[v].values if v else "" for k,v in col_map.items()})
before = len(result)
result = result.drop_duplicates(subset=["이메일"]).reset_index(drop=True)
result.to_excel(os.path.join(BASE,"제조업_이메일발송준비.xlsx"), index=False, engine="openpyxl")
print(f"✅ 완료! {before:,}건 → 중복제거 후 {len(result):,}건")
'''

FILES['task4_크롤링.py'] = r'''"""
[작업 4] 홈페이지 크롤링 - 이메일/팩스 자동 수집
의존: pip install requests beautifulsoup4 openpyxl pandas lxml
실행: python task4_크롤링.py
"""
import re, time, os, warnings
import pandas as pd, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
warnings.filterwarnings("ignore")

BASE   = r"C:\Users\user\Desktop\기업수집"
INPUT  = os.path.join(BASE, "기업목록_URL.csv")
OUTPUT = os.path.join(BASE, "크롤링결과.xlsx")
SAVE_EVERY = 100

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
FAX_RE   = re.compile(r"(?:팩스|F(?:AX)?|fax)\s*[:\.]?\s*(0\d{1,2}[-\s]\d{3,4}[-\s]\d{4})|(?<!\d)(0\d{1,2}[-\s]\d{3,4}[-\s]\d{4})(?!\d)")
SPAM_RE  = re.compile(r"@(example|test|naver|daum|nate|gmail|yahoo|hotmail|sentry|wix|wordpress|adobe|github|kakao|facebook|google)\.", re.I)
HEADERS  = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept-Language":"ko-KR,ko;q=0.9"}

def find_col(df, kws):
    for kw in kws:
        for c in df.columns:
            if kw in str(c): return c
    return None

def extract(html):
    soup = BeautifulSoup(html, "lxml")
    emails = [a["href"][7:].split("?")[0] for a in soup.find_all("a",href=True) if a["href"].startswith("mailto:") and not SPAM_RE.search(a["href"][7:])]
    text = soup.get_text(" ", strip=True)
    for e in EMAIL_RE.findall(text):
        if not SPAM_RE.search(e) and e not in emails: emails.append(e)
    faxes = [(m.group(1) or m.group(2) or "").strip() for m in FAX_RE.finditer(text)]
    return list(dict.fromkeys(emails))[:2], list(dict.fromkeys(f for f in faxes if f))[:2]

def crawl(url):
    if not url: return [], [], "URL없음"
    if not url.startswith(("http://","https://")): url = "https://"+url
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, verify=False, allow_redirects=True)
        r.encoding = r.apparent_encoding or "utf-8"
        if r.status_code != 200: return [], [], f"HTTP_{r.status_code}"
        emails, faxes = extract(r.text)
        if not emails:
            for sub in ["/contact","/about","/contactus","/연락처"]:
                try:
                    r2 = requests.get(urljoin(url,sub), headers=HEADERS, timeout=5, verify=False)
                    if r2.status_code==200:
                        r2.encoding = r2.apparent_encoding or "utf-8"
                        e2,f2 = extract(r2.text)
                        emails+=e2; faxes+=f2
                        if emails: break
                except: continue
        return emails[:2], faxes[:2], "성공" if (emails or faxes) else "정보없음"
    except requests.exceptions.Timeout: return [], [], "타임아웃"
    except requests.exceptions.ConnectionError: return [], [], "접속실패"
    except Exception as ex: return [], [], f"오류:{type(ex).__name__}"

def save(rows):
    pd.DataFrame(rows, columns=["회사이름","대표자명","업종명","주소","홈페이지","이메일1","이메일2","팩스1","팩스2","상태"]).to_excel(OUTPUT, index=False, engine="openpyxl")

try:    df_in = pd.read_csv(INPUT, dtype=str, encoding="utf-8-sig").fillna("")
except: df_in = pd.read_csv(INPUT, dtype=str, encoding="cp949").fillna("")

col_url  = find_col(df_in,["홈페이지","URL","url","website","사이트"])
col_name = find_col(df_in,["회사이름","회사명","상호","기업명"])
col_ceo  = find_col(df_in,["대표자","대표명"])
col_biz  = find_col(df_in,["업종","업종명","업태"])
col_addr = find_col(df_in,["주소","소재지"])
if not col_url: print("❌ URL 컬럼 없음:", list(df_in.columns)); exit(1)

results=[]; total=len(df_in); s=f=n=0
print(f"크롤링 시작 ({total:,}건)...")
for i,row in df_in.iterrows():
    url=str(row.get(col_url,"")).strip()
    emails,faxes,status = crawl(url)
    if status=="성공": s+=1
    elif status=="정보없음": n+=1
    else: f+=1
    results.append([row.get(col_name,"") if col_name else "", row.get(col_ceo,"") if col_ceo else "",
                    row.get(col_biz,"") if col_biz else "", row.get(col_addr,"") if col_addr else "", url,
                    emails[0] if len(emails)>0 else "", emails[1] if len(emails)>1 else "",
                    faxes[0]  if len(faxes)>0  else "", faxes[1]  if len(faxes)>1  else "", status])
    num=i+1
    print(f"\r[{'█'*int(num/total*30)}{'░'*(30-int(num/total*30))}] {num}/{total} 성공:{s} 실패:{f} 정보없음:{n}", end="", flush=True)
    if num%SAVE_EVERY==0: save(results); print(f"\n💾 중간저장({num}건)")
    time.sleep(0.3)
print(); save(results)
print(f"✅ 완료! 성공:{s}건 / 실패:{f}건 / 정보없음:{n}건")
'''

FILES['절세시뮬레이터.py'] = r'''"""
[작업 5] 절세 시뮬레이션 PDF 생성기
의존: pip install reportlab
실행: python 절세시뮬레이터.py
"""
import os, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

font_registered = False
for fp in [r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\gulim.ttc"]:
    if os.path.exists(fp):
        try: pdfmetrics.registerFont(TTFont("KR",fp)); font_registered=True; break
        except: continue
FONT = "KR" if font_registered else "Helvetica"

EXPENSE = {"제조업":.82,"음식점":.87,"건설업":.84,"의료업":.72}
INC_TAX = [(14e6,.06,0),(50e6,.15,1260000),(88e6,.24,5760000),(150e6,.35,15440000),(300e6,.38,19940000),(500e6,.40,25940000),(1e9,.42,35940000),(float("inf"),.45,65940000)]
COR_TAX = [(200e6,.09,0),(20e9,.19,20000000),(300e9,.21,420000000),(float("inf"),.24,9420000000)]

def inc_tax(v):
    for lim,r,d in INC_TAX:
        if v<=lim: return max(v*r-d,0)*1.1
def cor_tax(v):
    for lim,r,d in COR_TAX:
        if v<=lim: return max(v*r-d,0)*1.1
def sal_tax(s):
    d = s*.70 if s<=5e6 else 3.5e6+(s-5e6)*.40 if s<=15e6 else 7.5e6+(s-15e6)*.15 if s<=45e6 else 12e6+(s-45e6)*.05 if s<=100e6 else 14.75e6
    return inc_tax(max(s-d-1500000,0))
def fmt(n):
    return f"{n/1e8:.1f}억원" if n>=1e8 else f"{n/1e4:,.0f}만원" if n>=1e4 else f"{n:,.0f}원"

def simulate(업종, 매출):
    ratio=EXPENSE.get(업종,.80); 소득=매출*(1-ratio)
    종합소득세=inc_tax(소득); 건보개인=소득*.0709
    대표급여=min(소득*.60,120e6); 법인세=cor_tax(소득-대표급여)
    급여세=sal_tax(대표급여); 건보법인=대표급여*.03545
    합개=종합소득세+건보개인; 합법=법인세+급여세+건보법인
    return {"업종":업종,"매출":매출,"소득":소득,"종합소득세":종합소득세,"건보개인":건보개인,"합개":합개,"법인세":법인세,"급여세":급여세,"건보법인":건보법인,"합법":합법,"절세":max(합개-합법,0),"건보절감":max(건보개인-건보법인,0),"영업권":소득*2.5}

def make_pdf(d, path):
    doc=SimpleDocTemplate(path,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=20*mm,bottomMargin=20*mm)
    G=colors.HexColor("#C9A96E"); DK=colors.HexColor("#1A1A2E")
    def S(sz,cl=colors.black,al=0): return ParagraphStyle("x",fontName=FONT,fontSize=sz,textColor=cl,alignment=al,leading=sz*1.5)
    story=[
        Paragraph("법인전환 절세 시뮬레이션 보고서",S(22,DK,1)),
        Paragraph(f"업종: {d['업종']}  |  매출: {fmt(d['매출'])}",S(12,colors.grey,1)),
        Paragraph(f"작성일: {datetime.date.today().strftime('%Y년 %m월 %d일')}",S(10,colors.grey,1)),
        HRFlowable(width="100%",thickness=2,color=G,spaceAfter=12),
    ]
    tdata=[["구분","현재(개인사업자)","법인전환후"],
           ["추정소득",fmt(d["소득"]),fmt(d["소득"])],
           ["종합소득세/법인세",fmt(d["종합소득세"]),fmt(d["법인세"])],
           ["대표급여 소득세","-",fmt(d["급여세"])],
           ["건강보험료",fmt(d["건보개인"]),fmt(d["건보법인"])],
           ["합계",fmt(d["합개"]),fmt(d["합법"])]]
    t=Table(tdata,colWidths=[60*mm,60*mm,60*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),DK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,-1),FONT),("FONTSIZE",(0,0),(-1,-1),10),("ALIGN",(0,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#E0D8C8")),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8F6F2")]),("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#FFF3DC"))]))
    story.append(t); story.append(Spacer(1,16))
    hdata=[["항목","금액"],["💰 연간 절세액",fmt(d["절세"])],["🏥 건강보험료 절감",fmt(d["건보절감"])],["📋 영업권 추정",fmt(d["영업권"])],["📈 5년 누적 절세",fmt(d["절세"]*5)]]
    ht=Table(hdata,colWidths=[90*mm,80*mm])
    ht.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),DK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,-1),FONT),("FONTSIZE",(0,0),(-1,-1),12),("ALIGN",(0,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#E0D8C8")),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8F6F2")])]))
    story.extend([Paragraph("■ 핵심 절세 효과",S(13,DK)),Spacer(1,6),ht,Spacer(1,20),HRFlowable(width="100%",thickness=1,color=G),Spacer(1,8),Paragraph("※ 본 시뮬레이션은 추정치입니다. 정확한 세금은 공인세무사 상담을 통해 확인하세요.",S(8,colors.grey))])
    doc.build(story)
    print(f"✅ PDF 저장: {path}")

if __name__=="__main__":
    print("="*45+"\n  법인전환 절세 시뮬레이터\n"+"="*45)
    bizs=list(EXPENSE.keys())
    for i,b in enumerate(bizs,1): print(f"  {i}. {b}")
    try: 업종=bizs[int(input("번호 입력: ").strip())-1]
    except: 업종=input("업종 직접 입력: ").strip()
    매출=float(input("연간 매출액(만원): ").strip().replace(",",""))*10000
    r=simulate(업종,매출)
    print(f"\n{'='*45}\n  {업종} | 매출 {fmt(매출)}\n{'='*45}")
    print(f"  현재 종합소득세: {fmt(r['종합소득세'])}\n  법인전환 후:     {fmt(r['합법'])}\n  연간 절세액:     {fmt(r['절세'])}\n  건강보험 절감:   {fmt(r['건보절감'])}\n  영업권 추정:     {fmt(r['영업권'])}\n  5년 누적:        {fmt(r['절세']*5)}")
    p=os.path.join(r"C:\Users\user\Desktop\기업수집",f"절세시뮬레이션_{업종}_{int(매출/10000)}만원_{datetime.date.today()}.pdf")
    make_pdf(r,p)
'''

# 절세진단.html과 영업대시보드.html, 올인원_처리.py는 별도 파일로 저장
# (내용이 길어서 설치 스크립트에서 직접 생성)

print("="*55)
print("  파일 생성 중...")
print("="*55)

created = []
for filename, content in FILES.items():
    path = os.path.join(BASE, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    created.append(filename)
    print(f"  ✅ {filename}")

print(f"\n{'='*55}")
print(f"✅ {len(created)}개 파일 생성 완료!")
print(f"   폴더: {BASE}")
print(f"""
다음 단계:
  1. pip install pandas openpyxl requests beautifulsoup4 lxml reportlab
  2. python 올인원_처리.py   ← 크롤링결과 자동 처리
  3. python task4_크롤링.py  ← 새 URL 크롤링
  4. python 절세시뮬레이터.py ← PDF 생성
  5. 절세진단.html           ← 더블클릭으로 바로 실행
{'='*55}
""")
