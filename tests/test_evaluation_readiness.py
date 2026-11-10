import pytest
import math
from datetime import datetime, timezone, timedelta

from backend.app.models import (
    User,
    Skill,
    UserSkill,
    LearningOutcome,
    RecommendationSession,
)
from backend.app.ml.evaluation import (
    EvaluationThresholds,
    audit_data_readiness,
    check_data_sufficiency,
    prepare_track_a_partitions,
    prepare_track_b_partitions,
    ZeroMasteryBaseline,
    GlobalMeanBaseline,
    ActionSpecificMeanBaseline,
    generate_evaluation_readiness_report,
)


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
            "engine_mode": "rule_graph_v1",
        },
        "target_context": {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery": 0.75,
            "confidence": 0.85,
            "has_prior_activity": True,
            "activity_count": 8,
            "features": sample_flat_features(),
        },
        "remediation_context": {
            "is_remediation": False,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery": 0.75,
            "confidence": 0.85,
            "has_prior_activity": True,
            "activity_count": 8,
            "features": sample_flat_features(),
        },
        "expected_outcome": {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "expected_action": action,
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
                "primary_gap_path": None,
            },
        },
        "action_context": {
            "recommended_action": action,
            "candidate_actions": ["hard_practice"],
        },
    }


def create_linked_record(
    db,
    user_id=1,
    skill_id=1,
    recommended_action="hard_practice",
    actual_action="hard_practice",
    before_mastery=0.60,
    after_mastery=0.70,
    is_test=False,
    created_at=None,
    custom_snapshot=None,
    no_session=False,
    mismatch_session_action=None,
    mismatch_session_user=None,
    mismatch_session_skill=None,
):
    """Helper to generate consistent recommendation sessions and linked outcomes."""
    session_id = None
    if not no_session:
        session_before = (
            0.60
            if (isinstance(before_mastery, (int, float)) and not math.isfinite(before_mastery))
            else before_mastery
        )
        session = RecommendationSession(
            user_id=mismatch_session_user if mismatch_session_user else user_id,
            skill_id=mismatch_session_skill if mismatch_session_skill else skill_id,
            recommended_action=mismatch_session_action if mismatch_session_action else recommended_action,
            before_mastery=session_before,
            feature_snapshot=custom_snapshot if custom_snapshot is not None else sample_v2_snapshot(
                skill_id=skill_id, action=recommended_action
            ),
            status="completed",
        )
        if created_at:
            session.created_at = created_at
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    mastery_change = round(after_mastery - before_mastery, 4)
    outcome = LearningOutcome(
        user_id=user_id,
        skill_id=skill_id,
        recommended_action=recommended_action,
        actual_action=actual_action,
        before_mastery=before_mastery,
        after_mastery=after_mastery,
        mastery_change=mastery_change,
        outcome="positive" if mastery_change > 0 else "neutral",
        is_test=is_test,
        recommendation_session_id=session_id,
        feature_snapshot=sample_flat_features(),
    )
    if created_at:
        outcome.created_at = created_at
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


