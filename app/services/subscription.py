"""HabitFlow 구독 플랜"""
from enum import Enum

class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"   # 월 3,900원

PLAN_LIMITS = {
    PlanType.FREE: {"habits": 5,  "ai_coaching": False, "streak_analysis": False, "reminders": 3},
    PlanType.PRO:  {"habits": 50, "ai_coaching": True,  "streak_analysis": True,  "reminders": 20},
}

PLAN_PRICES_KRW = {PlanType.FREE: 0, PlanType.PRO: 3900}
