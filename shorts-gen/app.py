"""쇼츠 생성기 화면 (이지컷 스타일).  실행: streamlit run app.py
내 프로젝트 목록 → 새 쇼츠 만들기 → 프로젝트 상세(쇼츠별 점수·타임라인·AI 하이라이트·스크립트·편집·다운로드)"""
import datetime
import io
import os
import zipfile
from pathlib import Path

import streamlit as st

from shortsgen.download import download
from shortsgen.pipeline import list_projects, load_project, rerender, run
from shortsgen.render import default_font, have_ffmpeg

st.set_page_config(page_title="쇼츠 생성기", page_icon="🎬", layout="centered")
st.markdown("""<style>
.chip{display:inline-block;padding:3px 12px;border-radius:8px;background:#2a2450;color:#c9b8ff;font-weight:700;font-size:.85rem;border:1px solid #473f87}
.tl{color:#9aa4b2;font-size:.85rem}
</style>""", unsafe_allow_html=True)

if not have_ffmpeg():
    st.error("ffmpeg가 설치되어 있지 않습니다. README 1단계를 먼저 진행해 주세요.")
    st.stop()


def mmss(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}" if sec < 3600 else f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def dur_text(sec):
    h, m = int(sec // 3600), int(sec % 3600 // 60)
    return (f"{h}시간 " if h else "") + f"{m}분"


ss = st.session_state
ss.setdefault("view", "list")
ss.setdefault("project", None)

# ───────────── 사이드바: 설정 ─────────────
with st.sidebar:
    st.header("설정")
    n = st.slider("만들 쇼츠 개수", 1, 10, 5)
    min_s, max_s = st.slider("길이 범위(초)", 15, 90, (25, 55))
    layout = st.selectbox("화면 구성", ["stack", "fit", "crop"], format_func={
        "stack": "제목+정사각 영상 (이지컷 스타일)", "fit": "블러 배경 전체 보이기", "crop": "꽉 채우기"}.get)
    cap_style = st.selectbox("자막 스타일", ["box", "karaoke"], format_func={"box": "박스 자막", "karaoke": "말하는 단어 노랑 강조"}.get)
    footer = st.text_input("하단 문구(선택)", "", help="예) 댓글에 '세금' → 3분 계산기 링크 보내드려요")
    use_llm = st.radio("하이라이트 분석", ["Claude (권장)", "규칙 기반(키 없이)"]) == "Claude (권장)"
    api_key = st.text_input("Anthropic API 키", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""),
                            help="이 창에만 쓰이고 저장되지 않습니다.") if use_llm else ""
    audience = st.text_input("대상 시청자", "병원 원장님")
    avoid = st.text_input("제외할 표현(쉼표)", "조합,수익 보장", help="이 단어가 나오는 구간은 쇼츠에서 제외합니다.")
    whisper_model = st.selectbox("음성 인식 정확도", ["large-v3", "medium", "small"])
    font = st.text_input("자막 글꼴", default_font())

fonts_dir = "fonts" if Path("fonts").exists() else None

# ───────────── 1) 내 프로젝트 ─────────────
if ss["view"] == "list":
    projects = list_projects("output")
    c1, c2 = st.columns([3, 2])
    c1.title(f"내 프로젝트  {len(projects)}")
    if c2.button("새 쇼츠 만들기 →", type="primary", use_container_width=True):
        ss["view"] = "new"; st.rerun()
    for p in projects:
        with st.container(border=True):
            a, b = st.columns([5, 1])
            a.markdown(f"**{p['title']}**")
            a.caption(f"🟢 완료 · 쇼츠 {p['n']}개 · 원본 {dur_text(p['duration'])} · {p['created'][:10]}")
            if b.button("열기", key=f"open{p['dir']}"):
                ss["project"], ss["view"] = p["dir"], "detail"; st.rerun()
    if not projects:
        st.info("아직 프로젝트가 없어요. 오른쪽 위 ‘새 쇼츠 만들기’로 시작하세요.")

