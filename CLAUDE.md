# CLAUDE.md — 법인전환 컨설팅 자동화 프로젝트

## 사용자 정보
- **직업**: 법인전환 전문 컨설턴트
- **지역**: 여수·순천·광양 (전남)
- **타겟**: 연매출 3억~10억 개인사업자 사장님
- **목표**: DB 수집 → 이메일 발송 → SNS 마케팅 → 상담 유도

## 환경
- **OS**: Windows 10, OneDrive 연동 바탕화면
- **Python**: 3.14 (`C:\Python314\`)
- **작업폴더**: `C:\Users\user\Desktop\기업수집` (실제: OneDrive\바탕화면\기업수집)
- **GitHub**: `kimshinkyun/elle-career` / branch: `claude/utilize-internal-resources-Wldx1`
- **이메일**: `tlsrbs3000@gmail.com` (Gmail 앱비밀번호 설정됨)
- **Claude API**: `api_key.txt` 파일에 저장 (기업수집 폴더 내)
- **GitHub PAT**: 별도 보관 (push 시 remote URL에 직접 입력)

## 파일 구조 (`기업수집_도구/`)
```
런처.py                  ← 통합 메뉴 (python 런처.py 로 실행)
올인원_처리.py            ← 크롤링결과*.xlsx → DB분류완성.xlsx + 이메일발송준비.xlsx
이메일_자동발송.py         ← Gmail SMTP, 하루 80건, 업종별 맞춤 이메일
자동_콘텐츠생성기.py       ← Claude API → 오늘의 SNS 콘텐츠 HTML 생성
카카오_발송.py             ← 카카오 API 안내 (직접발송 불가, 채널 유도)
패치.py                  ← 올인원_처리.py has() 버그 수정용 (이미 적용됨)
setup.py                 ← 전체 파일 다운로드 스크립트
절세_챗봇.html            ← 웹 챗봇 (업종/매출 입력→절세액 계산)
SNS마케팅_콘텐츠.html      ← 인스타/블로그/쇼츠/DM/이메일/카카오 콘텐츠 전체
영업대시보드.html           ← 발송현황/업종통계 대시보드
절세진단.html              ← 절세 진단 웹페이지
카카오오픈빌더_시나리오.txt ← 카카오 i 오픈빌더 설정 가이드
api_key.txt              ← Claude API 키 (로컬 전용, GitHub 미포함)
```

## 데이터 구조
- **입력**: `크롤링결과_YYYYMMDD_HHMM.xlsx`
  - 컬럼: `회사이름, 대표자명, 업종명, 주소, 홈페이지, 이메일1, 이메일2, 이메일3, 팩스1, 팩스2, 상태코드`
  - 행수: 2,700행
- **출력**:
  - `DB분류완성.xlsx` — 5시트 (팩스+이메일/팩스만/이메일만/둘다없음/업종통계)
  - `이메일발송준비.xlsx` — 이메일 있는 업체만
  - `발송기록.csv` — 발송 이력 (중복발송 방지용)
  - `콘텐츠생성결과/YYYYMMDD_업종_콘텐츠.html` — 일별 SNS 콘텐츠

## 핵심 로직

### 올인원_처리.py
```python
BASE = os.path.dirname(os.path.abspath(__file__))  # 경로 자동감지
# has() 함수 — 이메일1/2/3, 팩스1/2 유무 판별 (bool Series 반환)
def has(col):
    result = df[col].str.strip() != ""
    if col == c_email1:
        for extra in [c_email2, find_col(df, ["이메일3"])]:
            if extra: result = result | (df[extra].str.strip() != "")
    if col == c_fax1 and c_fax2:
        result = result | (df[c_fax2].str.strip() != "")
    return result
```

### 이메일_자동발송.py
```python
SMTP: smtp.gmail.com:587
USER: tlsrbs3000@gmail.com
DAILY_LIMIT: 80건/일
DELAY: 8~20초 랜덤 (스팸필터 우회)
# 업종 키워드로 맞춤 제목+본문 자동 선택
# 발송기록.csv로 중복 방지
```

### 자동_콘텐츠생성기.py
```python
# api_key.txt에서 키 읽기 (utf-8-sig, BOM 처리)
# 섹션별 4회 API 호출 (JSON 아님 — 잘림 방지)
# 업종/주제 연중일수 기준 자동 순환
# 결과: HTML 파일 (탭별 복사버튼)
```

## 알려진 이슈 & 해결책
| 이슈 | 원인 | 해결 |
|------|------|------|
| `has()` TypeError | str\|bool 타입충돌 | `df[col].str.strip() != ""` bool Series 사용 |
| cmd 한글 깨짐 | CP949 vs UTF-8 | PowerShell 사용 또는 영어 파일명 |
| curl -o 한글 오류 | cmd 인코딩 | `Invoke-WebRequest` 사용 |
| api_key.txt BOM | PowerShell Out-File | `encoding="utf-8-sig"` 로 읽기 |
| JSON 잘림 | max_tokens 부족 | 섹션별 분리호출로 변경 |
| GitHub push 거절 | API 키 노출 감지 | api_key.txt 로컬 저장, gitignore |
| 경로 못찾음 | OneDrive 이동 | `os.path.dirname(os.path.abspath(__file__))` |

## 실행 방법 (PowerShell)
```powershell
cd "$env:USERPROFILE\Desktop\기업수집"
python 런처.py
# 메뉴: 1=DB분류 2=이메일발송 3=SNS콘텐츠 4~8=파일열기
```

## 파일 다운로드 (PowerShell)
```powershell
$base = "https://raw.githubusercontent.com/kimshinkyun/elle-career/claude/utilize-internal-resources-Wldx1/%EA%B8%B0%EC%97%85%EC%88%98%EC%A7%91_%EB%8F%84%EA%B5%AC/"
Invoke-WebRequest "${base}%EB%9F%B0%EC%B2%98.py" -OutFile "런처.py"
Invoke-WebRequest "${base}%EC%98%AC%EC%9D%B8%EC%9B%90_%EC%B2%98%EB%A6%AC.py" -OutFile "올인원_처리.py"
Invoke-WebRequest "${base}%EC%9D%B4%EB%A9%94%EC%9D%BC_%EC%9E%90%EB%8F%99%EB%B0%9C%EC%86%A1.py" -OutFile "이메일_자동발송.py"
Invoke-WebRequest "${base}%EC%9E%90%EB%8F%99_%EC%BD%98%ED%85%90%EC%B8%A0%EC%83%9D%EC%84%B1%EA%B8%B0.py" -OutFile "자동_콘텐츠생성기.py"
```

## 미완료 / 향후 작업
- [ ] `크롤링결과*.xlsx` 파일 복구 필요 (분실됨, Windows 검색으로 찾기)
- [ ] `자동_콘텐츠생성기.py` 3번 메뉴 최종 테스트 필요
- [ ] 이메일 발송 첫 실행 테스트 필요
- [ ] 카카오 i 오픈빌더 실제 설정 (i.kakao.com)
- [ ] 절세_챗봇.html Netlify 배포 후 링크 생성
- [ ] Windows 작업 스케줄러로 자동_콘텐츠생성기 매일 07:00 예약
