# 습관 모델 - 사용자가 추적할 습관 정의
from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Habit(Base):
    __tablename__ = "habits"

    # 기본 식별자
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 소유자 참조
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # 습관 기본 정보
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 빈도 설정: "daily", "weekly", "custom"
    frequency: Mapped[str] = mapped_column(String(20), default="daily")

    # 목표 요일 (JSON 문자열로 저장, 예: "1,2,3,4,5" = 월~금)
    target_days: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # UI 커스터마이징
    color: Mapped[str] = mapped_column(String(7), default="#4CAF50")  # HEX 컬러
    icon: Mapped[str] = mapped_column(String(50), default="check_circle")  # 아이콘 이름

    # 활성 상태 (소프트 삭제용)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 관계 정의
    user: Mapped["User"] = relationship("User", back_populates="habits")
    logs: Mapped[list["HabitLog"]] = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Habit id={self.id} name={self.name}>"
