# 사용자 라우터 - 회원가입, 로그인, 대시보드
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.habit import Habit
from app.models.log import HabitLog
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, DashboardResponse

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """JWT 액세스 토큰 생성"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT 토큰으로 현재 사용자 조회 (의존성 주입용)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 인증 정보입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# Bearer 토큰 추출 의존성
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await get_current_user(credentials.credentials, db)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """회원가입"""
    # 이메일 중복 확인
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다.",
        )

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        timezone=user_in.timezone,
    )
    db.add(user)
    await db.flush()  # ID 확보

    token = create_access_token(user.id)
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """로그인"""
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    token = create_access_token(user.id)
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user_dep)):
    """내 정보 조회"""
    return current_user


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """대시보드 - 오늘의 습관 현황 요약"""
    from datetime import date
    today = date.today()

    # 전체 활성 습관 수
    habits_result = await db.execute(
        select(func.count(Habit.id)).where(
            Habit.user_id == current_user.id,
            Habit.is_active == True,
        )
    )
    total_habits = habits_result.scalar() or 0

    # 오늘 완료한 고유 습관 수
    completed_result = await db.execute(
        select(func.count(func.distinct(HabitLog.habit_id))).where(
            HabitLog.user_id == current_user.id,
            func.date(HabitLog.completed_at) == today,
        )
    )
    completed_today = completed_result.scalar() or 0

    # 오늘 완료율
    completion_rate_today = round(completed_today / total_habits, 2) if total_habits > 0 else 0.0

    # 현재 최고 스트릭 (모든 습관 중 가장 높은 streak_count)
    streak_result = await db.execute(
        select(func.max(HabitLog.streak_count)).where(
            HabitLog.user_id == current_user.id
        )
    )
    current_best_streak = streak_result.scalar() or 0

    # 전체 누적 완료 횟수
    total_logs_result = await db.execute(
        select(func.count(HabitLog.id)).where(HabitLog.user_id == current_user.id)
    )
    total_logs = total_logs_result.scalar() or 0

    return DashboardResponse(
        total_habits=total_habits,
        completed_today=completed_today,
        completion_rate_today=completion_rate_today,
        current_best_streak=current_best_streak,
        total_logs=total_logs,
    )
