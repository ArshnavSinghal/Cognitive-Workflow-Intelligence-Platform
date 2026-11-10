import pytest
import math
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import ValidationError
from backend.app.main import app, get_current_user, calculate_feedback_loop_metrics
from backend.app.config import is_test_mode
from backend.app.schemas import ActivityCreate
from backend.app.models import (
    User,
    Skill,
    UserSkill,
    SkillDependency,
    Activity,
    RecommendationSession,
    LearningOutcome,
)
from backend.app.ml.real_training import validate_and_extract_training_record
from backend.app.ml.features import (
    build_v2_feature_snapshot,
    build_skill_features
)


def test_standalone_activity_creation(test_environment):
    """
    Standalone activities (without recommendation_session_id) update mastery
    and confidence, but do not create any LearningOutcome or alter sessions.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Enroll user
    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.50, confidence=0.40))
    db.commit()

    outcome_count_before = db.query(LearningOutcome).count()
    session_count_before = db.query(RecommendationSession).count()

    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 25,
            "difficulty": "medium",
            "score": 85.0,
            "errors": 1,
            "recommendation_session_id": None
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Activity recorded successfully"
    assert data["mastery_updated"] is True
    assert data["outcome_created"] is False
    assert "outcome_id" not in data

    # Verify database state
    assert db.query(LearningOutcome).count() == outcome_count_before
    assert db.query(RecommendationSession).count() == session_count_before

    # Verify user skill updated
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == regression.id
    ).one()
    assert user_skill.mastery > 0.50


def test_recommended_activity_creation_and_outcome_evaluation(test_environment):
    """
    An activity referencing an active recommendation session records the activity,
    recalculates mastery, marks session evaluated, and creates a LearningOutcome.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Enroll user
    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.50, confidence=0.50))
    db.commit()

    # Generate a real recommendation session
    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    session_id = rec_data.get("recommendation_session_id") or rec_data["recommendations"][0]["recommendation_session_id"]
    rec_item = rec_data["recommendations"][0]

    session_before = db.query(RecommendationSession).filter(RecommendationSession.id == session_id).one()
    assert session_before.status == "pending"

    # Use remediation skill topic if defined, else target_skill
    practice_topic = rec_item.get("remediation_skill") or rec_item["target_skill"]

    response = client.post(
        "/activities",
        json={
            "activity_type": rec_item["action_code"],
            "subject": "Machine Learning",
            "topic": practice_topic,
            "duration": 30,
            "difficulty": "medium",
            "score": 95.0,
            "errors": 0,
            "recommendation_session_id": session_id
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["outcome_created"] is True
    assert data["outcome_id"] is not None
    assert data["recommendation_session_id"] == session_id

    # Session status must be evaluated
    db.refresh(session_before)
    assert session_before.status == "evaluated"

    # Outcome record verification
    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id
    ).one()
    assert outcome.user_id == user.id
    assert outcome.skill_id == session_before.skill_id
    assert outcome.recommended_action == session_before.recommended_action
    assert outcome.actual_action == rec_item["action_code"]
    assert outcome.before_mastery == session_before.before_mastery
    assert outcome.after_mastery is not None
    assert outcome.feature_snapshot == session_before.feature_snapshot


def test_duplicate_activity_for_evaluated_session_rejected(test_environment):
    """
    Submitting another activity for an already evaluated session must return HTTP 400
    with detail 'Recommendation session already evaluated'.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.50, confidence=0.50))
    db.commit()

    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    rec_data = rec_resp.json()
    session_id = rec_data.get("recommendation_session_id") or rec_data["recommendations"][0]["recommendation_session_id"]
    rec_item = rec_data["recommendations"][0]
    practice_topic = rec_item.get("remediation_skill") or rec_item["target_skill"]

    # First submission -> succeeds
    resp1 = client.post(
        "/activities",
        json={
            "activity_type": rec_item["action_code"],
            "subject": "Machine Learning",
            "topic": practice_topic,
            "duration": 30,
            "difficulty": "medium",
            "score": 90.0,
            "errors": 1,
            "recommendation_session_id": session_id
        }
    )
    assert resp1.status_code == 200
    assert resp1.json()["outcome_created"] is True

    outcome_count = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id
    ).count()
    assert outcome_count == 1

    # Second submission with same session_id -> rejected
    resp2 = client.post(
        "/activities",
        json={
            "activity_type": rec_item["action_code"],
            "subject": "Machine Learning",
            "topic": practice_topic,
            "duration": 25,
            "difficulty": "medium",
            "score": 85.0,
            "errors": 2,
            "recommendation_session_id": session_id
        }
    )
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "Recommendation session already evaluated"

    # Outcome count must remain exactly 1
    assert db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id
    ).count() == 1


def test_activity_with_another_users_session_rejected(test_environment):
    """
    Submitting an activity referencing another learner's session must return HTTP 404
    'Recommendation session not found' to enforce learner isolation.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]

    # Session belongs to other_user
    foreign_session = RecommendationSession(
        user_id=other_user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.55,
        feature_snapshot={"mastery": 0.55},
        status="pending"
    )
    db.add(foreign_session)
    db.commit()

    # Authenticated user (user.id == 1) tries to complete foreign_session
    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 20,
            "difficulty": "medium",
            "score": 80.0,
            "errors": 1,
            "recommendation_session_id": foreign_session.id
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recommendation session not found"

    # Foreign session remains pending
    db.refresh(foreign_session)
    assert foreign_session.status == "pending"


