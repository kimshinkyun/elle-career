"""
[방법 C-2] 카카오 메시지 자동 발송 스크립트

▶ 카카오 알림톡 (비즈니스 API) — 법인 사업자 필요, 심사 있음
▶ 카카오 채널 메시지 (일반) — 채널 추가한 유저에게만 발송 가능
▶ 나에게 보내기 API — 개인 테스트용, 즉시 사용 가능

이 스크립트는 3가지 방식 모두 제공합니다.

설치: pip install requests pandas openpyxl
"""

import requests
import json
import os
import time
import pandas as pd
from datetime import datetime

# ══════════════════════════════════════════════
# ▼▼▼ 설정 ▼▼▼
# ══════════════════════════════════════════════

BASE_DIR = r"C:\Users\user\Desktop\기업수집"

# ── 카카오 API 키 발급 방법 ──
# 1. https://developers.kakao.com 접속
# 2. 애플리케이션 추가
# 3. 앱 키 → REST API 키 복사
# 4. 카카오 로그인 → 토큰 발급 (아래 STEP 1 실행)
KAKAO_REST_API_KEY = "여기에_REST_API_키"

# 토큰 파일 경로 (자동 저장됨)
TOKEN_FILE = os.path.join(BASE_DIR, "kakao_token.json")

# 채널 발송 설정 (카카오 채널 메시지 - 채널 추가 유저만 가능)
KAKAO_CHANNEL_ID = "_여기에채널ID"  # 카카오채널 관리자 → 설정에서 확인

PHONE      = "010-0000-0000"
CONSULTANT = "법인전환 전문 컨설턴트"


# ══════════════════════════════════════════════
# STEP 1 — 카카오 토큰 발급 (처음 한 번만)
# ══════════════════════════════════════════════

def get_kakao_token():
    """브라우저에서 인증 후 토큰 발급"""
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_REST_API_KEY}"
        f"&redirect_uri=https://example.com/oauth"
        f"&response_type=code"
        f"&scope=talk_message,friends"
    )
    print("=" * 60)
    print("카카오 로그인 필요")
    print("=" * 60)
    print(f"\n1. 아래 URL을 브라우저에서 열어주세요:\n")
    print(f"   {auth_url}\n")
    print("2. 카카오 로그인 후 리다이렉트된 URL에서")
    print("   'code=' 뒤의 값을 복사해서 붙여넣으세요.\n")

    code = input("인증 코드 입력: ").strip()

    resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type"  : "authorization_code",
            "client_id"   : KAKAO_REST_API_KEY,
            "redirect_uri": "https://example.com/oauth",
            "code"        : code,
        }
    )
    data = resp.json()
    if "access_token" not in data:
        print(f"❌ 토큰 발급 실패: {data}")
        return False

    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ 토큰 저장 완료: {TOKEN_FILE}")
    return True


def load_token() -> str | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f).get("access_token")


def refresh_token() -> bool:
    if not os.path.exists(TOKEN_FILE):
        return False
    with open(TOKEN_FILE) as f:
        token_data = json.load(f)
    refresh = token_data.get("refresh_token")
    if not refresh:
        return False
    resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type"   : "refresh_token",
            "client_id"    : KAKAO_REST_API_KEY,
            "refresh_token": refresh,
        }
    )
    data = resp.json()
    if "access_token" in data:
        token_data["access_token"] = data["access_token"]
        if "refresh_token" in data:
            token_data["refresh_token"] = data["refresh_token"]
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        return True
    return False


# ══════════════════════════════════════════════
# STEP 2 — 나에게 보내기 (테스트용)
# ══════════════════════════════════════════════

def send_to_me(access_token: str, text: str) -> bool:
    """내 카카오톡으로 메시지 전송 (테스트용)"""
    resp = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={
            "template_object": json.dumps({
                "object_type": "text",
                "text": text,
                "link": {
                    "web_url"    : "https://pf.kakao.com/_채널ID",
                    "mobile_web_url": "https://pf.kakao.com/_채널ID"
                }
            })
        }
    )
    return resp.status_code == 200


# ══════════════════════════════════════════════
# STEP 3 — 친구에게 보내기
# ══════════════════════════════════════════════

def get_friends(access_token: str) -> list:
    """카카오 친구 목록 조회"""
    resp = requests.get(
        "https://kapi.kakao.com/v1/api/talk/friends",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": 100}
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("elements", [])


def send_to_friend(access_token: str, uuid: str, text: str) -> bool:
    """특정 친구에게 메시지 전송"""
    resp = requests.post(
        "https://kapi.kakao.com/v1/api/talk/friends/message/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={
            "receiver_uuids": json.dumps([uuid]),
            "template_object": json.dumps({
                "object_type": "feed",
                "content": {
                    "title"      : "법인전환 절세 무료 진단",
                    "description": text,
                    "image_url"  : "",
                    "link"       : {
                        "web_url"    : "https://pf.kakao.com/_채널ID",
                        "mobile_web_url": "https://pf.kakao.com/_채널ID"
                    }
                },
                "buttons": [
                    {
                        "title": "무료 상담 신청",
                        "link" : {
                            "web_url"       : "https://pf.kakao.com/_채널ID",
                            "mobile_web_url": "https://pf.kakao.com/_채널ID"
                        }
                    }
                ]
            })
        }
    )
    return resp.status_code == 200