# ---------------------------------------------------------------------------
# Test 1: Data readiness audit accurately counts eligible vs excluded records
# ---------------------------------------------------------------------------
def test_audit_accurately_counts_eligible_and_categorizes_exclusions(test_environment):
    db = test_environment["db"]

    # 1. Eligible record
    create_linked_record(db, user_id=1, skill_id=1, recommended_action="hard_practice", actual_action="hard_practice")

    # 2. Excluded: test_record
    create_linked_record(db, user_id=1, skill_id=1, is_test=True)

    # 3. Excluded: unlinked_outcome
    create_linked_record(db, user_id=1, skill_id=1, no_session=True)

    # 4. Excluded: session_user_mismatch
    create_linked_record(db, user_id=1, skill_id=1, mismatch_session_user=2)

    # 5. Excluded: session_skill_mismatch
    create_linked_record(db, user_id=1, skill_id=1, mismatch_session_skill=2)

    # 6. Excluded: session_action_mismatch
    create_linked_record(db, user_id=1, skill_id=1, recommended_action="hard_practice", mismatch_session_action="practice_current")

    # 7. Excluded: invalid_action_or_outcome
    create_linked_record(db, user_id=1, skill_id=1, recommended_action="unknown_action", actual_action="unknown_action", mismatch_session_action="unknown_action")

    # 8. Excluded: missing_numeric_features
    corrupted_snap = sample_v2_snapshot(1, "Regression", "hard_practice")
    corrupted_snap["remediation_context"]["features"].pop("mastery")
    create_linked_record(db, user_id=1, skill_id=1, custom_snapshot=corrupted_snap)

    # 9. Excluded: invalid_numeric_values
    nan_snap = sample_v2_snapshot(1, "Regression", "hard_practice")
    nan_snap["remediation_context"]["features"]["confidence"] = float("nan")
    create_linked_record(db, user_id=1, skill_id=1, custom_snapshot=nan_snap)

    # 10. Excluded: concordance_mismatch
    concordance_snap = sample_v2_snapshot(1, "Regression", "hard_practice")
    concordance_snap["expected_outcome"]["skill_id"] = 2
    create_linked_record(db, user_id=1, skill_id=1, custom_snapshot=concordance_snap)

    # 11. Excluded: untrusted_provenance
    untrusted_snap = sample_v2_snapshot(1, "Regression", "hard_practice")
    untrusted_snap["_metadata"]["provenance"] = "untrusted_client"
    create_linked_record(db, user_id=1, skill_id=1, custom_snapshot=untrusted_snap)

    audit = audit_data_readiness(db, user_id=None)

    assert audit["total_inspected"] == 11
    assert audit["eligible_count"] == 1
    assert audit["excluded_count"] == 10
    assert audit["distinct_learners"] == [1]
    assert audit["distinct_skills"] == [1]
    assert audit["action_counts"] == {"hard_practice": 1}

    # Verify breakdown of exclusions
    reasons = audit["exclusion_reasons"]
    assert reasons["test_record"] == 1
    assert reasons["unlinked_outcome"] == 1
    assert reasons["session_ownership_mismatch"] == 1
    assert reasons["session_skill_mismatch"] == 1
    assert reasons["session_action_mismatch"] == 1
    assert reasons["invalid_action_or_outcome"] == 1
    assert reasons["missing_numeric_features"] == 1
    assert reasons["invalid_numeric_values"] == 1
    assert reasons["concordance_mismatch"] == 1
    assert reasons["untrusted_provenance"] == 1


# ---------------------------------------------------------------------------
# Test 2: Provenance enforcement & unverified client records excluded
# ---------------------------------------------------------------------------
def test_provenance_enforcement_and_unverified_records_excluded(test_environment):
    db = test_environment["db"]

    # Spoofed metadata claiming server_generated on outcome directly, but unlinked
    spoofed = LearningOutcome(
        user_id=1,
        skill_id=1,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=None,
        feature_snapshot={
            "_metadata": {"provenance": "server_generated", "schema_version": "2.0"},
            "remediation_context": {"features": sample_flat_features()},
        },
    )
    db.add(spoofed)
    db.commit()

    audit = audit_data_readiness(db, user_id=1)
    assert audit["total_inspected"] == 1
    assert audit["eligible_count"] == 0
    assert audit["exclusion_reasons"]["unlinked_outcome"] == 1


# ---------------------------------------------------------------------------
# Test 3: Learner isolation enforcement
# ---------------------------------------------------------------------------
def test_learner_isolation_enforcement(test_environment):
    db = test_environment["db"]

    # Record for User 1
    create_linked_record(db, user_id=1, skill_id=1, recommended_action="hard_practice", actual_action="hard_practice")

    # Record for User 2
    create_linked_record(db, user_id=2, skill_id=1, recommended_action="take_assessment", actual_action="take_assessment")

    # Audit scoped to User 1
    audit_u1 = audit_data_readiness(db, user_id=1)
    assert audit_u1["eligible_count"] == 1
    assert audit_u1["distinct_learners"] == [1]
    assert audit_u1["action_counts"] == {"hard_practice": 1}

    # Audit scoped to User 2
    audit_u2 = audit_data_readiness(db, user_id=2)
    assert audit_u2["eligible_count"] == 1
    assert audit_u2["distinct_learners"] == [2]
    assert audit_u2["action_counts"] == {"take_assessment": 1}

    # Global audit (user_id=None)
    audit_global = audit_data_readiness(db, user_id=None)
    assert audit_global["eligible_count"] == 2
    assert audit_global["distinct_learners"] == [1, 2]
    assert audit_global["action_counts"] == {"hard_practice": 1, "take_assessment": 1}


