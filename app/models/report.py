# 주간 리포트 모델 - AI 코칭 분석 결과 저장
from datetime import date, datetime
from sqlalchemy import Date, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    # 기본 식별자
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 소유자 참조
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # 리포트 기간
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)

    # 주간 완료율 (0.0 ~ 1.0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Gemini AI 생성 콘텐츠
    ai_coaching: Mapped[str | None] = mapped_column(Text, nullable=True)    # 전체 코칭 메시지
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)      # 잘한 점
    improvements: Mapped[str | None] = mapped_column(Text, nullable=True)   # 개선할 점

    # 생성 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 관계 정의
    user: Mapped["User"] = relationship("User", back_populates="weekly_reports")

    def __repr__(self) -> str:
        return f"<WeeklyReport id={self.id} user_id={self.user_id} week={self.week_start}~{self.week_end}>"
