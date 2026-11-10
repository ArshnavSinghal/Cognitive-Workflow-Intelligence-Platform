from datetime import datetime, timezone
from statistics import mean, pstdev

CANONICAL_ACTIONS = [
    "practice_current",
    "practice_prerequisite",
    "review_concept",
    "easy_practice",
    "hard_practice",
    "take_assessment"
]

VALID_ENGINE_MODES = {"rule_graph_v1", "ml_action_model_v1", "hybrid_v2"}
VALID_PROVENANCES = {"server_generated", "unverified_client", "legacy_database"}
VALID_GRAPH_STATES = {
    "evaluated_healthy",
    "bottleneck_detected",
    "no_prerequisites",
    "not_evaluated"
}

FEATURE_COLUMNS = [
    "average_score",
    "recent_score",
    "adjusted_score",
    "avg_difficulty_weight",
    "consistency",
    "error_rate",
    "mastery",
    "confidence",
    "activity_count",
    "trend"
]

# Difficulty weights: harder problems are worth more when scored well
DIFFICULTY_WEIGHTS = {
    "easy": 0.8,
    "medium": 1.0,
    "hard": 1.3
}


def build_skill_features(activities, mastery, confidence):
    scores = [a.score for a in activities if a.score is not None]

    if not scores:
        return {}

    avg_score = mean(scores)
    recent_score = mean(scores[-3:])

    consistency = max(
        0,
        1 - (pstdev(scores) / 50)
    )

    total_errors = sum(a.errors for a in activities)
    total_duration = sum(a.duration for a in activities)

    error_rate = total_errors / max(total_duration, 1)

    if recent_score > avg_score + 5:
        trend = 1
    elif recent_score < avg_score - 5:
        trend = -1
    else:
        trend = 0

    # Difficulty-adjusted score: scale each score by its difficulty weight,
    # then normalise back to a 0–100 range using the mean weight
    scored_activities = [a for a in activities if a.score is not None]
    weights = [
        DIFFICULTY_WEIGHTS.get(a.difficulty.lower(), 1.0)
        for a in scored_activities
    ]
    weighted_scores = [
        a.score * w
        for a, w in zip(scored_activities, weights)
    ]
    mean_weight = mean(weights) if weights else 1.0
    adjusted_score = mean(weighted_scores) / mean_weight if weighted_scores else avg_score

    # Average difficulty weight across all scored sessions (1.0 = medium baseline)
    avg_difficulty_weight = round(mean_weight, 3)

    return {
        "average_score": round(avg_score, 3),
        "recent_score": round(recent_score, 3),
        "adjusted_score": round(adjusted_score, 3),
        "avg_difficulty_weight": avg_difficulty_weight,
        "consistency": round(consistency, 3),
        "error_rate": round(error_rate, 3),
        "mastery": round(mastery, 3),
        "confidence": round(confidence, 3),
        "activity_count": len(activities),
        "trend": trend
    }


