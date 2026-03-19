# 주간 리포트 라우터 - AI 코칭 리포트 생성 및 조회
from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.report import WeeklyReport
from app.models.user import User
from app.routers.users import get_current_user_dep
from app.services.coach import generate_weekly_coaching, save_weekly_report

router = APIRouter(prefix="/reports", tags=["reports"])


class WeeklyReportResponse(BaseModel):
    """주간 리포트 응답 스키마"""
    id: int
    user_id: int
    week_start: date
    week_end: date
    completion_rate: float
    ai_coaching: str | None
    strengths: str | None
    improvements: str | None

    model_config = {"from_attributes": True}


class GenerateReportRequest(BaseModel):
    """리포트 생성 요청 스키마"""
    week_start: date | None = None  # None이면 이번 주 월요일 자동 설정


def _get_week_range(reference: date | None = None) -> tuple[date, date]:
    """기준일의 월~일 범위 반환"""
    if reference is None:
        reference = date.today()
    # 월요일(0) 기준으로 주 시작
    days_since_monday = reference.weekday()
    week_start = reference - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


@router.post("/generate", response_model=WeeklyReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    req: GenerateReportRequest = GenerateReportRequest(),
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    주간 리포트 수동 생성 (프리미엄 전용 AI 코칭 포함).
    비프리미엄 사용자도 기본 통계는 볼 수 있으나, AI 코칭은 빈 메시지 반환.
    """
    week_start, week_end = _get_week_range(req.week_start)

    # 프리미엄 여부와 관계없이 통계는 생성하되,
    # AI 코칭은 프리미엄 사용자만 실제 Gemini 호출
    coaching_data = await generate_weekly_coaching(db, current_user.id, week_start, week_end)

    if not current_user.is_premium:
        # 비프리미엄: AI 코칭 메시지 제거
        coaching_data["ai_coaching"] = "프리미엄 구독 시 AI 맞춤 코칭 메시지를 받을 수 있습니다."
        coaching_data["strengths"] = None
        coaching_data["improvements"] = None

    report = await save_weekly_report(db, current_user.id, week_start, week_end, coaching_data)
    return WeeklyReportResponse.model_validate(report)


@router.get("", response_model=List[WeeklyReportResponse])
async def list_reports(
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """내 주간 리포트 목록 조회 (최신순)"""
    result = await db.execute(
        select(WeeklyReport)
        .where(WeeklyReport.user_id == current_user.id)
        .order_by(WeeklyReport.week_start.desc())
        .limit(12)  # 최근 3개월치
    )
    reports = result.scalars().all()
    return [WeeklyReportResponse.model_validate(r) for r in reports]


@router.get("/latest", response_model=WeeklyReportResponse)
async def get_latest_report(
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """가장 최근 주간 리포트 조회"""
    result = await db.execute(
        select(WeeklyReport)
        .where(WeeklyReport.user_id == current_user.id)
        .order_by(WeeklyReport.week_start.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="아직 생성된 리포트가 없습니다.",
        )
    return WeeklyReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=WeeklyReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """특정 주간 리포트 상세 조회"""
    result = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.id == report_id,
            WeeklyReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다.",
        )
    return WeeklyReportResponse.model_validate(report)