# ───────────── 2) 새 쇼츠 만들기 ─────────────
elif ss["view"] == "new":
    if st.button("← 프로젝트"):
        ss["view"] = "list"; st.rerun()
    st.title("새 쇼츠 만들기")
    tab_up, tab_url = st.tabs(["📁 파일 올리기", "🔗 유튜브 링크"])
    video_path = None
    with tab_up:
        f = st.file_uploader("영상 파일", type=["mp4", "mov", "mkv", "webm", "m4a", "mp3"])
        tr = st.file_uploader("이미 있는 자막(선택, .srt/.json)", type=["srt", "json"])
        if f:
            up = Path("output/_uploads"); up.mkdir(parents=True, exist_ok=True)
            video_path = up / f.name
            video_path.write_bytes(f.getbuffer())
    with tab_url:
        url = st.text_input("유튜브 URL")
        ok = st.checkbox("내가 올린 영상이거나 사용 허락을 받은 영상입니다")
        if url and ok and st.button("내려받기"):
            with st.spinner("내려받는 중…"):
                ss["dl"] = str(download(url, "output/_downloads"))
        if ss.get("dl"):
            video_path = Path(ss["dl"]); st.success(f"준비됨: {video_path.name}")
    if video_path and st.button("🚀 쇼츠 만들기", type="primary"):
        tr_path = None
        if tr:
            tr_path = Path("output/_uploads") / tr.name
            tr_path.write_bytes(tr.getbuffer())
        log = st.status("작업 중…", expanded=True)
        try:
            res = run(video_path, "output", n, min_s, max_s, layout, font, fonts_dir, whisper_model, "ko", tr_path, use_llm,
                      "claude-sonnet-5-5", audience, [t.strip() for t in avoid.split(",") if t.strip()], api_key or None,
                      progress=lambda m: log.write(m), cap_style=cap_style, footer=footer)
            ss["project"], ss["view"] = res["out_dir"], "detail"; st.rerun()
        except Exception as e:
            log.update(label="실패", state="error"); st.error(str(e))

# ───────────── 3) 프로젝트 상세 ─────────────
else:
    out = ss["project"]
    meta, clips = load_project(out)
    top1, top2 = st.columns([3, 2])
    if top1.button("← 프로젝트"):
        ss["view"] = "list"; st.rerun()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for c in clips:
            z.write(c["file"], Path(c["file"]).name)
        z.write(Path(out) / "upload_sheet.csv", "upload_sheet.csv")
    top2.download_button("⬇ 모든 쇼츠 다운로드", buf.getvalue(), "shorts.zip", "application/zip", type="primary", use_container_width=True)
    st.subheader(meta["title"])
    st.caption(f"쇼츠 {len(clips)}개 · 원본 {dur_text(meta['duration'])}")

    for i, c in enumerate(clips):
        st.divider()
        flat_title = c["hook_title"].replace("\n", " ")
        st.markdown(f"### #{i + 1}  {flat_title}")
        st.markdown(f"<span class='chip'>바이럴 점수 {int(round(c['total']))}/100</span>", unsafe_allow_html=True)
        vcol = st.columns([1, 2, 1])[1]
        vcol.video(c["file"])
        b1, b2 = st.columns(2)
        with b2:
            st.download_button("⬇ 다운로드", Path(c["file"]).read_bytes(), Path(c["file"]).name, "video/mp4", key=f"dl{i}", use_container_width=True)
        with b1.popover("✎ 편집하기", use_container_width=True):
            t = st.text_area("제목 (줄바꿈=2줄, 둘째 줄이 강조색)", c["hook_title"], key=f"t{i}")
            s_, e_ = st.columns(2)
            ns = s_.number_input("시작(초)", value=float(c["start"]), step=0.5, key=f"s{i}")
            ne = e_.number_input("끝(초)", value=float(c["end"]), step=0.5, key=f"e{i}")
            lay = st.selectbox("화면 구성", ["stack", "fit", "crop"], index=["stack", "fit", "crop"].index(c.get("layout", "stack")), key=f"l{i}")
            cs = st.selectbox("자막", ["box", "karaoke"], index=["box", "karaoke"].index(c.get("cap_style", "box")), key=f"c{i}")
            ft = st.text_input("하단 문구", c.get("footer", ""), key=f"f{i}")
            if st.button("다시 렌더링", key=f"r{i}", type="primary"):
                with st.spinner("렌더링 중…"):
                    rerender(out, i, t, ns, ne, lay, cs, ft, font)
                st.rerun()
        st.markdown(f"<div class='tl'>원본 영상 타임라인</div>**⏱ {mmss(c['start'])} ~ {mmss(c['end'])}**  ({int(c['end'] - c['start'])}초)", unsafe_allow_html=True)
        with st.expander("AI 설명 · 스크립트 보기"):
            if c.get("summary"):
                st.info(f"✦ **AI 하이라이트**  \n{c['summary']}")
            sc = c["scores"]
            m = st.columns(4)
            for col, (k, label) in zip(m, [("hook", "훅"), ("flow", "흐름"), ("value", "가치"), ("trend", "트렌드")]):
                col.metric(label, sc[k])
            st.caption(c.get("reason", ""))
            if c.get("risk_flags"):
                st.warning("주의: " + " / ".join(c["risk_flags"]))
            st.text_input("업로드 제목", c["yt_title"], key=f"yt{i}")
            st.text_area("설명·해시태그", c.get("description", "") + "\n" + " ".join(c.get("hashtags", [])), key=f"ds{i}")
            st.markdown("**스크립트**")
            st.write(c.get("script", ""))