def test_activity_with_mismatched_skill_rejected(test_environment):
    """
    Submitting an activity where topic does not match session skill returns HTTP 400
    'Session skill does not match activity skill'.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Session for Statistics
    session = RecommendationSession(
        user_id=user.id,
        skill_id=statistics.id,
        recommended_action="practice_current",
        before_mastery=0.45,
        feature_snapshot={"mastery": 0.45},
        status="pending"
    )
    db.add(session)
    db.commit()

    # Activity specifies topic = "Regression" (mismatched)
    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 20,
            "difficulty": "medium",
            "score": 80.0,
            "errors": 1,
            "recommendation_session_id": session.id
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Session skill does not match activity skill"

    db.refresh(session)
    assert session.status == "pending"


def test_activity_with_nonexistent_session_rejected(test_environment):
    """
    Submitting an activity with a non-existent session ID returns HTTP 404.
    """
    client = test_environment["client"]
    regression = test_environment["regression"]

    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 20,
            "difficulty": "medium",
            "score": 80.0,
            "errors": 1,
            "recommendation_session_id": 999999
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recommendation session not found"


def test_activity_validation_duration(test_environment):
    """Duration must be a finite integer > 0 and <= 1440."""
    client = test_environment["client"]
    regression = test_environment["regression"]

    # duration 0
    resp1 = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "Math", "topic": regression.name,
        "duration": 0, "difficulty": "medium", "score": 80
    })
    assert resp1.status_code == 422

    # duration negative
    resp2 = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "Math", "topic": regression.name,
        "duration": -15, "difficulty": "medium", "score": 80
    })
    assert resp2.status_code == 422

    # duration > 1440
    resp3 = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "Math", "topic": regression.name,
        "duration": 1500, "difficulty": "medium", "score": 80
    })
    assert resp3.status_code == 422


def test_activity_validation_score_range_and_non_finite():
    """
    Finding 5: Score must reject NaN, +Inf, -Inf, values < 0, values > 100,
    while allowing None and valid floats in [0, 100].
    """
    # 1. Reject NaN via Pydantic model
    with pytest.raises(ValidationError):
        ActivityCreate(
            activity_type="practice_current",
            subject="Math",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=float("nan")
        )

    # 2. Reject +Infinity
    with pytest.raises(ValidationError):
        ActivityCreate(
            activity_type="practice_current",
            subject="Math",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=float("inf")
        )

    # 3. Reject -Infinity
    with pytest.raises(ValidationError):
        ActivityCreate(
            activity_type="practice_current",
            subject="Math",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=float("-inf")
        )

    # 4. Reject < 0.0
    with pytest.raises(ValidationError):
        ActivityCreate(
            activity_type="practice_current",
            subject="Math",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=-1.0
        )

    # 5. Reject > 100.0
    with pytest.raises(ValidationError):
        ActivityCreate(
            activity_type="practice_current",
            subject="Math",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=100.1
        )

    # 6. Valid None
    act_none = ActivityCreate(
        activity_type="practice_current",
        subject="Math",
        topic="Regression",
        duration=20,
        difficulty="medium",
        score=None
    )
    assert act_none.score is None

    # 7. Valid boundary values
    act_0 = ActivityCreate(
        activity_type="practice_current",
        subject="Math",
        topic="Regression",
        duration=20,
        difficulty="medium",
        score=0.0
    )
    assert act_0.score == 0.0

    act_100 = ActivityCreate(
        activity_type="practice_current",
        subject="Math",
        topic="Regression",
        duration=20,
        difficulty="medium",
        score=100.0
    )
    assert act_100.score == 100.0


def test_activity_validation_errors(test_environment):
    """Errors cannot be negative."""
    client = test_environment["client"]
    regression = test_environment["regression"]

    resp = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "Math", "topic": regression.name,
        "duration": 20, "difficulty": "medium", "score": 80.0,
        "errors": -2
    })
    assert resp.status_code == 422


def test_activity_validation_difficulty(test_environment):
    """Difficulty must be one of 'easy', 'medium', 'hard' (case-insensitive)."""
    client = test_environment["client"]
    regression = test_environment["regression"]

    # invalid difficulty
    resp1 = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "Math", "topic": regression.name,
        "duration": 20, "difficulty": "super_hard", "score": 80.0
    })
    assert resp1.status_code == 422

    # valid with mixed case
    resp2 = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "Math", "topic": regression.name,
        "duration": 20, "difficulty": "Medium", "score": 80.0
    })
    assert resp2.status_code == 200


def test_prerequisite_recommendation_and_remediation_activity_completion(test_environment):
    """
    Finding 2: Prerequisite recommendation workflow.
    - Target: Regression (Skill 1). Weak prerequisite: Statistics (Skill 2).
    - Recommendation generated for Statistics (the remediation skill).
    - Top level returns target_skill='Regression' and remediation_skill='Statistics'.
    - Activity topic on remediation skill (Statistics) completes session and evaluates outcome.
    - Activity topic on target skill (Regression) is rejected due to session skill mismatch.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Graph: Statistics -> Regression (Statistics is prerequisite)
    db.add(SkillDependency(
        parent_skill_id=statistics.id,
        child_skill_id=regression.id,
        dependency_strength=1.0
    ))
    db.add_all([
        UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.75, confidence=0.80),
        UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.25, confidence=0.30),
    ])
    db.commit()

    # Request recommendation on Regression (target)
    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()

    assert rec_data["recommendation_status"] == "prerequisite_gap_detected"
    assert rec_data["target_skill"] == "Regression"
    assert rec_data["remediation_skill"] == "Statistics"
    assert rec_data["recommendation_session_id"] is not None

    session_id = rec_data["recommendation_session_id"]
    session = db.query(RecommendationSession).filter(RecommendationSession.id == session_id).one()
    assert session.skill_id == statistics.id
    assert session.recommended_action == "practice_prerequisite"

    # Attempting to submit activity with target skill (Regression) must fail skill concordance
    wrong_skill_resp = client.post("/activities", json={
        "activity_type": "practice_prerequisite",
        "subject": "Math",
        "topic": regression.name,
        "duration": 30,
        "difficulty": "medium",
        "score": 85.0,
        "errors": 1,
        "recommendation_session_id": session_id
    })
    assert wrong_skill_resp.status_code == 400
    assert wrong_skill_resp.json()["detail"] == "Session skill does not match activity skill"

    # Submitting activity with remediation skill (Statistics) succeeds
    correct_resp = client.post("/activities", json={
        "activity_type": "practice_prerequisite",
        "subject": "Math",
        "topic": statistics.name,
        "duration": 30,
        "difficulty": "medium",
        "score": 90.0,
        "errors": 0,
        "recommendation_session_id": session_id
    })
    assert correct_resp.status_code == 200
    assert correct_resp.json()["outcome_created"] is True

    # Outcome is attributed to Statistics
    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id
    ).one()
    assert outcome.skill_id == statistics.id
    assert outcome.actual_action == "practice_prerequisite"


