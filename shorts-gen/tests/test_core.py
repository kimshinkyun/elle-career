import os
import shutil
import subprocess
from pathlib import Path

import pytest

from shortsgen import highlights as H
from shortsgen.models import Segment, Word
from shortsgen.render import build_ass, chunk_words, render_clip, probe
from shortsgen.transcribe import parse_srt, spread_words

SENT = [
    "원장님들이 가장 많이 놓치는 세금 실수 3가지를 알려드립니다.",
    "첫 번째는 내 소득 구간을 모르고 지나가는 겁니다.",
    "과세표준이 한 구간만 올라도 세율이 크게 달라집니다.",
    "두 번째는 연말 기한이 있는 항목을 놓치는 경우예요.",
    "1월에 알아서는 이미 늦습니다.",
    "세 번째는 한도와 조건을 읽지 않고 결정하는 겁니다.",
    "그래서 결론은 연말 전에 한 번 계산해 보시라는 거예요.",
    "안녕하세요 여러분 오늘도 영상 보러 와주셔서 감사합니다.",
    "이 부분은 잡담이라서 쇼츠로 쓰기에는 별로입니다.",
    "그런데 다음 이야기는 정말 중요한 핵심 포인트입니다.",
]


def make_segments(step=5.0):
    segs, t = [], 0.0
    for s in SENT * 3:
        segs.append(Segment(t, t + step, s, spread_words(t, t + step, s)))
        t += step
    return segs


def test_parse_srt():
    srt = "1\n00:00:01,000 --> 00:00:03,500\n안녕하세요 반갑습니다\n\n2\n00:00:04,000 --> 00:00:06,000\n두 번째 줄\n"
    segs = parse_srt(srt)
    assert len(segs) == 2 and segs[0].start == 1.0 and segs[0].end == 3.5
    assert segs[0].words[0].start == 1.0 and abs(segs[0].words[-1].end - 3.5) < 1e-6


def test_total_score_weights():
    assert H.total_score({"hook": 100, "flow": 0, "value": 0, "trend": 0}) == 35.0


def test_snap_and_limits():
    segs = make_segments()
    assert H.snap(segs, 0.4, 31.0, 25, 55) == (0.0, 30.0)      # 문장 경계로 보정
    assert H.snap(segs, 0, 100, 25, 55)[1] - 0 <= 55            # 최대 길이 강제
    assert H.snap(segs, 0, 10, 25, 55) is None                  # 최소 길이 미만 제외


def test_finalize_dedup_and_avoid_terms():
    segs = make_segments()
    base = {"hook_title": "t", "yt_title": "t", "reason": "r", "scores": {"hook": 80, "flow": 80, "value": 80, "trend": 80}}
    cands = [dict(base, start=0, end=30), dict(base, start=5, end=35), dict(base, start=50, end=80)]
    out = H.finalize(cands, segs, 5, 25, 55)
    assert len(out) == 2                                          # 겹치는 후보는 하나만
    out2 = H.finalize(cands, segs, 5, 25, 55, avoid_terms=["세금 실수"])
    assert all("세금 실수" not in H.clip_text(segs, c["start"], c["end"]) for c in out2)


def test_heuristic_prefers_non_greeting():
    segs = make_segments()
    out = H.select_heuristic(segs, n=3, min_s=25, max_s=45)
    assert out and all(c["end"] - c["start"] <= 45 for c in out)
    assert all(not c["hook_title"].startswith("안녕하세요") for c in out)


def test_chunk_and_ass():
    words = spread_words(0, 4, "원장님 연말 전에 세금 한 번 계산해 보세요.")
    chunks = chunk_words(words)
    assert all(len(c) <= 4 for c in chunks)
    ass = build_ass(words, 0, 4, "연말 전에 3분만 계산하세요")
    assert "Style: Cap" in ass and "Dialogue: 1," in ass and ass.count("Dialogue: 0,") == len(words)
    assert "{" not in ass.split("[Events]")[1].replace("{\\", "").replace("{\\c", "")  # 입력 중괄호 이스케이프


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg 필요")
def test_render_end_to_end(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=40",
                    "-f", "lavfi", "-i", "sine=f=440:d=40", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(src)], check=True)
    segs = make_segments()
    words = [w for s in segs for w in s.words]
    out = tmp_path / "o.mp4"
    render_clip(src, out, 5.0, 35.0, words, "연말 전에 3분만 계산하세요", "fit",
                fonts_dir=os.environ.get("SHORTS_TEST_FONTS"))
    w, h, d = probe(out)
    assert (w, h) == (1080, 1920) and 29 < d < 31
    out2 = tmp_path / "o2.mp4"
    render_clip(src, out2, 5.0, 35.0, words, "", "crop", fonts_dir=os.environ.get("SHORTS_TEST_FONTS"))
    assert probe(out2)[:2] == (1080, 1920)
