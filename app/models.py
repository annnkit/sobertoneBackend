from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    age_range = Column(String, nullable=True)  # e.g. "18-25", "26-35"
    addiction_type = Column(String, nullable=True)
    addiction_stage = Column(Integer, nullable=True)   # 1–5 from assessment
    goals = Column(Text, nullable=True)
    timezone = Column(String, default="UTC")
    sober_since = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    checkins = relationship("CheckIn", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")


class CheckIn(Base):
    __tablename__ = "checkins"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    mood_score = Column(Integer, nullable=False)      # 1-10
    craving_score = Column(Integer, nullable=False)   # 1-10
    trigger_type = Column(String, nullable=True)      # stress, boredom, loneliness, etc.
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="checkins")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    is_emergency = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="chat_messages")


class WeeklyInsight(Base):
    __tablename__ = "weekly_insights"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    week_start = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=False)
    patterns = Column(JSON, nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    stage = Column(Integer, nullable=False)          # 1–5
    total_score = Column(Integer, nullable=False)
    answers = Column(JSON, nullable=True)            # list of {question_id, score}
    taken_at = Column(DateTime(timezone=True), server_default=func.now())


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    author_name = Column(String, nullable=False)     # display name or "Anonymous"
    is_anonymous = Column(Boolean, default=True)
    addiction_type = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    is_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    replies = relationship("PostReply", back_populates="post", cascade="all, delete-orphan")


class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    post = relationship("CommunityPost", back_populates="likes")


class PostReply(Base):
    __tablename__ = "post_replies"

    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    author_name = Column(String, nullable=False)
    is_anonymous = Column(Boolean, default=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("CommunityPost", back_populates="replies")