def test_direct_recommendation_and_activity_completion(test_environment):
    """
    Finding 2: Direct recommendation workflow.
    - Requested target skill and remediation skill are identical.
    - Activity on target topic completes session.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.50, confidence=0.50))
    db.commit()

    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()

    assert rec_data["target_skill"] == "Regression"
    assert rec_data["remediation_skill"] == "Regression"
    session_id = rec_data["recommendation_session_id"]

    resp = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "ML",
        "topic": regression.name,
        "duration": 25,
        "difficulty": "medium",
        "score": 88.0,
        "errors": 1,
        "recommendation_session_id": session_id
    })
    assert resp.status_code == 200
    assert resp.json()["outcome_created"] is True


def test_intervening_standalone_activities_attribution(test_environment):
    """
    Finding 3: Mastery Change Attribution with intervening activities.
    - Recommendation generated at T0: session.before_mastery = 0.50.
    - Learner completes standalone activity at T1: updates UserSkill cumulative mastery.
    - Learner completes recommended activity at T2: completes session.
    - Verifies outcome.before_mastery is anchored to session.before_mastery,
      after_mastery incorporates the full sequence, and mastery formula is preserved.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.50, confidence=0.50))
    db.commit()

    # 1. Recommendation generated at T0
    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    session_id = rec_resp.json()["recommendation_session_id"]
    session = db.query(RecommendationSession).filter(RecommendationSession.id == session_id).one()
    baseline_before = session.before_mastery
    assert baseline_before == 0.50

    # 2. Intervening standalone activity at T1 (without session_id)
    sa_resp = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "ML",
        "topic": regression.name,
        "duration": 30,
        "difficulty": "hard",
        "score": 98.0,
        "errors": 0,
        "recommendation_session_id": None
    })
    assert sa_resp.status_code == 200
    assert sa_resp.json()["outcome_created"] is False

    # Cumulative user skill was updated
    user_skill_mid = db.query(UserSkill).filter(
        UserSkill.user_id == user.id, UserSkill.skill_id == regression.id
    ).one()
    assert user_skill_mid.mastery > 0.50

    # 3. Complete recommended activity at T2
    rec_act_resp = client.post("/activities", json={
        "activity_type": "practice_current",
        "subject": "ML",
        "topic": regression.name,
        "duration": 25,
        "difficulty": "medium",
        "score": 90.0,
        "errors": 1,
        "recommendation_session_id": session_id
    })
    assert rec_act_resp.status_code == 200
    assert rec_act_resp.json()["outcome_created"] is True

    # 4. Verify outcome attribution contract
    db.expire_all()
    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id
    ).one()
    user_skill_final = db.query(UserSkill).filter(
        UserSkill.user_id == user.id, UserSkill.skill_id == regression.id
    ).one()
    assert outcome.before_mastery == baseline_before
    assert outcome.after_mastery == user_skill_final.mastery
    assert outcome.mastery_change == round(outcome.after_mastery - baseline_before, 3)


