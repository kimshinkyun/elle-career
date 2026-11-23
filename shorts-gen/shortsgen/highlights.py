"""하이라이트 선별: Claude(대본 기반) 또는 규칙 기반(API 키 없을 때 대체).

점수 체계는 쇼츠 클리핑 도구들이 공개한 평가 축(Hook·Flow·Value·Trend)을 따릅니다.
- Hook  : 첫 3초에 계속 볼 이유가 생기는가 (질문·반전·숫자·선언)
- Flow  : 앞뒤 맥락 없이도 혼자 이해되고, 말이 중간에 끊기지 않는가
- Value : 끝까지 보면 얻는 것이 분명한가 (정보·감정·결론)
- Trend : 지금 시청자 관심사/검색 의도와 맞는가
가중치는 점수 합산 시 코드에서 직접 계산합니다(모델이 준 총점은 쓰지 않음).
"""
import json
import math
import os
import re

WEIGHTS = {"hook": 0.35, "flow": 0.25, "value": 0.25, "trend": 0.15}

SYSTEM = """당신은 유튜브 쇼츠·릴스 전문 편집 디렉터입니다. 롱폼 영상 대본에서 '혼자 떼어 놔도 끝까지 보게 되는' 구간을 고릅니다.

선정 원칙
1. 첫 3초(첫 문장)에 훅이 있어야 합니다: 질문, 반전, 구체적 숫자, 강한 주장, 손해 회피. 인사·잡담·'안녕하세요'로 시작하는 구간은 제외.
2. 구간은 시작과 끝이 문장 경계에서 끊겨야 하고, 앞 맥락 없이 이해돼야 합니다. 대명사('이거', '그게')만 있고 대상이 없으면 감점.
3. 하나의 완결된 이야기(문제 → 설명 → 결론/한 줄 요약)가 있어야 합니다.
4. 길이는 지정된 범위 안에서, 내용이 허락하는 가장 짧게. 군더더기·반복은 잘라내는 방향으로 경계를 잡습니다.
5. 서로 겹치지 않게 고릅니다. 같은 주제 중복 금지.
6. 시간은 대본에 표시된 초 단위 값을 그대로 사용합니다. 대본에 없는 시각을 만들지 마세요.
7. 점수는 엄격하게(대부분 40~85). 평균 이상만 후보로 제출합니다.
8. 확인되지 않은 수익 보장·단정적 투자/의료 효과 표현, 특정 금융상품 권유가 있으면 risk_flags에 적습니다.

hook_title: 화면 상단에 계속 띄울 한국어 제목. 줄바꿈(\n)으로 정확히 두 줄, 각 줄 14자 이내, 마침표 없음. 첫 줄은 상황/주체, 둘째 줄은 핵심 포인트(강조색으로 표시됨). 과장·낚시 금지, 영상 내용과 일치.
summary: 'AI 하이라이트' 한 문장(60자 이내) — 이 구간에서 시청자가 얻는 것."""

TOOL = {
    "name": "submit_clips",
    "description": "선정한 쇼츠 후보 구간을 제출합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "clips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "number", "description": "시작(초)"},
                        "end": {"type": "number", "description": "끝(초)"},
                        "hook_title": {"type": "string", "description": "두 줄(\\n 구분), 각 줄 14자 이내"},
                        "summary": {"type": "string", "description": "AI 하이라이트 한 문장"},
                        "yt_title": {"type": "string", "description": "업로드용 제목(40자 이내)"},
                        "description": {"type": "string", "description": "업로드용 설명 2~3줄"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "scores": {
                            "type": "object",
                            "properties": {k: {"type": "integer", "minimum": 0, "maximum": 100} for k in WEIGHTS},
                            "required": list(WEIGHTS),
                        },
                        "reason": {"type": "string", "description": "이 구간을 고른 이유 1~2문장"},
                        "risk_flags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["start", "end", "hook_title", "yt_title", "summary", "scores", "reason"],
                },
            }
        },
        "required": ["clips"],
    },
}


def total_score(scores):
    return round(sum(WEIGHTS[k] * float(scores.get(k, 0)) for k in WEIGHTS), 1)


# ───────────────────────── 대본 → 프롬프트 ─────────────────────────
def _windows(segments, max_chars=14000, overlap=4):
    """긴 영상은 대본을 겹치는 창으로 나눠 따로 평가."""
    wins, cur, size = [], [], 0
    for s in segments:
        line = f"[{s.start:.1f}~{s.end:.1f}] {s.text}"
        if size + len(line) > max_chars and cur:
            wins.append(cur)
            cur, size = cur[-overlap:], sum(len(f"[{x.start:.1f}~{x.end:.1f}] {x.text}") for x in cur[-overlap:])
        cur.append(s)
        size += len(line)
    if cur:
        wins.append(cur)
    return wins


def _prompt(win, n, min_s, max_s, audience, avoid_terms):
    lines = "\n".join(f"[{s.start:.1f}~{s.end:.1f}] {s.text}" for s in win)
    extra = f"\n- 다음 표현이 나오는 구간은 제외: {', '.join(avoid_terms)}" if avoid_terms else ""
    return (
        f"대상 시청자: {audience}\n"
        f"요청: 아래 대본에서 쇼츠 후보를 최대 {n}개 고르세요. 길이 {min_s}~{max_s}초.{extra}\n\n"
        f"대본(형식: [시작초~끝초] 문장):\n{lines}"
    )


