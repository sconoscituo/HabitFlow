# Gemini AI 코칭 서비스 - 사용자 습관 데이터 분석 및 맞춤 메시지 생성
import json
import logging
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import google.generativeai as genai

from app.config import get_settings
from app.models.habit import Habit
from app.models.log import HabitLog
from app.models.report import WeeklyReport

logger = logging.getLogger(__name__)
settings = get_settings()


def _init_gemini() -> genai.GenerativeModel | None:
    """Gemini 클라이언트 초기화 (API 키 없으면 None 반환)"""
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY가 설정되지 않았습니다. AI 코칭이 비활성화됩니다.")
        return None
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel("gemini-pro")


async def _collect_week_stats(
    db: AsyncSession,
    user_id: int,
    week_start: date,
    week_end: date,
) -> dict:
    """주간 습관 통계 데이터 수집"""
    # 활성 습관 목록 조회
    habits_result = await db.execute(
        select(Habit).where(Habit.user_id == user_id, Habit.is_active == True)
    )
    habits = habits_result.scalars().all()

    habit_stats = []
    total_expected = 0
    total_completed = 0

    for habit in habits:
        # 해당 주의 완료 횟수
        logs_result = await db.execute(
            select(func.count(HabitLog.id)).where(
                HabitLog.habit_id == habit.id,
                HabitLog.user_id == user_id,
                func.date(HabitLog.completed_at) >= week_start,
                func.date(HabitLog.completed_at) <= week_end,
            )
        )
        completed = logs_result.scalar() or 0

        # 주간 목표 횟수 계산 (daily = 7회, weekly = 1회)
        expected = 7 if habit.frequency == "daily" else 1
        total_expected += expected
        total_completed += min(completed, expected)

        # 최근 스트릭 조회 (로그의 마지막 streak_count)
        streak_result = await db.execute(
            select(HabitLog.streak_count)
            .where(HabitLog.habit_id == habit.id, HabitLog.user_id == user_id)
            .order_by(HabitLog.completed_at.desc())
            .limit(1)
        )
        current_streak = streak_result.scalar() or 0

        habit_stats.append({
            "name": habit.name,
            "frequency": habit.frequency,
            "completed": completed,
            "expected": expected,
            "rate": round(completed / expected, 2) if expected > 0 else 0.0,
            "current_streak": current_streak,
        })

    overall_rate = round(total_completed / total_expected, 2) if total_expected > 0 else 0.0

    return {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "habits": habit_stats,
        "overall_completion_rate": overall_rate,
        "total_habits": len(habits),
    }


async def generate_weekly_coaching(
    db: AsyncSession,
    user_id: int,
    week_start: date,
    week_end: date,
) -> dict:
    """
    주간 습관 데이터를 분석하여 Gemini AI로 맞춤 코칭 메시지 생성.
    프리미엄 사용자 전용 기능.
    반환값: {"ai_coaching": str, "strengths": str, "improvements": str, "completion_rate": float}
    """
    stats = await _collect_week_stats(db, user_id, week_start, week_end)
    completion_rate = stats["overall_completion_rate"]

    # Gemini 클라이언트 초기화
    model = _init_gemini()

    if model is None:
        # API 키 없을 때 기본 메시지 반환
        return _fallback_coaching(stats)

    # 프롬프트 구성
    prompt = f"""
당신은 습관 형성 전문 AI 코치입니다. 아래 사용자의 주간 습관 달성 데이터를 분석하고,
한국어로 따뜻하고 동기부여가 되는 코칭 메시지를 작성해주세요.

## 주간 데이터
- 기간: {stats['week_start']} ~ {stats['week_end']}
- 전체 완료율: {completion_rate * 100:.1f}%
- 습관 수: {stats['total_habits']}개

## 습관별 달성 현황
{json.dumps(stats['habits'], ensure_ascii=False, indent=2)}

## 작성 요청
다음 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{
  "ai_coaching": "전체 코칭 메시지 (200자 이내, 격려와 실천 팁 포함)",
  "strengths": "이번 주 잘한 점 (100자 이내, 구체적인 습관명 포함)",
  "improvements": "다음 주 개선할 점 (100자 이내, 실천 가능한 제안 포함)"
}}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # JSON 파싱 시도
        if text.startswith("```"):
            # 코드블록 제거
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text)
        result["completion_rate"] = completion_rate
        return result

    except Exception as e:
        logger.error(f"Gemini API 호출 실패: {e}")
        return _fallback_coaching(stats)


def _fallback_coaching(stats: dict) -> dict:
    """AI 사용 불가 시 기본 코칭 메시지 생성"""
    rate = stats["overall_completion_rate"]
    total = stats["total_habits"]

    if rate >= 0.8:
        coaching = f"이번 주 {rate*100:.0f}% 달성! 정말 훌륭합니다. 꾸준함이 최고의 재능입니다. 다음 주도 이 페이스를 유지해보세요!"
        strengths = f"{total}개 습관 중 대부분을 성공적으로 완료했습니다. 높은 일관성이 돋보입니다."
        improvements = "거의 완벽합니다! 빠진 날이 있다면 그 시간대에 방해 요소가 무엇인지 분석해보세요."
    elif rate >= 0.5:
        coaching = f"이번 주 {rate*100:.0f}% 달성했습니다. 절반 이상 해냈다는 것만으로도 대단해요! 조금만 더 힘내보세요."
        strengths = "포기하지 않고 꾸준히 시도하고 있습니다. 시작이 반이에요."
        improvements = "완료율이 낮은 습관 1개를 선택해 다음 주에 집중 공략해보세요."
    else:
        coaching = f"이번 주는 쉽지 않았군요. {rate*100:.0f}% 달성이지만 포기하지 마세요. 작은 습관 하나부터 다시 시작해봅시다."
        strengths = "어려운 상황에서도 일부 완료한 것은 의지가 있다는 증거입니다."
        improvements = "목표를 줄이고 가장 쉬운 습관 1~2개만 집중해서 성공 경험을 쌓아보세요."

    return {
        "ai_coaching": coaching,
        "strengths": strengths,
        "improvements": improvements,
        "completion_rate": rate,
    }


async def save_weekly_report(
    db: AsyncSession,
    user_id: int,
    week_start: date,
    week_end: date,
    coaching_data: dict,
) -> WeeklyReport:
    """코칭 결과를 DB에 저장"""
    # 같은 주의 기존 리포트 삭제 후 재생성
    existing = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.user_id == user_id,
            WeeklyReport.week_start == week_start,
        )
    )
    old_report = existing.scalar_one_or_none()
    if old_report:
        await db.delete(old_report)

    report = WeeklyReport(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        completion_rate=coaching_data.get("completion_rate", 0.0),
        ai_coaching=coaching_data.get("ai_coaching"),
        strengths=coaching_data.get("strengths"),
        improvements=coaching_data.get("improvements"),
    )
    db.add(report)
    await db.flush()
    return report