def test_concurrent_duplicate_submission_safety_postgresql():
    """
    Finding 4: Concurrency Control & Duplicate Submission Safety on PostgreSQL.
    - Two simultaneous requests submit activities for the exact same session ID against PostgreSQL.
    - Verifies that PostgreSQL row-level locking (SELECT ... FOR UPDATE) serializes requests:
      exactly ONE request succeeds (HTTP 200) and ONE fails (HTTP 400 'Recommendation session already evaluated').
    - Database contains exactly 1 LearningOutcome for that session.
    - Session status is marked 'evaluated' and not left broken.
    """
    from sqlalchemy import text
    from backend.app.database import SessionLocal
    from backend.app.main import get_db
    from fastapi import Depends
    from starlette.testclient import TestClient

    # Check PostgreSQL connection
    try:
        probe = SessionLocal()
        probe.execute(text("SELECT 1"))
        probe.close()
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")

    # Set up test session in PostgreSQL
    db = SessionLocal()
    pg_user = db.query(User).first()
    pg_skill = db.query(Skill).first()
    user_id = pg_user.id
    skill_id = pg_skill.id
    skill_name = pg_skill.name

    pg_session = RecommendationSession(
        user_id=user_id,
        skill_id=skill_id,
        recommended_action="practice_current",
        before_mastery=0.50,
        feature_snapshot={"mastery": 0.50},
        status="pending"
    )
    db.add(pg_session)
    db.commit()
    db.refresh(pg_session)
    session_id = pg_session.id
    db.close()

    def override_user(db_session: Session = Depends(get_db)):
        return db_session.query(User).filter(User.id == user_id).first()

    app.dependency_overrides[get_current_user] = override_user

    payload = {
        "activity_type": "practice_current",
        "subject": "ML",
        "topic": skill_name,
        "duration": 20,
        "difficulty": "medium",
        "score": 85.0,
        "errors": 1,
        "recommendation_session_id": session_id
    }

    try:
        def submit_req():
            with TestClient(app) as test_client:
                return test_client.post("/activities", json=payload)

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(submit_req)
            f2 = executor.submit(submit_req)
            res1 = f1.result()
            res2 = f2.result()

        statuses = [res1.status_code, res2.status_code]
        assert 200 in statuses
        assert 400 in statuses

        failed_res = res1 if res1.status_code == 400 else res2
        assert failed_res.json()["detail"] == "Recommendation session already evaluated"

        # Verify exactly 1 outcome in PostgreSQL
        db_verify = SessionLocal()
        outcomes = db_verify.query(LearningOutcome).filter(
            LearningOutcome.recommendation_session_id == session_id
        ).all()
        assert len(outcomes) == 1

        db_session_record = db_verify.query(RecommendationSession).filter(
            RecommendationSession.id == session_id
        ).one()
        assert db_session_record.status == "evaluated"
        db_verify.close()

    finally:
        # Strict cleanup of temporary test data from PostgreSQL
        db_clean = SessionLocal()
        db_clean.query(LearningOutcome).filter(
            LearningOutcome.recommendation_session_id == session_id
        ).delete()
        db_clean.query(RecommendationSession).filter(
            RecommendationSession.id == session_id
        ).delete()
        db_clean.query(Activity).filter(
            Activity.user_id == user_id,
            Activity.duration == 20,
            Activity.score == 85.0
        ).delete()
        db_clean.commit()
        db_clean.close()
        app.dependency_overrides.clear()


