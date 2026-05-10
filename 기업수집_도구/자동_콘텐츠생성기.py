"""
[방법 B] Claude API 기반 SNS 콘텐츠 자동 생성기
매일 실행하면 → 인스타/블로그/쇼츠/DM/이메일 콘텐츠 자동 생성 → HTML 파일 저장

설치: pip install anthropic
실행: python 자동_콘텐츠생성기.py
예약: Windows 작업 스케줄러로 매일 오전 7시 자동 실행 가능
"""

import anthropic
import os
import datetime
import json
import random

# ══════════════════════════════════════════════
# 설정 (여기만 수정하세요)
# ══════════════════════════════════════════════
_key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_key.txt")
CLAUDE_API_KEY = open(_key_file, encoding="utf-8-sig").read().strip() if os.path.exists(_key_file) else "여기에_API_키_입력"
OUTPUT_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "콘텐츠생성결과")

# 오늘 집중할 업종 (순환)
INDUSTRIES = ["제조업", "도소매업", "음식업/요식업", "병원/의원", "건설/인테리어", "서비스업"]

# 오늘 집중할 주제 (순환)
TOPICS = [
    "법인전환 절세 효과",
    "건강보험료 절감",
    "퇴직금 적립 전략",
    "법인전환 시기와 기준",
    "법인전환 오해와 진실",
    "대표 급여 설계 전략",
    "가족 임원 등재 절세",
]

# ══════════════════════════════════════════════
# Claude API 호출
# ══════════════════════════════════════════════
def ask(client, system: str, prompt: str) -> str:
    r = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return r.content[0].text.strip()


def generate_content(client, industry: str, topic: str) -> dict:
    today = datetime.date.today()
    weekday = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]

    sys_msg = f"""법인전환 컨설턴트 SNS 마케터. 업종:{industry} 주제:{topic}
타겟: 연매출3억~10억 개인사업자. 지역: 여수·순천·광양. 한국어로만 답하세요."""

    def q(prompt): return ask(client, sys_msg, prompt)

    print("  인스타 카드뉴스...", end=" ", flush=True)
    ig_raw = q(f"""인스타 카드뉴스 5장 문구를 작성하세요.
1장(후킹 제목 2줄) / 2장(문제제기 3줄) / 3장(해결책 3줄) / 4장(수치증거 3줄) / 5장(CTA 2줄)
마지막에 피드캡션(100자)과 해시태그15개를 추가하세요.
[1장]부터 [캡션] [해시태그] 형식으로 구분해서 작성하세요.""")
    print("완료")

    print("  블로그 아웃라인...", end=" ", flush=True)
    blog_raw = q(f"""네이버 블로그 글 아웃라인을 작성하세요.
SEO제목 / 핵심키워드3개 / 도입부3문장 / 소제목4개 / 마무리CTA3문장
각 항목을 [제목] [키워드] [도입] [소제목] [마무리] 로 구분하세요.""")
    print("완료")

    print("  쇼츠 대본...", end=" ", flush=True)
    shorts_raw = q(f"""유튜브 쇼츠 대본(40초)을 작성하세요.
[제목] [썸네일문구] [후킹3초] [본론20초] [CTA5초] 형식으로 구분하세요.""")
    print("완료")

    print("  DM+이메일...", end=" ", flush=True)
    dm_raw = q(f"""인스타 DM 메시지 3종을 작성하세요.
[첫DM](3줄이내) / [팔로업3일후](2줄) / [마지막7일후](2줄)
그리고 이메일제목과 이메일본문(150자)도 [이메일제목] [이메일본문] 형식으로 추가하세요.""")
    print("완료")

    return {
        "instagram_raw": ig_raw,
        "blog_raw"     : blog_raw,
        "shorts_raw"   : shorts_raw,
        "dm_raw"       : dm_raw,
    }

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # JSON 블록 추출
    if "```" in raw:
        parts = raw.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                raw = p
                break
    # 잘린 JSON 복구 시도
    raw = raw.strip()
    if not raw.endswith("}"):
        last = max(raw.rfind("}"), 0)
        raw = raw[:last+1]
        # 열린 괄호 닫기
        opens = raw.count("{") - raw.count("}")
        raw += "}" * max(opens, 0)
    return json.loads(raw)


# ══════════════════════════════════════════════
# HTML 보고서 생성
# ══════════════════════════════════════════════
def make_html(data: dict, industry: str, topic: str, date_str: str) -> str:
    def card(label, content):
        if not content:
            return ""
        escaped = str(content).replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        return f'<div class="item"><div class="item-label">{label}</div><div class="item-body">{escaped}</div><button class="copy-btn" onclick="copy(this)">복사</button></div>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{date_str} 콘텐츠 — {industry}</title>
