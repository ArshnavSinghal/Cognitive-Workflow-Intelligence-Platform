import math
from pydantic import BaseModel, EmailStr, field_validator
from .ml.actions import is_valid_action


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ActivityCreate(BaseModel):
    activity_type: str
    subject: str
    topic: str
    duration: int
    difficulty: str
    score: float | None = None
    errors: int = 0
    recommendation_session_id: int | None = None

    @field_validator("activity_type")
    @classmethod
    def must_be_valid_activity(cls, v):
        if not is_valid_action(v):
            raise ValueError(
                f"Invalid activity '{v}'. Must be one of: "
                "practice_current, practice_prerequisite, "
                "review_concept, easy_practice, hard_practice, "
                "take_assessment"
            )
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if not math.isfinite(v) or v <= 0:
            raise ValueError("Duration must be a positive integer (greater than 0 minutes)")
        if v > 1440:
            raise ValueError("Duration cannot exceed 1440 minutes (24 hours)")
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        trimmed = v.strip().lower() if isinstance(v, str) else ""
        if trimmed not in {"easy", "medium", "hard"}:
            raise ValueError("Difficulty must be one of: 'easy', 'medium', 'hard'")
        return trimmed

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float | None) -> float | None:
        if v is not None:
            if not math.isfinite(v):
                raise ValueError("Score must be a finite number (NaN and Infinity are not allowed)")
            if v < 0.0 or v > 100.0:
                raise ValueError("Score must be between 0.0 and 100.0")
        return v

    @field_validator("errors")
    @classmethod
    def validate_errors(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Errors cannot be negative")
        return v

    @field_validator("recommendation_session_id")
    @classmethod
    def validate_session_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Recommendation session ID must be a positive integer")
        return v


class SkillCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip() if v else ""
        if len(trimmed) < 2:
            raise ValueError("Skill name must be at least 2 characters long")
        return trimmed


class UserSkillCreate(BaseModel):
    skill_id: int
    mastery: float = 0.0
    confidence: float = 0.0


class SkillDependencyCreate(BaseModel):
    parent_skill_id: int
    child_skill_id: int
    dependency_strength: float = 1.0

    @field_validator("dependency_strength")
    @classmethod
    def validate_strength(cls, v: float) -> float:
        if v <= 0.0 or v > 2.0:
            raise ValueError("Dependency strength must be between 0.0 and 2.0")
        return round(v, 3)


class PrerequisiteResponse(BaseModel):
    skill_id: int
    skill_name: str
    direct_prerequisites: list[dict]
    transitive_prerequisites: list[dict]


class DescendantsResponse(BaseModel):
    skill_id: int
    skill_name: str
    direct_dependents: list[dict]
    transitive_dependents: list[dict]


class PrerequisiteDiagnosisResponse(BaseModel):
    target_skill_id: int
    target_skill_name: str
    target_mastery: float
    has_prerequisites: bool
    prerequisites: list[dict]
    primary_gap: dict | None = None
    diagnosis_summary: str


class DependencyPathResponse(BaseModel):
    source_id: int
    source_name: str
    target_id: int
    target_name: str
    has_path: bool
    distance: int | None = None
    path_ids: list[int] = []
    path_names: list[str] = []
    message: str


class RecommendationCreate(BaseModel):
    skill_id: int


class LearningOutcomeCreate(BaseModel):
    skill_id: int
    recommended_action: str
    actual_action: str
    before_mastery: float
    after_mastery: float
    is_test: bool = True
    feature_snapshot: dict | None = None
    recommendation_session_id: int | None = None

    @field_validator("recommended_action", "actual_action")
    @classmethod
    def must_be_valid_action(cls, v):
        if not is_valid_action(v):
            raise ValueError(
                f"Invalid action '{v}'. Must be one of: "
                "practice_current, practice_prerequisite, "
                "review_concept, easy_practice, hard_practice, "
                "take_assessment"
            )
        return v
