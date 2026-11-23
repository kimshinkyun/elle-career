"""쇼츠 생성기 화면.  실행: streamlit run app.py"""
import io
import os
import zipfile
from pathlib import Path

import streamlit as st

from shortsgen.download import download
from shortsgen.pipeline import run
from shortsgen.render import default_font, have_ffmpeg

st.set_page_config(page_title="쇼츠 생성기", page_icon="🎬", layout="wide")
st.title("🎬 롱폼 → 쇼츠 생성기")
st.caption("영상 1개를 올리면 하이라이트를 골라 9:16 쇼츠로 잘라 자막까지 입혀줍니다. 영상은 내 컴퓨터 밖으로 나가지 않고, 대본 텍스트만 Claude 분석에 사용됩니다.")

if not have_ffmpeg():
    st.error("ffmpeg가 설치되어 있지 않습니다. 설명서(README)의 1단계를 먼저 진행해 주세요.")
    st.stop()

with st.sidebar:
    st.header("설정")
    n = st.slider("만들 쇼츠 개수", 1, 10, 5)
    min_s, max_s = st.slider("길이 범위(초)", 15, 90, (25, 55))
    layout = st.selectbox("화면 구성", ["auto", "fit", "crop"], format_func={
        "auto": "자동", "fit": "전체 보이기(블러 배경)", "crop": "꽉 채우기(얼굴 따라 자르기)"}.get)
    use_llm = st.radio("하이라이트 분석", ["Claude (권장)", "규칙 기반(키 없이)"]) == "Claude (권장)"
    api_key = st.text_input("Anthropic API 키", type="password", value=os.environ.get("ANTHROPIC_API_KEY", ""),
                            help="이 창에만 사용되고 저장되지 않습니다.") if use_llm else ""
    audience = st.text_input("대상 시청자", "병원 원장님")
    avoid = st.text_input("제외할 표현(쉼표)", "조합,수익 보장", help="이 단어가 나오는 구간은 쇼츠에서 제외합니다.")
    whisper_model = st.selectbox("음성 인식 정확도", ["large-v3", "medium", "small"],
                                 help="large-v3가 가장 정확하지만 느립니다. 처음 실행 시 모델을 내려받습니다.")
    font = st.text_input("자막 글꼴", default_font())

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
            st.session_state["dl"] = str(download(url, "output/_downloads"))
    if st.session_state.get("dl"):
        video_path = Path(st.session_state["dl"]); st.success(f"준비됨: {video_path.name}")

if video_path and st.button("🚀 쇼츠 만들기", type="primary"):
    tr_path = None
    if tr:
        tr_path = Path("output/_uploads") / tr.name
        tr_path.write_bytes(tr.getbuffer())
    log = st.status("작업 중…", expanded=True)
    try:
        res = run(video_path, "output", n, min_s, max_s, layout, font, "fonts" if Path("fonts").exists() else None,
                  whisper_model, "ko", tr_path, use_llm, "claude-sonnet-5-5", audience,
                  [t.strip() for t in avoid.split(",") if t.strip()], api_key or None, progress=lambda m: log.write(m))
        log.update(label="완료!", state="complete")
        st.session_state["res"] = res
    except Exception as e:   # 비개발자에게 원인을 그대로 보여줌
        log.update(label="실패", state="error"); st.error(str(e))

res = st.session_state.get("res")
if res:
    st.subheader(f"결과 {len(res['clips'])}개")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for c in res["clips"]:
            z.write(c["file"], Path(c["file"]).name)
        z.write(Path(res["out_dir"]) / "upload_sheet.csv", "upload_sheet.csv")
    st.download_button("📦 전체 받기 (mp4 + 업로드 시트)", buf.getvalue(), "shorts.zip", "application/zip")
    for c in res["clips"]:
        a, b = st.columns([1, 2])
        with a:
            st.video(c["file"])
        with b:
            st.markdown(f"### {c['hook_title']}  ·  **{c['total']}점**")
            st.caption(f"{c['start']:.0f}초 ~ {c['end']:.0f}초  |  {c['reason']}")
            m = st.columns(4)
            for col, (k, label) in zip(m, [("hook", "훅"), ("flow", "흐름"), ("value", "가치"), ("trend", "트렌드")]):
                col.metric(label, c["scores"][k])
            st.text_input("업로드 제목", c["yt_title"], key=f"t{c['file']}")
            st.text_area("설명", c.get("description", "") + "\n" + " ".join(c.get("hashtags", [])), key=f"d{c['file']}")
            if c.get("risk_flags"):
                st.warning("주의: " + " / ".join(c["risk_flags"]))
            st.download_button("이 쇼츠 받기", Path(c["file"]).read_bytes(), Path(c["file"]).name, "video/mp4", key=f"dl{c['file']}")
