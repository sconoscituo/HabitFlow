# 결제 모델 - 포트원(PortOne) 프리미엄 구독 결제 내역 저장
# 프리미엄 구독: 월 6,900원
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

PREMIUM_MONTHLY_PRICE = 6900  # 월 6,900원


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    imp_uid: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)  # 포트원 결제 고유번호
    merchant_uid: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)  # 주문번호
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 결제금액 (원)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="premium")  # 구독 플랜
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending/paid/cancelled/failed
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Payment id={self.id} user_id={self.user_id} amount={self.amount} status={self.status}>"
