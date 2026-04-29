from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta, timezone
from collections import Counter
from app.database import get_db
from app.models import User, CheckIn
from app.schemas import DashboardData, TrendPoint, TriggerFrequency, CheckInOut
from app.utils.auth import get_current_user
from app.services.ai import generate_insight, detect_patterns
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

MONEY_ESTIMATES = {
    "alcohol": 15.0,
    "cigarettes": 12.0,
    "cannabis": 10.0,
    "gambling": 50.0,
    "substances": 30.0,
    "default": 20.0,
}


@router.get("", response_model=DashboardData)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # All check-ins (last 30 days)
    result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == current_user.id, CheckIn.created_at >= thirty_days_ago)
        .order_by(CheckIn.created_at)
    )
    checkins = result.scalars().all()

    # Recent 5 for display
    recent_result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == current_user.id)
        .order_by(desc(CheckIn.created_at))
        .limit(5)
    )
    recent = recent_result.scalars().all()

    # 7-day averages
    last_7 = [c for c in checkins if c.created_at >= seven_days_ago]
    avg_mood = round(sum(c.mood_score for c in last_7) / len(last_7), 1) if last_7 else None
    avg_craving = round(sum(c.craving_score for c in last_7) / len(last_7), 1) if last_7 else None

    # Streak calculation
    streak = _calculate_streak(checkins, now)

    # Trend data (daily averages)
    mood_trend, craving_trend = _build_trends(checkins, now)

    # Trigger frequency
    triggers = [c.trigger_type for c in checkins if c.trigger_type]
    trigger_freq = [
        TriggerFrequency(trigger=t, count=c)
        for t, c in Counter(triggers).most_common(6)
    ]

    # Days sober
    days_sober = None
    if current_user.sober_since:
        sober_dt = current_user.sober_since
        if sober_dt.tzinfo is None:
            sober_dt = sober_dt.replace(tzinfo=timezone.utc)
        days_sober = (now - sober_dt).days

    # Money saved estimate
    money_saved = None
    if days_sober is not None:
        addiction = (current_user.addiction_type or "").lower()
        daily_cost = MONEY_ESTIMATES.get(addiction, MONEY_ESTIMATES["default"])
        money_saved = round(days_sober * daily_cost, 2)

    # AI insight
    ai_insight = None
    if len(checkins) >= 3:
        try:
            summary = (
                f"Average mood: {avg_mood or 'N/A'}/10, "
                f"average craving: {avg_craving or 'N/A'}/10 over the last 7 days. "
                f"Most common trigger: {trigger_freq[0].trigger if trigger_freq else 'none'}."
            )
            checkin_dicts = [
                {"mood": c.mood_score, "craving": c.craving_score,
                 "trigger": c.trigger_type, "date": str(c.created_at.date())}
                for c in checkins
            ]
            patterns = await detect_patterns(checkin_dicts)
            ai_insight = await generate_insight(current_user.id, summary, patterns)
        except Exception as e:
            logger.warning(f"AI insight failed: {e}")

    return DashboardData(
        streak_days=streak,
        total_checkins=len(checkins),
        avg_mood_7d=avg_mood,
        avg_craving_7d=avg_craving,
        mood_trend=mood_trend,
        craving_trend=craving_trend,
        trigger_frequency=trigger_freq,
        days_sober=days_sober,
        money_saved_estimate=money_saved,
        recent_checkins=[CheckInOut.model_validate(c) for c in recent],
        ai_insight=ai_insight,
    )


def _calculate_streak(checkins, now):
    if not checkins:
        return 0
    check_dates = sorted({c.created_at.date() for c in checkins}, reverse=True)
    streak = 0
    expected = now.date()
    for d in check_dates:
        if d == expected or d == expected - timedelta(days=1):
            streak += 1
            expected = d - timedelta(days=1)
        else:
            break
    return streak


def _build_trends(checkins, now):
    from collections import defaultdict
    daily_mood = defaultdict(list)
    daily_craving = defaultdict(list)

    for c in checkins:
        day = c.created_at.date().isoformat()
        daily_mood[day].append(c.mood_score)
        daily_craving[day].append(c.craving_score)

    all_days = sorted(set(list(daily_mood.keys()) + list(daily_craving.keys())))

    mood_trend = [
        TrendPoint(date=d, mood=round(sum(daily_mood[d]) / len(daily_mood[d]), 1) if daily_mood[d] else None, craving=None)
        for d in all_days
    ]
    craving_trend = [
        TrendPoint(date=d, mood=None, craving=round(sum(daily_craving[d]) / len(daily_craving[d]), 1) if daily_craving[d] else None)
        for d in all_days
    ]
    return mood_trend, craving_trend
