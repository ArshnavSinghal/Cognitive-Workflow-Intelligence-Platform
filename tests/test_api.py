from backend.app.main import app, get_current_user
from backend.app.config import is_test_mode
from backend.app.models import (
    Activity,
    LearningOutcome,
    RecommendationSession,
    Skill,
    SkillDependency,
    UserSkill,
)


VALID_FEATURE_SNAPSHOT = {
    "average_score": 75.0,
    "recent_score": 80.0,
    "adjusted_score": 77.0,
    "avg_difficulty_weight": 1.0,
    "consistency": 0.9,
    "error_rate": 0.05,
    "mastery": 0.6,
    "confidence": 0.8,
    "activity_count": 5,
    "trend": 1,
}


def test_root_endpoint(test_environment):
    client = test_environment["client"]
    response = client.get("/")
    assert response.status_code == 200


def test_evaluated_session_is_rejected(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.70,
        feature_snapshot={"mastery": 0.70},
        status="evaluated"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    activity_count_before = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    outcome_count_before = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session.id
    ).count()

    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "medium",
            "score": 80,
            "errors": 2,
            "recommendation_session_id": session.id
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Recommendation session already evaluated"
    )

    activity_count_after = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    outcome_count_after = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session.id
    ).count()

    assert activity_count_after == activity_count_before
    assert outcome_count_after == outcome_count_before


def test_pending_session_creates_learning_outcome(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.50,
        feature_snapshot={"mastery": 0.50},
        status="pending"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = client.post(
        "/activities",
        json={
            "activity_type": "review_concept",
            "subject": "Machine Learning",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "medium",
            "score": 90,
            "errors": 1,
            "recommendation_session_id": session.id,
            "is_test": False
        }
    )

    assert response.status_code == 200
    assert response.json()["mastery_updated"] is True
    assert response.json()["outcome_created"] is True

    db.refresh(session)
    assert session.status == "evaluated"

    activity = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.topic == "Regression"
    ).first()
    assert activity is not None

    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session.id
    ).first()
    assert outcome is not None
    assert outcome.recommended_action == "practice_current"
    assert outcome.actual_action == "review_concept"
    assert outcome.is_test is True


def test_real_mode_creates_non_test_outcome_and_preserves_snapshot(
    test_environment, monkeypatch
):
    monkeypatch.setenv("CWIP_DATA_MODE", "real")

    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    original_snapshot = {
        "average_score": 75.0,
        "recent_score": 80.0,
        "adjusted_score": 77.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.9,
        "error_rate": 0.05,
        "mastery": 0.50,
        "confidence": 0.8,
        "activity_count": 5,
        "trend": 1,
    }

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.50,
        feature_snapshot=original_snapshot,
        status="pending",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "medium",
            "score": 90,
            "errors": 1,
            "recommendation_session_id": session.id,
        },
    )

    assert response.status_code == 200
    assert response.json()["outcome_created"] is True

    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session.id
    ).one()

    assert outcome.is_test is False
    assert outcome.feature_snapshot == original_snapshot
    assert outcome.recommended_action == "practice_current"

    db.refresh(session)
    assert session.status == "evaluated"


def test_nonexistent_session_is_rejected(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]

    before_count = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "medium",
            "score": 80,
            "errors": 2,
            "recommendation_session_id": 99999
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Recommendation session not found"
    )

    after_count = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    assert after_count == before_count


def test_other_users_session_is_rejected(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]
    user = test_environment["user"]

    session = RecommendationSession(
        user_id=other_user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.50,
        feature_snapshot={"mastery": 0.50},
        status="pending"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    before_count = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "medium",
            "score": 80,
            "errors": 2,
            "recommendation_session_id": session.id
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Recommendation session not found"
    )

    after_count = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    assert after_count == before_count


def test_session_skill_mismatch_is_rejected(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.50,
        feature_snapshot={"mastery": 0.50},
        status="pending"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    before_count = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Mathematics",
            "topic": "Statistics",
            "duration": 20,
            "difficulty": "medium",
            "score": 80,
            "errors": 2,
            "recommendation_session_id": session.id
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Session skill does not match activity skill"
    )

    after_count = db.query(Activity).filter(
        Activity.user_id == user.id
    ).count()

    assert after_count == before_count


