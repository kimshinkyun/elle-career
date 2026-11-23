# 원장님 리드 퍼널

인스타 릴스/카드뉴스 → 프로필 링크·DM 키워드 → `index.html`(3분 세금 계산기) → 동의 폼 → Google Sheets CRM → 상담

```
funnel/
├─ index.html                      랜딩 + 계산기 + 동의 폼 (정적 파일, 호스팅만 하면 끝)
├─ backend/apps-script.gs          Google Sheets 저장 · 동의 로그 · 철회 · 2년 재확인
├─ instagram/
│  ├─ cardnews_A_세금계산기.json      카드뉴스 에디터에 바로 임포트 (6장)
│  ├─ cardnews_B_원장님세금실수.json   카드뉴스 에디터에 바로 임포트 (5장)
│  └─ 릴스_대본_및_타겟팅.md          릴스 3종, 타겟팅, DM 자동화, 지표
└─ docs/CRM_스키마_및_컴플라이언스.md   스키마, 연락 판정표, 체크리스트
```

## 5분 가동 순서
1. `backend/apps-script.gs`를 새 스프레드시트의 Apps Script에 붙여넣고 `setup()` → 웹앱 배포 → URL 복사
2. `index.html` 상단 `CONFIG`에 URL, 보내는 이름, 연락처, 방침 URL 입력
3. 정적 호스팅(Vercel/Netlify/GitHub Pages)에 업로드, 인스타 프로필 링크에 `?utm_source=ig&utm_medium=bio` 붙여 등록
4. 테스트 제출 후 `leads`, `consent_log` 확인 → `installTriggers()` 실행
5. 릴스 1부터 업로드, 카드뉴스 JSON은 에디터 JSON 탭에 붙여넣기
