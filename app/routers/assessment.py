from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.database import get_db
from app.models import User, AssessmentResult
from app.schemas import AssessmentCreate, AssessmentOut
from app.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=AssessmentOut)
async def save_assessment(
    data: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = AssessmentResult(
        user_id=current_user.id,
        stage=data.stage,
        total_score=data.total_score,
        answers=data.answers,
    )
    db.add(result)
    # Also update user's current stage
    current_user.addiction_stage = data.stage
    await db.commit()
    await db.refresh(result)
    return result


@router.get("", response_model=List[AssessmentOut])
async def get_assessments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AssessmentResult)
        .where(AssessmentResult.user_id == current_user.id)
        .order_by(desc(AssessmentResult.taken_at))
        .limit(10)
    )
    return result.scalars().all()


@router.get("/latest", response_model=AssessmentOut)
async def get_latest_assessment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(
        select(AssessmentResult)
        .where(AssessmentResult.user_id == current_user.id)
        .order_by(desc(AssessmentResult.taken_at))
        .limit(1)
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found")
    return assessment