def test_training_data_excludes_test_outcomes(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    test_outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.50,
        after_mastery=0.70,
        mastery_change=0.20,
        outcome="positive",
        is_test=True,
        feature_snapshot={"mastery": 0.50}
    )
    db.add(test_outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 0
    assert data["message"] == (
        "No eligible real training samples with valid snapshots."
    )


def test_training_data_includes_real_outcome_with_snapshot(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    snapshot = VALID_FEATURE_SNAPSHOT.copy()

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.50,
        feature_snapshot=snapshot,
        status="completed"
    )
    db.add(session)
    db.commit()

    real_outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.50,
        after_mastery=0.60,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        feature_snapshot=snapshot,
        recommendation_session_id=session.id
    )
    db.add(real_outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 1
    assert len(data["dataset"]) == 1
    assert data["dataset"][0]["features"] == snapshot
    assert data["dataset"][0]["outcome"] == "positive"
    assert data["dataset"][0]["mastery_change"] == 0.10


def test_training_data_uses_session_snapshot_fallback(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    snapshot = VALID_FEATURE_SNAPSHOT.copy()

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.60,
        feature_snapshot=snapshot,
        status="evaluated"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.60,
        after_mastery=0.65,
        mastery_change=0.05,
        outcome="positive",
        is_test=False,
        feature_snapshot=None,
        recommendation_session_id=session.id
    )
    db.add(outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 1
    assert data["dataset"][0]["features"] == snapshot
    assert data["skipped_missing_snapshot"] == 0


def test_training_data_skips_missing_snapshots(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.50,
        after_mastery=0.52,
        mastery_change=0.02,
        outcome="neutral",
        is_test=False,
        feature_snapshot=None,
        recommendation_session_id=None
    )
    db.add(outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1
    assert data["message"] == (
        "No eligible real training samples with valid snapshots."
    )


def test_training_data_skips_out_of_range_mastery(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    invalid_snapshot = {
        "average_score": 75.0,
        "recent_score": 80.0,
        "adjusted_score": 77.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.9,
        "error_rate": 0.05,
        "mastery": 1.5,
        "confidence": 0.8,
        "activity_count": 5,
        "trend": 1,
    }

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.5,
        after_mastery=0.6,
        mastery_change=0.1,
        outcome="positive",
        is_test=False,
        feature_snapshot=invalid_snapshot,
    )
    db.add(outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1


def test_training_data_skips_invalid_feature_values(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    invalid_snapshot = {
        "average_score": "unknown",
        "recent_score": 80.0,
        "adjusted_score": 77.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.9,
        "error_rate": 0.05,
        "mastery": 0.6,
        "confidence": 0.8,
        "activity_count": 5,
        "trend": 1,
    }

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.5,
        after_mastery=0.6,
        mastery_change=0.1,
        outcome="positive",
        is_test=False,
        feature_snapshot=invalid_snapshot,
    )
    db.add(outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1


def test_invalid_token_is_rejected(test_environment):
    client = test_environment["client"]

    app.dependency_overrides.pop(get_current_user, None)

    try:
        response = client.get(
            "/activities",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid token"
    finally:
        app.dependency_overrides[get_current_user] = (
            lambda: test_environment["user"]
        )


def test_missing_token_is_rejected(test_environment):
    client = test_environment["client"]

    app.dependency_overrides.pop(get_current_user, None)

    try:
        response = client.get("/activities")
        assert response.status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = (
            lambda: test_environment["user"]
        )


def test_recommendation_rejects_unknown_skill(test_environment):
    client = test_environment["client"]

    response = client.get("/skills/99999/recommendation")

    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"


def test_recommendation_requires_user_skill_data(test_environment):
    client = test_environment["client"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    db = test_environment["db"]

    # Ensure this user has no mastery record for Regression.
    db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == regression.id
    ).delete()
    db.commit()

    response = client.get(f"/skills/{regression.id}/recommendation")

    assert response.status_code == 404
    assert response.json()["detail"] == "User skill data not found"


def test_low_mastery_creates_rule_based_recommendation_session(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Avoid dependency on an installed ML model.
    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: None
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.40,
        confidence=0.50
    )
    db.add(user_skill)
    db.commit()

    response = client.get(f"/skills/{regression.id}/recommendation")

    assert response.status_code == 200

    data = response.json()
    assert data["target_skill"] == "Regression"
    assert data["recommendation_status"] == "skill_gap_detected"
    assert data["recommendation_source"] == "rule_based_fallback"
    assert data["recommendations"][0]["action_code"] == "practice_current"
    assert data["fallback_reason"] == (
        "The ML model is unavailable or returned no prediction."
    )

    session_id = data["recommendation_session_id"]
    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == session_id,
        RecommendationSession.user_id == user.id
    ).first()

    assert session is not None
    assert session.status == "pending"
    assert session.recommended_action == "practice_current"


def test_low_mastery_with_hard_practice_prediction(test_environment, monkeypatch):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: "hard_practice"
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.40,
        confidence=0.50
    )
    db.add(user_skill)
    db.add(Activity(
        user_id=user.id,
        activity_type="practice_current",
        subject="Machine Learning",
        topic=regression.name,
        duration=20,
        difficulty="medium",
        score=80,
        errors=2,
    ))
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/recommendation"
    )

    assert response.status_code == 200

    data = response.json()

    # Record the behavior of the current recommendation policy.
    assert data["recommendations"][0]["action_code"] == "hard_practice"
    assert data["recommendation_source"] == (
        "random_forest_synthetic_development_model"
    )


def test_very_low_mastery_blocks_hard_practice_prediction(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: "hard_practice"
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.30,
        confidence=0.50
    )
    db.add(user_skill)
    db.add(
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=40,
            errors=6
        )
    )
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/recommendation"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["recommendations"][0]["action_code"] != "hard_practice"


def test_mastery_at_safeguard_threshold_allows_hard_practice(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: "hard_practice"
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.40,
        confidence=0.50
    )
    db.add(user_skill)
    db.add(
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=40,
            errors=6
        )
    )
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/recommendation"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["recommendations"][0]["action_code"] == "hard_practice"
    assert data["recommendation_source"] == (
        "random_forest_synthetic_development_model"
    )


def test_safeguard_saves_overridden_action_in_session(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: "hard_practice"
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.30,
        confidence=0.50
    )
    db.add(user_skill)
    db.add(
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=40,
            errors=6
        )
    )
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/recommendation"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["recommendations"][0]["action_code"] == "practice_current"

    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == data["recommendation_session_id"],
        RecommendationSession.user_id == user.id
    ).one()

    assert session.status == "pending"
    assert session.recommended_action == "practice_current"


def test_safeguard_action_completes_learning_outcome_lifecycle(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: "hard_practice"
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.30,
        confidence=0.50
    )
    db.add(user_skill)
    db.add(
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=40,
            errors=6
        )
    )
    db.commit()

    recommendation_response = client.get(
        f"/skills/{regression.id}/recommendation"
    )
    assert recommendation_response.status_code == 200

    recommendation = recommendation_response.json()
    session_id = recommendation["recommendation_session_id"]
    assert recommendation["recommendations"][0]["action_code"] == (
        "practice_current"
    )

    activity_response = client.post(
        "/activities",
        json={
            "activity_type": "practice_current",
            "subject": "Machine Learning",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "medium",
            "score": 95,
            "errors": 0,
            "recommendation_session_id": session_id
        }
    )
    assert activity_response.status_code == 200
    assert activity_response.json()["outcome_created"] is True

    db.expire_all()

    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == session_id,
        RecommendationSession.user_id == user.id
    ).one()

    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id,
        LearningOutcome.user_id == user.id
    ).one()

    assert session.status == "evaluated"
    assert session.recommended_action == "practice_current"
    assert outcome.recommended_action == "practice_current"
    assert outcome.actual_action == "practice_current"
    assert outcome.mastery_change is not None


def test_unsupported_ml_action_uses_rule_based_fallback(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: "unsupported_action"
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.40,
        confidence=0.50
    )
    db.add(user_skill)
    db.commit()

    db.add(Activity(
        user_id=user.id,
        activity_type="practice_current",
        subject="Machine Learning",
        topic=regression.name,
        duration=20,
        difficulty="medium",
        score=80,
        errors=2,
    ))
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/recommendation"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["recommendation_source"] == "rule_based_fallback"
    assert data["recommendations"][0]["action_code"] == "practice_current"
    assert data["fallback_reason"] == (
        "The ML model returned an unsupported action: unsupported_action."
    )


def test_ml_prerequisite_prediction_uses_rule_based_fallback(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    from backend.app import main as main_module
    monkeypatch.setattr(
        main_module,
        "predict_action",
        lambda features: "practice_prerequisite"
    )

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.40,
        confidence=0.50
    )
    db.add(user_skill)
    db.add(Activity(
        user_id=user.id,
        activity_type="practice_current",
        subject="Machine Learning",
        topic=regression.name,
        duration=20,
        difficulty="medium",
        score=80,
        errors=2,
    ))
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/recommendation"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["recommendation_source"] == "rule_based_fallback"
    assert data["recommendation_status"] == "skill_gap_detected"
    assert data["recommendations"][0]["action_code"] == "practice_current"
    assert data["fallback_reason"] == (
        "The model predicted practice_prerequisite, "
        "but a valid prerequisite target was not selected."
    )

    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == data["recommendation_session_id"],
        RecommendationSession.user_id == user.id
    ).one()

    assert session.status == "pending"
    assert session.recommended_action == "practice_current"


def test_weak_prerequisite_triggers_recommendation(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Statistics depends on Regression.
    dependency = SkillDependency(
        parent_skill_id=regression.id,
        child_skill_id=statistics.id,
        dependency_strength=0.8
    )
    db.add_all([
        dependency,
        UserSkill(
            user_id=user.id,
            skill_id=statistics.id,
            mastery=0.75,
            confidence=0.8
        ),
        UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.30,
            confidence=0.5
        )
    ])
    db.commit()

    response = client.get(f"/skills/{statistics.id}/recommendation")

    assert response.status_code == 200

    data = response.json()
    assert data["recommendation_status"] == "prerequisite_gap_detected"

    recommendation = data["recommendations"][0]
    assert recommendation["action_code"] == "practice_prerequisite"
    assert recommendation["target_skill"] == "Regression"
    assert recommendation["mastery"] == 0.30
    assert recommendation["risk"] == 0.56


