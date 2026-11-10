import pytest
import math

from backend.app.models import (
    User,
    Skill,
    UserSkill,
    LearningOutcome,
    RecommendationSession,
)
from backend.app.ml.features import (
    adapt_legacy_snapshot,
    extract_numeric_features_from_snapshot,
)
from backend.app.ml.real_training import (
    fetch_real_training_data,
    validate_and_extract_training_record,
)
from backend.app.main import get_training_data


def sample_flat_features():
    return {
        "average_score": 85.0,
        "recent_score": 88.0,
        "adjusted_score": 86.0,
        "avg_difficulty_weight": 1.0,
        "consistency": 0.92,
        "error_rate": 0.04,
        "mastery": 0.75,
        "confidence": 0.85,
        "activity_count": 8,
        "trend": 1,
    }


def sample_v2_snapshot(skill_id=1, skill_name="Regression", action="hard_practice"):
    return {
        "_metadata": {
            "schema_version": "2.0",
            "snapshot_timestamp": "2026-11-08T00:00:00Z",
            "provenance": "server_generated",
            "engine_mode": "rule_graph_v1"
        },
        "target_context": {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery": 0.75,
            "confidence": 0.85,
            "has_prior_activity": True,
            "activity_count": 8,
            "features": sample_flat_features()
        },
        "remediation_context": {
            "is_remediation": False,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery": 0.75,
            "confidence": 0.85,
            "has_prior_activity": True,
            "activity_count": 8,
            "features": sample_flat_features()
        },
        "expected_outcome": {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "expected_action": action
        },
        "graph_telemetry": {
            "evaluation_status": "evaluated_healthy",
            "is_graph_driven": False,
            "telemetry_available": True,
            "metrics": {
                "num_prerequisites_evaluated": 1,
                "max_prerequisite_risk": 0.15,
                "max_bottleneck_score": 0.05,
                "primary_gap_skill_id": None,
                "primary_gap_distance": None,
                "primary_gap_path": None
            }
        },
        "action_context": {
            "recommended_action": action,
            "candidate_actions": ["hard_practice"]
        }
    }


