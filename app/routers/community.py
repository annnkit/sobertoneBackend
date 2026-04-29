from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from app.database import get_db
from app.models import User, CommunityPost, PostLike, PostReply
from app.schemas import PostCreate, PostOut, ReplyCreate, ReplyOut
from app.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

BANNED_PHRASES = ["how to use", "where to buy", "best place to get", "dealer", "score some"]

def is_harmful(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in BANNED_PHRASES)


@router.get("", response_model=List[PostOut])
async def list_posts(
    addiction_type: Optional[str] = Query(None),
    limit: int = Query(30, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(CommunityPost).where(CommunityPost.is_flagged == False)
    if addiction_type and addiction_type != "all":
        q = q.where(CommunityPost.addiction_type == addiction_type)
    q = q.order_by(desc(CommunityPost.created_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    posts = result.scalars().all()

    out = []
    for p in posts:
        likes_result = await db.execute(select(func.count()).where(PostLike.post_id == p.id))
        likes_count = likes_result.scalar()
        replies_result = await db.execute(select(func.count()).where(PostReply.post_id == p.id))
        replies_count = replies_result.scalar()
        user_liked_result = await db.execute(select(PostLike).where(PostLike.post_id == p.id, PostLike.user_id == current_user.id))
        user_liked = user_liked_result.scalar_one_or_none() is not None
        replies_q = await db.execute(select(PostReply).where(PostReply.post_id == p.id).order_by(PostReply.created_at).limit(5))
        replies = replies_q.scalars().all()

        out.append(PostOut(
            id=p.id, author_name=p.author_name, is_anonymous=p.is_anonymous,
            addiction_type=p.addiction_type, content=p.content,
            likes_count=likes_count, replies_count=replies_count,
            user_liked=user_liked, created_at=p.created_at,
            replies=[ReplyOut(id=r.id, author_name=r.author_name, is_anonymous=r.is_anonymous, content=r.content, created_at=r.created_at) for r in replies],
        ))
    return out


@router.post("", response_model=PostOut)
async def create_post(
    data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if is_harmful(data.content):
        raise HTTPException(status_code=400, detail="This content violates community guidelines.")
    if len(data.content.strip()) < 5:
        raise HTTPException(status_code=400, detail="Post is too short.")

    post = CommunityPost(
        user_id=current_user.id,
        author_name="Anonymous" if data.is_anonymous else current_user.name,
        is_anonymous=data.is_anonymous,
        addiction_type=data.addiction_type or current_user.addiction_type,
        content=data.content.strip(),
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return PostOut(id=post.id, author_name=post.author_name, is_anonymous=post.is_anonymous,
                   addiction_type=post.addiction_type, content=post.content,
                   likes_count=0, replies_count=0, user_liked=False,
                   created_at=post.created_at, replies=[])


@router.post("/{post_id}/like")
async def toggle_like(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == current_user.id))
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        liked = False
    else:
        db.add(PostLike(post_id=post_id, user_id=current_user.id))
        liked = True
    await db.commit()
    return {"liked": liked}


@router.post("/{post_id}/replies", response_model=ReplyOut)
async def add_reply(
    post_id: str,
    data: ReplyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if is_harmful(data.content):
        raise HTTPException(status_code=400, detail="This content violates community guidelines.")
    reply = PostReply(
        post_id=post_id, user_id=current_user.id,
        author_name="Anonymous" if data.is_anonymous else current_user.name,
        is_anonymous=data.is_anonymous, content=data.content.strip(),
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return reply


@router.post("/{post_id}/report")
async def report_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CommunityPost).where(CommunityPost.id == post_id))
    post = result.scalar_one_or_none()
    if post:
        post.is_flagged = True
        await db.commit()
    return {"reported": True}