def select_with_claude(segments, n=5, min_s=25, max_s=55, audience="일반 시청자", avoid_terms=(),
                       model="claude-sonnet-5-5", api_key=None, progress=None):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    wins = _windows(segments)
    per_win = max(2, math.ceil(n * 1.6 / len(wins)))
    cands = []
    for i, win in enumerate(wins):
        resp = client.messages.create(
            model=model, max_tokens=4000, system=SYSTEM,
            tools=[TOOL], tool_choice={"type": "tool", "name": "submit_clips"},
            messages=[{"role": "user", "content": _prompt(win, per_win, min_s, max_s, audience, avoid_terms)}],
        )
        for block in resp.content:
            if block.type == "tool_use":
                cands.extend(block.input.get("clips", []))
        if progress:
            progress((i + 1) / len(wins))
    return finalize(cands, segments, n, min_s, max_s, avoid_terms)


# ───────────────────────── 규칙 기반 대체 ─────────────────────────
HOOK_WORDS = ["비밀", "실수", "절대", "진짜", "문제는", "결론", "핵심", "이유", "방법", "충격", "아무도", "손해", "꼭", "반드시", "차이"]
END_RE = re.compile(r"(다|요|죠|까|네|세요|습니다|니다)[.?!]?$|[.?!]$")


def _short(text, n):
    """n자 안에서 단어 경계로 자르기(단어 중간 절단 방지)."""
    text = text.strip().rstrip(" ,.")
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return (cut if len(cut) >= n // 2 else text[:n]).rstrip(" ,.")


def select_heuristic(segments, n=5, min_s=25, max_s=55, avoid_terms=()):
    cands = []
    target = (min_s + max_s) / 2
    for i, first in enumerate(segments):
        j, end = i, first.end
        while j + 1 < len(segments) and (segments[j].end - first.start) < target:
            j += 1
        # 문장 끝에서 끊기도록 max_s 안에서 뒤로 조정
        while j > i and (not END_RE.search(segments[j].text) or segments[j].end - first.start > max_s):
            j -= 1
        end = segments[j].end
        dur = end - first.start
        if dur < min_s:
            continue
        text = " ".join(s.text for s in segments[i:j + 1])
        head = first.text
        hook = 35 + (20 if "?" in head else 0) + (15 if re.search(r"\d", head) else 0) + 8 * sum(w in head for w in HOOK_WORDS)
        hook -= 30 if re.match(r"\s*(안녕|여러분|반갑|오늘은)", head) else 0
        value = 35 + min(30, 4 * len(re.findall(r"\d", text)) // 2) + 5 * sum(w in text for w in HOOK_WORDS)
        flow = 60 + (15 if END_RE.search(segments[j].text) else -20) - (15 if re.match(r"\s*(그리고|그래서|근데|그런데|이거|그게)", head) else 0)
        rate = len(text.replace(" ", "")) / dur
        trend = 50 + (10 if 4 <= rate <= 8 else -10)
        cands.append({
            "start": first.start, "end": end, "hook_title": _short(head, 28), "yt_title": _short(head, 40), "summary": _short(head, 60),
            "description": "", "hashtags": [], "reason": "규칙 기반 점수(훅 문구·숫자·문장 완결성)",
            "scores": {k: max(0, min(100, int(v))) for k, v in
                       {"hook": hook, "flow": flow, "value": value, "trend": trend}.items()},
        })
    return finalize(cands, segments, n, min_s, max_s, avoid_terms)


# ───────────────────────── 공통 후처리 ─────────────────────────
def snap(segments, start, end, min_s, max_s):
    """모델이 준 시간을 가장 가까운 문장 경계로 보정하고 길이 범위를 강제."""
    s_seg = min(segments, key=lambda s: abs(s.start - start))
    e_cands = [s for s in segments if s.end > s_seg.start]
    e_seg = min(e_cands, key=lambda s: abs(s.end - end))
    ns, ne = s_seg.start, e_seg.end
    if ne - ns > max_s:   # 너무 길면 max_s 안의 마지막 문장 끝으로
        inside = [s for s in segments if s.start >= ns and s.end - ns <= max_s]
        if not inside:
            return None
        ne = inside[-1].end
    if ne - ns < min_s:
        return None
    return round(ns, 2), round(ne, 2)


def clip_text(segments, start, end):
    return " ".join(s.text for s in segments if s.end > start and s.start < end)


def finalize(cands, segments, n, min_s, max_s, avoid_terms=()):
    ready = []
    for c in cands:
        snapped = snap(segments, float(c["start"]), float(c["end"]), min_s, max_s)
        if not snapped:
            continue
        s, e = snapped
        text = clip_text(segments, s, e)
        hit = [t for t in avoid_terms if t and t in text]
        if hit:   # 금지어(예: 조합·투자 권유 표현)가 들어간 구간은 제외
            continue
        c = dict(c, start=s, end=e, total=total_score(c["scores"]))
        c.setdefault("hashtags", [])
        c.setdefault("risk_flags", [])
        c.setdefault("summary", "")
        ready.append(c)
    ready.sort(key=lambda c: c["total"], reverse=True)
    picked = []
    for c in ready:
        overlap = lambda a: max(0, min(a["end"], c["end"]) - max(a["start"], c["start"]))
        if all(overlap(a) / min(a["end"] - a["start"], c["end"] - c["start"]) < 0.2 for a in picked):
            picked.append(c)
        if len(picked) == n:
            break
    return picked
