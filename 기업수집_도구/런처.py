"""
법인전환 컨설팅 업무 통합 런처
실행: python 런처.py
"""
import os, sys, subprocess, glob

BASE = os.path.dirname(os.path.abspath(__file__))

def clear():
    os.system("cls")

def run(script):
    path = os.path.join(BASE, script)
    if not os.path.exists(path):
        print(f"\n❌ 파일 없음: {script}")
        input("Enter 계속...")
        return
    subprocess.run([sys.executable, path], cwd=BASE)
    input("\nEnter 키로 메뉴로 돌아가기...")

def open_file(filename):
    path = os.path.join(BASE, filename)
    matches = glob.glob(path)
    if not matches:
        print(f"\n❌ 파일 없음: {filename}")
        input("Enter 계속...")
        return
    os.startfile(sorted(matches)[-1])

def check_files():
    required = ["올인원_처리.py", "이메일_자동발송.py", "자동_콘텐츠생성기.py"]
    excel    = glob.glob(os.path.join(BASE, "크롤링결과*.xlsx"))
    results  = {
        "DB분류완성.xlsx"   : os.path.exists(os.path.join(BASE, "DB분류완성.xlsx")),
        "이메일발송준비.xlsx": os.path.exists(os.path.join(BASE, "이메일발송준비.xlsx")),
        "크롤링결과 엑셀"    : len(excel) > 0,
        "발송기록.csv"      : os.path.exists(os.path.join(BASE, "발송기록.csv")),
    }
    return results

def main():
    while True:
        clear()
        status = check_files()

        def dot(key):
            return "✅" if status.get(key) else "❌"

        excel_files = glob.glob(os.path.join(BASE, "크롤링결과*.xlsx"))
        excel_name  = os.path.basename(excel_files[-1]) if excel_files else "없음"

        sent_count = 0
        log_path   = os.path.join(BASE, "발송기록.csv")
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8-sig") as f:
                sent_count = max(0, sum(1 for _ in f) - 1)

        print("=" * 52)
        print("   법인전환 컨설팅 업무 통합 런처")
        print("=" * 52)
        print(f"  폴더: {BASE}")
        print(f"  엑셀: {excel_name}")
        print("-" * 52)
        print(f"  {dot('크롤링결과 엑셀')} 크롤링 데이터")
        print(f"  {dot('DB분류완성.xlsx')} DB 분류 결과")
        print(f"  {dot('이메일발송준비.xlsx')} 이메일 발송 목록")
        print(f"  {'✅' if sent_count>0 else '❌'} 이메일 발송 기록 ({sent_count:,}건)")
        print("=" * 52)
        print()
        print("  [1] DB 분류 + 이메일 추출       (올인원_처리.py)")
        print("  [2] 이메일 자동 발송             (하루 80건)")
        print("  [3] SNS 콘텐츠 자동 생성         (Claude API)")
        print()
        print("  [4] DB분류 결과 열기             (Excel)")
        print("  [5] 이메일 발송 목록 열기        (Excel)")
        print("  [6] 절세 챗봇 열기              (브라우저)")
        print("  [7] SNS 마케팅 콘텐츠 열기       (브라우저)")
        print("  [8] 영업 대시보드 열기           (브라우저)")
        print()
        print("  [0] 종료")
        print()

        choice = input("  번호 입력: ").strip()

        if choice == "1":
            clear()
            print("DB 분류 + 이메일 추출 시작...\n")
            run("올인원_처리.py")
        elif choice == "2":
            clear()
            print("이메일 자동 발송 시작...\n")
            run("이메일_자동발송.py")
        elif choice == "3":
            clear()
            print("SNS 콘텐츠 생성 시작...\n")
            run("자동_콘텐츠생성기.py")
        elif choice == "4":
            open_file("DB분류완성.xlsx")
        elif choice == "5":
            open_file("이메일발송준비.xlsx")
        elif choice == "6":
            open_file("절세_챗봇.html")
        elif choice == "7":
            open_file("SNS마케팅_콘텐츠.html")
        elif choice == "8":
            open_file("영업대시보드.html")
        elif choice == "0":
            break
        else:
            pass

if __name__ == "__main__":
    main()