def test_platform_analytics_authorization(test_environment):
    """
    Finding 1: Platform Analytics Authorization.
    - Ordinary learner JWT authentication requesting scope='platform' or scope='all' is rejected with HTTP 403.
    - Default learner-scoped request succeeds (HTTP 200).
    - Internal calculation engine returns platform-wide aggregation when user_id is None.
    """
    client = test_environment["client"]
    db = test_environment["db"]

    # 1. Learner scope (default) -> HTTP 200
    res_learner = client.get("/analytics/feedback-loop")
    assert res_learner.status_code == 200
    assert res_learner.json()["scope"] == "learner"

    # 2. Ordinary learner attempting scope='platform' -> HTTP 403 Forbidden
    res_platform = client.get("/analytics/feedback-loop?scope=platform")
    assert res_platform.status_code == 403
    assert "Platform-wide aggregation is restricted" in res_platform.json()["detail"]

    # 3. Ordinary learner attempting scope='all' -> HTTP 403 Forbidden
    res_all = client.get("/analytics/feedback-loop?scope=all")
    assert res_all.status_code == 403
    assert "Platform-wide aggregation is restricted" in res_all.json()["detail"]

    # 4. Internal direct calculation engine (trusted context) returns platform metrics
    internal_platform = calculate_feedback_loop_metrics(db=db, user_id=None)
    assert internal_platform["scope"] == "platform"
    assert "activities" in internal_platform
    assert "recommendation_sessions" in internal_platform


def test_real_outcome_validates_against_provenance_rules(test_environment, monkeypatch):
    """
    When CWIP_DATA_MODE is 'real', outcomes created via POST /activities
    are flagged is_test=False and satisfy validate_and_extract_training_record.
    """
    monkeypatch.setenv("CWIP_DATA_MODE", "real")
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Provide initial activity for valid feature extraction
    db.add(Activity(
        user_id=user.id,
        activity_type="practice_current",
        subject="ML",
        topic=regression.name,
        duration=30,
        difficulty="medium",
        score=75.0,
        errors=1
    ))
    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.60, confidence=0.70))
    db.commit()

    # Generate recommendation with v2 snapshot
    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    session_id = rec_data.get("recommendation_session_id") or rec_data["recommendations"][0]["recommendation_session_id"]
    rec_item = rec_data["recommendations"][0]
    practice_topic = rec_item.get("remediation_skill") or rec_item["target_skill"]

    # Submit activity completing recommendation
    act_resp = client.post("/activities", json={
        "activity_type": rec_item["action_code"],
        "subject": "ML",
        "topic": practice_topic,
        "duration": 30,
        "difficulty": "medium",
        "score": 90.0,
        "errors": 0,
        "recommendation_session_id": session_id
    })
    assert act_resp.status_code == 200

    # Outcome must be real
    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id
    ).one()
    assert outcome.is_test is False

    # Must pass training record validator
    record = validate_and_extract_training_record(outcome, db)
    assert record is not None
    assert record["recommended_action"] == rec_item["action_code"]
    assert record["actual_action"] == rec_item["action_code"]
    assert "features" in record
    assert len(record["features"]) == 10


