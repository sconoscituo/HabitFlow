# 데이터베이스 연결 및 세션 관리
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# 비동기 SQLite 엔진 생성
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # 디버그 모드에서 SQL 쿼리 출력
    future=True,
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """모든 모델의 기본 클래스"""
    pass


async def get_db():
    """FastAPI 의존성 주입용 DB 세션 생성기"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """앱 시작 시 테이블 자동 생성"""
    # 모든 모델 임포트 (테이블 등록을 위해)
    from app.models import user, habit, log, report  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