# ---------------------------------------------------------------------------
# Test 4: Insufficient sample count fails sufficiency gates
# ---------------------------------------------------------------------------
def test_insufficient_sample_count_fails_sufficiency_gates():
    dummy_audit = {
        "eligible_count": 5,
        "distinct_learners": [1, 2],
        "distinct_skills": [1],
        "action_counts": {"hard_practice": 3, "take_assessment": 2},
        "learners_per_action": {"hard_practice": 2, "take_assessment": 1},
    }
    thresholds = EvaluationThresholds()
    sufficiency = check_data_sufficiency(dummy_audit, thresholds=thresholds)

    assert sufficiency["is_ready_for_real_data_evaluation"] is False
    assert sufficiency["gates"]["model_fitting_gate"]["passed"] is False
    assert sufficiency["gates"]["total_observations_gate"]["passed"] is False
    assert sufficiency["gates"]["distinct_learners_gate"]["passed"] is False

    reasons = " ".join(sufficiency["blocking_reasons"])
    assert "Total eligible observations" in reasons
    assert "Distinct learners" in reasons


# ---------------------------------------------------------------------------
# Test 5: Single-class action dataset fails diversity gate
# ---------------------------------------------------------------------------
def test_single_class_action_dataset_fails_diversity_gate():
    dummy_audit = {
        "eligible_count": 200,
        "distinct_learners": list(range(1, 25)),
        "distinct_skills": [1, 2],
        "action_counts": {"hard_practice": 200},  # Only 1 unique action
        "learners_per_action": {"hard_practice": 24},
    }
    thresholds = EvaluationThresholds()
    sufficiency = check_data_sufficiency(dummy_audit, thresholds=thresholds)

    assert sufficiency["is_ready_for_real_data_evaluation"] is False
    assert sufficiency["gates"]["action_diversity_gate"]["passed"] is False
    assert sufficiency["gates"]["action_diversity_gate"]["current"] == 1

    reasons = " ".join(sufficiency["blocking_reasons"])
    assert "Active action classes" in reasons