def test_strong_prerequisite_does_not_trigger_gap(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Statistics depends on Regression, but Regression is strong.
    dependency = SkillDependency(
        parent_skill_id=regression.id,
        child_skill_id=statistics.id,
        dependency_strength=0.8
    )
    db.add_all([
        dependency,
        UserSkill(
            user_id=user.id,
            skill_id=statistics.id,
            mastery=0.75,
            confidence=0.8
        ),
        UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.80,
            confidence=0.8
        )
    ])
    db.commit()

    response = client.get(f"/skills/{statistics.id}/recommendation")

    assert response.status_code == 200

    data = response.json()
    assert data["recommendation_status"] != "prerequisite_gap_detected"
    assert all(
        item["action_code"] != "practice_prerequisite"
        for item in data["recommendations"]
    )


def test_no_major_gap_creates_pending_recommendation_session(
    test_environment
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.80,
        confidence=0.90,
    )
    db.add(user_skill)
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/recommendation"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["recommendation_status"] == "no_major_gap"
    assert data["recommendation_source"] == "rule_based_fallback"
    assert data["recommendation_session_id"] is not None
    assert data["recommendations"][0]["action_code"] == "hard_practice"

    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == data["recommendation_session_id"],
        RecommendationSession.user_id == user.id,
    ).one()

    assert session.status == "pending"
    assert session.recommended_action == "hard_practice"
    assert session.skill_id == regression.id


def test_recommendation_activity_outcome_lifecycle(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # 1. Ensure the learner has sufficient mastery for hard practice.
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == regression.id,
    ).first()

    if user_skill:
        user_skill.mastery = 0.80
        user_skill.confidence = 0.90
    else:
        user_skill = UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.80,
            confidence=0.90,
        )
        db.add(user_skill)
    db.commit()

    # 2. Generate a recommendation.
    recommendation_response = client.get(
        f"/skills/{regression.id}/recommendation"
    )
    assert recommendation_response.status_code == 200

    recommendation = recommendation_response.json()
    session_id = recommendation["recommendation_session_id"]

    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == session_id,
        RecommendationSession.user_id == user.id,
    ).one()

    assert session.status == "pending"
    assert session.feature_snapshot is None or isinstance(
        session.feature_snapshot, dict
    )

    # 3. Record an activity linked to this recommendation.
    activity_response = client.post(
        "/activities",
        json={
            "activity_type": session.recommended_action,
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 20,
            "difficulty": "medium",
            "score": 95,
            "errors": 0,
            "recommendation_session_id": session_id,
        },
    )
    assert activity_response.status_code == 200
    assert activity_response.json()["outcome_created"] is True

    # 4. Verify the outcome and evaluated session.
    db.refresh(session)
    assert session.status == "evaluated"

    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id,
        LearningOutcome.user_id == user.id,
    ).one()

    assert outcome.is_test is True
    assert outcome.recommended_action == session.recommended_action
    assert outcome.feature_snapshot == session.feature_snapshot

    # 5. Test outcomes must not enter real training data.
    training_response = client.get("/ml/training-data")
    assert training_response.status_code == 200

    training_data = training_response.json()
    assert training_data["samples"] == 0
    assert training_data["dataset"] == []


def test_features_reject_unknown_skill(test_environment):
    client = test_environment["client"]

    response = client.get("/skills/99999/features")

    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"


def test_features_require_user_skill_data(test_environment):
    client = test_environment["client"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    db = test_environment["db"]

    db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == regression.id
    ).delete()
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/features"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "User skill data not found. Run /analysis first."
    )


def test_features_require_activities(test_environment):
    client = test_environment["client"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    db = test_environment["db"]

    db.add(
        UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.5,
            confidence=0.5
        )
    )
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/features"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No activities found for this skill"
    )


def test_features_require_scored_activities(test_environment):
    client = test_environment["client"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    db = test_environment["db"]

    db.add_all([
        UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.5,
            confidence=0.5
        ),
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=None,
            errors=1
        )
    ])
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/features"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "No scored activities available to build features"
    )


def test_features_returns_valid_structure(test_environment):
    client = test_environment["client"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    db = test_environment["db"]

    db.add_all([
        UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.7,
            confidence=0.8
        ),
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=85,
            errors=1
        )
    ])
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/features"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["skill"] == "Regression"
    assert isinstance(data["features"], dict)
    assert data["features"]


def test_skill_analysis_rejects_unknown_skill(test_environment):
    client = test_environment["client"]

    response = client.get("/skills/99999/analysis")

    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"


def test_skill_analysis_requires_activities(test_environment):
    client = test_environment["client"]
    regression = test_environment["regression"]

    response = client.get(
        f"/skills/{regression.id}/analysis"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No activities found for this skill"
    )


def test_skill_analysis_requires_scored_activities(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add(
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=None,
            errors=1
        )
    )
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/analysis"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "No scored activities available"
    )


def test_skill_analysis_calculates_metrics_and_saves_mastery(
    test_environment
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=80,
            errors=2
        ),
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=25,
            difficulty="medium",
            score=90,
            errors=1
        )
    ])
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/analysis"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["skill"] == "Regression"
    assert data["activities_analyzed"] == 2
    assert data["average_score"] == 85.0
    assert data["recent_average"] == 85.0
    assert 0 <= data["mastery"] <= 1
    assert 0 <= data["confidence"] <= 1

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == regression.id
    ).first()

    assert user_skill is not None
    assert user_skill.mastery == data["mastery"]
    assert user_skill.confidence == data["confidence"]


def test_unscored_activity_does_not_inflate_confidence(
    test_environment
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=80,
            errors=2
        ),
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="Machine Learning",
            topic="Regression",
            duration=20,
            difficulty="medium",
            score=None,
            errors=0
        )
    ])
    db.commit()

    response = client.get(
        f"/skills/{regression.id}/analysis"
    )

    assert response.status_code == 200

    data = response.json()

    # Only one activity has a score.
    assert data["activities_analyzed"] == 2
    assert data["average_score"] == 80.0

    # Confidence should be based on scored activities,
    # not the total number of activity records.
    expected_confidence = min(
        1,
        (1 / 5) * 0.6 + data["consistency"] * 0.4
    )

    assert data["confidence"] == round(expected_confidence, 3)


