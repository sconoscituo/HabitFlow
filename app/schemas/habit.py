# 습관 관련 Pydantic 스키마 - 요청/응답 데이터 검증
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class HabitCreate(BaseModel):
    """습관 생성 요청 스키마"""
    name: str
    description: Optional[str] = None
    frequency: str = "daily"          # "daily" | "weekly" | "custom"
    target_days: Optional[str] = None  # "1,2,3,4,5" 형식 (월=1 ~ 일=7)
    color: str = "#4CAF50"
    icon: str = "check_circle"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("습관 이름은 비워둘 수 없습니다.")
        return v.strip()

    @field_validator("frequency")
    @classmethod
    def valid_frequency(cls, v: str) -> str:
        allowed = {"daily", "weekly", "custom"}
        if v not in allowed:
            raise ValueError(f"frequency는 {allowed} 중 하나여야 합니다.")
        return v


class HabitUpdate(BaseModel):
    """습관 수정 요청 스키마 (부분 업데이트)"""
    name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    target_days: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class HabitResponse(BaseModel):
    """습관 응답 스키마"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    frequency: str
    target_days: Optional[str]
    color: str
    icon: str
    is_active: bool
    created_at: datetime
    # 오늘 완료 여부 (동적 필드)
    completed_today: bool = False
    current_streak: int = 0

    model_config = {"from_attributes": True}


class HabitLogCreate(BaseModel):
    """습관 완료 체크 요청 스키마"""
    habit_id: int
    note: Optional[str] = None


class HabitLogResponse(BaseModel):
    """습관 로그 응답 스키마"""
    id: int
    habit_id: int
    user_id: int
    completed_at: datetime
    note: Optional[str]
    streak_count: int

    model_config = {"from_attributes": True}


class HabitStats(BaseModel):
    """습관 통계 스키마"""
    habit_id: int
    habit_name: str
    total_completions: int      # 전체 완료 횟수
    current_streak: int         # 현재 연속 달성일
    best_streak: int            # 역대 최고 연속 달성일
    completion_rate_7d: float   # 최근 7일 완료율
    completion_rate_30d: float  # 최근 30일 완료율