# ---------------------------------------------------------------------------
# Test 6: Action-specific baseline support and intersection evaluation
# ---------------------------------------------------------------------------
def test_action_baseline_support_and_intersection_evaluation():
    # 1. Action "hard_practice": 10 samples across 5 unique learners (mean = 0.12) -> SUPPORTED (N_dev >= 10, K_dev >= 5)
    # 2. Action "take_assessment": 9 samples across 5 unique learners -> UNSUPPORTED (N_dev = 9 < 10)
    # 3. Action "review_concept": 10 samples across 4 unique learners -> UNSUPPORTED (K_dev = 4 < 5)
    dev_samples = []

    # 10 samples across 5 learners (2 per learner) for hard_practice
    for uid in range(1, 6):
        dev_samples.append({"user_id": uid, "actual_action": "hard_practice", "mastery_change": 0.10})
        dev_samples.append({"user_id": uid, "actual_action": "hard_practice", "mastery_change": 0.14})

    # 9 samples across 5 learners for take_assessment (insufficient N)
    for i in range(9):
        dev_samples.append({"user_id": (i % 5) + 1, "actual_action": "take_assessment", "mastery_change": 0.05})

    # 10 samples across 4 learners for review_concept (insufficient K)
    for i in range(10):
        dev_samples.append({"user_id": (i % 4) + 1, "actual_action": "review_concept", "mastery_change": 0.08})

    baseline = ActionSpecificMeanBaseline()
    baseline.fit(dev_samples, min_obs=10, min_learners=5)

    # Verify hard_practice is supported
    assert baseline.action_support_["hard_practice"]["supported"] is True
    assert baseline.action_support_["hard_practice"]["count"] == 10
    assert baseline.action_support_["hard_practice"]["learners"] == 5
    assert baseline.action_support_["hard_practice"]["mean"] == 0.12

    # Verify take_assessment is unsupported due to N = 9 < 10
    assert baseline.action_support_["take_assessment"]["supported"] is False
    assert baseline.action_support_["take_assessment"]["count"] == 9
    assert baseline.action_support_["take_assessment"]["learners"] == 5
    assert baseline.action_support_["take_assessment"]["mean"] is None

    # Verify review_concept is unsupported due to K = 4 < 5
    assert baseline.action_support_["review_concept"]["supported"] is False
    assert baseline.action_support_["review_concept"]["count"] == 10
    assert baseline.action_support_["review_concept"]["learners"] == 4
    assert baseline.action_support_["review_concept"]["mean"] is None

    # Predict: Supported action returns mean, unsupported actions return None (never fabricated)
    assert baseline.predict({"actual_action": "hard_practice"}) == 0.12
    assert baseline.predict({"actual_action": "take_assessment"}) is None
    assert baseline.predict({"actual_action": "review_concept"}) is None
    assert baseline.predict({"actual_action": "practice_current"}) is None

    # Evaluate intersection on test samples
    eval_samples = [
        {"user_id": 6, "actual_action": "hard_practice", "mastery_change": 0.15},  # abs(0.15 - 0.12) = 0.03
        {"user_id": 6, "actual_action": "hard_practice", "mastery_change": 0.09},  # abs(0.09 - 0.12) = 0.03
        {"user_id": 6, "actual_action": "take_assessment", "mastery_change": 0.08}, # unsupported, skipped
        {"user_id": 6, "actual_action": "review_concept", "mastery_change": 0.08},  # unsupported, skipped
    ]

    metrics = baseline.evaluate_intersection(eval_samples)
    assert metrics["evaluated_samples"] == 2
    assert metrics["unsupported_samples_skipped"] == 2
    assert metrics["mae"] == 0.03


# ---------------------------------------------------------------------------
# Test 7: Track A disjoint partition leakage prevention
# ---------------------------------------------------------------------------
def test_track_a_disjoint_partitions_leakage_prevention():
    # 1. Infeasible when K < 3
    infeasible_samples = [
        {"user_id": 1, "actual_action": "hard_practice", "mastery_change": 0.1},
        {"user_id": 2, "actual_action": "take_assessment", "mastery_change": 0.1},
    ]
    track_a_inf = prepare_track_a_partitions(infeasible_samples)
    assert track_a_inf["feasible"] is False
    assert "Insufficient distinct learners" in track_a_inf["reason"]

    # 2. Feasible with 25 unique learners
    synthetic_records = []
    for uid in range(1, 26):
        for _ in range(5):
            synthetic_records.append({
                "user_id": uid,
                "session_id": uid * 10,
                "actual_action": "hard_practice",
                "mastery_change": 0.1,
            })

    track_a = prepare_track_a_partitions(synthetic_records)
    assert track_a["feasible"] is True

    dev_uids = set(track_a["dev_learners"])
    cal_uids = set(track_a["cal_learners"])
    eval_uids = set(track_a["eval_learners"])

    # Strict disjointness - zero identity overlap
    assert len(dev_uids & cal_uids) == 0
    assert len(dev_uids & eval_uids) == 0
    assert len(cal_uids & eval_uids) == 0

    # Every record belongs strictly to its allocated partition
    for r in track_a["dev_records"]:
        assert r["user_id"] in dev_uids
    for r in track_a["cal_records"]:
        assert r["user_id"] in cal_uids
    for r in track_a["eval_records"]:
        assert r["user_id"] in eval_uids


