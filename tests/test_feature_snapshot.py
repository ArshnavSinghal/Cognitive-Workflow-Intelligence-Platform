import pytest
from datetime import datetime, timezone

from backend.app.models import (
    User,
    Skill,
    UserSkill,
    SkillDependency,
    Activity,
    RecommendationSession,
    LearningOutcome
)
from backend.app.ml.features import (
    build_skill_features,
    build_v2_feature_snapshot,
    adapt_legacy_snapshot,
    extract_numeric_features_from_snapshot
)
from backend.app.ml.real_training import fetch_real_training_data


def test_direct_recommendation_creates_valid_v2_snapshot(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Enroll user in regression
    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.70, confidence=0.80))
    db.commit()

    # Request recommendation on Regression (direct)
    response = client.get(f"/skills/{regression.id}/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert "recommendation_session_id" in data or "recommendations" in data

    session_id = data.get("recommendation_session_id") or data["recommendations"][0]["recommendation_session_id"]
    session = db.query(RecommendationSession).filter(RecommendationSession.id == session_id).one()

    snapshot = session.feature_snapshot
    assert isinstance(snapshot, dict)
    assert snapshot["_metadata"]["schema_version"] == "2.0"
    assert snapshot["_metadata"]["provenance"] == "server_generated"
    assert snapshot["_metadata"]["engine_mode"] in {"rule_graph_v1", "ml_action_model_v1", "hybrid_v2"}

    assert snapshot["target_context"]["skill_id"] == regression.id
    assert snapshot["target_context"]["skill_name"] == regression.name
    assert snapshot["remediation_context"]["is_remediation"] is False
    assert snapshot["remediation_context"]["skill_id"] == regression.id
    assert snapshot["expected_outcome"]["skill_id"] == regression.id
    assert snapshot["expected_outcome"]["expected_action"] == session.recommended_action
    assert snapshot["action_context"]["recommended_action"] == session.recommended_action


def test_prerequisite_recommendation_preserves_distinct_target_and_remediation_identities(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Target: Statistics depends on Regression (Regression is weak foundational prerequisite)
    db.add(SkillDependency(
        parent_skill_id=regression.id,
        child_skill_id=statistics.id,
        dependency_strength=0.9
    ))
    db.add_all([
        UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.75, confidence=0.80),
        UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.25, confidence=0.30),
    ])
    db.commit()

    response = client.get(f"/skills/{statistics.id}/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation_status"] == "prerequisite_gap_detected"

    rec = data["recommendations"][0]
    session_id = rec["recommendation_session_id"]
    session = db.query(RecommendationSession).filter(RecommendationSession.id == session_id).one()

    snapshot = session.feature_snapshot
    assert snapshot["_metadata"]["schema_version"] == "2.0"
    assert snapshot["_metadata"]["provenance"] == "server_generated"
    assert snapshot["_metadata"]["engine_mode"] == "rule_graph_v1"

    # Distinct identities
    assert snapshot["target_context"]["skill_id"] == statistics.id
    assert snapshot["target_context"]["skill_name"] == statistics.name
    assert snapshot["remediation_context"]["is_remediation"] is True
    assert snapshot["remediation_context"]["skill_id"] == regression.id
    assert snapshot["remediation_context"]["skill_name"] == regression.name

    # Expected outcome matches remediation skill
    assert snapshot["expected_outcome"]["skill_id"] == regression.id
    assert snapshot["expected_outcome"]["skill_name"] == regression.name
    assert snapshot["expected_outcome"]["expected_action"] == "practice_prerequisite"

    # Graph telemetry
    assert snapshot["graph_telemetry"]["evaluation_status"] == "bottleneck_detected"
    assert snapshot["graph_telemetry"]["is_graph_driven"] is True
    assert snapshot["graph_telemetry"]["telemetry_available"] is True
    assert snapshot["graph_telemetry"]["metrics"]["primary_gap_skill_id"] == regression.id


