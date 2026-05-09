"""
올인원 처리기 - 크롤링결과 엑셀 하나로 전부 처리
의존: pip install pandas openpyxl
실행: python 올인원_처리.py
"""
import pandas as pd
import os, json, datetime, glob

BASE   = r"C:\Users\user\Desktop\기업수집"

# 크롤링결과 파일 자동 탐지 (날짜 상관없이)
pattern = os.path.join(BASE, "크롤링결과*.xlsx")
files   = sorted(glob.glob(pattern), reverse=True)
if not files:
    print("❌ 크롤링결과*.xlsx 파일을 찾지 못했습니다.")
    print("   경로 확인:", BASE)
    exit(1)

INPUT = files[0]
print(f"📂 파일 발견: {os.path.basename(INPUT)}")

# ── 파일 읽기 ──────────────────────────────────────────────────
print("\n파일 읽는 중...")
df = pd.read_excel(INPUT, dtype=str).fillna("")
print(f"총 {len(df):,}행 / 컬럼: {list(df.columns)}")

def find_col(df, candidates):
    for kw in candidates:
        for col in df.columns:
            if kw in str(col):
                return col
    return None

# 컬럼 자동 탐지
c_name  = find_col(df, ["회사이름","회사명","상호","기업명","사업장명"])
c_ceo   = find_col(df, ["대표자","대표명"])
c_biz   = find_col(df, ["업종","업종명","업태","종목"])
c_addr  = find_col(df, ["주소","소재지","사업장주소"])
c_web   = find_col(df, ["홈페이지","URL","url","website","사이트"])
c_email1= find_col(df, ["이메일1","이메일","EMAIL","email","메일"])
c_email2= find_col(df, ["이메일2"])
c_fax1  = find_col(df, ["팩스1","팩스","FAX","fax"])
c_fax2  = find_col(df, ["팩스2"])
c_status= find_col(df, ["상태","status"])

print(f"\n컬럼 매핑:")
print(f"  회사이름: {c_name}  /  업종: {c_biz}  /  이메일: {c_email1}  /  팩스: {c_fax1}")

# 이메일·팩스 유무 판별
def has(col):
    if col is None:
        return pd.Series([False] * len(df))
    s = df[col].str.strip()
    # 이메일2/팩스2 있으면 합산
    s2_col = {"이메일1": c_email2, "팩스1": c_fax2}.get(col)
    if s2_col:
        s = s | (df[s2_col].str.strip() != "")
    return s != ""

has_email = has(c_email1)
has_fax   = has(c_fax1)

# ══════════════════════════════════════════════════════════
# [작업 1] DB 분류 → DB분류완성.xlsx
# ══════════════════════════════════════════════════════════
print("\n" + "="*50)
print("[작업 1] DB 분류 처리 중...")

s1 = df[has_email & has_fax].reset_index(drop=True)
s2 = df[has_fax & ~has_email].reset_index(drop=True)
s3 = df[~has_fax & has_email].reset_index(drop=True)
s4 = df[~has_fax & ~has_email].reset_index(drop=True)

# 업종별 통계
if c_biz:
    stats_rows = []
    for biz, grp in df.groupby(c_biz):
        if not biz:
            continue
        he = grp[c_email1].str.strip() != "" if c_email1 else pd.Series([False]*len(grp))
        hf = grp[c_fax1].str.strip()   != "" if c_fax1   else pd.Series([False]*len(grp))
        stats_rows.append({
            "업종": biz,
            "전체": len(grp),
            "팩스+이메일": int((he & hf).sum()),
            "팩스만":      int((hf & ~he).sum()),
            "이메일만":    int((he & ~hf).sum()),
            "둘다없음":    int((~he & ~hf).sum()),
        })
    stats = pd.DataFrame(stats_rows).sort_values("전체", ascending=False)
else:
    stats = pd.DataFrame({
        "항목":["팩스+이메일","팩스만","이메일만","둘다없음"],
        "건수":[len(s1),len(s2),len(s3),len(s4)],
    })