def test_real_outcome_advances_evaluation_readiness(test_environment, monkeypatch):
    """
    Submitting a real learning outcome advances the eligible count in
    GET /ml/evaluation/readiness and GET /analytics/feedback-loop.
    """
    monkeypatch.setenv("CWIP_DATA_MODE", "real")
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Baseline readiness
    r_initial = client.get("/ml/evaluation/readiness?scope=learner").json()
    initial_eligible = r_initial["dataset_eligibility"]["eligible_count"]

    # Initial activity
    db.add(Activity(
        user_id=user.id,
        activity_type="practice_current",
        subject="ML",
        topic=regression.name,
        duration=30,
        difficulty="medium",
        score=75.0,
        errors=1
    ))
    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.60, confidence=0.70))
    db.commit()

    # Generate recommendation
    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    rec_data = rec_resp.json()
    session_id = rec_data.get("recommendation_session_id") or rec_data["recommendations"][0]["recommendation_session_id"]
    rec_item = rec_data["recommendations"][0]
    practice_topic = rec_item.get("remediation_skill") or rec_item["target_skill"]

    # Submit activity
    act_resp = client.post("/activities", json={
        "activity_type": rec_item["action_code"],
        "subject": "ML",
        "topic": practice_topic,
        "duration": 30,
        "difficulty": "medium",
        "score": 90.0,
        "errors": 0,
        "recommendation_session_id": session_id
    })
    assert act_resp.status_code == 200

    # Readiness after
    r_after = client.get("/ml/evaluation/readiness?scope=learner").json()
    after_eligible = r_after["dataset_eligibility"]["eligible_count"]
    assert after_eligible == initial_eligible + 1

    # Feedback loop reflects eligible count
    fb_data = client.get("/analytics/feedback-loop?scope=learner").json()
    assert fb_data["evaluation_readiness_progress"]["eligible_real_samples"] == after_eligible


def test_transactional_rollback_on_activity_failure(test_environment, monkeypatch):
    """
    If an unexpected error occurs during outcome creation or mastery calculation,
    the transaction is rolled back and no activity or outcome is persisted.
    """
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.50, confidence=0.50))
    db.commit()

    rec_resp = client.get(f"/skills/{regression.id}/recommendation")
    rec_data = rec_resp.json()
    session_id = rec_data.get("recommendation_session_id") or rec_data["recommendations"][0]["recommendation_session_id"]
    rec_item = rec_data["recommendations"][0]
    practice_topic = rec_item.get("remediation_skill") or rec_item["target_skill"]

    act_count_before = db.query(Activity).count()
    outcome_count_before = db.query(LearningOutcome).count()

    # Simulate an unexpected database error during commit
    from backend.app import main as app_main

    def failing_calc(acts):
        raise RuntimeError("Simulated calculation explosion")

    monkeypatch.setattr(app_main, "calculate_skill_metrics", failing_calc)

    with pytest.raises(RuntimeError, match="Simulated calculation explosion"):
        client.post("/activities", json={
            "activity_type": rec_item["action_code"],
            "subject": "ML",
            "topic": practice_topic,
            "duration": 30,
            "difficulty": "medium",
            "score": 90.0,
            "errors": 0,
            "recommendation_session_id": session_id
        })

    # Verify rollback: no new activity or outcome
    assert db.query(Activity).count() == act_count_before
    assert db.query(LearningOutcome).count() == outcome_count_before

    session = db.query(RecommendationSession).filter(RecommendationSession.id == session_id).one()
    assert session.status == "pending"