def build_v2_feature_snapshot(
    target_skill,
    target_mastery: float,
    target_confidence: float,
    target_activities: list,
    recommended_action: str,
    remediation_skill=None,
    remediation_mastery: float | None = None,
    remediation_confidence: float | None = None,
    remediation_activities: list | None = None,
    candidate_actions: list[str] | None = None,
    engine_mode: str = "rule_graph_v1",
    graph_diagnosis: dict | None = None,
    provenance: str = "server_generated",
    snapshot_timestamp: str | None = None
) -> dict:
    """
    Constructs a formal, structured version 2.0 feature snapshot adhering to the CWIP
    data contract. Decouples requested target skill context from actual remediation
    skill context, captures multi-hop graph telemetry, expected outcome identity, and
    enforces cryptographic/server-side provenance.
    """
    if engine_mode not in VALID_ENGINE_MODES:
        engine_mode = "rule_graph_v1"

    if provenance not in VALID_PROVENANCES:
        provenance = "server_generated"

    timestamp = snapshot_timestamp or datetime.now(timezone.utc).isoformat()

    # 1. Target Context
    target_id = target_skill.id if hasattr(target_skill, "id") else target_skill["id"]
    target_name = target_skill.name if hasattr(target_skill, "name") else target_skill["name"]
    t_acts = target_activities or []
    target_features = build_skill_features(t_acts, target_mastery, target_confidence) if t_acts else {}
    has_target_activity = bool(target_features)

    target_context = {
        "skill_id": target_id,
        "skill_name": target_name,
        "mastery": round(float(target_mastery), 3),
        "confidence": round(float(target_confidence), 3),
        "has_prior_activity": has_target_activity,
        "activity_count": len(t_acts),
        "features": target_features if has_target_activity else None
    }

    # 2. Remediation Context
    is_remediation = False
    if remediation_skill is not None:
        rem_id = remediation_skill.id if hasattr(remediation_skill, "id") else remediation_skill["id"]
        if rem_id != target_id:
            is_remediation = True

    if is_remediation:
        rem_name = remediation_skill.name if hasattr(remediation_skill, "name") else remediation_skill["name"]
        rem_m = float(remediation_mastery if remediation_mastery is not None else 0.0)
        rem_c = float(remediation_confidence if remediation_confidence is not None else 0.0)
        rem_acts = remediation_activities or []
        rem_features = build_skill_features(rem_acts, rem_m, rem_c) if rem_acts else {}
        has_rem_activity = bool(rem_features)

        remediation_context = {
            "is_remediation": True,
            "skill_id": rem_id,
            "skill_name": rem_name,
            "mastery": round(rem_m, 3),
            "confidence": round(rem_c, 3),
            "has_prior_activity": has_rem_activity,
            "activity_count": len(rem_acts),
            "features": rem_features if has_rem_activity else None
        }
    else:
        remediation_context = {
            "is_remediation": False,
            "skill_id": target_id,
            "skill_name": target_name,
            "mastery": round(float(target_mastery), 3),
            "confidence": round(float(target_confidence), 3),
            "has_prior_activity": has_target_activity,
            "activity_count": len(t_acts),
            "features": target_features if has_target_activity else None
        }

    # 3. Expected Outcome Identity
    expected_outcome = {
        "skill_id": remediation_context["skill_id"],
        "skill_name": remediation_context["skill_name"],
        "expected_action": recommended_action
    }

    # 4. Graph Telemetry
    if graph_diagnosis is None:
        graph_telemetry = {
            "evaluation_status": "not_evaluated",
            "is_graph_driven": False,
            "telemetry_available": False,
            "metrics": {
                "num_prerequisites_evaluated": None,
                "max_prerequisite_risk": None,
                "max_bottleneck_score": None,
                "primary_gap_skill_id": None,
                "primary_gap_distance": None,
                "primary_gap_path": None
            }
        }
    elif not graph_diagnosis.get("has_prerequisites", False):
        graph_telemetry = {
            "evaluation_status": "no_prerequisites",
            "is_graph_driven": False,
            "telemetry_available": True,
            "metrics": {
                "num_prerequisites_evaluated": 0,
                "max_prerequisite_risk": None,
                "max_bottleneck_score": None,
                "primary_gap_skill_id": None,
                "primary_gap_distance": None,
                "primary_gap_path": None
            }
        }
    else:
        prereqs = graph_diagnosis.get("prerequisites", [])
        primary_gap = graph_diagnosis.get("primary_gap")
        risks = [p["risk"] for p in prereqs if "risk" in p and p["risk"] is not None]
        scores = [p["bottleneck_score"] for p in prereqs if "bottleneck_score" in p and p["bottleneck_score"] is not None]
        max_risk = max(risks) if risks else None
        max_score = max(scores) if scores else None

        if primary_gap:
            graph_telemetry = {
                "evaluation_status": "bottleneck_detected",
                "is_graph_driven": True,
                "telemetry_available": True,
                "metrics": {
                    "num_prerequisites_evaluated": len(prereqs),
                    "max_prerequisite_risk": round(max_risk, 3) if max_risk is not None else None,
                    "max_bottleneck_score": round(max_score, 4) if max_score is not None else None,
                    "primary_gap_skill_id": primary_gap.get("skill_id"),
                    "primary_gap_distance": primary_gap.get("distance"),
                    "primary_gap_path": primary_gap.get("path_names")
                }
            }
        else:
            graph_telemetry = {
                "evaluation_status": "evaluated_healthy",
                "is_graph_driven": False,
                "telemetry_available": True,
                "metrics": {
                    "num_prerequisites_evaluated": len(prereqs),
                    "max_prerequisite_risk": round(max_risk, 3) if max_risk is not None else None,
                    "max_bottleneck_score": round(max_score, 4) if max_score is not None else None,
                    "primary_gap_skill_id": None,
                    "primary_gap_distance": None,
                    "primary_gap_path": None
                }
            }

    # 5. Metadata & Action Context
    metadata = {
        "schema_version": "2.0",
        "snapshot_timestamp": timestamp,
        "provenance": provenance,
        "engine_mode": engine_mode
    }

    action_context = {
        "recommended_action": recommended_action,
        "candidate_actions": candidate_actions or list(CANONICAL_ACTIONS)
    }

    return {
        "_metadata": metadata,
        "target_context": target_context,
        "remediation_context": remediation_context,
        "expected_outcome": expected_outcome,
        "graph_telemetry": graph_telemetry,
        "action_context": action_context
    }


