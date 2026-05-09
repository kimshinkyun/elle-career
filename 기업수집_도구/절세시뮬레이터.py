"""
[작업 5] 절세 시뮬레이션 PDF 생성기
의존: pip install reportlab
실행: python 절세시뮬레이터.py
"""
import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 한글 폰트 등록 (시스템에 맞게 경로 조정) ──────────────────────────
FONT_PATHS = [
    r"C:\Windows\Fonts\malgun.ttf",          # 맑은 고딕 (Windows)
    r"C:\Windows\Fonts\gulim.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]
font_registered = False
for fp in FONT_PATHS:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont("KR", fp))
            font_registered = True
            break
        except Exception:
            continue

FONT = "KR" if font_registered else "Helvetica"

# ── 세금 계산 함수 ────────────────────────────────────────────────────

# 업종별 비용비율 (추정치)
EXPENSE_RATIO = {
    "제조업": 0.82,
    "음식점": 0.87,
    "건설업": 0.84,
    "의료업": 0.72,
}

# 종합소득세 누진세율 (2024)
INCOME_TAX_BRACKETS = [
    (14_000_000,  0.06, 0),
    (50_000_000,  0.15, 1_260_000),
    (88_000_000,  0.24, 5_760_000),
    (150_000_000, 0.35, 15_440_000),
    (300_000_000, 0.38, 19_940_000),
    (500_000_000, 0.40, 25_940_000),
    (1_000_000_000, 0.42, 35_940_000),
    (float("inf"),  0.45, 65_940_000),
]

# 법인세 누진세율 (2024)
CORP_TAX_BRACKETS = [
    (200_000_000,       0.09, 0),
    (20_000_000_000,    0.19, 20_000_000),
    (300_000_000_000,   0.21, 420_000_000),
    (float("inf"),      0.24, 9_420_000_000),
]

def calc_income_tax(income: float) -> float:
    """종합소득세 계산 (지방소득세 10% 포함)"""
    for limit, rate, deduct in INCOME_TAX_BRACKETS:
        if income <= limit:
            tax = income * rate - deduct
            return max(tax, 0) * 1.1
    return 0.0

def calc_corp_tax(profit: float) -> float:
    """법인세 계산 (지방소득세 10% 포함)"""
    for limit, rate, deduct in CORP_TAX_BRACKETS:
        if profit <= limit:
            tax = profit * rate - deduct
            return max(tax, 0) * 1.1
    return 0.0

def calc_근로소득세(salary: float) -> float:
    """대표자 급여 소득세 (근로소득공제 적용 후)"""
    # 근로소득공제 간이 계산
    if salary <= 5_000_000:
        deduction = salary * 0.70
    elif salary <= 15_000_000:
        deduction = 3_500_000 + (salary - 5_000_000) * 0.40
    elif salary <= 45_000_000:
        deduction = 7_500_000 + (salary - 15_000_000) * 0.15
    elif salary <= 100_000_000:
        deduction = 12_000_000 + (salary - 45_000_000) * 0.05
    else:
        deduction = 14_750_000
    net = max(salary - deduction - 1_500_000, 0)  # 인적공제 150만
    return calc_income_tax(net) / 1.1  # 지방소득세 제외 후 재계산 (급여는 별도)

def simulate(업종: str, 매출: float) -> dict:
    ratio = EXPENSE_RATIO.get(업종, 0.80)
    소득 = 매출 * (1 - ratio)

    # ── 개인사업자 ────────────────────────────────────
    종합소득세 = calc_income_tax(소득)
    건보_개인 = 소득 * 0.0709  # 건강보험료 (개인사업자)

    # ── 법인 전환 후 ──────────────────────────────────
    # 대표자 급여: 소득의 60% (절세 최적화 설정)
    대표급여 = min(소득 * 0.60, 120_000_000)
    법인이익 = 소득 - 대표급여
    법인세 = calc_corp_tax(법인이익)
    대표급여세 = calc_근로소득세(대표급여) * 1.1  # 지방소득세 포함
    건보_법인 = 대표급여 * 0.03545  # 직장가입자 개인부담분 (~절반)

    총세금_개인 = 종합소득세 + 건보_개인
    총세금_법인 = 법인세 + 대표급여세 + 건보_법인

    연간절세 = max(총세금_개인 - 총세금_법인, 0)
    건보절감 = max(건보_개인 - 건보_법인, 0)

    # 영업권 추정 (세법상 3년 평균 순이익 기준 간이계산)
    영업권 = 소득 * 2.5

    return {
        "업종": 업종,
        "매출": 매출,
        "추정소득": 소득,
        "종합소득세": 종합소득세,
        "건보_개인": 건보_개인,
        "총세금_개인": 총세금_개인,
        "법인세": 법인세,
        "대표급여세": 대표급여세,
        "건보_법인": 건보_법인,
        "총세금_법인": 총세금_법인,
        "연간절세": 연간절세,
        "건보절감": 건보절감,
        "영업권": 영업권,
        "5년누적": 연간절세 * 5,
    }

# ── PDF 생성 ─────────────────────────────────────────────────────────

def fmt(n: float) -> str:
    if n >= 100_000_000:
        return f"{n/100_000_000:.1f}억원"
    elif n >= 10_000:
        return f"{n/10_000:,.0f}만원"
    return f"{n:,.0f}원"

