"""음성 → 단어 단위 타임스탬프 대본. 로컬 faster-whisper 사용(무료, 영상이 외부로 나가지 않음)."""
import json
import re
from pathlib import Path

from .models import Segment, Word, segments_from_dicts


def transcribe(path, model_size="large-v3", language="ko", device="auto", progress=None):
    from faster_whisper import WhisperModel   # 지연 임포트: 설치 안 된 환경에서도 나머지 기능 사용 가능

    model = WhisperModel(model_size, device=device, compute_type="auto")
    seg_iter, info = model.transcribe(
        str(path), language=language, word_timestamps=True, vad_filter=True, beam_size=5
    )
    out = []
    for s in seg_iter:
        words = [Word(w.start, w.end, w.word.strip()) for w in (s.words or []) if w.word.strip()]
        out.append(Segment(s.start, s.end, s.text.strip(), words))
        if progress and info.duration:
            progress(min(s.end / info.duration, 1.0))
    return out


def _ts(v):
    h, m, rest = v.strip().split(":")
    s, ms = re.split(r"[,.]", rest)
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def spread_words(start, end, text):
    """단어 타임스탬프가 없는 자막(SRT)용: 글자 수 비례로 단어 시간을 배분."""
    toks = text.split()
    if not toks:
        return []
    total = sum(len(t) for t in toks) or 1
    t, out = start, []
    for tok in toks:
        d = (end - start) * len(tok) / total
        out.append(Word(t, t + d, tok))
        t += d
    return out


def parse_srt(text):
    segs = []
    for block in re.split(r"\n\s*\n", text.strip().replace("\r\n", "\n")):
        lines = [l for l in block.split("\n") if l.strip()]
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        a, b = lines[idx].split("-->")
        body = " ".join(lines[idx + 1:]).strip()
        s, e = _ts(a), _ts(b.split()[0])
        if body:
            segs.append(Segment(s, e, body, spread_words(s, e, body)))
    return segs


def load_transcript(path):
    p = Path(path)
    raw = p.read_text(encoding="utf-8-sig")
    if p.suffix.lower() == ".json":
        segs = segments_from_dicts(json.loads(raw))
        for s in segs:
            if not s.words:
                s.words = spread_words(s.start, s.end, s.text)
        return segs
    return parse_srt(raw)


def save_transcript(segments, path):
    Path(path).write_text(json.dumps([s.to_dict() for s in segments], ensure_ascii=False, indent=1), encoding="utf-8")
