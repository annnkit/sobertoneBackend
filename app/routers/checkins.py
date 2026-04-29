from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from app.database import get_db
from app.models import User, CheckIn
from app.schemas import CheckInCreate, CheckInOut
from app.utils.auth import get_current_user
from app.services.ai import store_memory

router = APIRouter()


@router.post("", response_model=CheckInOut)
async def create_checkin(
    data: CheckInCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    checkin = CheckIn(
        user_id=current_user.id,
        mood_score=data.mood_score,
        craving_score=data.craving_score,
        trigger_type=data.trigger_type,
        notes=data.notes,
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)

    # Store in vector memory for AI context retrieval
    memory_content = (
        f"Check-in: mood={data.mood_score}/10, craving={data.craving_score}/10, "
        f"trigger={data.trigger_type or 'none'}"
        + (f", notes: {data.notes}" if data.notes else "")
    )
    await store_memory(
        current_user.id,
        memory_content,
        "checkin",
        {"mood": data.mood_score, "craving": data.craving_score, "trigger": data.trigger_type or ""},
    )

    return checkin


@router.get("", response_model=List[CheckInOut])
async def list_checkins(
    limit: int = Query(30, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == current_user.id)
        .order_by(desc(CheckIn.created_at))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