<style>
  * {{ box-sizing: border-box; margin:0; padding:0; }}
  body {{ font-family:'Malgun Gothic',sans-serif; background:#f0f4f8; color:#1e293b; }}
  header {{ background:linear-gradient(135deg,#0f2d6b,#1b4f9b); color:white; padding:24px 20px; }}
  header h1 {{ font-size:20px; }}
  header p {{ font-size:13px; opacity:.8; margin-top:4px; }}
  .tabs {{ display:flex; flex-wrap:wrap; gap:6px; padding:16px; background:white;
           border-bottom:2px solid #e0e0e0; position:sticky; top:0; z-index:99;
           box-shadow:0 2px 8px rgba(0,0,0,.1); }}
  .tab {{ padding:9px 16px; border-radius:8px 8px 0 0; cursor:pointer; font-size:13px;
          font-weight:700; border:none; background:#f0f4f8; color:#64748b; }}
  .tab.on {{ background:#1b4f9b; color:white; }}
  .pane {{ display:none; padding:20px; max-width:760px; margin:0 auto; }}
  .pane.on {{ display:block; }}
  .item {{ background:white; border-radius:12px; padding:18px; margin-bottom:14px;
           box-shadow:0 2px 8px rgba(0,0,0,.07); border-left:4px solid #1b4f9b; }}
  .item-label {{ font-size:12px; font-weight:700; color:#1b4f9b; margin-bottom:8px;
                 text-transform:uppercase; letter-spacing:.5px; }}
  .item-body {{ font-size:14px; line-height:1.75; white-space:pre-wrap; background:#f8fafc;
                padding:12px; border-radius:8px; border:1px solid #e2e8f0; }}
  .copy-btn {{ background:#1b4f9b; color:white; border:none; padding:6px 14px;
               border-radius:6px; cursor:pointer; font-size:12px; margin-top:10px;
               float:right; font-family:inherit; }}
  .copy-btn.ok {{ background:#16a34a; }}
  ul.sections {{ padding-left:18px; margin-top:6px; }}
  ul.sections li {{ margin-bottom:6px; font-size:14px; }}
  .tag {{ display:inline-block; background:#e8f0fe; color:#1b4f9b; padding:3px 10px;
          border-radius:20px; font-size:12px; font-weight:700; margin-bottom:12px; }}
  .clearfix::after {{ content:""; display:block; clear:both; }}
</style>
</head>
<body>
<header>
  <h1>📅 {date_str} 오늘의 콘텐츠</h1>
  <p>업종: {industry} &nbsp;|&nbsp; 주제: {topic}</p>
</header>
<div class="tabs">
  <button class="tab on" onclick="show('ig',this)">📸 인스타그램</button>
  <button class="tab" onclick="show('blog',this)">📝 블로그</button>
  <button class="tab" onclick="show('sh',this)">🎬 쇼츠</button>
  <button class="tab" onclick="show('dm',this)">💬 DM+이메일</button>
</div>

<!-- 인스타그램 -->
<div id="ig" class="pane on">
  <span class="tag">📸 카드뉴스 + 캡션 + 해시태그</span>
  {card("인스타그램 카드뉴스", data.get("instagram_raw",""))}
</div>

<!-- 블로그 -->
<div id="blog" class="pane">
  <span class="tag">📝 네이버 블로그 아웃라인</span>
  {card("블로그 아웃라인", data.get("blog_raw",""))}
</div>

<!-- 쇼츠 -->
<div id="sh" class="pane">
  <span class="tag">🎬 유튜브 쇼츠 대본</span>
  {card("쇼츠 대본", data.get("shorts_raw",""))}
</div>

<!-- DM + 이메일 -->
<div id="dm" class="pane">
  <span class="tag">💬 DM + 📧 이메일</span>
  {card("DM 메시지 + 이메일", data.get("dm_raw",""))}
</div>

<script>
function show(id,btn){{
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('on'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  document.getElementById(id).classList.add('on');
  btn.classList.add('on');
}}
function copy(btn){{
  const text = btn.previousElementSibling.innerText;
  navigator.clipboard.writeText(text).then(()=>{{
    btn.textContent='복사됨 ✓'; btn.classList.add('ok');
    setTimeout(()=>{{btn.textContent='복사';btn.classList.remove('ok');}},2000);
  }});
}}
</script>
</body>
</html>"""


# ══════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════
def main():
    print("="*55)
    print("  Claude API SNS 콘텐츠 자동 생성기")
    print("="*55)

    if CLAUDE_API_KEY == "여기에_API_키_입력":
        print("""
❌ API 키가 설정되지 않았습니다.

▶ 발급 방법:
  1. https://console.anthropic.com 접속
  2. 회원가입 → API Keys → Create Key
  3. 이 파일 상단 CLAUDE_API_KEY 에 붙여넣기

▶ 비용: 이 스크립트 1회 실행 = 약 $0.01~0.03 (15~45원)
  매일 실행해도 월 500~1,000원 수준
""")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    today = datetime.date.today()
    day_idx = today.timetuple().tm_yday  # 오늘이 연중 몇 번째 날인지

    # 오늘의 업종/주제 자동 순환
    industry = INDUSTRIES[day_idx % len(INDUSTRIES)]
    topic    = TOPICS[day_idx % len(TOPICS)]

    print(f"\n오늘 업종: {industry}")
    print(f"오늘 주제: {topic}")
    print(f"\nClaude API 호출 중...", end="", flush=True)

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    try:
        data = generate_content(client, industry, topic)
        print(" 완료!")
    except Exception as e:
        print(f"\n❌ API 오류: {e}")
        return

    # HTML 파일 저장
    date_str = today.strftime("%Y년 %m월 %d일")
    fname = today.strftime("%Y%m%d") + f"_{industry}_콘텐츠.html"
    fpath = os.path.join(OUTPUT_DIR, fname)

    html = make_html(data, industry, topic, date_str)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"""
✅ 콘텐츠 생성 완료!
→ {fpath}

포함된 콘텐츠:
  📸 인스타 카드뉴스 5장 + 캡션 + 해시태그
  📝 블로그 아웃라인 + SEO 키워드
  🎬 유튜브 쇼츠 대본 + 썸네일
  💬 DM 메시지 3종 (첫/팔로업/마지막)
  📧 이메일 제목 + 본문

▶ 파일을 더블클릭해서 브라우저로 열면 됩니다.
▶ 각 항목 옆 [복사] 버튼으로 바로 복사 가능합니다.
""")


if __name__ == "__main__":
    main()
