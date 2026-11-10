from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from datetime import datetime, timezone
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    activity_type = Column(String(50), nullable=False)
    subject = Column(String(100), nullable=False)
    topic = Column(String(100), nullable=False)

    duration = Column(Integer, nullable=False)
    difficulty = Column(String(20), nullable=False)
    score = Column(Float, nullable=True)
    errors = Column(Integer, default=0)

    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500))
    category = Column(String(100))


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)

    mastery = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)

    last_updated = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class SkillDependency(Base):
    __tablename__ = "skill_dependencies"

    id = Column(Integer, primary_key=True, index=True)

    parent_skill_id = Column(
        Integer,
        ForeignKey("skills.id"),
        nullable=False
    )

    child_skill_id = Column(
        Integer,
        ForeignKey("skills.id"),
        nullable=False
    )

    dependency_strength = Column(Float, default=1.0)


class LearningOutcome(Base):
    __tablename__ = "learning_outcomes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    skill_id = Column(
        Integer,
        ForeignKey("skills.id"),
        nullable=False
    )

    recommended_action = Column(
        String(100),
        nullable=False
    )

    actual_action = Column(
        String(100),
        nullable=False
    )

    before_mastery = Column(
        Float,
        nullable=False
    )

    after_mastery = Column(
        Float,
        nullable=False
    )

    mastery_change = Column(
        Float,
        nullable=False
    )

    outcome = Column(
        String(20),
        nullable=False
    )

    is_test = Column(
        Boolean,
        nullable=False,
        default=True
    )

    feature_snapshot = Column(
        JSON,
        nullable=True
    )

    recommendation_session_id = Column(
        Integer,
        ForeignKey("recommendation_sessions.id"),
        nullable=True
    )

    evaluated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )


class RecommendationSession(Base):
    __tablename__ = "recommendation_sessions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    skill_id = Column(
        Integer,
        ForeignKey("skills.id"),
        nullable=False
    )

    recommended_action = Column(
        String(100),
        nullable=False
    )

    before_mastery = Column(
        Float,
        nullable=False
    )

    feature_snapshot = Column(
        JSON,
        nullable=True
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending"
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