def adapt_legacy_snapshot(snapshot: dict, session=None, skill=None) -> dict:
    """
    Controlled adapter providing backward compatibility for legacy flat (v1)
    feature snapshots stored in historical database records. Recovers identity from
    linked session where possible, marks historical prerequisite targets as unknown,
    and preserves missing telemetry semantics without fabricating data.
    """
    if not isinstance(snapshot, dict):
        return {}

    if "_metadata" in snapshot and snapshot["_metadata"].get("schema_version") == "2.0":
        return snapshot

    # Legacy flat dictionary adaptation
    skill_id = None
    skill_name = None
    if skill is not None:
        skill_id = skill.id if hasattr(skill, "id") else skill.get("id")
        skill_name = skill.name if hasattr(skill, "name") else skill.get("name")

    if session is not None:
        rec_action = session.recommended_action
        session_skill_id = session.skill_id
        before_mastery = getattr(session, "before_mastery", 0.0)

        if rec_action == "practice_prerequisite":
            # In legacy prerequisite sessions, session.skill_id was the remediation skill.
            # The original requested target skill was never persisted in the database schema.
            # In accordance with data integrity rules, target identity is marked unknown.
            target_context = {
                "skill_id": None,
                "skill_name": None,
                "target_identity_status": "unknown",
                "mastery": 0.0,
                "confidence": 0.0,
                "has_prior_activity": False,
                "activity_count": 0,
                "features": None
            }
            remediation_context = {
                "is_remediation": True,
                "skill_id": session_skill_id,
                "skill_name": skill_name,
                "mastery": snapshot.get("mastery", before_mastery),
                "confidence": snapshot.get("confidence", 0.0),
                "has_prior_activity": True,
                "activity_count": snapshot.get("activity_count", 0),
                "features": snapshot
            }
            expected_outcome = {
                "skill_id": session_skill_id,
                "skill_name": skill_name,
                "expected_action": rec_action
            }
        else:
            # Direct recommendation
            target_context = {
                "skill_id": session_skill_id,
                "skill_name": skill_name,
                "mastery": snapshot.get("mastery", before_mastery),
                "confidence": snapshot.get("confidence", 0.0),
                "has_prior_activity": True,
                "activity_count": snapshot.get("activity_count", 0),
                "features": snapshot
            }
            remediation_context = {
                "is_remediation": False,
                "skill_id": session_skill_id,
                "skill_name": skill_name,
                "mastery": snapshot.get("mastery", before_mastery),
                "confidence": snapshot.get("confidence", 0.0),
                "has_prior_activity": True,
                "activity_count": snapshot.get("activity_count", 0),
                "features": snapshot
            }
            expected_outcome = {
                "skill_id": session_skill_id,
                "skill_name": skill_name,
                "expected_action": rec_action
            }
    else:
        # Unlinked legacy outcome
        target_context = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery": snapshot.get("mastery", 0.0),
            "confidence": snapshot.get("confidence", 0.0),
            "has_prior_activity": True,
            "activity_count": snapshot.get("activity_count", 0),
            "features": snapshot
        }
        remediation_context = {
            "is_remediation": False,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "mastery": snapshot.get("mastery", 0.0),
            "confidence": snapshot.get("confidence", 0.0),
            "has_prior_activity": True,
            "activity_count": snapshot.get("activity_count", 0),
            "features": snapshot
        }
        expected_outcome = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "expected_action": "unknown"
        }

    return {
        "_metadata": {
            "schema_version": "1.0_migrated",
            "snapshot_timestamp": None,
            "provenance": "legacy_database",
            "engine_mode": "legacy_v1"
        },
        "target_context": target_context,
        "remediation_context": remediation_context,
        "expected_outcome": expected_outcome,
        "graph_telemetry": {
            "evaluation_status": "not_evaluated",
            "is_graph_driven": False,
            "telemetry_available": False,
            "metrics": {
                "num_prerequisites_evaluated": None,
                "max_prerequisite_risk": None,
                "max_bottleneck_score": None,
                "primary_gap_skill_id": None,
                "primary_gap_distance": None,
                "primary_gap_path": None
            }
        },
        "action_context": {
            "recommended_action": session.recommended_action if session else "unknown",
            "candidate_actions": None
        }
    }


def extract_numeric_features_from_snapshot(snapshot: dict) -> dict | None:
    """
    Extracts the ML numeric feature dictionary corresponding to the actual skill
    practiced (remediation_context). Returns None for cold-start prerequisites
    having no prior activity or for malformed snapshots.
    """
    if not isinstance(snapshot, dict):
        return None

    if "_metadata" in snapshot:
        rem_context = snapshot.get("remediation_context", {})
        if isinstance(rem_context, dict):
            return rem_context.get("features")
        return None

    # Legacy flat dictionary
    return snapshot

