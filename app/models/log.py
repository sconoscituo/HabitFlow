# 습관 로그 모델 - 습관 완료 기록 및 스트릭 추적
from datetime import datetime
from sqlalchemy import Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HabitLog(Base):
    __tablename__ = "habit_logs"

    # 기본 식별자
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 참조 키
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # 완료 시각
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # 메모 (선택 사항)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 이 완료 시점의 연속 달성일 수
    streak_count: Mapped[int] = mapped_column(Integer, default=1)

    # 관계 정의
    habit: Mapped["Habit"] = relationship("Habit", back_populates="logs")
    user: Mapped["User"] = relationship("User", back_populates="habit_logs")

    def __repr__(self) -> str:
        return f"<HabitLog id={self.id} habit_id={self.habit_id} completed_at={self.completed_at}>"
