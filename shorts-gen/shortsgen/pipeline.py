"""전체 파이프라인: 영상 → 대본 → 하이라이트 → 쇼츠 mp4 + 업로드용 시트."""
import csv
import json
import re
from pathlib import Path

from . import highlights
from .render import render_clip
from .transcribe import load_transcript, save_transcript, transcribe
from .models import segments_from_dicts


def slug(s):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "_", s).strip("_")[:40] or "video"


def run(video, out_root="output", n=5, min_s=25, max_s=55, layout="auto", font="Noto Sans KR", fonts_dir=None,
        whisper_model="large-v3", language="ko", transcript=None, use_llm=True, llm_model="claude-sonnet-5-5",
        audience="일반 시청자", avoid_terms=(), api_key=None, progress=print):
    video = Path(video)
    out = Path(out_root) / slug(video.stem)
    (out / "clips").mkdir(parents=True, exist_ok=True)

    # 1) 대본 (이미 있으면 재사용)
    cache = out / "transcript.json"
    if transcript:
        segs = load_transcript(transcript)
        progress(f"대본 불러옴: {len(segs)}문장")
    elif cache.exists():
        segs = segments_from_dicts(json.loads(cache.read_text(encoding="utf-8")))
        progress(f"저장된 대본 재사용: {len(segs)}문장")
    else:
        progress("음성 인식 중… (처음엔 모델 다운로드로 오래 걸릴 수 있어요)")
        segs = transcribe(video, whisper_model, language)
    save_transcript(segs, cache)
    if not segs:
        raise RuntimeError("대본이 비었습니다. 음성이 없는 영상이거나 인식에 실패했어요.")

    # 2) 하이라이트
    if use_llm:
        progress("하이라이트 분석 중 (Claude)…")
        clips = highlights.select_with_claude(segs, n, min_s, max_s, audience, avoid_terms, llm_model, api_key)
    else:
        progress("하이라이트 분석 중 (규칙 기반)…")
        clips = highlights.select_heuristic(segs, n, min_s, max_s, avoid_terms)
    if not clips:
        raise RuntimeError("조건에 맞는 구간을 찾지 못했어요. 길이 범위를 넓히거나 금지어를 줄여 보세요.")

    # 3) 렌더링
    all_words = [w for s in segs for w in s.words]
    rows = []
    for i, c in enumerate(clips, 1):
        name = f"short_{i:02d}.mp4"
        progress(f"렌더링 {i}/{len(clips)}: {c['hook_title']} ({c['start']:.0f}~{c['end']:.0f}초)")
        render_clip(video, out / "clips" / name, c["start"], c["end"], all_words, c["hook_title"], layout, font, fonts_dir)
        c["file"] = str(out / "clips" / name)
        rows.append(c)

    (out / "clips.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "upload_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f)
        wr.writerow(["파일", "업로드 제목", "설명", "해시태그", "총점", "훅", "흐름", "가치", "트렌드", "선정 이유", "주의"])
        for c in rows:
            s = c["scores"]
            wr.writerow([Path(c["file"]).name, c["yt_title"], c.get("description", ""), " ".join(c.get("hashtags", [])),
                         c["total"], s["hook"], s["flow"], s["value"], s["trend"], c["reason"], "; ".join(c.get("risk_flags", []))])
    progress(f"완료: {out}")
    return {"out_dir": str(out), "clips": rows}