OUT1 = os.path.join(BASE, "DB분류완성.xlsx")
with pd.ExcelWriter(OUT1, engine="openpyxl") as w:
    s1.to_excel(w, sheet_name="팩스+이메일", index=False)
    s2.to_excel(w, sheet_name="팩스만",      index=False)
    s3.to_excel(w, sheet_name="이메일만",    index=False)
    s4.to_excel(w, sheet_name="둘다없음",    index=False)
    stats.to_excel(w, sheet_name="업종별통계", index=False)

print(f"✅ DB분류완성.xlsx 저장 완료")
print(f"   팩스+이메일: {len(s1):,}건  /  팩스만: {len(s2):,}건  /  이메일만: {len(s3):,}건  /  둘다없음: {len(s4):,}건")

# ══════════════════════════════════════════════════════════
# [작업 3] 이메일 보유 업체 추출 → 이메일발송준비.xlsx
# ══════════════════════════════════════════════════════════
print("\n[작업 3] 이메일 발송 준비 추출 중...")

email_df = df[has_email].copy().reset_index(drop=True)

# 원하는 컬럼 구성
want = ["업종명","회사이름","대표자명","주소","이메일","팩스"]
col_map = {
    "업종명":   c_biz,
    "회사이름": c_name,
    "대표자명": c_ceo,
    "주소":     c_addr,
    "이메일":   c_email1,
    "팩스":     c_fax1,
}
result3 = pd.DataFrame()
for w_col in want:
    src = col_map.get(w_col)
    result3[w_col] = email_df[src].values if src else ""

# 이메일 중복 제거
before = len(result3)
result3 = result3.drop_duplicates(subset=["이메일"]).reset_index(drop=True)

OUT3 = os.path.join(BASE, "이메일발송준비.xlsx")
result3.to_excel(OUT3, index=False, engine="openpyxl")
print(f"✅ 이메일발송준비.xlsx 저장 완료 ({before:,}건 → 중복제거 후 {len(result3):,}건)")

# ══════════════════════════════════════════════════════════
# [작업 7] 영업 현황 대시보드 HTML 생성 (데이터 내장)
# ══════════════════════════════════════════════════════════
print("\n[작업 7] 영업 대시보드 생성 중...")

# 통계 계산
total     = len(df)
email_cnt = int(has_email.sum())
fax_cnt   = int(has_fax.sum())
both_cnt  = int((has_email & has_fax).sum())
none_cnt  = int((~has_email & ~has_fax).sum())

# 업종별 이메일 보유 TOP10
biz_email = {}
biz_fax   = {}
biz_total = {}
if c_biz:
    for biz, grp in df.groupby(c_biz):
        if not biz: continue
        biz_total[biz] = len(grp)
        if c_email1:
            biz_email[biz] = int((grp[c_email1].str.strip() != "").sum())
        if c_fax1:
            biz_fax[biz] = int((grp[c_fax1].str.strip() != "").sum())

top_biz_email = sorted(biz_email.items(), key=lambda x:-x[1])[:10]
top_biz_fax   = sorted(biz_fax.items(),   key=lambda x:-x[1])[:10]
top_biz_total = sorted(biz_total.items(), key=lambda x:-x[1])[:10]

# 지역별 통계
region_cnt = {}
if c_addr:
    for addr in df[c_addr]:
        parts = str(addr).strip().split()
        if parts:
            r = parts[0]
            if len(r) >= 2:
                region_cnt[r] = region_cnt.get(r, 0) + 1
top_regions = sorted(region_cnt.items(), key=lambda x:-x[1])[:10]

# 샘플 데이터 (테이블용, 최대 50건)
sample_cols = [c for c in [c_biz, c_name, c_ceo, c_addr, c_email1, c_fax1, c_web, c_status] if c]
sample_df   = df[has_email][sample_cols].head(50) if sample_cols else df.head(50)
sample_rows = sample_df.values.tolist()
sample_head = sample_df.columns.tolist()

