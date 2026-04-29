"""
Seed script: creates a demo user with 30 days of check-ins and chat history.
Run: python seed.py
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from app.database import engine, Base, AsyncSessionLocal
from app.models import User, CheckIn, ChatMessage, WeeklyInsight, CommunityPost, AssessmentResult
from app.utils.auth import hash_password
import uuid

DEMO_EMAIL = "demo@sobertone.app"
DEMO_PASSWORD = "demo1234"

TRIGGERS = ["stress", "boredom", "loneliness", "social_pressure", "anxiety", "habit", None]

NOTES = [
    "Tough day at work but got through it.",
    "Feeling stronger today.",
    "Had a hard evening — called a friend instead.",
    "Workout helped a lot this morning.",
    "The weekend feels risky, staying aware.",
    "Grateful for waking up sober.",
    "Craving was bad at night but passed.",
    None, None, None,
]

CHAT_PAIRS = [
    ("I'm really struggling tonight", "I hear you. You reached out — that's the right move. What's happening right now?"),
    ("I feel a craving coming on", "Let's slow that down together. Try this: breathe in for 4, hold for 4, out for 6. What triggered this feeling?"),
    ("I made it through the day", "That's real. Every day counts. What helped you most today?"),
    ("I'm bored and that's when it gets hard", "Boredom is one of the sneakiest triggers. Can you do one physical thing right now — even just stand up and stretch?"),
    ("I feel proud of myself", "You should. That pride is evidence — keep it close for the hard moments."),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if demo user exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Demo user already exists: {DEMO_EMAIL}")
            return

        # Create demo user
        user = User(
            id=str(uuid.uuid4()),
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            name="Alex",
            age_range="26–35",
            addiction_type="alcohol",
            goals="Stay alcohol-free for 90 days and rebuild my sleep schedule.",
            timezone="America/New_York",
            sober_since=datetime.now(timezone.utc) - timedelta(days=28),
        )
        db.add(user)
        await db.flush()

        # 30 days of check-ins
        now = datetime.now(timezone.utc)
        for i in range(30, 0, -1):
            dt = now - timedelta(days=i)
            # Simulate improvement trend over time
            base_mood = 4 + (i / 30) * 0 + random.uniform(-1.5, 1.5)
            base_craving = 7 - (i / 30) * 3 + random.uniform(-1.5, 1.5)
            checkin = CheckIn(
                id=str(uuid.uuid4()),
                user_id=user.id,
                mood_score=max(1, min(10, round(base_mood + (30 - i) * 0.05))),
                craving_score=max(1, min(10, round(base_craving))),
                trigger_type=random.choice(TRIGGERS),
                notes=random.choice(NOTES),
                created_at=dt.replace(hour=random.randint(8, 22), minute=random.randint(0, 59)),
            )
            db.add(checkin)

        # Some chat messages
        for msg, reply in CHAT_PAIRS:
            dt = now - timedelta(days=random.randint(1, 25))
            db.add(ChatMessage(
                id=str(uuid.uuid4()),
                user_id=user.id,
                role="user",
                content=msg,
                created_at=dt,
            ))
            db.add(ChatMessage(
                id=str(uuid.uuid4()),
                user_id=user.id,
                role="assistant",
                content=reply,
                created_at=dt + timedelta(seconds=5),
            ))

        # Weekly insight
        db.add(WeeklyInsight(
            id=str(uuid.uuid4()),
            user_id=user.id,
            week_start=now - timedelta(days=7),
            summary=(
                "You've been showing up consistently — 7 check-ins this week is real discipline. "
                "Your cravings have been highest on weekday evenings, often when stress is the trigger. "
                "One thing to try this week: a 10-minute walk right after work as a buffer. "
                "You're building something real here, one day at a time."
            ),
            patterns=["Evening cravings peak after work", "Stress is the most frequent trigger", "Mood improving week-over-week"],
        ))

        # Assessment result
        db.add(AssessmentResult(
            id=str(uuid.uuid4()),
            user_id=user.id,
            stage=2,
            total_score=18,
            answers=[{"question_id": f"q{i+1}", "score": random.randint(0, 2)} for i in range(15)],
        ))

        # Community posts (from other demo users)
        COMMUNITY_POSTS = [
            ("Alex M.", False, "alcohol",      "30 days sober today. Never thought I could do it. One day at a time really works 💙", 47, 12, 2),
            ("Anonymous", True, "gambling",    "Slipped yesterday but I'm back today. That's what matters. Not giving up.", 83, 21, 1),
            ("Jamie",    False, "nicotine",    "Week 2 without cigarettes. The cravings are real but so is the progress. Keep going everyone 🌟", 34, 8, 5),
            ("Anonymous", True, "other",       "Some days are just survival days. And that's okay. You don't have to thrive every day. Just stay.", 126, 34, 2),
            ("Sam K.",   False, "alcohol",     "My therapist told me to celebrate small wins. Today's win: I made it to 9pm without a drink. That's enough.", 58, 15, 3),
            ("Anonymous", True, "cannabis",    "3 months today. I didn't think I'd make it past week 1. Proud of everyone here fighting.", 91, 22, 0),
        ]
        for name, anon, atype, content, _, _, days_ago in COMMUNITY_POSTS:
            db.add(CommunityPost(
                id=str(uuid.uuid4()),
                user_id=user.id,
                author_name=name, is_anonymous=anon,
                addiction_type=atype, content=content,
                created_at=now - timedelta(days=days_ago, hours=random.randint(0, 8)),
            ))

        await db.commit()
        print(f"""
✅ Seed complete!
   Email:    {DEMO_EMAIL}
   Password: {DEMO_PASSWORD}
   Name:     Alex
   Sober since: {(now - timedelta(days=28)).date()}
   Check-ins: 30 days seeded
        """)


if __name__ == "__main__":
    asyncio.run(seed())
