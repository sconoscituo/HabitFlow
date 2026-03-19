"""
습관 스트릭 분석 라우터
"""
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user

router = APIRouter(prefix="/streak", tags=["스트릭 분석"])

try:
    from app.models.habit import Habit, HabitLog
    HAS_MODELS = True
except ImportError:
    HAS_MODELS = False


@router.get("/summary")
async def get_streak_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """전체 습관 스트릭 요약"""
    if not HAS_MODELS:
        return {"message": "습관 모델이 없습니다"}

    result = await db.execute(
        select(Habit).where(Habit.user_id == current_user.id, Habit.is_active == True)
    )
    habits = result.scalars().all()

    summaries = []
    for habit in habits:
        # 최근 30일 로그 조회
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        log_result = await db.execute(
            select(HabitLog)
            .where(HabitLog.habit_id == habit.id, HabitLog.logged_at >= thirty_days_ago)
            .order_by(HabitLog.logged_at.desc())
        )
        logs = log_result.scalars().all()
        log_dates = {l.logged_at.date() for l in logs}

        # 현재 스트릭 계산
        current_streak = 0
        check_date = date.today()
        while check_date in log_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        summaries.append({
            "habit_id": habit.id,
            "habit_name": habit.name,
            "current_streak": current_streak,
            "completions_30d": len(logs),
            "completion_rate": round(len(logs) / 30 * 100, 1),
        })

    best = max(summaries, key=lambda x: x["current_streak"]) if summaries else None
    return {
        "habits": summaries,
        "best_streak_habit": best["habit_name"] if best else None,
        "best_streak_days": best["current_streak"] if best else 0,
    }
