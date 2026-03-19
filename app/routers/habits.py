# 습관 라우터 - CRUD, 오늘 완료 체크, 스트릭 조회
from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.habit import Habit
from app.models.log import HabitLog
from app.models.user import User
from app.schemas.habit import (
    HabitCreate,
    HabitUpdate,
    HabitResponse,
    HabitLogCreate,
    HabitLogResponse,
    HabitStats,
)
from app.routers.users import get_current_user_dep
from app.services.streak import (
    calculate_current_streak,
    calculate_best_streak,
    get_completion_rate,
    is_completed_today,
)

router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
async def create_habit(
    habit_in: HabitCreate,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """새 습관 생성"""
    habit = Habit(
        user_id=current_user.id,
        name=habit_in.name,
        description=habit_in.description,
        frequency=habit_in.frequency,
        target_days=habit_in.target_days,
        color=habit_in.color,
        icon=habit_in.icon,
    )
    db.add(habit)
    await db.flush()

    response = HabitResponse.model_validate(habit)
    response.completed_today = False
    response.current_streak = 0
    return response


@router.get("", response_model=List[HabitResponse])
async def list_habits(
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """내 활성 습관 목록 조회 (오늘 완료 여부 + 스트릭 포함)"""
    result = await db.execute(
        select(Habit).where(
            Habit.user_id == current_user.id,
            Habit.is_active == True,
        ).order_by(Habit.created_at.asc())
    )
    habits = result.scalars().all()

    responses = []
    for habit in habits:
        response = HabitResponse.model_validate(habit)
        response.completed_today = await is_completed_today(db, habit.id, current_user.id)
        response.current_streak = await calculate_current_streak(db, habit.id, current_user.id)
        responses.append(response)

    return responses


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: int,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """특정 습관 상세 조회"""
    habit = await _get_habit_or_404(db, habit_id, current_user.id)

    response = HabitResponse.model_validate(habit)
    response.completed_today = await is_completed_today(db, habit.id, current_user.id)
    response.current_streak = await calculate_current_streak(db, habit.id, current_user.id)
    return response


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: int,
    habit_in: HabitUpdate,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """습관 수정 (부분 업데이트)"""
    habit = await _get_habit_or_404(db, habit_id, current_user.id)

    update_data = habit_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(habit, field, value)

    await db.flush()

    response = HabitResponse.model_validate(habit)
    response.completed_today = await is_completed_today(db, habit.id, current_user.id)
    response.current_streak = await calculate_current_streak(db, habit.id, current_user.id)
    return response


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: int,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """습관 비활성화 (소프트 삭제)"""
    habit = await _get_habit_or_404(db, habit_id, current_user.id)
    habit.is_active = False
    await db.flush()


@router.post("/{habit_id}/check", response_model=HabitLogResponse, status_code=status.HTTP_201_CREATED)
async def check_habit(
    habit_id: int,
    log_in: HabitLogCreate,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """오늘 습관 완료 체크"""
    habit = await _get_habit_or_404(db, habit_id, current_user.id)

    # 오늘 이미 완료한 경우 중복 방지
    already_done = await is_completed_today(db, habit_id, current_user.id)
    if already_done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="오늘은 이미 완료한 습관입니다.",
        )

    # 현재 스트릭 계산
    current_streak = await calculate_current_streak(db, habit_id, current_user.id)
    new_streak = current_streak + 1

    log = HabitLog(
        habit_id=habit.id,
        user_id=current_user.id,
        note=log_in.note,
        streak_count=new_streak,
    )
    db.add(log)
    await db.flush()

    return HabitLogResponse.model_validate(log)


@router.get("/{habit_id}/stats", response_model=HabitStats)
async def get_habit_stats(
    habit_id: int,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """습관 상세 통계 조회"""
    habit = await _get_habit_or_404(db, habit_id, current_user.id)

    from sqlalchemy import func as sqlfunc
    total_result = await db.execute(
        select(sqlfunc.count(HabitLog.id)).where(
            HabitLog.habit_id == habit_id,
            HabitLog.user_id == current_user.id,
        )
    )
    total_completions = total_result.scalar() or 0

    current_streak = await calculate_current_streak(db, habit_id, current_user.id)
    best_streak = await calculate_best_streak(db, habit_id, current_user.id)
    rate_7d = await get_completion_rate(db, habit_id, current_user.id, days=7)
    rate_30d = await get_completion_rate(db, habit_id, current_user.id, days=30)

    return HabitStats(
        habit_id=habit_id,
        habit_name=habit.name,
        total_completions=total_completions,
        current_streak=current_streak,
        best_streak=best_streak,
        completion_rate_7d=rate_7d,
        completion_rate_30d=rate_30d,
    )


@router.get("/{habit_id}/streak")
async def get_streak(
    habit_id: int,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """스트릭 정보만 빠르게 조회"""
    await _get_habit_or_404(db, habit_id, current_user.id)

    current = await calculate_current_streak(db, habit_id, current_user.id)
    best = await calculate_best_streak(db, habit_id, current_user.id)

    return {"habit_id": habit_id, "current_streak": current, "best_streak": best}


async def _get_habit_or_404(db: AsyncSession, habit_id: int, user_id: int) -> Habit:
    """습관 조회 헬퍼 - 없거나 권한 없으면 404"""
    result = await db.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    )
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="습관을 찾을 수 없습니다.",
        )
    return habit