# ---------------------------------------------------------------------------
# Test 8: Track B chronological ordering with no future leakage
# ---------------------------------------------------------------------------
def test_track_b_chronological_ordering_no_future_leakage():
    # Create 5 chronological records for a single learner
    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    learner_records = [
        {
            "user_id": 1,
            "outcome_id": 1,
            "session_id": 101,
            "created_at": (base_time + timedelta(hours=1)).isoformat(),
            "actual_action": "hard_practice",
            "mastery_change": 0.05,
        },
        {
            "user_id": 1,
            "outcome_id": 2,
            "session_id": 102,
            "created_at": (base_time + timedelta(hours=2)).isoformat(),
            "actual_action": "hard_practice",
            "mastery_change": 0.07,
        },
        {
            "user_id": 1,
            "outcome_id": 3,
            "session_id": 103,
            "created_at": (base_time + timedelta(hours=3)).isoformat(),
            "actual_action": "take_assessment",
            "mastery_change": 0.10,
        },
        {
            "user_id": 1,
            "outcome_id": 4,
            "session_id": 104,
            "created_at": (base_time + timedelta(hours=4)).isoformat(),
            "actual_action": "take_assessment",
            "mastery_change": 0.08,
        },
        {
            "user_id": 1,
            "outcome_id": 5,
            "session_id": 105,
            "created_at": (base_time + timedelta(hours=5)).isoformat(),
            "actual_action": "hard_practice",
            "mastery_change": 0.12,
        },
    ]

    track_b = prepare_track_b_partitions(learner_records)
    assert track_b["feasible"] is True

    dev_recs = track_b["dev_records"]
    eval_recs = track_b["eval_records"]

    assert len(dev_recs) == 4
    assert len(eval_recs) == 1

    # Verification: maximum session ID in dev <= minimum session ID in eval
    max_dev_session = max(r["session_id"] for r in dev_recs)
    min_eval_session = min(r["session_id"] for r in eval_recs)
    assert max_dev_session < min_eval_session

    # Verification: max dev created_at <= min eval created_at
    max_dev_time = max(r["created_at"] for r in dev_recs)
    min_eval_time = min(r["created_at"] for r in eval_recs)
    assert max_dev_time < min_eval_time


# ---------------------------------------------------------------------------
# Test 9: Deterministic report structure, blocked claims & causal disclaimer
# ---------------------------------------------------------------------------
def test_deterministic_reporting_and_causal_disclaimer(test_environment):
    db = test_environment["db"]

    create_linked_record(db, user_id=1, skill_id=1, recommended_action="hard_practice", actual_action="hard_practice")

    report1 = generate_evaluation_readiness_report(db, user_id=1)
    report2 = generate_evaluation_readiness_report(db, user_id=1)

    # Core determinism
    assert report1["is_ready_for_real_data_evaluation"] == report2["is_ready_for_real_data_evaluation"]
    assert report1["dataset_eligibility"] == report2["dataset_eligibility"]
    assert report1["action_coverage"] == report2["action_coverage"]
    assert report1["sufficiency_gates"] == report2["sufficiency_gates"]
    assert report1["blocking_reasons"] == report2["blocking_reasons"]

    # Blocked claims verification
    assert len(report1["blocked_evaluation_claims"]) >= 4
    claims_text = " ".join(report1["blocked_evaluation_claims"]).lower()
    assert "accuracy" in claims_text
    assert "effectiveness" in claims_text
    assert "generalization" in claims_text
    assert "conformal" in claims_text

    # Causal disclaimer verification
    disclaimer = report1["causal_disclaimer"]
    assert "observational prediction only" in disclaimer.lower()
    assert "counterfactual" in disclaimer.lower()

    # Human-readable markdown summary verification
    summary = report1["human_readable_summary"]
    assert "# CWIP Real-Data ML Evaluation Readiness Report" in summary
    assert "Overall Verdict:" in summary
    assert "Dataset Eligibility & Exclusions" in summary
    assert "Sufficiency Gates Status" in summary


