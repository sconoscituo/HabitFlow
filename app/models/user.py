# 사용자 모델 - 인증 및 프리미엄 구독 정보 관리
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # 기본 식별자
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # 사용자 설정
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Seoul")

    # 프리미엄 구독 여부 (AI 코칭 기능 접근 제어)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 관계 정의
    habits: Mapped[list["Habit"]] = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    habit_logs: Mapped[list["HabitLog"]] = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
    weekly_reports: Mapped[list["WeeklyReport"]] = relationship("WeeklyReport", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
