"""9:16 렌더링: 리프레이밍 + 단어별 하이라이트 자막(ASS) + 상단 훅 문구 + 음량 정규화."""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

W, H = 1080, 1920
YELLOW = r"{\c&H0000F0FF&}"   # BGR: 노랑
WHITE = r"{\c&H00FFFFFF&}"


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


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


def build_ass(words, clip_start, clip_end, title, font="Noto Sans KR", cap_size=84, title_size=78, title_secs=3.0):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,{font},{cap_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,2,2,60,60,560,1
Style: Title,{font},{title_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,9,0,8,70,70,230,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    ev = []
    if title:
        # 두 줄로 자연스럽게 나눔
        t = _esc(title)
        if len(t) > 10 and " " in t:
            mid = len(t) // 2
            cut = min((m.start() for m in re.finditer(" ", t)), key=lambda i: abs(i - mid))
            t = t[:cut] + r"\N" + t[cut + 1:]
        ev.append(f"Dialogue: 1,{_t(0)},{_t(title_secs)},Title,,0,0,0,,{{\\fad(150,250)}}{t}")
    inside = [w for w in words if w.end > clip_start and w.start < clip_end]
    for chunk in chunk_words(inside):
        for i, w in enumerate(chunk):
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


def video_filter(layout, src_w, src_h, cx):
    ar = src_w / src_h
    if layout == "auto":
        layout = "crop" if ar <= 0.75 else "fit"
    if layout == "crop":
        # 높이를 1920에 맞추고 가로를 잘라냄. 얼굴 중심이 있으면 그쪽으로 이동
        scaled_w = ar * H
        x = 0 if scaled_w <= W else min(max((cx if cx is not None else 0.5) * scaled_w - W / 2, 0), scaled_w - W)
        return f"[0:v]scale=-2:{H},crop={W}:{H}:{x:.0f}:0,setsar=1[base]"
    # fit: 원본은 위·아래 여백 없이 가운데, 배경은 같은 영상을 키워 블러(슬라이드·화면공유·와이드 영상에 안전)
    return (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:6,"
            f"eq=brightness=-0.08[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[base]")


def _filter_path(p):
    return str(p).replace("\\", "/").replace(":", r"\:")


def render_clip(src, out, start, end, words, title="", layout="auto", font="Noto Sans KR", fonts_dir=None,
                loudnorm=True, crf=20):
    src_w, src_h, _ = probe(src)
    dur = end - start
    ar = src_w / src_h
    resolved = layout if layout != "auto" else ("crop" if ar <= 0.75 else "fit")
    cx = face_center(src, start, dur) if resolved == "crop" and ar > 0.75 else None   # 가로 영상을 잘라낼 때만 얼굴 추적
    vf = video_filter(resolved, src_w, src_h, cx)
    with tempfile.TemporaryDirectory() as td:
        ass = Path(td) / "cap.ass"
        ass.write_text(build_ass(words, start, end, title, font=font), encoding="utf-8")
        sub = f"ass=cap.ass" + (f":fontsdir={_filter_path(Path(fonts_dir).resolve())}" if fonts_dir else "")
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
