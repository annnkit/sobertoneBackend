from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import User, CheckIn, WeeklyInsight
from app.schemas import InsightOut
from app.utils.auth import get_current_user
from app.services.ai import generate_insight, detect_patterns
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[InsightOut])
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Return saved insights or generate one on the fly
    result = await db.execute(
        select(WeeklyInsight)
        .where(WeeklyInsight.user_id == current_user.id)
        .order_by(desc(WeeklyInsight.generated_at))
        .limit(4)
    )
    insights = result.scalars().all()

    if not insights:
        # Generate a fresh insight if none exist
        await _generate_and_save_insight(current_user, db)
        result = await db.execute(
            select(WeeklyInsight)
            .where(WeeklyInsight.user_id == current_user.id)
            .order_by(desc(WeeklyInsight.generated_at))
            .limit(4)
        )
        insights = result.scalars().all()

    return insights


async def _generate_and_save_insight(user: User, db: AsyncSession):
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == user.id, CheckIn.created_at >= week_ago)
        .order_by(CheckIn.created_at)
    )
    checkins = result.scalars().all()
    if not checkins:
        return

    checkin_dicts = [
        {"mood": c.mood_score, "craving": c.craving_score, "trigger": c.trigger_type}
        for c in checkins
    ]
    try:
        patterns = await detect_patterns(checkin_dicts)
        avg_mood = sum(c.mood_score for c in checkins) / len(checkins)
        avg_craving = sum(c.craving_score for c in checkins) / len(checkins)
        summary = f"Avg mood {avg_mood:.1f}/10, avg craving {avg_craving:.1f}/10 this week."
        text = await generate_insight(user.id, summary, patterns)

        insight = WeeklyInsight(
            user_id=user.id,
            week_start=week_ago,
            summary=text,
            patterns=patterns,
        )
        db.add(insight)
        await db.commit()
    except Exception as e:
        logger.warning(f"Insight generation failed: {e}")
