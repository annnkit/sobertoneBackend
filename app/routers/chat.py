from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import User, ChatMessage
from app.schemas import ChatRequest, ChatResponse, RelapseRequest, RelapseResponse
from app.utils.auth import get_current_user
from app.services.ai import chat_with_ai, retrieve_memories, store_memory
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

SELF_HARM_KEYWORDS = ["kill myself", "want to die", "end my life", "suicide", "self-harm", "hurt myself"]

CRISIS_RESPONSE = (
    "I hear you, and I'm genuinely concerned about your safety right now. "
    "Please reach out to the 988 Suicide & Crisis Lifeline — call or text **988**. "
    "They're available 24/7 and want to help. You don't have to face this alone. 💙"
)


def check_self_harm(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in SELF_HARM_KEYWORDS)


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Safety gate
    if check_self_harm(data.message):
        await _save_message(db, current_user.id, "user", data.message, data.is_emergency)
        await _save_message(db, current_user.id, "assistant", CRISIS_RESPONSE, True)
        return ChatResponse(reply=CRISIS_RESPONSE, is_emergency=True)

    # Fetch recent chat history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(desc(ChatMessage.created_at))
        .limit(20)
    )
    raw_history = list(reversed(history_result.scalars().all()))
    history = [{"role": msg.role, "content": msg.content} for msg in raw_history]

    # Retrieve relevant memories
    memories = await retrieve_memories(current_user.id, data.message, top_k=4)
    context = "\n".join(memories) if memories else ""

    # Add user profile context
    profile_context = f"User: {current_user.name}"
    if current_user.addiction_type:
        profile_context += f", working on {current_user.addiction_type} recovery"
    if current_user.goals:
        profile_context += f". Their goal: {current_user.goals}"
    if context:
        context = profile_context + "\n" + context
    else:
        context = profile_context

    try:
        reply = await chat_with_ai(
            current_user.id,
            data.message,
            history,
            context,
            data.is_emergency,
        )
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        reply = "I'm here with you. Take one slow breath. I'll be right back — there may be a brief connection issue."

    # Save messages
    await _save_message(db, current_user.id, "user", data.message, data.is_emergency)
    await _save_message(db, current_user.id, "assistant", reply, data.is_emergency)

    # Store chat summary in memory
    await store_memory(
        current_user.id,
        f"User said: {data.message[:200]} | Assistant: {reply[:200]}",
        "chat",
    )

    return ChatResponse(reply=reply, is_emergency=data.is_emergency)


@router.post("/relapse-mode", response_model=RelapseResponse)
async def relapse_mode(
    data: RelapseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    context = data.context or "I feel like I'm about to relapse."

    if check_self_harm(context):
        return RelapseResponse(
            reply=CRISIS_RESPONSE,
            steps=["Call or text 988 now", "Find a safe place", "Tell someone you trust"],
            breathing_exercise="Take one breath at a time. You are not alone.",
        )

    # Retrieve memories for personalization
    memories = await retrieve_memories(current_user.id, context, top_k=3)
    memory_hint = ""
    if memories:
        memory_hint = f"\nRelevant context: {memories[0]}"

    message = f"I feel like relapsing. {context}{memory_hint}"

    try:
        reply = await chat_with_ai(
            current_user.id,
            message,
            [],
            f"User: {current_user.name}, recovery focus: {current_user.addiction_type or 'general'}",
            is_emergency=True,
        )
    except Exception as e:
        logger.error(f"Relapse mode AI error: {e}")
        reply = "You reached out — that took strength. Let's get through the next 10 minutes together."

    steps = [
        "Take 4 slow breaths: inhale 4 counts, hold 4, exhale 6",
        "Move to a different room or step outside",
        "Text or call one person you trust right now",
        "Set a 10-minute timer — just get through that",
        "Open this app again when the timer ends",
    ]

    breathing = "Breathe in for 4 counts... hold for 4... breathe out for 6. Repeat 3 times."

    await _save_message(db, current_user.id, "user", f"[EMERGENCY] {context}", True)
    await _save_message(db, current_user.id, "assistant", reply, True)

    return RelapseResponse(reply=reply, steps=steps, breathing_exercise=breathing)


async def _save_message(db: AsyncSession, user_id: str, role: str, content: str, is_emergency: bool):
    msg = ChatMessage(user_id=user_id, role=role, content=content, is_emergency=is_emergency)
    db.add(msg)
    await db.commit()
