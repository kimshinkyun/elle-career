import argparse
import sys

from .download import download
from .pipeline import run
from .render import default_font


def main(argv=None):
    p = argparse.ArgumentParser(prog="shortsgen", description="롱폼 영상 → 쇼츠 자동 생성기")
    p.add_argument("input", help="영상 파일 경로 또는 유튜브 URL")
    p.add_argument("-n", type=int, default=5, help="만들 쇼츠 개수")
    p.add_argument("--min", dest="min_s", type=int, default=25)
    p.add_argument("--max", dest="max_s", type=int, default=55)
    p.add_argument("--layout", choices=["stack", "fit", "crop"], default="stack", help="stack: 이지컷 스타일(상단 제목+정사각 영상)")
    p.add_argument("--cap-style", choices=["box", "karaoke"], default="box", help="box: 박스 자막 / karaoke: 말하는 단어 노랑 강조")
    p.add_argument("--footer", default="", help="하단 문구 (예: 댓글에 '세금' → 3분 계산기)")
    p.add_argument("--font", default=default_font(), help="자막 글꼴 이름 (기본: 운영체제별 한글 글꼴)")
    p.add_argument("--fonts-dir", help="글꼴 파일이 들어있는 폴더 (선택)")
    p.add_argument("--whisper", default="large-v3", help="large-v3(정확) / medium / small(빠름)")
    p.add_argument("--language", default="ko")
    p.add_argument("--transcript", help="이미 있는 자막(.srt/.json) 사용 시")
    p.add_argument("--no-llm", action="store_true", help="Claude 없이 규칙 기반으로 선별")
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--audience", default="일반 시청자")
    p.add_argument("--avoid", default="", help="이 단어가 나오는 구간은 제외 (쉼표 구분). 예: 조합,수익 보장")
    p.add_argument("--out", default="output")
    a = p.parse_args(argv)

    src = a.input
    if src.startswith("http"):
        print("영상 내려받는 중… (본인 소유/허락받은 영상만 사용하세요)")
        src = download(src, f"{a.out}/_downloads")
    res = run(src, a.out, a.n, a.min_s, a.max_s, a.layout, a.font, a.fonts_dir, a.whisper, a.language,
              a.transcript, not a.no_llm, a.model, a.audience, [t.strip() for t in a.avoid.split(",") if t.strip()], None, print, a.cap_style, a.footer)
    for c in res["clips"]:
        print(f"  {c['total']:5.1f}점  {c['hook_title']}  →  {c['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