# ---------------------------------------------------------------------------
# Test 10: GET /ml/evaluation/readiness API endpoint integration
# ---------------------------------------------------------------------------
def test_get_evaluation_readiness_api_endpoint(test_environment):
    client = test_environment["client"]
    db = test_environment["db"]

    # Seed 1 record for user 1
    create_linked_record(db, user_id=1, skill_id=1, recommended_action="hard_practice", actual_action="hard_practice")

    # 1. Default learner scope
    res = client.get("/ml/evaluation/readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["verdict_status"] == "NOT_READY"
    assert data["is_ready_for_real_data_evaluation"] is False
    assert "Learner (user_id=1)" in data["audit_scope"]
    assert data["dataset_eligibility"]["eligible_count"] == 1
    assert "human_readable_summary" in data

    # 2. Platform scope
    res_platform = client.get("/ml/evaluation/readiness?scope=platform")
    assert res_platform.status_code == 200
    data_platform = res_platform.json()
    assert data_platform["audit_scope"] == "Platform Global"
    assert data_platform["dataset_eligibility"]["eligible_count"] == 1


# ---------------------------------------------------------------------------
# Test 11: Real persistent database current state is NOT_READY
# ---------------------------------------------------------------------------
def test_real_database_readiness_state(test_environment):
    # In an environment with only 2 real outcomes, verify evaluation is correctly blocked
    db = test_environment["db"]
    create_linked_record(db, user_id=1, skill_id=1, recommended_action="hard_practice", actual_action="hard_practice")
    create_linked_record(db, user_id=1, skill_id=1, recommended_action="hard_practice", actual_action="hard_practice")

    report = generate_evaluation_readiness_report(db, user_id=1)
    assert report["is_ready_for_real_data_evaluation"] is False
    assert report["verdict_status"] == "NOT_READY"

    # Fails model fitting gate (N=2 < 30)
    assert report["sufficiency_gates"]["model_fitting_gate"]["passed"] is False

    # Fails platform observations gate (N=2 < 150)
    assert report["sufficiency_gates"]["total_observations_gate"]["passed"] is False

    # Fails distinct learners gate (K=1 < 15)
    assert report["sufficiency_gates"]["distinct_learners_gate"]["passed"] is False

    # Fails action diversity gate (1 action < 2)
    assert report["sufficiency_gates"]["action_diversity_gate"]["passed"] is False


# ---------------------------------------------------------------------------
# Test 12: Track B created_at ordering overrides session ID
# ---------------------------------------------------------------------------
def test_track_b_created_at_ordering_overrides_session_id():
    """
    Finding 2 test: Proves that Track B follows created_at timestamp ordering,
    even when session_id ordering directly disagrees.
    """
    # Session 999 was created at 10:00 (earlier)
    # Session 500 was created at 11:00 (middle)
    # Session 100 was created at 12:00 (later)
    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    records = [
        {
            "user_id": 1,
            "session_id": 999,
            "session_created_at": (base_time + timedelta(hours=0)).isoformat(),
            "actual_action": "hard_practice",
            "mastery_change": 0.05,
        },
        {
            "user_id": 1,
            "session_id": 500,
            "session_created_at": (base_time + timedelta(hours=1)).isoformat(),
            "actual_action": "hard_practice",
            "mastery_change": 0.07,
        },
        {
            "user_id": 1,
            "session_id": 100,
            "session_created_at": (base_time + timedelta(hours=2)).isoformat(),
            "actual_action": "take_assessment",
            "mastery_change": 0.10,
        },
    ]

    track_b = prepare_track_b_partitions(records)
    assert track_b["structural_partition_feasible"] is True

    dev_sessions = [r["session_id"] for r in track_b["dev_records"]]
    eval_sessions = [r["session_id"] for r in track_b["eval_records"]]

    # Under session_id ordering, 100 would be dev and 999 eval.
    # Under created_at ordering, 999 and 500 are dev, and 100 is eval!
    assert dev_sessions == [999, 500]
    assert eval_sessions == [100]


# ---------------------------------------------------------------------------
# Test 13: Track B timezone normalization (Asia/Calcutta +05:30 vs UTC)
# ---------------------------------------------------------------------------
def test_track_b_timezone_normalization_asia_calcutta_and_utc():
    """
    Finding 2 test: Verifies that timestamps in Asia/Calcutta (+05:30) and UTC (Z)
    are properly normalized and ordered by absolute wall-clock UTC time.
    """
    # Record A: 15:00:00+05:30 -> 09:30:00 UTC (earliest)
    # Record B: 10:00:00Z -> 10:00:00 UTC (middle)
    # Record C: 16:00:00+05:30 -> 10:30:00 UTC (latest)
    records = [
        {
            "user_id": 1,
            "session_id": 1,
            "created_at": "2026-11-01T15:00:00+05:30",
            "actual_action": "hard_practice",
            "mastery_change": 0.05,
        },
        {
            "user_id": 1,
            "session_id": 2,
            "created_at": "2026-11-01T10:00:00Z",
            "actual_action": "hard_practice",
            "mastery_change": 0.07,
        },
        {
            "user_id": 1,
            "session_id": 3,
            "created_at": "2026-11-01T16:00:00+05:30",
            "actual_action": "take_assessment",
            "mastery_change": 0.10,
        },
    ]

    track_b = prepare_track_b_partitions(records)
    assert track_b["structural_partition_feasible"] is True

    dev_sessions = [r["session_id"] for r in track_b["dev_records"]]
    eval_sessions = [r["session_id"] for r in track_b["eval_records"]]

    assert dev_sessions == [1, 2]
    assert eval_sessions == [3]


# ---------------------------------------------------------------------------
# Test 14: Track B ordering across aware and naive Calcutta timestamps
# ---------------------------------------------------------------------------
def test_track_b_ordering_across_aware_and_naive_calcutta_timestamps():
    """
    Finding 2 & Final Timestamp Semantics test:
    Proves that Track B correctly orders timestamps across:
    - Naive string representing Asia/Calcutta local time ("2026-11-01T15:00:00" -> 09:30 UTC)
    - Aware UTC string ("2026-11-01T10:00:00Z" -> 10:00 UTC)
    - Aware Asia/Calcutta string ("2026-11-01T16:00:00+05:30" -> 10:30 UTC)
    - Naive Python datetime representing Asia/Calcutta local time (datetime(2026, 11, 1, 16, 30, 0) -> 11:00 UTC)
    All 4 resolve to chronological sequence: [1, 2, 3] in dev and [4] in eval.
    """
    records = [
        {
            "user_id": 1,
            "session_id": 1,
            "created_at": "2026-11-01T15:00:00",  # Naive local Calcutta -> 09:30 UTC
            "actual_action": "hard_practice",
            "mastery_change": 0.05,
        },
        {
            "user_id": 1,
            "session_id": 2,
            "created_at": "2026-11-01T10:00:00Z",  # Aware UTC -> 10:00 UTC
            "actual_action": "hard_practice",
            "mastery_change": 0.07,
        },
        {
            "user_id": 1,
            "session_id": 3,
            "created_at": "2026-11-01T16:00:00+05:30",  # Aware Calcutta -> 10:30 UTC
            "actual_action": "hard_practice",
            "mastery_change": 0.06,
        },
        {
            "user_id": 1,
            "session_id": 4,
            "created_at": datetime(2026, 11, 1, 16, 30, 0),  # Naive datetime local Calcutta -> 11:00 UTC
            "actual_action": "take_assessment",
            "mastery_change": 0.10,
        },
    ]

    track_b = prepare_track_b_partitions(records)
    assert track_b["structural_partition_feasible"] is True

    dev_sessions = [r["session_id"] for r in track_b["dev_records"]]
    eval_sessions = [r["session_id"] for r in track_b["eval_records"]]

    assert dev_sessions == [1, 2, 3]
    assert eval_sessions == [4]


# ---------------------------------------------------------------------------
# Test 15: Track B structural partition feasibility vs statistical readiness
# ---------------------------------------------------------------------------
def test_track_b_structural_feasibility_vs_statistical_readiness():
    """
    Finding 3 test: Explicitly proves that a 2-observation, 1-learner dataset
    is structurally partition feasible, but NOT statistically evaluation ready
    and NOT model evaluation eligible.
    """
    records = [
        {
            "user_id": 1,
            "session_id": 1,
            "session_created_at": "2026-11-01T10:00:00Z",
            "actual_action": "hard_practice",
            "mastery_change": 0.05,
        },
        {
            "user_id": 1,
            "session_id": 2,
            "session_created_at": "2026-11-01T11:00:00Z",
            "actual_action": "hard_practice",
            "mastery_change": 0.07,
        },
    ]

    track_b = prepare_track_b_partitions(records)

    # Structural feasibility is True (chronological split exists: 1 dev, 1 eval)
    assert track_b["structural_partition_feasible"] is True
    assert track_b["feasible"] is True

    # Statistical readiness is False (insufficient power/samples)
    assert track_b["statistical_evaluation_ready"] is False
    assert track_b["model_evaluation_eligible"] is False

    # Limitations explicitly documented
    assert len(track_b["limitations"]) >= 3
    limitations_text = " ".join(track_b["limitations"])
    assert "Evaluation sample size" in limitations_text
    assert "Eligible learners" in limitations_text
    assert "Development history" in limitations_text


# ---------------------------------------------------------------------------
# Test 16: Verified linked historical flat snapshot remains eligible
# ---------------------------------------------------------------------------
def test_verified_linked_historical_flat_snapshot_is_eligible_in_readiness_audit(test_environment):
    """
    Finding 4 test: Confirms that Step 3.3 rules remain authoritative:
    - Verified linked historical flat snapshot (Case B) without _metadata is ELIGIBLE.
    - Unlinked flat snapshot is EXCLUDED under unlinked_outcome.
    - Client-claimed spoofed provenance is EXCLUDED under untrusted_provenance.
    """
    db = test_environment["db"]

    # 1. Verified linked historical flat snapshot on RecommendationSession (Case B)
    session_flat = RecommendationSession(
        user_id=1,
        skill_id=1,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=sample_flat_features(),  # Flat dict without _metadata
        status="completed",
    )
    db.add(session_flat)
    db.commit()
    db.refresh(session_flat)

    outcome_linked = LearningOutcome(
        user_id=1,
        skill_id=1,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=session_flat.id,
        feature_snapshot=session_flat.feature_snapshot,
    )
    db.add(outcome_linked)
    db.commit()

    # 2. Unlinked flat snapshot
    outcome_unlinked = LearningOutcome(
        user_id=1,
        skill_id=1,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=None,
        feature_snapshot=sample_flat_features(),
    )
    db.add(outcome_unlinked)
    db.commit()

    # 3. Spoofed client metadata
    spoofed_snap = {
        "_metadata": {"schema_version": "2.0", "provenance": "unverified_client"},
        "remediation_context": {"features": sample_flat_features()},
    }
    session_spoofed = RecommendationSession(
        user_id=1,
        skill_id=1,
        recommended_action="hard_practice",
        before_mastery=0.60,
        feature_snapshot=spoofed_snap,
        status="completed",
    )
    db.add(session_spoofed)
    db.commit()
    db.refresh(session_spoofed)

    outcome_spoofed = LearningOutcome(
        user_id=1,
        skill_id=1,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.60,
        after_mastery=0.70,
        mastery_change=0.10,
        outcome="positive",
        is_test=False,
        recommendation_session_id=session_spoofed.id,
        feature_snapshot=session_spoofed.feature_snapshot,
    )
    db.add(outcome_spoofed)
    db.commit()

    audit = audit_data_readiness(db, user_id=1)
    assert audit["total_inspected"] == 3
    # Verified linked historical flat snapshot is eligible
    assert audit["eligible_count"] == 1
    assert audit["excluded_count"] == 2
    assert audit["exclusion_reasons"]["unlinked_outcome"] == 1
    assert audit["exclusion_reasons"]["untrusted_provenance"] == 1