stats_json = json.dumps({
    "total": total, "email": email_cnt, "fax": fax_cnt,
    "both": both_cnt, "none": none_cnt,
    "topBizEmail": top_biz_email,
    "topBizFax":   top_biz_fax,
    "topBizTotal": top_biz_total,
    "topRegions":  top_regions,
    "sampleHead":  sample_head,
    "sampleRows":  sample_rows,
    "filename":    os.path.basename(INPUT),
    "generated":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
}, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>영업 현황 대시보드</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--gold:#C9A96E;--dark:#1A1A2E;--darker:#0F0F1A;--white:#fff;--gray:#F4F6FB;--blue:#3498DB;--green:#2ECC71;--red:#E74C3C;--purple:#9B59B6;--orange:#E67E22;}}
body{{font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:var(--gray);color:var(--dark)}}
nav{{background:var(--darker);padding:16px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}}
.nav-logo{{color:var(--gold);font-size:1.05rem;font-weight:700}}
.nav-sub{{color:rgba(255,255,255,.4);font-size:.75rem}}
.wrap{{padding:24px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:24px}}
.kpi{{background:var(--white);border-radius:16px;padding:22px;box-shadow:0 2px 12px rgba(0,0,0,.05);border-left:4px solid transparent}}
.kpi.blue{{border-left-color:var(--blue)}}.kpi.green{{border-left-color:var(--green)}}.kpi.gold{{border-left-color:var(--gold)}}.kpi.red{{border-left-color:var(--red)}}.kpi.purple{{border-left-color:var(--purple)}}.kpi.orange{{border-left-color:var(--orange)}}
.kpi-icon{{font-size:1.4rem;margin-bottom:6px}}.kpi-label{{font-size:.7rem;color:#999;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin-bottom:3px}}.kpi-value{{font-size:1.6rem;font-weight:700;line-height:1}}.kpi-sub{{font-size:.7rem;color:#aaa;margin-top:3px}}
.row2{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
@media(max-width:700px){{.row2{{grid-template-columns:1fr}}}}
.row3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:20px}}
@media(max-width:900px){{.row3{{grid-template-columns:1fr 1fr}}}}
@media(max-width:560px){{.row3{{grid-template-columns:1fr}}}}
.panel{{background:var(--white);border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.05)}}
.panel-title{{font-size:.88rem;font-weight:700;color:var(--dark);margin-bottom:16px}}
.bar-list{{display:flex;flex-direction:column;gap:8px}}
.bar-item{{display:flex;align-items:center;gap:8px}}
.bl-label{{font-size:.75rem;color:#666;min-width:88px;max-width:88px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bl-track{{flex:1;background:#F0EBE0;border-radius:5px;height:20px;overflow:hidden}}
.bl-fill{{height:100%;border-radius:5px;display:flex;align-items:center;padding-left:7px;font-size:.68rem;font-weight:600;color:rgba(255,255,255,.9)}}
.bl-val{{font-size:.72rem;color:#888;min-width:36px;text-align:right}}
.pie-wrap{{display:flex;align-items:center;gap:18px;flex-wrap:wrap}}
.pie-legend{{display:flex;flex-direction:column;gap:7px}}
.pie-li{{display:flex;align-items:center;gap:7px;font-size:.76rem;color:#555}}
.pie-dot{{width:11px;height:11px;border-radius:3px;flex-shrink:0}}
.data-table{{width:100%;border-collapse:collapse;font-size:.78rem}}
.data-table th{{background:#F8F6F2;padding:9px 10px;text-align:left;font-weight:600;color:#666;font-size:.72rem;border-bottom:2px solid #EEE8DC}}
.data-table td{{padding:9px 10px;border-bottom:1px solid #F0EBE0}}
.data-table tr:hover td{{background:#FDFAF5}}
.action-box{{padding:14px;background:#FFF8EC;border-radius:10px;border:1px solid #E8D5B0;font-size:.82rem;line-height:1.9;color:#555}}
.action-box strong{{color:var(--dark)}}
.tip{{margin-top:10px;padding:10px;background:#F0FBF4;border-radius:8px;font-size:.76rem;color:#27AE60}}
</style>
</head>
<body>
<nav>
  <div class="nav-logo">📊 영업 현황 대시보드</div>
  <div class="nav-sub">소스: <span id="fname"></span> &nbsp;|&nbsp; 생성: <span id="gen"></span></div>
</nav>
<div class="wrap">
  <div class="kpi-grid">
    <div class="kpi blue"><div class="kpi-icon">📋</div><div class="kpi-label">전체 업체</div><div class="kpi-value" id="k_total">—</div><div class="kpi-sub">수집된 전체</div></div>
    <div class="kpi green"><div class="kpi-icon">📧</div><div class="kpi-label">이메일 보유</div><div class="kpi-value" id="k_email">—</div><div class="kpi-sub">발송 가능</div></div>
    <div class="kpi gold"><div class="kpi-icon">📠</div><div class="kpi-label">팩스 보유</div><div class="kpi-value" id="k_fax">—</div><div class="kpi-sub">발송 가능</div></div>
    <div class="kpi orange"><div class="kpi-icon">⚡</div><div class="kpi-label">이메일+팩스</div><div class="kpi-value" id="k_both">—</div><div class="kpi-sub">이중 채널</div></div>
    <div class="kpi purple"><div class="kpi-icon">📈</div><div class="kpi-label">이메일 수집률</div><div class="kpi-value" id="k_rate">—</div><div class="kpi-sub">전체 대비</div></div>
    <div class="kpi red"><div class="kpi-icon">❌</div><div class="kpi-label">연락처 없음</div><div class="kpi-value" id="k_none">—</div><div class="kpi-sub">추가 수집 필요</div></div>
  </div>
  <div class="row2">
    <div class="panel"><div class="panel-title">🏭 업종별 이메일 보유 TOP 10</div><div class="bar-list" id="bizEmailChart"></div></div>
    <div class="panel"><div class="panel-title">📠 업종별 팩스 보유 TOP 10</div><div class="bar-list" id="bizFaxChart"></div></div>
  </div>
  <div class="row3">
    <div class="panel"><div class="panel-title">📍 지역별 업체 수</div><div class="bar-list" id="regionChart"></div></div>
    <div class="panel"><div class="panel-title">🥧 연락처 보유 현황</div><div class="pie-wrap" id="pieChart"></div></div>
    <div class="panel"><div class="panel-title">🎯 핵심 액션 가이드</div><div class="action-box" id="actionBox"></div></div>
  </div>
  <div class="panel">
    <div class="panel-title">📋 이메일 보유 업체 목록 (상위 50건)</div>
    <div style="overflow-x:auto"><table class="data-table"><thead><tr id="tHead"></tr></thead><tbody id="tBody"></tbody></table></div>
  </div>
</div>
<script>
const D = {stats_json};
const C=['#3498DB','#2ECC71','#E67E22','#9B59B6','#E74C3C','#1ABC9C','#F39C12','#2980B9','#27AE60','#8E44AD'];
document.getElementById('fname').textContent=D.filename;
document.getElementById('gen').textContent=D.generated;
function setText(id,v){{const el=document.getElementById(id);if(el)el.textContent=v;}}
setText('k_total',D.total.toLocaleString());
setText('k_email',D.email.toLocaleString());
setText('k_fax',D.fax.toLocaleString());
setText('k_both',D.both.toLocaleString());
setText('k_rate',(D.total>0?(D.email/D.total*100).toFixed(1):0)+'%');
setText('k_none',D.none.toLocaleString());
function drawBars(id,entries,colors){{
  const max=entries[0]?.[1]||1;
  document.getElementById(id).innerHTML=entries.length?entries.map(([l,v],i)=>
    `<div class="bar-item"><div class="bl-label" title="${{l}}">${{l}}</div><div class="bl-track"><div class="bl-fill" style="width:${{(v/max*100).toFixed(1)}}%;background:${{C[i%C.length]}}">${{v}}</div></div><div class="bl-val">${{v}}</div></div>`
  ).join(''):'<p style="color:#aaa;font-size:.8rem">데이터 없음</p>';
}}
drawBars('bizEmailChart',D.topBizEmail);
drawBars('bizFaxChart',D.topBizFax);
drawBars('regionChart',D.topRegions);
// 파이
(function(){{
  const slices=[
    {{l:'이메일+팩스',v:D.both,c:'#E67E22'}},
    {{l:'이메일만',v:D.email-D.both,c:'#2ECC71'}},
    {{l:'팩스만',v:D.fax-D.both,c:'#3498DB'}},
    {{l:'없음',v:D.none,c:'#EEE8DC'}},
  ].filter(s=>s.v>0);
  const t=slices.reduce((a,s)=>a+s.v,0)||1;
  const cx=70,cy=70,r=60;let ang=-Math.PI/2,paths='';
  for(const s of slices){{const a=(s.v/t)*2*Math.PI,x1=cx+r*Math.cos(ang),y1=cy+r*Math.sin(ang),x2=cx+r*Math.cos(ang+a),y2=cy+r*Math.sin(ang+a),lg=a>Math.PI?1:0;paths+=`<path d="M${{cx}},${{cy}} L${{x1}},${{y1}} A${{r}},${{r}} 0 ${{lg}} 1 ${{x2}},${{y2}} Z" fill="${{s.c}}" opacity=".9"/>`;ang+=a;}}
  const svg=`<svg width="140" height="140" viewBox="0 0 140 140">${{paths}}<circle cx="${{cx}}" cy="${{cy}}" r="28" fill="white"/><text x="${{cx}}" y="${{cy+5}}" text-anchor="middle" font-size="9" fill="#666">${{D.total.toLocaleString()}}건</text></svg>`;
  let legend='<div class="pie-legend">'+slices.map(s=>`<div class="pie-li"><div class="pie-dot" style="background:${{s.c}}"></div>${{s.l}}: <strong>${{s.v.toLocaleString()}}</strong></div>`).join('')+'</div>';
  document.getElementById('pieChart').innerHTML=svg+legend;
}})();
// 액션 가이드
(function(){{
  const topBiz=D.topBizTotal[0]?.[0]||'제조업',topE=D.topBizEmail[0]?.[0]||'',rate=(D.total>0?(D.email/D.total*100).toFixed(1):0);
  document.getElementById('actionBox').innerHTML=`
    <p>✅ 총 <strong>${{D.total.toLocaleString()}}개</strong> 업체 수집 완료</p>
    <p>📧 이메일 보유: <strong>${{D.email.toLocaleString()}}개</strong> (수집률 ${{rate}}%)</p>
    <p>📠 팩스 보유: <strong>${{D.fax.toLocaleString()}}개</strong></p>
    ${{topE?`<p>🎯 이메일 최다 업종: <strong>${{topE}}</strong></p>`:''}}
    <p>📌 이메일 없는 업체: <strong>${{D.none.toLocaleString()}}개</strong><br>&nbsp;&nbsp;→ 홈페이지 재크롤링 권장</p>
    <div class="tip">💡 이메일 발송 후 3일 내 팔로업 전화 시 반응률 약 2.5배 상승</div>`;
}})();
// 테이블
(function(){{
  document.getElementById('tHead').innerHTML=D.sampleHead.map(h=>`<th>${{h}}</th>`).join('');
  document.getElementById('tBody').innerHTML=D.sampleRows.map(row=>`<tr>${{row.map(v=>`<td>${{v??''}}</td>`).join('')}}</tr>`).join('');
}})();
</script>
</body>
</html>"""

OUT7 = os.path.join(BASE, "영업대시보드.html")
with open(OUT7, "w", encoding="utf-8") as f:
    f.write(html)
print(f"✅ 영업대시보드.html 저장 완료 (데이터 내장)")

# ══════════════════════════════════════════════════════════
# 최종 요약
# ══════════════════════════════════════════════════════════
print(f"""
{'='*55}
✅ 전체 처리 완료!

저장된 파일:
  📊 {os.path.join(BASE, 'DB분류완성.xlsx')}
  📧 {os.path.join(BASE, '이메일발송준비.xlsx')}
  🌐 {OUT7}

요약:
  전체 업체:     {total:,}건
  이메일 보유:   {email_cnt:,}건 ({email_cnt/total*100:.1f}%)
  팩스 보유:     {fax_cnt:,}건 ({fax_cnt/total*100:.1f}%)
  이메일+팩스:   {both_cnt:,}건
  연락처 없음:   {none_cnt:,}건

영업대시보드.html → 더블클릭으로 브라우저에서 바로 확인!
{'='*55}
""")
