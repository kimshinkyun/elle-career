"""9:16 렌더링.

레이아웃
  stack(기본, 이지컷 스타일): 검은 배경 · 상단 2줄 제목(둘째 줄 강조색) · 가운데 정사각 영상 · 영상 위 박스 자막 · 하단 문구
  fit  : 블러 배경 위에 원본 전체 보이기 (슬라이드·화면공유에 안전)
  crop : 화면 꽉 채우기 (가로 영상은 얼굴 위치 따라 자름)
"""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

W, H = 1080, 1920
ZONE_Y, ZONE_H = 420, 1080            # stack: 영상 영역 (위 420 제목, 아래 420 하단 문구)
YELLOW = r"{\c&H0000F0FF&}"           # BGR 노랑
WHITE = r"{\c&H00FFFFFF&}"
ACCENT = r"{\c&H00D6E62E&}"           # BGR → #2EE6D6 청록 (제목 둘째 줄)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


# ───────────────────────── 제목 ─────────────────────────
def split_title(title, max_line=16):
    """제목을 두 줄로. 줄바꿈이 있으면 존중, 없으면 가운데 공백 근처에서 나눔."""
    t = title.replace("\r", "").strip()
    if "\n" in t:
        a, b = [x.strip() for x in t.split("\n", 1)]
    elif len(t) <= 12 or " " not in t:
        a, b = (t, "") if len(t) <= max_line else (t[: len(t) // 2], t[len(t) // 2:])
    else:
        mid = len(t) // 2
        cut = min((m.start() for m in re.finditer(" ", t)), key=lambda i: abs(i - mid))
        a, b = t[:cut].strip(), t[cut + 1:].strip()
    return a[:max_line], b[:max_line]


# ───────────────────────── 자막(ASS) ─────────────────────────
def _t(sec):
    sec = max(sec, 0)
    cs = int(round(sec * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _esc(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def chunk_words(words, max_chars=12, max_words=4, max_gap=0.6):
    chunks, cur = [], []
    for w in words:
        if cur and (sum(len(x.text) for x in cur) + len(w.text) > max_chars or len(cur) >= max_words
                    or w.start - cur[-1].end > max_gap):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w.text):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(words, clip_start, clip_end, title, font="Noto Sans KR", layout="stack", cap_style="box",
              footer="", cap_size=None, title_size=None, title_secs=3.0):
    stack = layout == "stack"
    cap_size = cap_size or (62 if stack else 84)
    title_size = title_size or (72 if stack else 78)
    # 자막 위치: stack은 영상 영역 안쪽 하단, 그 외는 화면 아래쪽 1/3 지점
    cap_margin_v = H - (ZONE_Y + ZONE_H - 90) if stack else 560
    if cap_style == "box":
        cap_style_line = (f"Style: Cap,{font},{cap_size},&H00FFFFFF,&H00FFFFFF,&H40000000,&H40000000,-1,0,0,0,100,100,0,0,3,16,0,2,60,60,{cap_margin_v},1")
    else:
        cap_style_line = (f"Style: Cap,{font},{cap_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,2,2,60,60,{cap_margin_v},1")
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
{cap_style_line}
Style: Title,{font},{title_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{4 if stack else 9},0,{8 if not stack else 8},50,50,{120 if stack else 230},1
Style: Foot,{font},44,&H00D8D8D8,&H00D8D8D8,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,8,60,60,{ZONE_Y + ZONE_H + 150},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    ev = []
    dur = clip_end - clip_start
    if title:
        l1, l2 = split_title(title)
        text = WHITE + _esc(l1) + ((r"\N" + ACCENT + _esc(l2)) if l2 else "")
        end = dur if stack else min(title_secs, dur)      # stack은 제목 상시 표시
        ev.append(f"Dialogue: 1,{_t(0)},{_t(end)},Title,,0,0,0,,{{\\fad(150,0)}}{text}")
    if footer and stack:
        ev.append(f"Dialogue: 1,{_t(0)},{_t(dur)},Foot,,0,0,0,,{_esc(footer)}")
    inside = [w for w in words if w.end > clip_start and w.start < clip_end]
    for chunk in chunk_words(inside, max_chars=14 if cap_style == "box" else 12, max_words=5 if cap_style == "box" else 4):
        if cap_style == "box":      # 구절 단위로 통째로 표시 (이지컷 스타일)
            s = max(chunk[0].start, clip_start) - clip_start
            e = min(max(chunk[-1].end, chunk[0].start + 0.4), clip_end) - clip_start
            if e > s:
                ev.append(f"Dialogue: 0,{_t(s)},{_t(e)},Cap,,0,0,0,,{_esc(' '.join(x.text for x in chunk))}")
            continue
        for i, w in enumerate(chunk):   # karaoke: 말하는 단어만 노랗게
            s = max(w.start, clip_start) - clip_start
            nxt = chunk[i + 1].start if i + 1 < len(chunk) else max(w.end, w.start + 0.25)
            e = min(nxt, clip_end) - clip_start
            if e <= s:
                continue
            parts = [(YELLOW if j == i else WHITE) + _esc(x.text) for j, x in enumerate(chunk)]
            ev.append(f"Dialogue: 0,{_t(s)},{_t(e)},Cap,,0,0,0,,{' '.join(parts)}")
    return head + "\n".join(ev) + "\n"


# ───────────────────────── 리프레이밍 ─────────────────────────
def face_center(path, start, dur, samples=12):
    """얼굴 가로 중심(0~1) 중앙값. OpenCV 없거나 못 찾으면 None."""
    try:
        import cv2
    except ImportError:
        return None
    cap = cv2.VideoCapture(str(path))
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    xs = []
    for k in range(samples):
        cap.set(cv2.CAP_PROP_POS_MSEC, (start + dur * (k + 0.5) / samples) * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = det.detectMultiScale(gray, 1.2, 5, minSize=(max(60, frame.shape[1] // 25),) * 2)
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            xs.append((x + w / 2) / frame.shape[1])
    cap.release()
    return sorted(xs)[len(xs) // 2] if len(xs) >= 3 else None


def resolve_layout(layout):
    return "stack" if layout == "auto" else layout


def video_filter(layout, src_w, src_h, cx):
    ar = src_w / src_h
    layout = resolve_layout(layout)
    if layout == "stack":
        if ar >= 1:   # 가로 영상: 높이를 영역에 맞추고 가로를 잘라냄(얼굴 중심 쪽으로)
            scaled_w = ar * ZONE_H
            x = min(max((cx if cx is not None else 0.5) * scaled_w - W / 2, 0), max(scaled_w - W, 0))
            crop = f"scale=-2:{ZONE_H},crop={W}:{ZONE_H}:{x:.0f}:0"
        else:         # 세로 영상: 폭을 맞추고 위쪽 25% 지점부터 잘라냄(얼굴이 보통 위쪽)
            crop = f"scale={W}:-2,crop={W}:{ZONE_H}:0:(ih-{ZONE_H})*0.25"
        return (f"[0:v]{crop},setsar=1[v1];color=c=black:s={W}x{H}:r=30[bg];"
                f"[bg][v1]overlay=0:{ZONE_Y}:shortest=1,setsar=1[base]")
    if layout == "crop":
        scaled_w = ar * H
        x = 0 if scaled_w <= W else min(max((cx if cx is not None else 0.5) * scaled_w - W / 2, 0), scaled_w - W)
        return f"[0:v]scale=-2:{H},crop={W}:{H}:{x:.0f}:0,setsar=1[base]"
    return (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:6,"
            f"eq=brightness=-0.08[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[base]")


def _filter_path(p):
    return str(p).replace("\\", "/").replace(":", r"\:")


def render_clip(src, out, start, end, words, title="", layout="auto", font="Noto Sans KR", fonts_dir=None,
                loudnorm=True, crf=20, cap_style="box", footer=""):
    src_w, src_h, _ = probe(src)
    dur = end - start
    resolved = resolve_layout(layout)
    ar = src_w / src_h
    cx = face_center(src, start, dur) if resolved in ("stack", "crop") and ar > 1 else None   # 가로 영상을 잘라낼 때만 얼굴 추적
    vf = video_filter(resolved, src_w, src_h, cx)
    with tempfile.TemporaryDirectory() as td:
        ass = Path(td) / "cap.ass"
        ass.write_text(build_ass(words, start, end, title, font, resolved, cap_style, footer), encoding="utf-8")
        sub = "ass=cap.ass" + (f":fontsdir={_filter_path(Path(fonts_dir).resolve())}" if fonts_dir else "")
        fc = f"{vf};[base]{sub}[v]"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(Path(src).resolve()),
               "-filter_complex", fc, "-map", "[v]", "-map", "0:a?"]
        if loudnorm:
            cmd += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-r", "30",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(Path(out).resolve())]
        subprocess.run(cmd, cwd=td, check=True)
    return out


def default_font():
    import platform
    return {"Windows": "Malgun Gothic", "Darwin": "Apple SD Gothic Neo"}.get(platform.system(), "Noto Sans KR")


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
