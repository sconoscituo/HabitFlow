# 스트릭(연속 달성일) 계산 서비스
from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import HabitLog


async def calculate_current_streak(
    db: AsyncSession,
    habit_id: int,
    user_id: int,
    reference_date: date | None = None,
) -> int:
    """
    현재 연속 달성일 계산.
    오늘(또는 어제)부터 거슬러 올라가며 연속된 날을 카운트.
    """
    if reference_date is None:
        reference_date = date.today()

    # 최근 로그를 날짜 역순으로 가져옴
    result = await db.execute(
        select(HabitLog.completed_at)
        .where(HabitLog.habit_id == habit_id, HabitLog.user_id == user_id)
        .order_by(HabitLog.completed_at.desc())
    )
    logs = result.scalars().all()

    if not logs:
        return 0

    # datetime -> date 변환 및 중복 제거 (하루에 여러 번 완료해도 1일로 카운트)
    completed_dates = sorted(
        {log.date() if isinstance(log, datetime) else log for log in logs},
        reverse=True,
    )

    # 오늘 또는 어제 완료가 없으면 스트릭 0
    if completed_dates[0] < reference_date - timedelta(days=1):
        return 0

    streak = 0
    expected = completed_dates[0]

    for log_date in completed_dates:
        if log_date == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break

    return streak


async def calculate_best_streak(
    db: AsyncSession,
    habit_id: int,
    user_id: int,
) -> int:
    """
    역대 최고 연속 달성일 계산.
    전체 로그를 순회하며 가장 긴 연속 구간을 탐색.
    """
    result = await db.execute(
        select(HabitLog.completed_at)
        .where(HabitLog.habit_id == habit_id, HabitLog.user_id == user_id)
        .order_by(HabitLog.completed_at.asc())
    )
    logs = result.scalars().all()

    if not logs:
        return 0

    # 중복 날짜 제거 후 정렬
    completed_dates = sorted(
        {log.date() if isinstance(log, datetime) else log for log in logs}
    )

    best = 1
    current = 1

    for i in range(1, len(completed_dates)):
        if completed_dates[i] - completed_dates[i - 1] == timedelta(days=1):
            current += 1
            best = max(best, current)
        else:
            current = 1

    return best


async def get_completion_rate(
    db: AsyncSession,
    habit_id: int,
    user_id: int,
    days: int = 7,
) -> float:
    """
    최근 N일간 완료율 계산 (0.0 ~ 1.0).
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    result = await db.execute(
        select(func.count(HabitLog.id))
        .where(
            HabitLog.habit_id == habit_id,
            HabitLog.user_id == user_id,
            func.date(HabitLog.completed_at) >= start_date,
            func.date(HabitLog.completed_at) <= end_date,
        )
    )
    completed_days = result.scalar() or 0

    return round(completed_days / days, 2)


async def is_completed_today(
    db: AsyncSession,
    habit_id: int,
    user_id: int,
) -> bool:
    """오늘 해당 습관을 완료했는지 확인"""
    today = date.today()
    result = await db.execute(
        select(func.count(HabitLog.id))
        .where(
            HabitLog.habit_id == habit_id,
            HabitLog.user_id == user_id,
            func.date(HabitLog.completed_at) == today,
        )
    )
    count = result.scalar() or 0
    return count > 0