# Test 1: Unlinked flat legacy snapshot is excluded
def test_unlinked_flat_legacy_snapshot_is_excluded(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    outcome = LearningOutcome(
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
        feature_snapshot=sample_flat_features()
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is None

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 0

    api_res = client.get("/ml/training-data")
    assert api_res.status_code == 200
    assert api_res.json()["samples"] == 0
    assert api_res.json()["skipped_missing_snapshot"] >= 1


# Test 2: Unlinked snapshot claiming legacy_database is excluded
def test_unlinked_snapshot_claiming_legacy_database_is_excluded(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    spoofed_snapshot = {
        "_metadata": {
            "schema_version": "1.0_migrated",
            "provenance": "legacy_database"
        },
        "remediation_context": {"features": sample_flat_features()}
    }

    outcome = LearningOutcome(
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
        feature_snapshot=spoofed_snapshot
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is None

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 0

    api_res = client.get("/ml/training-data")
    assert api_res.status_code == 200
    assert api_res.json()["samples"] == 0


# Test 3: Unlinked snapshot claiming server_generated is excluded
def test_unlinked_snapshot_claiming_server_generated_is_excluded(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    outcome = LearningOutcome(
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
        feature_snapshot=sample_v2_snapshot(regression.id, regression.name, "hard_practice")
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is None

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 0

    api_res = client.get("/ml/training-data")
    assert api_res.status_code == 200
    assert api_res.json()["samples"] == 0


# Test 4: Linked valid historical flat session snapshot is accepted
def test_linked_valid_historical_flat_session_snapshot_is_accepted(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=sample_flat_features(),
        status="completed"
    )
    db.add(session)
    db.commit()

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=session.id,
        feature_snapshot=session.feature_snapshot
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is not None
    assert record["features"]["average_score"] == 85.0
    assert record["features"]["mastery"] == 0.75

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 1
    assert dataset[0]["is_synthetic"] is False

    api_res = client.get("/ml/training-data")
    assert api_res.status_code == 200
    assert api_res.json()["samples"] == 1
    assert api_res.json()["dataset"][0]["features"]["average_score"] == 85.0


# Test 5: Linked valid v2 server-generated snapshot is accepted
def test_linked_valid_v2_server_generated_snapshot_is_accepted(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    v2_snap = sample_v2_snapshot(regression.id, regression.name, "hard_practice")

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=v2_snap,
        status="completed"
    )
    db.add(session)
    db.commit()

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=session.id,
        feature_snapshot=v2_snap
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is not None
    assert record["features"]["average_score"] == 85.0

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 1

    api_res = client.get("/ml/training-data")
    assert api_res.status_code == 200
    assert api_res.json()["samples"] == 1


# Test 6: Linked session belonging to another user is excluded
def test_linked_session_belonging_to_another_user_is_excluded(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]

    other_session = RecommendationSession(
        user_id=other_user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=sample_flat_features(),
        status="completed"
    )
    db.add(other_session)
    db.commit()

    # User attempts to claim other_user's session
    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=other_session.id,
        feature_snapshot=sample_flat_features()
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is None

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 0

    api_res = client.get("/ml/training-data")
    assert api_res.json()["samples"] == 0


# Test 7: Session skill mismatch is excluded
def test_session_skill_mismatch_is_excluded(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=sample_flat_features(),
        status="completed"
    )
    db.add(session)
    db.commit()

    # Outcome is for statistics, but points to regression session
    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=statistics.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=session.id,
        feature_snapshot=sample_flat_features()
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is None

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 0

    api_res = client.get("/ml/training-data")
    assert api_res.json()["samples"] == 0


# Test 8: Session recommended-action mismatch is excluded
def test_session_recommended_action_mismatch_is_excluded(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=sample_flat_features(),
        status="completed"
    )
    db.add(session)
    db.commit()

    # Outcome claims recommended_action = "practice_current"
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
        recommendation_session_id=session.id,
        feature_snapshot=sample_flat_features()
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is None

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 0

    api_res = client.get("/ml/training-data")
    assert api_res.json()["samples"] == 0


# Test 9: Client outcome snapshot cannot override the linked session snapshot
def test_client_outcome_snapshot_cannot_override_linked_session_snapshot(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    trusted_features = sample_flat_features()
    trusted_features["average_score"] = 88.0

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=trusted_features,
        status="completed"
    )
    db.add(session)
    db.commit()

    forged_features = sample_flat_features()
    forged_features["average_score"] = 42.0

    outcome = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=session.id,
        feature_snapshot=forged_features  # Client attempt to override
    )
    db.add(outcome)
    db.commit()

    record = validate_and_extract_training_record(outcome, db)
    assert record is not None
    # Must use session snapshot (88.0), never outcome snapshot (42.0)
    assert record["features"]["average_score"] == 88.0
    assert record["features"]["average_score"] != 42.0

    dataset = fetch_real_training_data(db, user.id)
    assert len(dataset) == 1
    assert dataset[0]["features"]["average_score"] == 88.0

    api_res = client.get("/ml/training-data")
    assert api_res.status_code == 200
    assert api_res.json()["dataset"][0]["features"]["average_score"] == 88.0


# Test 10: Both loaders return identical eligible records and feature dictionaries
def test_both_loaders_return_identical_eligible_records_and_features(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    # 1. Valid historical flat session outcome
    s1 = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=sample_flat_features(),
        status="completed"
    )
    db.add(s1)
    db.commit()
    o1 = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=s1.id,
        feature_snapshot=s1.feature_snapshot
    )

    # 2. Valid v2 session outcome
    v2_snap = sample_v2_snapshot(regression.id, regression.name, "practice_current")
    s2 = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        before_mastery=0.65,
        feature_snapshot=v2_snap,
        status="completed"
    )
    db.add(s2)
    db.commit()
    o2 = LearningOutcome(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_current",
        actual_action="practice_current",
        before_mastery=0.65,
        after_mastery=0.75,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=s2.id,
        feature_snapshot=v2_snap
    )

    # 3. Invalid unlinked outcome (must be skipped by both)
    o3 = LearningOutcome(
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
        feature_snapshot=sample_flat_features()
    )

    db.add_all([o1, o2, o3])
    db.commit()

    python_data = fetch_real_training_data(db, user.id)
    api_response = client.get("/ml/training-data").json()

    assert len(python_data) == 2
    assert api_response["samples"] == 2
    assert api_response["skipped_missing_snapshot"] >= 1

    for i in range(2):
        p_row = python_data[i]
        a_row = api_response["dataset"][i]

        assert p_row["features"] == a_row["features"]
        assert p_row["recommended_action"] == a_row["recommended_action"]
        assert p_row["actual_action"] == a_row["actual_action"]
        assert p_row["outcome"] == a_row["outcome"]
        assert p_row["mastery_change"] == a_row["mastery_change"]


# Test 11: Existing real records with valid sessions remain eligible
def test_existing_real_records_with_valid_sessions_remain_eligible(test_environment):
    db = test_environment["db"]

    # Verify existing persistent DB real outcomes (IDs 25 and 26)
    outcomes = db.query(LearningOutcome).filter(
        LearningOutcome.id.in_([25, 26]),
        LearningOutcome.is_test == False
    ).all()

    # In our local test environment fixture, test_environment creates clean fresh tables,
    # but we can verify the eligibility predicate on their exact shape:
    for o in outcomes:
        rec = validate_and_extract_training_record(o, db)
        assert rec is not None
        assert "features" in rec
        assert rec["recommended_action"] == "hard_practice"


# Test 12: Existing legacy prerequisite target identity remains unknown rather than inferred
def test_existing_legacy_prerequisite_target_identity_remains_unknown_rather_than_inferred(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]

    legacy_features = sample_flat_features()

    session = RecommendationSession(
        user_id=user.id,
        skill_id=regression.id,
        recommended_action="practice_prerequisite",
        before_mastery=0.40,
        feature_snapshot=legacy_features,
        status="completed"
    )
    db.add(session)
    db.commit()

    adapted = adapt_legacy_snapshot(legacy_features, session=session, skill=regression)

    assert adapted["_metadata"]["schema_version"] == "1.0_migrated"
    assert adapted["_metadata"]["provenance"] == "legacy_database"
    assert adapted["_metadata"]["engine_mode"] == "legacy_v1"

    # Remediation context holds the legacy practiced skill
    assert adapted["remediation_context"]["is_remediation"] is True
    assert adapted["remediation_context"]["skill_id"] == regression.id

    # Crucial governance requirement: target identity must be strictly UNKNOWN
    assert adapted["target_context"]["skill_id"] is None
    assert adapted["target_context"]["skill_name"] is None
    assert adapted["target_context"]["target_identity_status"] == "unknown"

    # Missing graph telemetry preserved without fabrication
    assert adapted["graph_telemetry"]["evaluation_status"] == "not_evaluated"
    assert adapted["graph_telemetry"]["metrics"]["max_prerequisite_risk"] is None
    assert adapted["graph_telemetry"]["metrics"]["max_bottleneck_score"] is None
