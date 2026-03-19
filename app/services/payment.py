"""
포트원(PortOne) 결제 연동 서비스
실제 사용 시 PORTONE_API_KEY, PORTONE_API_SECRET 환경변수 필요
프리미엄 구독: 월 6,900원
"""
import httpx
from app.config import get_settings

PORTONE_API_URL = "https://api.iamport.kr"

PREMIUM_MONTHLY_PRICE = 6900  # 월 6,900원


async def get_access_token() -> str:
    """포트원 액세스 토큰 발급"""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PORTONE_API_URL}/users/getToken",
            json={
                "imp_key": settings.portone_api_key,
                "imp_secret": settings.portone_api_secret,
            },
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise ValueError(f"포트원 토큰 발급 실패: {data.get('message')}")
        return data["response"]["access_token"]


async def verify_payment(imp_uid: str, expected_amount: int) -> bool:
    """결제 검증 - 결제금액 위변조 방지"""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PORTONE_API_URL}/payments/{imp_uid}",
            headers={"Authorization": token},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            return False
        payment = data["response"]
        return (
            payment.get("status") == "paid"
            and payment.get("amount") == expected_amount
        )


async def cancel_payment(imp_uid: str, reason: str) -> dict:
    """결제 취소"""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PORTONE_API_URL}/payments/cancel",
            headers={"Authorization": token},
            json={"imp_uid": imp_uid, "reason": reason},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise ValueError(f"결제 취소 실패: {data.get('message')}")
        return data["response"]