def test_training_data_skips_real_outcome_without_snapshot(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.60,
        after_mastery=0.65,
        mastery_change=0.05,
        outcome="neutral",
        is_test=False,
        feature_snapshot=None,
    )
    db.add(outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1


def test_training_data_skips_incomplete_feature_snapshot(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        feature_snapshot={
            "mastery": 0.70
        },
    )
    db.add(outcome)
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1


def test_data_mode_is_controlled_by_server_configuration(monkeypatch):
    monkeypatch.setenv("CWIP_DATA_MODE", "development")
    assert is_test_mode() is True

    monkeypatch.setenv("CWIP_DATA_MODE", "real")
    assert is_test_mode() is False


def test_prerequisite_recommendation_activity_lifecycle(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Statistics depends on Regression.
    db.add(
        SkillDependency(
            parent_skill_id=regression.id,
            child_skill_id=statistics.id,
            dependency_strength=0.8,
        )
    )
    db.add_all([
        UserSkill(
            user_id=user.id,
            skill_id=statistics.id,
            mastery=0.75,
            confidence=0.80,
        ),
        UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.30,
            confidence=0.40,
        ),
    ])
    db.commit()

    # 1. Request a recommendation for Statistics.
    response = client.get(
        f"/skills/{statistics.id}/recommendation"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["recommendation_status"] == "prerequisite_gap_detected"

    recommendation = next(
        item for item in data["recommendations"]
        if item["target_skill"] == regression.name
    )
    session_id = recommendation["recommendation_session_id"]

    # 2. Verify that the session tracks Regression.
    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == session_id,
        RecommendationSession.user_id == user.id,
    ).one()

    assert session.skill_id == regression.id
    assert session.recommended_action == "practice_prerequisite"
    assert session.status == "pending"

    # 3. Record an activity for the prerequisite skill.
    activity_response = client.post(
        "/activities",
        json={
            "activity_type": "practice_prerequisite",
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 20,
            "difficulty": "medium",
            "score": 95,
            "errors": 0,
            "recommendation_session_id": session_id,
        },
    )
    assert activity_response.status_code == 200
    assert activity_response.json()["outcome_created"] is True

    # 4. Verify the session and linked outcome.
    db.refresh(session)
    assert session.status == "evaluated"

    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session_id,
        LearningOutcome.user_id == user.id,
    ).one()

    assert outcome.skill_id == regression.id
    assert outcome.recommended_action == "practice_prerequisite"
    assert outcome.is_test is True


def test_training_data_normalizes_numeric_feature_values(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    snapshot = {
        "average_score": "80.0",
        "recent_score": "85.0",
        "adjusted_score": "82.0",
        "avg_difficulty_weight": "1.0",
        "consistency": "0.9",
        "error_rate": "0.1",
        "mastery": "0.7",
        "confidence": "0.8",
        "activity_count": "5",
        "trend": "1",
    }

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.6,
        feature_snapshot=snapshot,
        status="completed"
    )
    db.add(session)
    db.commit()

    db.add(
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.6,
            after_mastery=0.7,
            mastery_change=0.1,
            outcome="positive",
            is_test=False,
            feature_snapshot=snapshot,
            recommendation_session_id=session.id
        )
    )
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 1

    features = data["dataset"][0]["features"]

    assert features["average_score"] == 80.0
    assert isinstance(features["average_score"], (int, float))

    assert features["activity_count"] == 5
    assert isinstance(features["activity_count"], int)

    assert features["trend"] == 1
    assert isinstance(features["trend"], int)


def test_training_data_skips_non_finite_feature_values(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # float("nan") is not valid JSON, so store it as the string "nan".
    # The endpoint calls float() on each value before math.isfinite(),
    # so float("nan") → NaN → isfinite() returns False → record is skipped.
    snapshot = {
        "average_score": "nan",
        "recent_score": 85.0,
        "adjusted_score": 82.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.9,
        "error_rate": 0.1,
        "mastery": 0.7,
        "confidence": 0.8,
        "activity_count": 5,
        "trend": 1,
    }

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.6,
        feature_snapshot=snapshot,
        status="completed"
    )
    db.add(session)
    db.commit()

    db.add(
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.6,
            after_mastery=0.7,
            mastery_change=0.1,
            outcome="positive",
            is_test=False,
            feature_snapshot=snapshot,
            recommendation_session_id=session.id
        )
    )
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1


def test_training_data_skips_invalid_action_labels(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    snapshot = {
        "average_score": 80.0,
        "recent_score": 85.0,
        "adjusted_score": 82.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.9,
        "error_rate": 0.1,
        "mastery": 0.7,
        "confidence": 0.8,
        "activity_count": 5,
        "trend": 1,
    }

    db.add(
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="invalid_action",
            actual_action="practice_current",
            before_mastery=0.6,
            after_mastery=0.7,
            mastery_change=0.1,
            outcome="positive",
            is_test=False,
            feature_snapshot=snapshot,
        )
    )
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1


def test_training_data_skips_invalid_outcome_label(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    snapshot = {
        "average_score": 80.0,
        "recent_score": 85.0,
        "adjusted_score": 82.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.9,
        "error_rate": 0.1,
        "mastery": 0.7,
        "confidence": 0.8,
        "activity_count": 5,
        "trend": 1,
    }

    db.add(
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.6,
            after_mastery=0.7,
            mastery_change=0.1,
            outcome="unknown",
            is_test=False,
            feature_snapshot=snapshot,
        )
    )
    db.commit()

    response = client.get("/ml/training-data")

    assert response.status_code == 200

    data = response.json()
    assert data["samples"] == 0
    assert data["dataset"] == []
    assert data["skipped_missing_snapshot"] == 1


def test_invalid_activity_action_is_rejected(test_environment):
    client = test_environment["client"]

    response = client.post(
        "/activities",
        json={
            "activity_type": "watch_video",
            "subject": "Machine Learning",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "medium",
            "score": 80,
            "errors": 2
        }
    )

    assert response.status_code == 422


def test_adherence_metrics_with_zero_real_outcomes(test_environment):
    client = test_environment["client"]
    response = client.get("/learning-outcomes")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["total_real_evaluated"] == 0
    assert data["recommendations_followed"] == 0
    assert data["recommendations_not_followed"] == 0
    assert data["adherence_rate"] == 0
    assert data["outcomes"] == []


def test_adherence_metrics_with_all_recommendations_followed(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.55,
            mastery_change=0.05,
            outcome="positive",
            is_test=False,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="hard_practice",
            before_mastery=0.70,
            after_mastery=0.72,
            mastery_change=0.02,
            outcome="neutral",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/learning-outcomes")
    assert response.status_code == 200
    data = response.json()
    assert data["total_real_evaluated"] == 2
    assert data["recommendations_followed"] == 2
    assert data["recommendations_not_followed"] == 0
    assert data["adherence_rate"] == 100.0


def test_adherence_metrics_with_mixed_outcomes(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.55,
            mastery_change=0.05,
            outcome="positive",
            is_test=False,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="review_concept",
            before_mastery=0.70,
            after_mastery=0.71,
            mastery_change=0.01,
            outcome="neutral",
            is_test=False,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="easy_practice",
            actual_action="easy_practice",
            before_mastery=0.40,
            after_mastery=0.48,
            mastery_change=0.08,
            outcome="positive",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/learning-outcomes")
    assert response.status_code == 200
    data = response.json()
    assert data["total_real_evaluated"] == 3
    assert data["recommendations_followed"] == 2
    assert data["recommendations_not_followed"] == 1
    assert data["adherence_rate"] == 66.67


def test_adherence_metrics_excludes_test_outcomes(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.55,
            mastery_change=0.05,
            outcome="positive",
            is_test=True,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="hard_practice",
            before_mastery=0.70,
            after_mastery=0.72,
            mastery_change=0.02,
            outcome="neutral",
            is_test=True,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="review_concept",
            before_mastery=0.50,
            after_mastery=0.52,
            mastery_change=0.02,
            outcome="neutral",
            is_test=False,
        ),
    ])
    db.commit()

    response_test = client.get("/learning-outcomes?is_test=true")
    assert response_test.status_code == 200
    data_test = response_test.json()
    assert data_test["total"] == 2
    assert data_test["total_real_evaluated"] == 1
    assert data_test["recommendations_followed"] == 0
    assert data_test["recommendations_not_followed"] == 1
    assert data_test["adherence_rate"] == 0.0

    response_all = client.get("/learning-outcomes")
    assert response_all.status_code == 200
    data_all = response_all.json()
    assert data_all["total"] == 3
    assert data_all["total_real_evaluated"] == 1
    assert data_all["recommendations_followed"] == 0
    assert data_all["recommendations_not_followed"] == 1
    assert data_all["adherence_rate"] == 0.0