# ══════════════════════════════════════════════
# 업종별 메시지
# ══════════════════════════════════════════════

def get_message(industry: str, name: str) -> str:
    name_str = f"{name} " if name.strip() else ""
    ind = str(industry).lower()

    if any(k in ind for k in ["제조"]):
        tip = "제조업은 설비 비용 구조 활용으로 법인 절세 효과가 매우 큽니다."
    elif any(k in ind for k in ["도매", "소매", "유통"]):
        tip = "도소매업은 재고·물류 비용을 법인에서 최적화하면 절세가 됩니다."
    elif any(k in ind for k in ["음식", "식당", "카페"]):
        tip = "음식업은 건강보험료 절감 효과가 특히 커서 법인 전환이 유리합니다."
    elif any(k in ind for k in ["병원", "의원", "치과"]):
        tip = "의원은 일반 법인 구조로 소득세+건보료를 합법적으로 줄일 수 있습니다."
    else:
        tip = "연매출 3억 이상이시면 법인 전환으로 연 1,500만원 이상 절세 가능합니다."

    return f"""안녕하세요, {name_str}사장님! 😊

법인전환 전문 컨설턴트입니다.
{tip}

5분 무료 절세 진단 해드립니다.
아래 채널로 편하게 연락 주세요.

📞 {PHONE}
💬 카카오채널: {KAKAO_CHANNEL_ID}

강요 없는 100% 무료 상담입니다 🙏"""


# ══════════════════════════════════════════════
# 메인 메뉴
# ══════════════════════════════════════════════

def main():
    print("=" * 55)
    print("  카카오 메시지 자동 발송")
    print("=" * 55)

    if KAKAO_REST_API_KEY == "여기에_REST_API_키":
        print("""
❌ 카카오 API 키가 필요합니다.

▶ 발급 방법:
  1. https://developers.kakao.com 접속
  2. 로그인 → 내 애플리케이션 → 애플리케이션 추가
  3. 앱 이름: "법인전환상담" 입력 후 저장
  4. 앱 키 → REST API 키 복사
  5. 이 파일 상단 KAKAO_REST_API_KEY 에 붙여넣기

▶ 카카오 API 비용: 완전 무료 (나에게 보내기 / 친구 보내기)
  알림톡은 건당 약 8~15원 (비즈니스 신청 필요)
""")
        return

    print("\n메뉴를 선택하세요:")
    print("  1. 카카오 로그인 (처음 한 번만)")
    print("  2. 나에게 테스트 메시지 보내기")
    print("  3. 친구 목록 확인")
    print("  4. DB 업체들에게 메시지 작성 안내")

    choice = input("\n선택 (1~4): ").strip()

    if choice == "1":
        get_kakao_token()

    elif choice == "2":
        token = load_token()
        if not token:
            print("❌ 먼저 메뉴 1번으로 로그인하세요.")
            return
        test_msg = get_message("제조업", "테스트")
        ok = send_to_me(token, test_msg)
        if ok:
            print("✅ 내 카카오톡으로 테스트 메시지 발송 완료!")
            print("   카카오톡 앱에서 확인하세요.")
        else:
            print("❌ 발송 실패. 토큰을 갱신하고 다시 시도하세요.")
            if refresh_token():
                print("  토큰 갱신됨. 다시 실행해보세요.")

    elif choice == "3":
        token = load_token()
        if not token:
            print("❌ 먼저 메뉴 1번으로 로그인하세요.")
            return
        friends = get_friends(token)
        if not friends:
            print("친구 목록이 없거나 권한이 없습니다.")
            print("카카오 개발자 콘솔에서 '친구목록' 동의항목을 활성화하세요.")
            return
        print(f"\n친구 {len(friends)}명:")
        for f in friends[:20]:
            print(f"  - {f.get('profile_nickname','?')} (uuid: {f.get('uuid','?')[:12]}...)")

    elif choice == "4":
        print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
카카오 채널 메시지 발송 안내
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

카카오톡 채널 메시지는 채널을 "추가"한 유저에게만 발송 가능합니다.
(카카오 정책상 불특정 다수에게 카카오로 직접 발송은 불가)

▶ 현실적인 카카오 활용 방법:

방법 1. 이메일 발송 + 카카오채널 링크 포함 (권장)
  → 이메일_자동발송.py 로 이메일 발송
  → 이메일 본문에 카카오채널 링크 포함
  → 관심 있는 사장님이 채널 추가 → 이후 채널 메시지 발송 가능

방법 2. 카카오 알림톡 (비즈니스 API)
  → https://business.kakao.com 신청
  → 법인 사업자 + 심사 필요 (2~4주)
  → 전화번호로 직접 발송 가능 (건당 8~15원)
  → 승인되면 이 스크립트에 알림톡 코드 추가해드릴게요

방법 3. 친구톡 (카카오채널 추가 유저 대상)
  → 카카오채널 관리자 → 메시지 발송
  → 채널 추가 고객에게 무료 or 소량 유료 발송
  → 카카오채널 관리자 센터에서 직접 설정

▶ 지금 당장 할 수 있는 것:
  python 이메일_자동발송.py 실행
  → 2,700개 업체에 이메일 발송 (하루 80건씩)
  → 이메일에 카카오채널 링크 포함
  → 관심 있는 분들이 채널 추가 → 이후 카카오 메시지 가능
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    main()
