# FastAPI 앱 엔트리포인트 - 앱 초기화, 라우터 등록, 스케줄러 설정
import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import get_settings
from app.database import init_db, AsyncSessionLocal
from app.models.user import User
from app.routers import users, habits, reports, streak
from app.services.coach import generate_weekly_coaching, save_weekly_report

logger = logging.getLogger(__name__)
settings = get_settings()

# APScheduler 인스턴스
scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def generate_weekly_reports_for_all_users():
    """
    매주 월요일 오전 8시에 실행 - 모든 프리미엄 사용자의 주간 리포트 자동 생성.
    지난 주(월~일) 데이터를 기준으로 리포트 생성.
    """
    today = date.today()
    # 지난 주 월요일 계산
    days_since_monday = today.weekday()  # 오늘이 월요일이면 0
    last_week_end = today - timedelta(days=days_since_monday + 1)   # 지난 일요일
    last_week_start = last_week_end - timedelta(days=6)              # 지난 월요일

    logger.info(f"주간 리포트 자동 생성 시작: {last_week_start} ~ {last_week_end}")

    async with AsyncSessionLocal() as db:
        try:
            # 프리미엄 사용자 목록 조회
            result = await db.execute(
                select(User).where(User.is_premium == True)
            )
            premium_users = result.scalars().all()
            logger.info(f"대상 프리미엄 사용자: {len(premium_users)}명")

            for user in premium_users:
                try:
                    coaching_data = await generate_weekly_coaching(
                        db, user.id, last_week_start, last_week_end
                    )
                    await save_weekly_report(
                        db, user.id, last_week_start, last_week_end, coaching_data
                    )
                    logger.info(f"사용자 {user.id} 리포트 생성 완료")
                except Exception as e:
                    logger.error(f"사용자 {user.id} 리포트 생성 실패: {e}")
                    continue

            await db.commit()
            logger.info("주간 리포트 자동 생성 완료")

        except Exception as e:
            await db.rollback()
            logger.error(f"주간 리포트 자동 생성 중 오류 발생: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 lifespan 핸들러"""
    # 시작 시
    logger.info("HabitFlow 서버 시작 중...")

    # DB 테이블 초기화
    await init_db()
    logger.info("데이터베이스 초기화 완료")

    # 스케줄러 등록: 매주 월요일 오전 8시 (KST)
    scheduler.add_job(
        generate_weekly_reports_for_all_users,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_report",
        replace_existing=True,
        misfire_grace_time=3600,  # 1시간 이내 놓친 작업 재실행
    )
    scheduler.start()
    logger.info("스케줄러 시작 완료 (매주 월요일 08:00 KST 리포트 자동 생성)")

    yield

    # 종료 시
    scheduler.shutdown(wait=False)
    logger.info("HabitFlow 서버 종료")


# FastAPI 앱 생성
app = FastAPI(
    title="HabitFlow API",
    description="습관 추적 + AI 코칭 + 주간 리포트 서비스",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://habitflow.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(users.router, prefix="/api/v1")
app.include_router(habits.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(streak.router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def root():
    """헬스체크 엔드포인트"""
    return {
        "service": "HabitFlow API",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """상세 헬스체크"""
    return {
        "status": "ok",
        "debug": settings.debug,
        "scheduler": scheduler.running,
    }
