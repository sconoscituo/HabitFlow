# 사용자 관련 Pydantic 스키마 - 요청/응답 데이터 검증
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """회원가입 요청 스키마"""
    email: EmailStr
    password: str
    timezone: str = "Asia/Seoul"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        return v


class UserLogin(BaseModel):
    """로그인 요청 스키마"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """사용자 정보 응답 스키마"""
    id: int
    email: str
    timezone: str
    is_premium: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT 토큰 응답 스키마"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DashboardResponse(BaseModel):
    """대시보드 응답 스키마 - 오늘의 습관 현황 요약"""
    total_habits: int           # 전체 활성 습관 수
    completed_today: int        # 오늘 완료한 습관 수
    completion_rate_today: float  # 오늘 완료율 (0.0 ~ 1.0)
    current_best_streak: int    # 현재 최고 연속 달성일
    total_logs: int             # 전체 누적 완료 횟수
