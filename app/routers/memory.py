from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, CheckIn, ChatMessage
from app.schemas import MemorySyncRequest, MemorySyncResponse
from app.utils.auth import get_current_user
from app.services.ai import store_memory
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sync", response_model=MemorySyncResponse)
async def sync_memory(
    data: MemorySyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync recent check-ins and chat summaries to vector memory."""
    synced = 0

    checkin_result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == current_user.id)
        .order_by(CheckIn.created_at.desc())
        .limit(20)
    )
    checkins = checkin_result.scalars().all()

    for c in checkins:
        content = (
            f"Check-in on {c.created_at.date()}: mood={c.mood_score}/10, "
            f"craving={c.craving_score}/10, trigger={c.trigger_type or 'none'}"
            + (f", notes: {c.notes}" if c.notes else "")
        )
        await store_memory(current_user.id, content, "checkin")
        synced += 1

    return MemorySyncResponse(
        synced=synced,
        message=f"Synced {synced} check-ins to memory."
    )