def test_adherence_metrics_user_isolation(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]

    db.add_all([
        LearningOutcome(
            user_id=other_user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.55,
            mastery_change=0.05,
            outcome="positive",
            is_test=False,
        ),
        LearningOutcome(
            user_id=other_user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="hard_practice",
            before_mastery=0.70,
            after_mastery=0.72,
            mastery_change=0.02,
            outcome="neutral",
            is_test=False,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="review_concept",
            before_mastery=0.50,
            after_mastery=0.52,
            mastery_change=0.02,
            outcome="neutral",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/learning-outcomes")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["total_real_evaluated"] == 1
    assert data["recommendations_followed"] == 0
    assert data["recommendations_not_followed"] == 1
    assert data["adherence_rate"] == 0.0


def test_full_recommendation_activity_adherence_lifecycle(
    test_environment, monkeypatch
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Ensure real mode so outcomes are evaluated as real (non-test)
    monkeypatch.setenv("CWIP_DATA_MODE", "real")

    # Step 1: Initial state - 0 real evaluated outcomes, 0% adherence
    init_res = client.get("/learning-outcomes")
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["total_real_evaluated"] == 0
    assert init_data["recommendations_followed"] == 0
    assert init_data["recommendations_not_followed"] == 0
    assert init_data["adherence_rate"] == 0

    # Step 2: Establish UserSkill and prior activities to enable feature extraction
    user_skill = UserSkill(
        user_id=user.id,
        skill_id=regression.id,
        mastery=0.75,
        confidence=0.8,
    )
    prior_activity = Activity(
        user_id=user.id,
        activity_type="practice_current",
        subject="Mathematics",
        topic="Regression",
        duration=25,
        difficulty="medium",
        score=85.0,
        errors=1,
    )
    db.add_all([user_skill, prior_activity])
    db.commit()

    # Step 3: Generate Recommendation -> creates pending RecommendationSession
    rec_res = client.get(f"/skills/{regression.id}/recommendation")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    session_id = rec_data.get("recommendation_session_id")
    assert session_id is not None
    rec_action = rec_data["recommendations"][0]["action_code"]

    # Step 4: Submit Activity matching recommended action (Followed)
    act_res1 = client.post(
        "/activities",
        json={
            "activity_type": rec_action,
            "subject": "Mathematics",
            "topic": "Regression",
            "duration": 30,
            "difficulty": "medium",
            "score": 90.0,
            "errors": 0,
            "recommendation_session_id": session_id,
        },
    )
    assert act_res1.status_code == 200
    act_data1 = act_res1.json()
    assert act_data1["mastery_updated"] is True
    assert act_data1["outcome_created"] is True

    # Step 5: Dashboard refresh - adherence should now be 100% (1/1 followed)
    dash_res1 = client.get("/learning-outcomes")
    assert dash_res1.status_code == 200
    dash_data1 = dash_res1.json()
    assert dash_data1["total_real_evaluated"] == 1
    assert dash_data1["recommendations_followed"] == 1
    assert dash_data1["recommendations_not_followed"] == 0
    assert dash_data1["adherence_rate"] == 100.0

    # Step 6: Generate second recommendation
    rec_res2 = client.get(f"/skills/{regression.id}/recommendation")
    assert rec_res2.status_code == 200
    rec_data2 = rec_res2.json()
    session_id2 = rec_data2.get("recommendation_session_id")
    rec_action2 = rec_data2["recommendations"][0]["action_code"]

    # Learner reports a DIFFERENT action (Not Followed)
    different_action = (
        "review_concept" if rec_action2 != "review_concept" else "easy_practice"
    )
    act_res2 = client.post(
        "/activities",
        json={
            "activity_type": different_action,
            "subject": "Mathematics",
            "topic": "Regression",
            "duration": 20,
            "difficulty": "easy",
            "score": 80.0,
            "errors": 2,
            "recommendation_session_id": session_id2,
        },
    )
    assert act_res2.status_code == 200
    assert act_res2.json()["outcome_created"] is True

    # Step 7: Dashboard refresh - adherence should now be 50.0% (1/2 followed, 1 not followed)
    dash_res2 = client.get("/learning-outcomes")
    assert dash_res2.status_code == 200
    dash_data2 = dash_res2.json()
    assert dash_data2["total_real_evaluated"] == 2
    assert dash_data2["recommendations_followed"] == 1
    assert dash_data2["recommendations_not_followed"] == 1
    assert dash_data2["adherence_rate"] == 50.0


def test_effectiveness_analytics_empty_outcomes(test_environment):
    client = test_environment["client"]

    response = client.get("/analytics/effectiveness")
    assert response.status_code == 200
    data = response.json()

    assert data["total_real_evaluated"] == 0
    assert data["average_mastery_change"] == 0.0
    assert data["positive_outcomes"] == 0
    assert data["neutral_outcomes"] == 0
    assert data["negative_outcomes"] == 0
    assert data["by_skill"] == []
    assert data["by_recommended_action"] == []
    assert data["by_actual_action"] == []
    assert data["comparison_by_adherence"]["followed"]["sample_count"] == 0
    assert data["comparison_by_adherence"]["not_followed"]["sample_count"] == 0
    assert "observational_caveat" in data


def test_effectiveness_analytics_positive_negative_neutral_outcomes(
    test_environment
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.58,
            mastery_change=0.08,
            outcome="positive",
            is_test=False,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.58,
            after_mastery=0.59,
            mastery_change=0.01,
            outcome="neutral",
            is_test=False,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="hard_practice",
            before_mastery=0.59,
            after_mastery=0.53,
            mastery_change=-0.06,
            outcome="negative",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/analytics/effectiveness")
    assert response.status_code == 200
    data = response.json()

    assert data["total_real_evaluated"] == 3
    assert data["positive_outcomes"] == 1
    assert data["neutral_outcomes"] == 1
    assert data["negative_outcomes"] == 1
    assert data["average_mastery_change"] == 0.01


def test_effectiveness_analytics_multiple_skills_and_actions(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    db.add_all([
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.56,
            mastery_change=0.06,
            outcome="positive",
            is_test=False,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=statistics.id,
            recommended_action="hard_practice",
            actual_action="review_concept",
            before_mastery=0.70,
            after_mastery=0.72,
            mastery_change=0.02,
            outcome="neutral",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/analytics/effectiveness")
    assert response.status_code == 200
    data = response.json()

    assert data["total_real_evaluated"] == 2
    assert len(data["by_skill"]) == 2

    skill_names = {item["skill_name"] for item in data["by_skill"]}
    assert "Regression" in skill_names
    assert "Statistics" in skill_names

    # Test filtering by skill_id
    filtered_res = client.get(f"/analytics/effectiveness?skill_id={regression.id}")
    assert filtered_res.status_code == 200
    filtered_data = filtered_res.json()
    assert filtered_data["total_real_evaluated"] == 1
    assert len(filtered_data["by_skill"]) == 1
    assert filtered_data["by_skill"][0]["skill_name"] == "Regression"
    assert filtered_data["average_mastery_change"] == 0.06


def test_effectiveness_analytics_followed_vs_non_followed_comparison(
    test_environment
):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        # Followed: rec == act (change: +0.06)
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.56,
            mastery_change=0.06,
            outcome="positive",
            is_test=False,
        ),
        # Followed: rec == act (change: +0.04)
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="hard_practice",
            before_mastery=0.70,
            after_mastery=0.74,
            mastery_change=0.04,
            outcome="neutral",
            is_test=False,
        ),
        # Not Followed: rec != act (change: -0.02)
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="review_concept",
            before_mastery=0.74,
            after_mastery=0.72,
            mastery_change=-0.02,
            outcome="neutral",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/analytics/effectiveness")
    assert response.status_code == 200
    data = response.json()

    followed = data["comparison_by_adherence"]["followed"]
    not_followed = data["comparison_by_adherence"]["not_followed"]

    assert followed["sample_count"] == 2
    assert followed["average_mastery_change"] == 0.05
    assert followed["positive_count"] == 1
    assert followed["neutral_count"] == 1
    assert followed["negative_count"] == 0

    assert not_followed["sample_count"] == 1
    assert not_followed["average_mastery_change"] == -0.02
    assert not_followed["positive_count"] == 0
    assert not_followed["neutral_count"] == 1
    assert not_followed["negative_count"] == 0


def test_effectiveness_analytics_excludes_test_outcomes(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add_all([
        # Synthetic/Test outcomes with inflated mastery changes
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.70,
            mastery_change=0.20,
            outcome="positive",
            is_test=True,
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="hard_practice",
            before_mastery=0.70,
            after_mastery=0.85,
            mastery_change=0.15,
            outcome="positive",
            is_test=True,
        ),
        # Only 1 real outcome
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.52,
            mastery_change=0.02,
            outcome="neutral",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/analytics/effectiveness")
    assert response.status_code == 200
    data = response.json()

    assert data["total_real_evaluated"] == 1
    assert data["average_mastery_change"] == 0.02
    assert data["positive_outcomes"] == 0
    assert data["neutral_outcomes"] == 1


def test_effectiveness_analytics_user_isolation(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]

    # other_user has 3 positive outcomes
    db.add_all([
        LearningOutcome(
            user_id=other_user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.60,
            mastery_change=0.10,
            outcome="positive",
            is_test=False,
        ),
        # current user has 1 negative outcome
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.44,
            mastery_change=-0.06,
            outcome="negative",
            is_test=False,
        ),
    ])
    db.commit()

    response = client.get("/analytics/effectiveness")
    assert response.status_code == 200
    data = response.json()

    assert data["total_real_evaluated"] == 1
    assert data["average_mastery_change"] == -0.06
    assert data["positive_outcomes"] == 0
    assert data["negative_outcomes"] == 1


def test_effectiveness_analytics_handles_missing_session_id(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    db.add(
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",
            before_mastery=0.50,
            after_mastery=0.55,
            mastery_change=0.05,
            outcome="positive",
            is_test=False,
            recommendation_session_id=None,
        )
    )
    db.commit()

    response = client.get("/analytics/effectiveness")
    assert response.status_code == 200
    data = response.json()

    assert data["total_real_evaluated"] == 1
    assert data["average_mastery_change"] == 0.05
    assert data["positive_outcomes"] == 1


# ============================================================================
# PHASE 3: Dynamic Skill Catalogue & Profile Endpoints Tests
# ============================================================================

def test_skills_catalogue_retrieval(test_environment):
    client = test_environment["client"]

    response = client.get("/skills")
    assert response.status_code == 200
    data = response.json()

    assert "skills" in data
    assert data["total"] >= 2
    skill_names = [s["name"] for s in data["skills"]]
    assert "Regression" in skill_names
    assert "Statistics" in skill_names

    regression_entry = next(s for s in data["skills"] if s["name"] == "Regression")
    assert "id" in regression_entry
    assert "category" in regression_entry
    assert "description" in regression_entry
    assert "is_enrolled" in regression_entry


def test_individual_skill_retrieval(test_environment):
    client = test_environment["client"]
    regression = test_environment["regression"]

    response = client.get(f"/skills/{regression.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == regression.id
    assert data["name"] == "Regression"
    assert data["category"] == "Machine Learning"


def test_skill_retrieval_unknown_id(test_environment):
    client = test_environment["client"]

    response = client.get("/skills/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"


def test_skill_enrollment_success(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    statistics = test_environment["statistics"]

    response = client.post(f"/skills/{statistics.id}/enroll")
    assert response.status_code == 200
    data = response.json()

    assert data["is_enrolled"] is True
    assert data["skill_id"] == statistics.id
    assert "Successfully enrolled" in data["message"]

    # Verify database persistence
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == statistics.id
    ).first()
    assert user_skill is not None
    assert user_skill.mastery == 0.0
    assert user_skill.confidence == 0.0


def test_skill_duplicate_enrollment_rejected(test_environment):
    client = test_environment["client"]
    statistics = test_environment["statistics"]

    # Initial enrollment
    res1 = client.post(f"/skills/{statistics.id}/enroll")
    assert res1.status_code == 200

    # Duplicate enrollment attempt
    res2 = client.post(f"/skills/{statistics.id}/enroll")
    assert res2.status_code == 400
    assert "already enrolled" in res2.json()["detail"]


def test_skill_enrollment_unknown_id(test_environment):
    client = test_environment["client"]

    response = client.post("/skills/9999/enroll")
    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"


def test_skill_profile_empty_learner(test_environment):
    client = test_environment["client"]
    statistics = test_environment["statistics"]

    # Enroll in statistics without activities
    client.post(f"/skills/{statistics.id}/enroll")

    response = client.get(f"/skills/{statistics.id}/profile")
    assert response.status_code == 200
    data = response.json()

    assert data["skill_id"] == statistics.id
    assert data["name"] == "Statistics"
    assert data["is_enrolled"] is True
    assert data["mastery"] == 0.0
    assert data["confidence"] == 0.0
    assert data["trend"] == "insufficient_data"
    assert data["total_activities"] == 0
    assert data["recent_activity"] is None
    assert data["total_real_evaluated"] == 0
    assert data["positive_outcomes"] == 0
    assert data["average_mastery_change"] is None  # Must not fabricate 0.0
    assert data["adherence"] is None  # Must not fabricate 0.0% adherence


def test_skill_profile_populated_metrics(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Ensure enrolled
    db.add(
        UserSkill(
            user_id=user.id,
            skill_id=regression.id,
            mastery=0.75,
            confidence=0.80
        )
    )

    # Add 2 activities
    db.add_all([
        Activity(
            user_id=user.id,
            activity_type="practice_current",
            subject="ML",
            topic="Regression",
            duration=30,
            difficulty="medium",
            score=80.0,
            errors=2
        ),
        Activity(
            user_id=user.id,
            activity_type="hard_practice",
            subject="ML",
            topic="Regression",
            duration=45,
            difficulty="hard",
            score=90.0,
            errors=1
        ),
    ])

    # Add 2 real outcomes
    db.add_all([
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="practice_current",
            actual_action="practice_current",  # Followed
            before_mastery=0.69,
            after_mastery=0.75,
            mastery_change=0.06,
            outcome="positive",
            is_test=False
        ),
        LearningOutcome(
            user_id=user.id,
            skill_id=regression.id,
            recommended_action="hard_practice",
            actual_action="review_concept",  # Not followed
            before_mastery=0.75,
            after_mastery=0.77,
            mastery_change=0.02,
            outcome="neutral",
            is_test=False
        ),
    ])
    db.commit()

    response = client.get(f"/skills/{regression.id}/profile")
    assert response.status_code == 200
    data = response.json()

    assert data["is_enrolled"] is True
    assert data["mastery"] == 0.75
    assert data["total_activities"] == 2
    assert data["recent_activity"]["score"] == 90.0
    assert data["total_real_evaluated"] == 2
    assert data["positive_outcomes"] == 1
    assert data["neutral_outcomes"] == 1
    assert data["negative_outcomes"] == 0
    assert data["average_mastery_change"] == 0.04
    assert data["adherence"]["recommendations_followed"] == 1
    assert data["adherence"]["recommendations_not_followed"] == 1
    assert data["adherence"]["adherence_rate"] == 50.0


def test_skill_profile_user_isolation(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]

    # other_user has 10 activities and high mastery
    db.add(
        UserSkill(
            user_id=other_user.id,
            skill_id=regression.id,
            mastery=0.99,
            confidence=0.95
        )
    )
    db.add(
        Activity(
            user_id=other_user.id,
            activity_type="practice_current",
            subject="ML",
            topic="Regression",
            duration=30,
            difficulty="hard",
            score=100.0,
            errors=0
        )
    )
    # current user has no enrollment or activities for regression
    db.commit()

    response = client.get(f"/skills/{regression.id}/profile")
    assert response.status_code == 200
    data = response.json()

    # Current user must not see other_user's data
    assert data["is_enrolled"] is False
    assert data["mastery"] is None
    assert data["total_activities"] == 0
    assert data["recent_activity"] is None


def test_skill_profile_unknown_id(test_environment):
    client = test_environment["client"]

    response = client.get("/skills/9999/profile")
    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"


def test_skill_profile_and_enroll_require_auth(test_environment):
    client = test_environment["client"]
    regression = test_environment["regression"]

    # Temporarily remove override
    app.dependency_overrides.pop(get_current_user, None)

    try:
        res_profile = client.get(f"/skills/{regression.id}/profile")
        assert res_profile.status_code == 403
        assert res_profile.json()["detail"] == "Not authenticated"

        res_enroll = client.post(f"/skills/{regression.id}/enroll")
        assert res_enroll.status_code == 403
        assert res_enroll.json()["detail"] == "Not authenticated"
    finally:
        app.dependency_overrides[get_current_user] = (
            lambda: test_environment["user"]
        )


def test_skill_creation_forbidden_for_learners(test_environment):
    client = test_environment["client"]

    response = client.post(
        "/skills",
        json={"name": "Deep Learning", "category": "AI"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Global skill creation is disabled. Administrative privileges required."
    )


def test_skill_creation_unauthenticated_forbidden(test_environment):
    client = test_environment["client"]

    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.post(
            "/skills",
            json={"name": "Deep Learning", "category": "AI"}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"
    finally:
        app.dependency_overrides[get_current_user] = (
            lambda: test_environment["user"]
        )


def test_skill_create_schema_validation():
    import pytest
    from pydantic import ValidationError
    from backend.app.schemas import SkillCreate

    # Valid with whitespace stripping
    s = SkillCreate(name="  Neural Networks  ", category="AI")
    assert s.name == "Neural Networks"

    # Rejection of whitespace-only name
    with pytest.raises(ValidationError):
        SkillCreate(name="   ")

    # Rejection of single-character name
    with pytest.raises(ValidationError):
        SkillCreate(name="A")


def test_skill_enrollment_integrity_rollback(test_environment):
    client = test_environment["client"]
    statistics = test_environment["statistics"]
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session
    import unittest.mock

    original_rollback = Session.rollback
    rollback_called = False

    def mock_rollback(self):
        nonlocal rollback_called
        rollback_called = True
        return original_rollback(self)

    def mock_commit(self):
        raise IntegrityError("duplicate key", params={}, orig=Exception("unique constraint"))

    with unittest.mock.patch.object(Session, "commit", mock_commit), \
         unittest.mock.patch.object(Session, "rollback", mock_rollback):
        response = client.post(f"/skills/{statistics.id}/enroll")
        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Learner is already enrolled in this skill"
        )
        assert rollback_called is True


def test_skill_enrollment_unrelated_integrity_error(test_environment):
    client = test_environment["client"]
    statistics = test_environment["statistics"]
    db = test_environment["db"]
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session
    import unittest.mock

    original_rollback = Session.rollback
    rollback_called = False

    def mock_rollback(self):
        nonlocal rollback_called
        rollback_called = True
        return original_rollback(self)

    # An unrelated integrity error (e.g. foreign key or check violation, not duplicate/unique)
    def mock_commit(self):
        raise IntegrityError("violates foreign key constraint", params={}, orig=Exception("fk error"))

    with unittest.mock.patch.object(Session, "commit", mock_commit), \
         unittest.mock.patch.object(Session, "rollback", mock_rollback):
        response = client.post(f"/skills/{statistics.id}/enroll")
        assert response.status_code == 400
        # Must not misclassify as duplicate enrollment
        assert response.json()["detail"] == "Database integrity constraint violation"
        assert rollback_called is True

    # Confirm session remains usable after failure
    res_check = client.get(f"/skills/{statistics.id}")
    assert res_check.status_code == 200
    assert res_check.json()["name"] == "Statistics"


# ==============================================================================
# Phase 4: Graph API & Multi-Hop Recommendation Tests
# ==============================================================================

def test_dependency_creation_forbidden_for_learners(test_environment):
    client = test_environment["client"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]
    db = test_environment["db"]

    initial_count = db.query(SkillDependency).count()

    response = client.post(
        "/skill-dependencies",
        json={
            "parent_skill_id": statistics.id,
            "child_skill_id": regression.id,
            "dependency_strength": 0.85
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Global skill dependency creation is disabled. Administrative privileges required."
    )

    # Verify no record was inserted
    assert db.query(SkillDependency).count() == initial_count


def test_dependency_creation_unauthenticated_forbidden(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    initial_count = db.query(SkillDependency).count()

    app.dependency_overrides.pop(get_current_user, None)
    try:
        # 1. Missing token -> 403 Not authenticated
        res_missing = client.post(
            "/skill-dependencies",
            json={
                "parent_skill_id": statistics.id,
                "child_skill_id": regression.id,
                "dependency_strength": 0.85
            }
        )
        assert res_missing.status_code == 403
        assert res_missing.json()["detail"] == "Not authenticated"

        # 2. Invalid token -> 401 Invalid token
        res_invalid = client.post(
            "/skill-dependencies",
            headers={"Authorization": "Bearer invalid_malformed_token"},
            json={
                "parent_skill_id": statistics.id,
                "child_skill_id": regression.id,
                "dependency_strength": 0.85
            }
        )
        assert res_invalid.status_code == 401
        assert res_invalid.json()["detail"] == "Invalid token"

        # Verify no record was inserted
        assert db.query(SkillDependency).count() == initial_count
    finally:
        app.dependency_overrides[get_current_user] = (
            lambda: test_environment["user"]
        )


def test_validate_dependency_addition_cycle_rejection(test_environment):
    import pytest
    from backend.app.ml.skill_graph import build_skill_graph, validate_dependency_addition
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]
    db = test_environment["db"]

    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    # Seed Algebra (3) -> Statistics (2) and Statistics (2) -> Regression (1)
    db.add_all([
        SkillDependency(parent_skill_id=algebra.id, child_skill_id=statistics.id, dependency_strength=0.9),
        SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.9)
    ])
    db.commit()

    G = build_skill_graph(db)

    # Attempting to add Regression (1) -> Algebra (3) would complete a cycle: 3 -> 2 -> 1 -> 3
    with pytest.raises(ValueError) as excinfo:
        validate_dependency_addition(
            G=G,
            parent_skill_id=regression.id,
            child_skill_id=algebra.id
        )
    assert "cyclic dependency loop" in str(excinfo.value)


def test_validate_dependency_addition_self_loop_duplicate_and_missing(test_environment):
    import pytest
    from backend.app.ml.skill_graph import build_skill_graph, validate_dependency_addition
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]
    db = test_environment["db"]

    db.add(SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.85))
    db.commit()

    G = build_skill_graph(db)

    # 1. Self-loop
    with pytest.raises(ValueError) as exc_self:
        validate_dependency_addition(G=G, parent_skill_id=regression.id, child_skill_id=regression.id)
    assert "cannot be its own prerequisite" in str(exc_self.value)

    # 2. Duplicate edge
    with pytest.raises(ValueError) as exc_dup:
        validate_dependency_addition(G=G, parent_skill_id=statistics.id, child_skill_id=regression.id)
    assert "already exists" in str(exc_dup.value)

    # 3. Missing parent skill
    with pytest.raises(ValueError) as exc_parent:
        validate_dependency_addition(G=G, parent_skill_id=99999, child_skill_id=regression.id)
    assert "does not exist" in str(exc_parent.value)

    # 4. Missing child skill
    with pytest.raises(ValueError) as exc_child:
        validate_dependency_addition(G=G, parent_skill_id=statistics.id, child_skill_id=88888)
    assert "does not exist" in str(exc_child.value)


def test_get_skill_prerequisites_and_descendants_api(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    # Algebra -> Statistics -> Regression
    db.add_all([
        SkillDependency(parent_skill_id=algebra.id, child_skill_id=statistics.id, dependency_strength=0.9),
        SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8),
    ])
    db.commit()

    # Query prerequisites of Regression
    res_prereq = client.get(f"/skills/{regression.id}/prerequisites")
    assert res_prereq.status_code == 200
    data_p = res_prereq.json()
    assert data_p["skill_name"] == "Regression"
    assert len(data_p["direct_prerequisites"]) == 1
    assert data_p["direct_prerequisites"][0]["name"] == "Statistics"
    assert len(data_p["transitive_prerequisites"]) == 2

    # Query descendants of Algebra
    res_desc = client.get(f"/skills/{algebra.id}/descendants")
    assert res_desc.status_code == 200
    data_d = res_desc.json()
    assert data_d["skill_name"] == "Algebra"
    assert len(data_d["direct_dependents"]) == 1
    assert data_d["direct_dependents"][0]["name"] == "Statistics"
    assert len(data_d["transitive_dependents"]) == 2


def test_get_skill_diagnosis_api(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    # Algebra (3) -> Statistics (2) -> Regression (1)
    db.add_all([
        SkillDependency(parent_skill_id=algebra.id, child_skill_id=statistics.id, dependency_strength=1.0),
        SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8),
        # Algebra is weak: 0.20
        UserSkill(user_id=user.id, skill_id=algebra.id, mastery=0.20, confidence=0.3),
        # Statistics is moderate: 0.70
        UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.70, confidence=0.8),
    ])
    db.commit()

    res_diag = client.get(f"/skills/{regression.id}/diagnosis")
    assert res_diag.status_code == 200
    diag = res_diag.json()

    assert diag["has_prerequisites"] is True
    assert diag["primary_gap"] is not None
    assert diag["primary_gap"]["name"] == "Algebra"
    assert diag["primary_gap"]["distance"] == 2
    assert diag["primary_gap"]["is_direct"] is False
    assert "Algebra" in diag["diagnosis_summary"]


def test_get_skill_dependency_path_api(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    # Algebra -> Statistics -> Regression
    db.add_all([
        SkillDependency(parent_skill_id=algebra.id, child_skill_id=statistics.id, dependency_strength=1.0),
        SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8),
    ])
    db.commit()

    # Path from Algebra (3) to Regression (1)
    res_path = client.get(f"/skills/{algebra.id}/path/{regression.id}")
    assert res_path.status_code == 200
    data = res_path.json()
    assert data["has_path"] is True
    assert data["distance"] == 2
    assert data["path_names"] == ["Algebra", "Statistics", "Regression"]


def test_multihop_recommendation_targets_root_prerequisite(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # 3-tier chain: Algebra (3) -> Statistics (2) -> Regression (1)
    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    db.add_all([
        SkillDependency(parent_skill_id=algebra.id, child_skill_id=statistics.id, dependency_strength=1.0),
        SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8),
        # Learner has mastery 0.75 in Regression, 0.70 in Statistics, but 0.20 in Algebra
        UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.75, confidence=0.8),
        UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.70, confidence=0.8),
        UserSkill(user_id=user.id, skill_id=algebra.id, mastery=0.20, confidence=0.3),
    ])
    db.commit()

    response = client.get(f"/skills/{regression.id}/recommendation")
    assert response.status_code == 200
    data = response.json()

    assert data["recommendation_status"] == "prerequisite_gap_detected"
    rec = data["recommendations"][0]
    assert rec["action_code"] == "practice_prerequisite"
    # Target skill must be the multi-hop root bottleneck (Algebra)!
    assert rec["target_skill"] == "Algebra"
    assert rec["distance"] == 2
    assert rec["is_direct"] is False
    assert "Algebra" in rec["message"]

    # Verify session is created for Algebra
    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == rec["recommendation_session_id"]
    ).one()
    assert session.skill_id == algebra.id
    assert session.recommended_action == "practice_prerequisite"



