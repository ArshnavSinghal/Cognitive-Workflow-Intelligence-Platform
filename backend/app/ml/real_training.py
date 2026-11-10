import math

import pandas as pd

from .actions import is_valid_action
from .features import extract_numeric_features_from_snapshot, adapt_legacy_snapshot
from .model import FEATURE_COLUMNS
from .training import prepare_training_dataframe
from ..models import LearningOutcome, RecommendationSession

MIN_REAL_SAMPLES = 30
REQUIRED_FEATURES = set(FEATURE_COLUMNS)


def prepare_real_training_dataframe(dataset):
    """Prepare and validate genuine learner records."""

    if not dataset:
        raise ValueError("No real training samples available.")

    for sample in dataset:
        if sample.get("is_synthetic", False):
            raise ValueError("Synthetic records are not allowed.")

    df = prepare_training_dataframe(dataset)

    if df.empty:
        raise ValueError("No valid real training records.")

    required = FEATURE_COLUMNS + ["action"]

    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if df[required].isnull().any().any():
        raise ValueError("Training data contains missing values.")

    if not df[required].map(
        lambda value: isinstance(value, (int, float))
        and math.isfinite(float(value))
    ).all().all():
        raise ValueError("Training features must be numeric.")

    if len(df) < MIN_REAL_SAMPLES:
        raise ValueError(
            f"At least {MIN_REAL_SAMPLES} real samples are required. "
            f"Currently available: {len(df)}."
        )

    if df["action"].nunique() < 2:
        raise ValueError(
            "At least two action classes are required."
        )

    return df


def validate_and_extract_training_record(outcome: LearningOutcome, db) -> dict | None:
    """
    Validates a LearningOutcome record against CWIP training data integrity rules.

    Mandatory Rules:
    1. Exclude test records (is_test == True).
    2. Require canonical action labels and valid outcome labels.
    3. Require a non-null recommendation_session_id.
    4. Verify linked RecommendationSession exists and belongs to outcome.user_id.
    5. Verify session.skill_id == outcome.skill_id and session.recommended_action == outcome.recommended_action.
    6. Authoritative snapshot is strictly session.feature_snapshot (never outcome.feature_snapshot).
    7. Provenance handling:
       - Case A (Version 2): session_snapshot has _metadata.schema_version == "2.0" and
         _metadata.provenance == "server_generated", with expected outcome concordance.
       - Case B (Historical flat): session_snapshot is a flat dictionary without _metadata from
         the verified owned session. Adapt via adapt_legacy_snapshot (provenance becomes "legacy_database").
       - All other shapes (including client-supplied legacy_database or unverified_client) are rejected.
    8. Numeric domain validation: all 10 features present, finite, integer activity_count >= 0,
       trend in {-1, 0, 1}, scores in [0, 100], mastery/confidence/consistency in [0, 1],
       avg_difficulty_weight > 0, error_rate >= 0.

    Returns structured record dictionary if eligible, or None if rejected.
    """
    if outcome.is_test:
        return None

    if (
        not is_valid_action(outcome.recommended_action)
        or not is_valid_action(outcome.actual_action)
        or outcome.outcome not in {"positive", "negative", "neutral"}
    ):
        return None

    # Rule 1: Mandatory non-null recommendation_session_id
    if outcome.recommendation_session_id is None:
        return None

    # Rule 2: Retrieve and verify session ownership and existence
    session = (
        db.query(RecommendationSession)
        .filter(
            RecommendationSession.id == outcome.recommendation_session_id,
            RecommendationSession.user_id == outcome.user_id
        )
        .first()
    )
    if not session:
        return None

    # Rule 3: Session skill and recommended action concordance
    if session.skill_id != outcome.skill_id:
        return None

    if session.recommended_action != outcome.recommended_action:
        return None

    # Rule 4: Authoritative server snapshot is strictly session.feature_snapshot
    session_snapshot = session.feature_snapshot
    if not isinstance(session_snapshot, dict) or not session_snapshot:
        return None

    # Rule 5: Provenance verification (Case A vs Case B)
    if "_metadata" in session_snapshot:
        meta = session_snapshot.get("_metadata")
        if not isinstance(meta, dict):
            return None

        # Case A: v2 server-generated snapshot
        if meta.get("schema_version") != "2.0" or meta.get("provenance") != "server_generated":
            return None

        expected_skill = session_snapshot.get("expected_outcome", {}).get("skill_id")
        if expected_skill is not None and outcome.skill_id != expected_skill:
            return None

        features = extract_numeric_features_from_snapshot(session_snapshot)
    else:
        # Case B: Historical flat snapshot directly from verified owned RecommendationSession
        adapted_snapshot = adapt_legacy_snapshot(session_snapshot, session=session)
        if adapted_snapshot.get("_metadata", {}).get("provenance") != "legacy_database":
            return None
        features = extract_numeric_features_from_snapshot(adapted_snapshot)

    # Rule 6: Complete numeric validation
    if (
        not isinstance(features, dict)
        or not REQUIRED_FEATURES.issubset(features.keys())
    ):
        return None

    try:
        numeric = {
            key: float(features[key])
            for key in REQUIRED_FEATURES
        }

        if not all(math.isfinite(v) for v in numeric.values()):
            return None

        if numeric["activity_count"] < 0:
            return None

        if not numeric["activity_count"].is_integer():
            return None

        if numeric["trend"] not in {-1, 0, 1}:
            return None

        if not all(
            0 <= numeric[key] <= 100
            for key in (
                "average_score",
                "recent_score",
                "adjusted_score"
            )
        ):
            return None

        if not (
            0 <= numeric["mastery"] <= 1
            and 0 <= numeric["confidence"] <= 1
            and 0 <= numeric["consistency"] <= 1
            and numeric["avg_difficulty_weight"] > 0
            and numeric["error_rate"] >= 0
        ):
            return None

    except (TypeError, ValueError, OverflowError):
        return None

    return {
        "features": {
            **numeric,
            "activity_count": int(numeric["activity_count"]),
            "trend": int(numeric["trend"]),
        },
        "recommended_action": outcome.recommended_action,
        "actual_action": outcome.actual_action,
        "mastery_change": outcome.mastery_change,
        "outcome": outcome.outcome
    }


def fetch_real_training_data(db, user_id):
    """Retrieve validated real outcomes for one user."""

    outcomes = (
        db.query(LearningOutcome)
        .filter(
            LearningOutcome.user_id == user_id,
            LearningOutcome.is_test.is_(False)
        )
        .order_by(LearningOutcome.id.asc())
        .all()
    )

    dataset = []

    for outcome in outcomes:
        record = validate_and_extract_training_record(outcome, db)
        if record is not None:
            dataset.append({
                **record,
                "is_synthetic": False
            })

    return dataset