def make_pdf(data: dict, path: str):
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )
    styles = getSampleStyleSheet()
    def S(size, bold=False, color=colors.black, align=0):
        return ParagraphStyle(
            "x", fontName=FONT, fontSize=size,
            textColor=color, alignment=align,
            leading=size*1.5,
            spaceAfter=2,
            fontWeight="Bold" if bold else "Normal",
        )

    GOLD = colors.HexColor("#C9A96E")
    DARK = colors.HexColor("#1A1A2E")

    story = []

    # 헤더
    story.append(Paragraph("법인전환 절세 시뮬레이션 보고서", S(22, bold=True, color=DARK, align=1)))
    story.append(Paragraph(f"업종: {data['업종']}  |  매출: {fmt(data['매출'])}", S(12, color=colors.grey, align=1)))
    story.append(Paragraph(f"작성일: {datetime.date.today().strftime('%Y년 %m월 %d일')}", S(10, color=colors.grey, align=1)))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=12))

    # 비교 표
    def row(label, val1, val2, highlight=False):
        bg = colors.HexColor("#FFF8EC") if highlight else colors.white
        return [label, val1, val2]

    table_data = [
        ["구분", "현재 (개인사업자)", "법인 전환 후"],
        ["추정 소득(순이익)", fmt(data["추정소득"]), fmt(data["추정소득"])],
        ["종합소득세 / 법인세", fmt(data["종합소득세"]), fmt(data["법인세"])],
        ["대표자 급여 소득세", "-", fmt(data["대표급여세"])],
        ["건강보험료", fmt(data["건보_개인"]), fmt(data["건보_법인"])],
        ["합계 세금+보험료", fmt(data["총세금_개인"]), fmt(data["총세금_법인"])],
    ]

    t = Table(table_data, colWidths=[60*mm, 60*mm, 60*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), FONT),
        ("FONTSIZE",      (0, 0), (-1, 0), 11),
        ("FONTSIZE",      (0, 1), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F6F2")]),
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#FFF3DC")),
        ("FONTNAME",      (0, -1), (-1, -1), FONT),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#E0D8C8")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # 핵심 결과 박스
    highlights = [
        ("💰 연간 절세액",    fmt(data["연간절세"]),  GOLD),
        ("🏥 건강보험료 절감", fmt(data["건보절감"]),  colors.HexColor("#4CAF50")),
        ("📋 영업권 추정액",  fmt(data["영업권"]),    colors.HexColor("#2196F3")),
        ("📈 5년 누적 절세액", fmt(data["5년누적"]),  colors.HexColor("#E91E63")),
    ]

    hi_data = [["항목", "금액"]] + [[h[0], h[1]] for h in highlights]
    ht = Table(hi_data, colWidths=[90*mm, 80*mm])
    ht.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), FONT),
        ("FONTSIZE",      (0, 0), (-1, -1), 12),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR",     (1, 1), (1, 1), GOLD),
        ("TEXTCOLOR",     (1, 2), (1, 2), colors.HexColor("#4CAF50")),
        ("TEXTCOLOR",     (1, 3), (1, 3), colors.HexColor("#2196F3")),
        ("TEXTCOLOR",     (1, 4), (1, 4), colors.HexColor("#E91E63")),
        ("FONTNAME",      (1, 1), (1, -1), FONT),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#E0D8C8")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F6F2")]),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(Paragraph("■ 핵심 절세 효과 요약", S(13, bold=True, color=DARK)))
    story.append(Spacer(1, 6))
    story.append(ht)
    story.append(Spacer(1, 20))

    # 안내문
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "※ 본 시뮬레이션은 추정치이며, 실제 세금은 공인세무사 상담을 통해 정확히 산출하시기 바랍니다.",
        S(8, color=colors.grey)
    ))
    story.append(Paragraph(
        "※ 영업권은 법인전환 시 세법상 양도소득세 계산에 활용되며, 실제 평가액과 차이가 있을 수 있습니다.",
        S(8, color=colors.grey)
    ))

    doc.build(story)
    print(f"✅ PDF 저장 완료: {path}")


# ── 메인 실행 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  법인전환 절세 시뮬레이터")
    print("=" * 50)

    업종목록 = list(EXPENSE_RATIO.keys())
    print("\n업종을 선택하세요:")
    for i, b in enumerate(업종목록, 1):
        print(f"  {i}. {b}")
    선택 = input("번호 입력: ").strip()
    try:
        업종 = 업종목록[int(선택) - 1]
    except (ValueError, IndexError):
        업종 = input("업종명 직접 입력: ").strip()

    매출_입력 = input("연간 매출액을 입력하세요 (단위: 만원, 예: 50000): ").strip()
    매출 = float(매출_입력.replace(",", "")) * 10_000

    result = simulate(업종, 매출)

    print("\n" + "=" * 50)
    print(f"  {업종} | 매출 {fmt(매출)}")
    print("=" * 50)
    print(f"  추정 소득:       {fmt(result['추정소득'])}")
    print(f"  현재 종합소득세: {fmt(result['종합소득세'])}")
    print(f"  법인전환 후 세금합계: {fmt(result['총세금_법인'])}")
    print(f"  ─────────────────────")
    print(f"  연간 절세액:     {fmt(result['연간절세'])}")
    print(f"  건강보험료 절감: {fmt(result['건보절감'])}")
    print(f"  영업권 추정:     {fmt(result['영업권'])}")
    print(f"  5년 누적 절세:   {fmt(result['5년누적'])}")

    save_dir = r"C:\Users\user\Desktop\기업수집"
    os.makedirs(save_dir, exist_ok=True)
    fname = f"절세시뮬레이션_{업종}_{int(매출/10000)}만원_{datetime.date.today()}.pdf"
    path = os.path.join(save_dir, fname)
    make_pdf(result, path)
