"""유튜브 링크 내려받기(yt-dlp). 본인 소유 또는 사용 허락을 받은 영상에만 사용하세요."""
import subprocess
from pathlib import Path


def download(url, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmpl = str(out_dir / "source.%(ext)s")
    subprocess.run(
        ["yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4",
         "--no-playlist", "-o", tmpl, url], check=True)
    found = sorted(out_dir.glob("source.*"))
    if not found:
        raise RuntimeError("다운로드한 파일을 찾지 못했습니다")
    return found[0]
