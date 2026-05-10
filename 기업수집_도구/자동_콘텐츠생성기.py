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
def generate_content(client, industry: str, topic: str) -> dict:
    today = datetime.date.today()
    weekday = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]

    system = """당신은 법인전환 전문 컨설턴트의 SNS 마케팅 담당자입니다.
타겟: 연매출 3억~10억 개인사업자 사장님
지역: 여수·순천·광양 (전남)
목표: 법인전환 상담 문의 유도
톤: 친근하고 전문적, 강요 없음
항상 한국어로 작성하세요."""

    prompt = f"""오늘({today} {weekday}요일) 업로드할 SNS 콘텐츠를 생성해주세요.

집중 업종: {industry}
오늘의 주제: {topic}

아래 5가지를 각각 생성해주세요. 반드시 JSON 형식으로만 응답하세요:

{{
  "instagram_card": {{
    "slide1": "표지 문구 (후킹, 2~3줄)",
    "slide2": "문제 제기 (3~4줄)",
    "slide3": "해결책 (3~4줄)",
    "slide4": "수치/증거 (3~4줄)",
    "slide5": "CTA (2~3줄, DM 유도)",
    "caption": "피드 캡션 전체 (150자 내외)",
    "hashtags": "해시태그 20개"
  }},
  "blog_outline": {{
    "title": "SEO 최적화 제목",
    "keyword": "핵심 키워드 3개",
    "intro": "도입부 (3~4문장)",
    "sections": ["소제목1", "소제목2", "소제목3", "소제목4"],
    "conclusion": "마무리 + CTA (3~4문장)"
  }},
  "shorts_script": {{
    "hook": "0~3초 후킹 대사",
    "body": "본론 대사 (15~25초 분량)",
    "cta": "마무리 CTA 대사",
    "title": "유튜브 제목",
    "thumbnail": "썸네일 문구 (10자 내)"
  }},
  "dm_message": {{
    "first": "첫 번째 DM 메시지 (3줄 이내, 스팸 아닌 자연스러운 접근)",
    "followup": "3일 후 팔로업 DM (2줄)",
    "after_no_reply": "7일 후 마지막 DM (2줄)"
  }},
  "email_subject": "이메일 제목 (클릭률 높은)",
  "email_body": "이메일 본문 (200자 내외, 업종 맞춤)"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # JSON 파싱
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ══════════════════════════════════════════════
# HTML 보고서 생성
# ══════════════════════════════════════════════
def make_html(data: dict, industry: str, topic: str, date_str: str) -> str:
    c = data
    ig = c.get("instagram_card", {})
    bl = c.get("blog_outline", {})
    sh = c.get("shorts_script", {})
    dm = c.get("dm_message", {})

    def card(label, content):
        if not content:
            return ""
        escaped = str(content).replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        return f"""
        <div class="item">
          <div class="item-label">{label}</div>
          <div class="item-body">{escaped}</div>
          <button class="copy-btn" onclick="copy(this)">복사</button>
        </div>"""

    sections_html = "".join(f"<li>{s}</li>" for s in bl.get("sections", []))

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
  <button class="tab" onclick="show('dm',this)">💬 DM</button>
  <button class="tab" onclick="show('email',this)">📧 이메일</button>
</div>

<!-- 인스타그램 -->
<div id="ig" class="pane on">
  <span class="tag">📸 카드뉴스 5장</span>
  {card("1장 — 표지 (후킹)", ig.get("slide1",""))}
  {card("2장 — 문제 제기", ig.get("slide2",""))}
  {card("3장 — 해결책", ig.get("slide3",""))}
  {card("4장 — 수치/증거", ig.get("slide4",""))}
  {card("5장 — CTA", ig.get("slide5",""))}
  {card("📝 피드 캡션", ig.get("caption",""))}
  {card("🏷️ 해시태그", ig.get("hashtags",""))}
</div>

<!-- 블로그 -->
<div id="blog" class="pane">
  <span class="tag">📝 네이버 블로그 아웃라인</span>
  {card("SEO 제목", bl.get("title",""))}
  {card("핵심 키워드", bl.get("keyword",""))}
  {card("도입부", bl.get("intro",""))}
  <div class="item">
    <div class="item-label">본문 소제목 구성</div>
    <ul class="sections">{sections_html}</ul>
  </div>
  {card("마무리 + CTA", bl.get("conclusion",""))}
</div>

<!-- 쇼츠 -->
<div id="sh" class="pane">
  <span class="tag">🎬 유튜브 쇼츠 대본</span>
  {card("유튜브 제목", sh.get("title",""))}
  {card("썸네일 문구", sh.get("thumbnail",""))}
  {card("0~3초 후킹", sh.get("hook",""))}
  {card("본론 대사", sh.get("body",""))}
  {card("마무리 CTA", sh.get("cta",""))}
</div>

<!-- DM -->
<div id="dm" class="pane">
  <span class="tag">💬 인스타그램 DM 메시지</span>
  {card("첫 번째 DM", dm.get("first",""))}
  {card("3일 후 팔로업", dm.get("followup",""))}
  {card("7일 후 마지막", dm.get("after_no_reply",""))}
</div>

<!-- 이메일 -->
<div id="email" class="pane">
  <span class="tag">📧 이메일 발송</span>
  {card("이메일 제목", c.get("email_subject",""))}
  {card("이메일 본문", c.get("email_body",""))}
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
