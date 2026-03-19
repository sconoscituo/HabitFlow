# 앱 설정 관리 - 환경변수 로드 및 설정값 정의
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 앱 기본 설정
    app_name: str = "HabitFlow"
    debug: bool = False

    # 데이터베이스 설정
    database_url: str = "sqlite+aiosqlite:///./habitflow.db"

    # JWT 인증 설정
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7일

    # Gemini AI API 설정
    gemini_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환 (캐시 적용)"""
    return Settings()
