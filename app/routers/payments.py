# 결제 라우터 - 포트원 프리미엄 구독 결제 검증/취소/내역 조회
# 프리미엄 구독: 월 6,900원
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.payment import Payment, PREMIUM_MONTHLY_PRICE
from app.models.user import User
from app.routers.users import get_current_user_dep
from app.services.payment import verify_payment, cancel_payment

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class PaymentVerifyRequest(BaseModel):
    imp_uid: str
    merchant_uid: str


class PaymentCancelRequest(BaseModel):
    imp_uid: str
    reason: str = "사용자 요청 취소"


@router.post("/verify", summary="결제 검증 후 프리미엄 구독 활성화")
async def verify_and_activate_premium(
    body: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    포트원 결제 검증 후 프리미엄 구독을 활성화합니다.
    월 6,900원 고정 금액을 검증합니다.
    """
    # 중복 결제 확인
    result = await db.execute(
        select(Payment).where(Payment.imp_uid == body.imp_uid)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 처리된 결제입니다.")

    # 포트원 결제 검증
    is_valid = await verify_payment(body.imp_uid, PREMIUM_MONTHLY_PRICE)
    if not is_valid:
        payment = Payment(
            imp_uid=body.imp_uid,
            merchant_uid=body.merchant_uid,
            user_id=current_user.id,
            amount=PREMIUM_MONTHLY_PRICE,
            plan="premium",
            status="failed",
        )
        db.add(payment)
        await db.commit()
        raise HTTPException(status_code=400, detail="결제 검증 실패: 금액이 일치하지 않습니다.")

    # 결제 내역 저장
    payment = Payment(
        imp_uid=body.imp_uid,
        merchant_uid=body.merchant_uid,
        user_id=current_user.id,
        amount=PREMIUM_MONTHLY_PRICE,
        plan="premium",
        status="paid",
    )
    db.add(payment)

    # 프리미엄 구독 활성화
    current_user.is_premium = True
    await db.commit()

    return {
        "message": "프리미엄 구독이 활성화되었습니다.",
        "amount_paid": PREMIUM_MONTHLY_PRICE,
        "is_premium": True,
    }


@router.post("/cancel", summary="구독 취소 및 환불")
async def cancel_subscription(
    body: PaymentCancelRequest,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """결제를 취소하고 프리미엄 구독을 해지합니다."""
    result = await db.execute(
        select(Payment).where(
            Payment.imp_uid == body.imp_uid,
            Payment.user_id == current_user.id,
            Payment.status == "paid",
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="취소할 결제 내역을 찾을 수 없습니다.")

    # 포트원 결제 취소
    await cancel_payment(body.imp_uid, body.reason)

    # 결제 상태 업데이트
    payment.status = "cancelled"
    payment.cancel_reason = body.reason

    # 프리미엄 구독 해지
    current_user.is_premium = False
    await db.commit()

    return {"message": "구독이 취소되고 환불이 처리되었습니다."}


@router.get("/history", summary="결제 내역 조회")
async def get_payment_history(
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자의 구독 결제 내역을 조회합니다."""
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return {
        "total": len(payments),
        "is_premium": current_user.is_premium,
        "payments": [
            {
                "id": p.id,
                "imp_uid": p.imp_uid,
                "merchant_uid": p.merchant_uid,
                "amount": p.amount,
                "plan": p.plan,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ],
    }
