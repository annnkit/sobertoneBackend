from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    age_range: Optional[str] = None
    addiction_type: Optional[str] = None
    goals: Optional[str] = None
    timezone: str = "UTC"
    sober_since: Optional[datetime] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    age_range: Optional[str]
    addiction_type: Optional[str]
    goals: Optional[str]
    timezone: str
    sober_since: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    age_range: Optional[str] = None
    addiction_type: Optional[str] = None
    goals: Optional[str] = None
    timezone: Optional[str] = None
    sober_since: Optional[datetime] = None


# Check-ins
class CheckInCreate(BaseModel):
    mood_score: int       # 1-10
    craving_score: int    # 1-10
    trigger_type: Optional[str] = None
    notes: Optional[str] = None


class CheckInOut(BaseModel):
    id: str
    user_id: str
    mood_score: int
    craving_score: int
    trigger_type: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Chat
class ChatRequest(BaseModel):
    message: str
    is_emergency: bool = False


class ChatResponse(BaseModel):
    reply: str
    is_emergency: bool
    suggestions: Optional[List[str]] = None


class RelapseRequest(BaseModel):
    context: Optional[str] = None  # what they're feeling


class RelapseResponse(BaseModel):
    reply: str
    steps: List[str]
    breathing_exercise: str


# Dashboard
class TrendPoint(BaseModel):
    date: str
    mood: Optional[float]
    craving: Optional[float]


class TriggerFrequency(BaseModel):
    trigger: str
    count: int


class DashboardData(BaseModel):
    streak_days: int
    total_checkins: int
    avg_mood_7d: Optional[float]
    avg_craving_7d: Optional[float]
    mood_trend: List[TrendPoint]
    craving_trend: List[TrendPoint]
    trigger_frequency: List[TriggerFrequency]
    days_sober: Optional[int]
    money_saved_estimate: Optional[float]
    recent_checkins: List[CheckInOut]
    ai_insight: Optional[str]


# Insights
class InsightOut(BaseModel):
    id: str
    week_start: datetime
    summary: str
    patterns: Optional[list]
    generated_at: datetime

    class Config:
        from_attributes = True


# Memory
class MemorySyncRequest(BaseModel):
    force: bool = False


class MemorySyncResponse(BaseModel):
    synced: int
    message: str


# Assessment
class AssessmentCreate(BaseModel):
    stage: int
    total_score: int
    answers: Optional[list] = None


class AssessmentOut(BaseModel):
    id: str
    stage: int
    total_score: int
    answers: Optional[list]
    taken_at: datetime

    class Config:
        from_attributes = True


# Community
class PostCreate(BaseModel):
    content: str
    is_anonymous: bool = True
    addiction_type: Optional[str] = None


class ReplyCreate(BaseModel):
    content: str
    is_anonymous: bool = True


class ReplyOut(BaseModel):
    id: str
    author_name: str
    is_anonymous: bool
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class PostOut(BaseModel):
    id: str
    author_name: str
    is_anonymous: bool
    addiction_type: Optional[str]
    content: str
    likes_count: int
    replies_count: int
    user_liked: bool
    created_at: datetime
    replies: List[ReplyOut] = []

    class Config:
        from_attributes = True
TokenResponse.model_rebuild()
