"""릴스 1 (구간 충격형) 조립 스크립트.
배경 클립 4개(clips/c1..c4.mp4, 720x1280) + 한글 자막 PNG 오버레이 + 엔드카드 → reel1.mp4
사용: python3 make_reel1.py <clips_dir> <font.ttf> <out.mp4>"""
import sys, subprocess, os, tempfile
from PIL import Image, ImageDraw, ImageFont

clips_dir, font_path, out = sys.argv[1:4]
W, H = 720, 1280
DISC = "세금 정보 제공 목적의 참고용 추정 · 투자 권유 아님"

def font(size, bold=True):
    f = ImageFont.truetype(font_path, size)
    try: f.set_variation_by_name("Bold" if bold else "Regular")
    except Exception: pass
    return f

def centered(d, y, s, f, fill, shadow=True):
    w = d.textlength(s, font=f); x = (W - w) / 2
    if shadow:
        for dx, dy in [(-2,2),(2,2),(0,3),(3,0)]: d.text((x+dx, y+dy), s, font=f, fill=(0,0,0,200))
    d.text((x, y), s, font=f, fill=fill)

def overlay(path, lines, accent_idx=None, sub=None):
    img = Image.new("RGBA", (W, H), (0,0,0,0)); d = ImageDraw.Draw(img)
    # 가독성용 하단·중앙 스크림
    scrim = Image.new("RGBA", (W, H), (0,0,0,0)); sd = ImageDraw.Draw(scrim)
    for i in range(520):
        a = int(170 * (i/520)); sd.line([(0, H-520+i), (W, H-520+i)], fill=(8,16,34,a))
    sd.rectangle([0, 360, W, 840], fill=(8,16,34,70))
    img = Image.alpha_composite(img, scrim); d = ImageDraw.Draw(img)
    f = font(54); y = 470 - (len(lines)-1)*38
    for i, s in enumerate(lines):
        centered(d, y, s, f, (232,213,176,255) if i == accent_idx else (255,255,255,255)); y += 84
    if sub: centered(d, y + 10, sub, font(34, False), (225,230,240,255))
    centered(d, H-96, DISC, font(22, False), (210,215,225,255), shadow=False)
    img.save(path)

def endcard(path):
    img = Image.new("RGBA", (W, H), (15,27,51,255))
    glow = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(glow).ellipse([W/2-300, 300, W/2+300, 900], fill=(201,169,110,28))
    img = Image.alpha_composite(img, glow); d = ImageDraw.Draw(img)
    centered(d, 380, "댓글에 ‘세금’", font(78), (232,213,176,255), shadow=False)
    centered(d, 500, "3분 계산기 링크를", font(54), (255,255,255,255), shadow=False)
    centered(d, 575, "보내드려요", font(54), (255,255,255,255), shadow=False)
    d.rounded_rectangle([W/2-210, 720, W/2+210, 800], radius=40, outline=(201,169,110,255), width=3)
    centered(d, 735, "가입 없이 결과 확인", font(36, False), (255,255,255,255), shadow=False)
    centered(d, 880, "MAKERS", font(44), (201,169,110,255), shadow=False)
    centered(d, H-96, DISC, font(22, False), (170,180,200,255), shadow=False)
    img.save(path)

segs = [
  ("c1", ["원장님, 같은 3천만원 공제인데", "절세액이 이렇게 달라요"], 1, None),
  ("c2", ["과세표준 8,800만원 초과 35%", "1.5억 초과 38% · 3억 초과 40%"], None, "내 최고세율부터 확인하세요"),
  ("c3", ["2.5억 원장님 · 3천만원 공제", "추정 절세 약 1,254만원"], 1, "소득세+지방소득세 포함"),
  ("c4", ["단, 한도와 조건이 있어요", "세무사 확인은 필수"], None, None),
]
tmp = tempfile.mkdtemp(); parts = []
for name, lines, acc, sub in segs:
    png = f"{tmp}/{name}.png"; overlay(png, lines, acc, sub)
    seg = f"{tmp}/{name}.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",f"{clips_dir}/{name}.mp4","-loop","1","-i",png,
        "-filter_complex","[0:v]scale=720:1280,fps=30,setsar=1[v];[1:v]format=rgba,fade=t=in:st=0.15:d=0.35:alpha=1[o];[v][o]overlay=0:0:shortest=1,format=yuv420p",
        "-t","5","-an","-c:v","libx264","-crf","18",seg], check=True)
    parts.append(seg)
png = f"{tmp}/end.png"; endcard(png); seg = f"{tmp}/end.mp4"
subprocess.run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",png,"-t","4","-vf","fps=30,format=yuv420p,fade=t=in:st=0:d=0.3","-c:v","libx264","-crf","18",seg], check=True); parts.append(seg)
lst = f"{tmp}/list.txt"; open(lst,"w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,"-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
    "-shortest","-c:v","libx264","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","96k","-movflags","+faststart",out], check=True)
print("done", out)