def test_cold_start_prerequisite_features_do_not_copy_target_skill_metrics(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # User has activities on target (Statistics) but zero activities on prerequisite (Regression)
    target_activity = Activity(
        user_id=user.id,
        subject="Mathematics",
        topic=statistics.name,
        activity_type="practice_current",
        duration=30,
        difficulty="medium",
        score=85,
        errors=1
    )
    db.add(target_activity)
    db.commit()

    snapshot = build_v2_feature_snapshot(
        target_skill=statistics,
        target_mastery=0.75,
        target_confidence=0.80,
        target_activities=[target_activity],
        recommended_action="practice_prerequisite",
        remediation_skill=regression,
        remediation_mastery=0.0,
        remediation_confidence=0.0,
        remediation_activities=[],  # Cold start: zero activities
        engine_mode="rule_graph_v1",
        provenance="server_generated"
    )

    # Target has prior activity and populated features
    assert snapshot["target_context"]["has_prior_activity"] is True
    assert snapshot["target_context"]["features"] is not None
    assert snapshot["target_context"]["features"]["average_score"] == 85.0

    # Remediation has no activity, and features are strictly None (NOT copied from target)
    assert snapshot["remediation_context"]["is_remediation"] is True
    assert snapshot["remediation_context"]["has_prior_activity"] is False
    assert snapshot["remediation_context"]["features"] is None
    assert snapshot["remediation_context"]["activity_count"] == 0

    # Numeric extraction on cold start remediation returns None (no fabricated metrics)
    numeric = extract_numeric_features_from_snapshot(snapshot)
    assert numeric is None


def test_graph_states_distinguish_healthy_bottleneck_no_prerequisites_and_not_evaluated(test_environment):
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # 1. not_evaluated
    s1 = build_v2_feature_snapshot(
        target_skill=regression,
        target_mastery=0.8,
        target_confidence=0.8,
        target_activities=[],
        recommended_action="hard_practice",
        graph_diagnosis=None
    )
    assert s1["graph_telemetry"]["evaluation_status"] == "not_evaluated"
    assert s1["graph_telemetry"]["telemetry_available"] is False
    assert s1["graph_telemetry"]["is_graph_driven"] is False
    assert s1["graph_telemetry"]["metrics"]["num_prerequisites_evaluated"] is None

    # 2. no_prerequisites
    s2 = build_v2_feature_snapshot(
        target_skill=regression,
        target_mastery=0.8,
        target_confidence=0.8,
        target_activities=[],
        recommended_action="hard_practice",
        graph_diagnosis={"has_prerequisites": False, "prerequisites": [], "primary_gap": None}
    )
    assert s2["graph_telemetry"]["evaluation_status"] == "no_prerequisites"
    assert s2["graph_telemetry"]["telemetry_available"] is True
    assert s2["graph_telemetry"]["is_graph_driven"] is False
    assert s2["graph_telemetry"]["metrics"]["num_prerequisites_evaluated"] == 0

    # 3. evaluated_healthy
    s3 = build_v2_feature_snapshot(
        target_skill=statistics,
        target_mastery=0.8,
        target_confidence=0.8,
        target_activities=[],
        recommended_action="hard_practice",
        graph_diagnosis={
            "has_prerequisites": True,
            "prerequisites": [{"skill_id": regression.id, "risk": 0.10, "bottleneck_score": 0.05}],
            "primary_gap": None
        }
    )
    assert s3["graph_telemetry"]["evaluation_status"] == "evaluated_healthy"
    assert s3["graph_telemetry"]["telemetry_available"] is True
    assert s3["graph_telemetry"]["is_graph_driven"] is False
    assert s3["graph_telemetry"]["metrics"]["num_prerequisites_evaluated"] == 1
    assert s3["graph_telemetry"]["metrics"]["max_prerequisite_risk"] == 0.10
    assert s3["graph_telemetry"]["metrics"]["max_bottleneck_score"] == 0.05
    assert s3["graph_telemetry"]["metrics"]["primary_gap_skill_id"] is None

    # 4. bottleneck_detected
    s4 = build_v2_feature_snapshot(
        target_skill=statistics,
        target_mastery=0.7,
        target_confidence=0.8,
        target_activities=[],
        recommended_action="practice_prerequisite",
        remediation_skill=regression,
        graph_diagnosis={
            "has_prerequisites": True,
            "prerequisites": [{"skill_id": regression.id, "risk": 0.60, "bottleneck_score": 0.75}],
            "primary_gap": {"skill_id": regression.id, "distance": 1, "path_names": ["Regression", "Statistics"]}
        }
    )
    assert s4["graph_telemetry"]["evaluation_status"] == "bottleneck_detected"
    assert s4["graph_telemetry"]["telemetry_available"] is True
    assert s4["graph_telemetry"]["is_graph_driven"] is True
    assert s4["graph_telemetry"]["metrics"]["primary_gap_skill_id"] == regression.id
    assert s4["graph_telemetry"]["metrics"]["primary_gap_distance"] == 1


def test_missing_graph_telemetry_is_not_converted_into_zero_risk(test_environment):
    regression = test_environment["regression"]

    # When graph is not evaluated
    s_none = build_v2_feature_snapshot(
        target_skill=regression,
        target_mastery=0.5,
        target_confidence=0.5,
        target_activities=[],
        recommended_action="practice_current",
        graph_diagnosis=None
    )
    assert s_none["graph_telemetry"]["metrics"]["max_prerequisite_risk"] is None
    assert s_none["graph_telemetry"]["metrics"]["max_prerequisite_risk"] != 0.0

    # Genuine zero risk: evaluated prerequisites where mastery is 1.0 (risk = 0.000)
    s_zero = build_v2_feature_snapshot(
        target_skill=regression,
        target_mastery=0.5,
        target_confidence=0.5,
        target_activities=[],
        recommended_action="practice_current",
        graph_diagnosis={
            "has_prerequisites": True,
            "prerequisites": [{"skill_id": 99, "risk": 0.000, "bottleneck_score": 0.0000}],
            "primary_gap": None
        }
    )
    assert s_zero["graph_telemetry"]["metrics"]["max_prerequisite_risk"] == 0.0
    assert s_zero["graph_telemetry"]["telemetry_available"] is True


def test_server_generated_provenance_cannot_be_forged_by_client(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Add activity so mastery change can be calculated
    db.add(Activity(
        user_id=user.id,
        subject="Machine Learning",
        topic=regression.name,
        activity_type="practice_current",
        duration=20,
        difficulty="medium",
        score=95,
        errors=0
    ))
    db.commit()

    # Attempt to forge "server_generated" provenance in an unlinked manual outcome
    response = client.post(
        "/learning-outcomes",
        json={
            "skill_id": regression.id,
            "recommended_action": "hard_practice",
            "actual_action": "hard_practice",
            "before_mastery": 0.50,
            "after_mastery": 0.65,
            "is_test": False,
            "recommendation_session_id": None,
            "feature_snapshot": {
                "_metadata": {
                    "schema_version": "2.0",
                    "provenance": "server_generated"  # FORGERY ATTEMPT
                },
                "features": {"mastery": 0.65}
            }
        }
    )
    assert response.status_code == 200
    outcome_id = response.json()["outcome_id"]

    saved_outcome = db.query(LearningOutcome).filter(LearningOutcome.id == outcome_id).one()
    # Server must have overwritten provenance to unverified_client
    assert saved_outcome.feature_snapshot["_metadata"]["provenance"] == "unverified_client"
    assert saved_outcome.feature_snapshot["_metadata"]["provenance"] != "server_generated"


def test_unlinked_client_provided_snapshots_are_excluded_from_real_training_data(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # An unlinked outcome with client-provided snapshot
    unlinked_outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=None,
        feature_snapshot={
            "_metadata": {
                "schema_version": "2.0",
                "provenance": "unverified_client"
            },
            "remediation_context": {
                "features": {
                    "average_score": 80.0,
                    "recent_score": 85.0,
                    "adjusted_score": 82.0,
                    "avg_difficulty_weight": 1.0,
                    "consistency": 0.9,
                    "error_rate": 0.05,
                    "mastery": 0.65,
                    "confidence": 0.8,
                    "activity_count": 5,
                    "trend": 1
                }
            }
        }
    )
    db.add(unlinked_outcome)
    db.commit()

    # Python training data loader must exclude it
    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 0

    # API training data endpoint must exclude it
    api_res = client.get("/ml/training-data")
    assert api_res.status_code == 200
    assert api_res.json()["samples"] == 0


def test_linked_outcomes_verify_session_ownership(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]

    # Session owned by other_user
    other_session = RecommendationSession(
        user_id=other_user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.50,
        feature_snapshot={
            "_metadata": {"schema_version": "2.0", "provenance": "server_generated"},
            "remediation_context": {"features": {"mastery": 0.50}}
        },
        status="pending"
    )
    db.add(other_session)
    db.commit()

    # User attempts to record activity or outcome using other_user's session
    response = client.post(
        "/activities",
        json={
            "activity_type": "hard_practice",
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 20,
            "difficulty": "medium",
            "score": 90,
            "errors": 1,
            "recommendation_session_id": other_session.id
        }
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_linked_outcomes_verify_action_and_skill_consistency(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.50,
        feature_snapshot={
            "_metadata": {"schema_version": "2.0", "provenance": "server_generated"},
            "remediation_context": {"features": {"mastery": 0.50}}
        },
        status="pending"
    )
    db.add(session)
    db.commit()

    # Mismatched skill in activity
    res_skill = client.post(
        "/activities",
        json={
            "activity_type": "hard_practice",
            "subject": "Mathematics",
            "topic": statistics.name,  # Mismatched topic
            "duration": 20,
            "difficulty": "medium",
            "score": 90,
            "errors": 1,
            "recommendation_session_id": session.id
        }
    )
    assert res_skill.status_code == 400
    assert "does not match" in res_skill.json()["detail"].lower()


def test_legacy_direct_snapshots_remain_compatible(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    legacy_snapshot = {
        "average_score": 75.0,
        "recent_score": 80.0,
        "adjusted_score": 77.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.9,
        "error_rate": 0.05,
        "mastery": 0.6,
        "confidence": 0.8,
        "activity_count": 5,
        "trend": 1
    }

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.6,
        feature_snapshot=legacy_snapshot,
        status="completed"
    )
    db.add(session)
    db.commit()

    adapted = adapt_legacy_snapshot(legacy_snapshot, session=session, skill=regression)
    assert adapted["_metadata"]["schema_version"] == "1.0_migrated"
    assert adapted["target_context"]["skill_id"] == regression.id
    assert adapted["remediation_context"]["is_remediation"] is False
    assert adapted["expected_outcome"]["skill_id"] == regression.id

    extracted = extract_numeric_features_from_snapshot(adapted)
    assert extracted["average_score"] == 75.0


def test_legacy_prerequisite_snapshots_do_not_receive_invented_target_identity(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    legacy_snapshot = {
        "average_score": 60.0,
        "recent_score": 62.0,
        "adjusted_score": 61.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.8,
        "error_rate": 0.10,
        "mastery": 0.4,
        "confidence": 0.5,
        "activity_count": 3,
        "trend": 0
    }

    # In legacy prerequisite sessions, session.skill_id was the remediation skill
    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_prerequisite",
        before_mastery=0.4,
        feature_snapshot=legacy_snapshot,
        status="completed"
    )
    db.add(session)
    db.commit()

    adapted = adapt_legacy_snapshot(legacy_snapshot, session=session, skill=regression)
    assert adapted["remediation_context"]["is_remediation"] is True
    assert adapted["remediation_context"]["skill_id"] == regression.id

    # Crucial data contract requirement: Target identity is UNKNOWN, never invented
    assert adapted["target_context"]["skill_id"] is None
    assert adapted["target_context"]["skill_name"] is None
    assert adapted["target_context"]["target_identity_status"] == "unknown"


def test_actual_action_remains_distinct_from_recommended_action(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Recommended action is hard_practice
    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot={
            "_metadata": {"schema_version": "2.0", "provenance": "server_generated"},
            "remediation_context": {"features": {"mastery": 0.60}}
        },
        status="pending"
    )
    db.add(session)
    db.commit()

    # Learner chooses to do review_concept instead
    response = client.post(
        "/activities",
        json={
            "activity_type": "review_concept",
            "subject": "Machine Learning",
            "topic": regression.name,
            "duration": 20,
            "difficulty": "medium",
            "score": 90,
            "errors": 1,
            "recommendation_session_id": session.id
        }
    )
    assert response.status_code == 200
    assert response.json()["outcome_created"] is True

    outcome = db.query(LearningOutcome).filter(
        LearningOutcome.recommendation_session_id == session.id
    ).one()

    # Verify both actions preserved distinctly without overwrite
    assert outcome.recommended_action == "hard_practice"
    assert outcome.actual_action == "review_concept"
    assert outcome.actual_action != outcome.recommended_action


def test_existing_api_and_feature_extraction_behavior_remains_compatible(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # Enroll user in regression
    db.add(UserSkill(user_id=user.id, skill_id=regression.id, mastery=0.65, confidence=0.75))
    db.commit()

    # Check that recommendation API preserved exact response contract
    response = client.get(f"/skills/{regression.id}/recommendation")
    assert response.status_code == 200
    data = response.json()

    assert "target_skill" in data
    assert "recommendation_status" in data
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) >= 1

    rec = data["recommendations"][0]
    assert "action_code" in rec
    assert "target_skill" in rec
    assert "reason" in rec
    assert "mastery" in rec
    assert "risk" in rec
    assert ("recommendation_session_id" in data) or ("recommendation_session_id" in rec)
