"""
CWIP Real-Data Model Evaluation Readiness & Statistical Governance Module
Phase 5 Step 4

Provides:
1. Data Readiness Audit: Reuses validate_and_extract_training_record, tracks exclusions,
   enforces learner isolation, and categorizes failure reasons.
2. Data Sufficiency Gates: Deterministic verification of dataset sample counts (N),
   distinct learners (K), action diversity, action support, and cluster thresholds.
3. Evaluation Partitioning Readiness:
   - Track A: Disjoint unseen learner clusters (K_dev, K_cal, K_eval) with leakage prevention.
   - Track B: Chronological partitioning for existing learners with no-future-information leakage.
4. Baseline Evaluation Infrastructure:
   - Baseline 1: Zero mastery change (Delta y = 0.0)
   - Baseline 2: Development global mean
   - Baseline 3: Development action-specific mean with strict support requirements
5. Comprehensive Readiness Report: Machine-readable JSON and human-readable markdown summary,
   with clear distinctions between observational prediction and causal effectiveness.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statistics import mean
from typing import Any

PLATFORM_TIMEZONE = ZoneInfo("Asia/Calcutta")

from sqlalchemy.orm import Session

from ..models import LearningOutcome, RecommendationSession, Skill, User
from .actions import ACTIONS, ACTION_SET, is_valid_action

CANONICAL_ACTIONS = ACTIONS
from .features import FEATURE_COLUMNS, adapt_legacy_snapshot, extract_numeric_features_from_snapshot
from .real_training import validate_and_extract_training_record


@dataclass
class EvaluationThresholds:
    """Configurable project thresholds based on Phase 5 architectural specifications."""
    min_model_samples: int = 30             # Minimum samples for model fitting (MIN_REAL_SAMPLES)
    min_eval_observations: int = 150        # Full platform evaluation observation threshold
    min_distinct_learners: int = 15         # Minimum unique learners for platform evaluation
    min_eval_cluster_learners: int = 20     # K_eval threshold for conservative deployment evaluation
    min_action_eval_learners: int = 10      # K_eval,a threshold for action-specific evaluation
    min_conformal_cal_clusters: int = 19    # K_cal,a for 95% finite group conformal quantile
    min_action_diversity: int = 2           # Minimum unique action classes in dataset
    min_supported_actions: int = 3          # Minimum actions meeting sample support threshold
    min_action_observations: int = 20       # N_a threshold for action sample support
    min_baseline_action_obs: int = 10       # Minimum dev observations to fit action baseline (N_dev,a >= 10)
    min_baseline_action_learners: int = 5   # Minimum dev learners to fit action baseline (K_dev,a >= 5)
    min_track_b_learner_sessions: int = 2   # Minimum chronological sessions for Track B


def normalize_to_utc(ts: datetime | str | None) -> datetime:
    """
    Normalizes a timestamp (datetime or ISO string) to UTC datetime with tzinfo=timezone.utc.
    - If timezone-aware (e.g. Asia/Calcutta or UTC): converted directly to UTC via astimezone(timezone.utc).
    - If timezone-naive (e.g. from local database without time zone): interpreted as platform
      local time (Asia/Calcutta) in accordance with approved Phase 5 Step 2 architecture,
      then converted to UTC.
    """
    if ts is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(ts, str):
        iso_str = ts.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(iso_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=PLATFORM_TIMEZONE)
        return parsed.astimezone(timezone.utc)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=PLATFORM_TIMEZONE).astimezone(timezone.utc)
        return ts.astimezone(timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


def audit_data_readiness(db: Session, user_id: int | None = None) -> dict:
    """
    Audits database learning outcomes for real-data evaluation readiness.
    If user_id is provided, enforces learner isolation by restricting scope to that user.
    """
    query = db.query(LearningOutcome)
    if user_id is not None:
        query = query.filter(LearningOutcome.user_id == user_id)

    outcomes = query.order_by(LearningOutcome.id.asc()).all()

    total_inspected = len(outcomes)
    eligible_records = []
    excluded_counts = {
        "test_record": 0,
        "unlinked_outcome": 0,
        "invalid_action_or_outcome": 0,
        "session_not_found": 0,
        "session_ownership_mismatch": 0,
        "session_skill_mismatch": 0,
        "session_action_mismatch": 0,
        "invalid_session_snapshot": 0,
        "untrusted_provenance": 0,
        "concordance_mismatch": 0,
        "missing_numeric_features": 0,
        "invalid_numeric_values": 0,
    }

    for o in outcomes:
        if o.is_test:
            excluded_counts["test_record"] += 1
            continue

        if (
            not is_valid_action(o.recommended_action)
            or not is_valid_action(o.actual_action)
            or o.outcome not in {"positive", "negative", "neutral"}
        ):
            excluded_counts["invalid_action_or_outcome"] += 1
            continue

        if o.recommendation_session_id is None:
            excluded_counts["unlinked_outcome"] += 1
            continue

        session = (
            db.query(RecommendationSession)
            .filter(RecommendationSession.id == o.recommendation_session_id)
            .first()
        )
        if not session:
            excluded_counts["session_not_found"] += 1
            continue

        if session.user_id != o.user_id:
            excluded_counts["session_ownership_mismatch"] += 1
            continue

        if session.skill_id != o.skill_id:
            excluded_counts["session_skill_mismatch"] += 1
            continue

        if session.recommended_action != o.recommended_action:
            excluded_counts["session_action_mismatch"] += 1
            continue

        session_snapshot = session.feature_snapshot
        if not isinstance(session_snapshot, dict) or not session_snapshot:
            excluded_counts["invalid_session_snapshot"] += 1
            continue

        if "_metadata" in session_snapshot:
            meta = session_snapshot.get("_metadata")
            if (
                not isinstance(meta, dict)
                or meta.get("schema_version") != "2.0"
                or meta.get("provenance") != "server_generated"
            ):
                excluded_counts["untrusted_provenance"] += 1
                continue

            expected_skill = session_snapshot.get("expected_outcome", {}).get("skill_id")
            if expected_skill is not None and o.skill_id != expected_skill:
                excluded_counts["concordance_mismatch"] += 1
                continue

            features = extract_numeric_features_from_snapshot(session_snapshot)
        else:
            adapted = adapt_legacy_snapshot(session_snapshot, session=session)
            if adapted.get("_metadata", {}).get("provenance") != "legacy_database":
                excluded_counts["untrusted_provenance"] += 1
                continue
            features = extract_numeric_features_from_snapshot(adapted)

        if not isinstance(features, dict) or not set(FEATURE_COLUMNS).issubset(features.keys()):
            excluded_counts["missing_numeric_features"] += 1
            continue

        validated = validate_and_extract_training_record(o, db)
        if validated is None:
            excluded_counts["invalid_numeric_values"] += 1
            continue

        eligible_records.append({
            "outcome_id": o.id,
            "session_id": o.recommendation_session_id,
            "session_created_at": session.created_at,
            "user_id": o.user_id,
            "skill_id": o.skill_id,
            "recommended_action": o.recommended_action,
            "actual_action": o.actual_action,
            "before_mastery": o.before_mastery,
            "after_mastery": o.after_mastery,
            "mastery_change": o.mastery_change,
            "outcome_label": o.outcome,
            "features": validated["features"],
        })

    eligible_count = len(eligible_records)
    excluded_count = total_inspected - eligible_count

    distinct_learners = sorted(list(set(r["user_id"] for r in eligible_records)))
    distinct_skills = sorted(list(set(r["skill_id"] for r in eligible_records)))

    action_counts = {}
    learners_per_action = {}
    for r in eligible_records:
        action = r["actual_action"]
        action_counts[action] = action_counts.get(action, 0) + 1
        learners_per_action.setdefault(action, set()).add(r["user_id"])

    learners_per_action_counts = {
        action: len(learners)
        for action, learners in learners_per_action.items()
    }

    return {
        "total_inspected": total_inspected,
        "eligible_count": eligible_count,
        "excluded_count": excluded_count,
        "exclusion_reasons": excluded_counts,
        "distinct_learners": distinct_learners,
        "distinct_skills": distinct_skills,
        "action_counts": action_counts,
        "learners_per_action": learners_per_action_counts,
        "eligible_records": eligible_records,
    }


def check_data_sufficiency(audit: dict, thresholds: EvaluationThresholds = EvaluationThresholds()) -> dict:
    """Evaluates deterministic readiness gates against audit results."""
    eligible_count = audit["eligible_count"]
    distinct_learners_count = len(audit["distinct_learners"])
    action_counts = audit["action_counts"]
    learners_per_action = audit["learners_per_action"]

    model_fitting_gate = eligible_count >= thresholds.min_model_samples
    total_observations_gate = eligible_count >= thresholds.min_eval_observations
    distinct_learners_gate = distinct_learners_count >= thresholds.min_distinct_learners
    action_diversity_gate = len(action_counts) >= thresholds.min_action_diversity

    supported_actions_count = sum(
        1 for a, count in action_counts.items()
        if count >= thresholds.min_action_observations
    )
    action_sample_support_gate = supported_actions_count >= thresholds.min_supported_actions

    eval_cluster_gate = distinct_learners_count >= thresholds.min_eval_cluster_learners

    conformal_calibration_gate = (
        len(learners_per_action) > 0
        and all(c >= thresholds.min_conformal_cal_clusters for c in learners_per_action.values())
    )

    all_gates_pass = (
        model_fitting_gate
        and total_observations_gate
        and distinct_learners_gate
        and action_diversity_gate
        and action_sample_support_gate
        and eval_cluster_gate
    )

    blocking_reasons = []
    if not model_fitting_gate:
        blocking_reasons.append(
            f"Sample size (N = {eligible_count}) is below minimum model training threshold (N >= {thresholds.min_model_samples})."
        )
    if not total_observations_gate:
        blocking_reasons.append(
            f"Total eligible observations (N = {eligible_count}) below platform evaluation threshold (N >= {thresholds.min_eval_observations})."
        )
    if not distinct_learners_gate:
        blocking_reasons.append(
            f"Distinct learners (K = {distinct_learners_count}) below evaluation threshold (K >= {thresholds.min_distinct_learners})."
        )
    if not action_diversity_gate:
        blocking_reasons.append(
            f"Active action classes ({len(action_counts)}) below required diversity ({thresholds.min_action_diversity})."
        )
    if not action_sample_support_gate:
        blocking_reasons.append(
            f"Supported actions with N_a >= {thresholds.min_action_observations} ({supported_actions_count}) below requirement (>= {thresholds.min_supported_actions})."
        )
    if not eval_cluster_gate:
        blocking_reasons.append(
            f"Evaluation learner clusters (K = {distinct_learners_count}) below deployment threshold (K_eval >= {thresholds.min_eval_cluster_learners})."
        )
    if not conformal_calibration_gate:
        blocking_reasons.append(
            f"Conformal calibration cluster threshold (K_cal,a >= {thresholds.min_conformal_cal_clusters}) not met across actions."
        )

    return {
        "is_ready_for_real_data_evaluation": all_gates_pass,
        "gates": {
            "model_fitting_gate": {
                "passed": model_fitting_gate,
                "current": eligible_count,
                "required": thresholds.min_model_samples,
            },
            "total_observations_gate": {
                "passed": total_observations_gate,
                "current": eligible_count,
                "required": thresholds.min_eval_observations,
            },
            "distinct_learners_gate": {
                "passed": distinct_learners_gate,
                "current": distinct_learners_count,
                "required": thresholds.min_distinct_learners,
            },
            "action_diversity_gate": {
                "passed": action_diversity_gate,
                "current": len(action_counts),
                "required": thresholds.min_action_diversity,
            },
            "action_sample_support_gate": {
                "passed": action_sample_support_gate,
                "current_supported_actions": supported_actions_count,
                "required_supported_actions": thresholds.min_supported_actions,
                "threshold_per_action": thresholds.min_action_observations,
            },
            "eval_cluster_gate": {
                "passed": eval_cluster_gate,
                "current": distinct_learners_count,
                "required": thresholds.min_eval_cluster_learners,
            },
            "conformal_calibration_gate": {
                "passed": conformal_calibration_gate,
                "required_clusters_per_action": thresholds.min_conformal_cal_clusters,
                "learners_per_action": learners_per_action,
            },
        },
        "blocking_reasons": blocking_reasons,
    }


def extract_record_timestamp(r: dict) -> datetime:
    ts = r.get("session_created_at") or r.get("created_at")
    return normalize_to_utc(ts)


def prepare_track_a_partitions(records: list[dict], thresholds: EvaluationThresholds = EvaluationThresholds()) -> dict:
    """
    Prepares Track A: Unseen learner clustering (disjoint learner partitions).
    Guarantees zero identity overlap and zero cross-partition leakage.
    Separates structural partition feasibility from statistical evaluation readiness.
    """
    if not records:
        return {
            "feasible": False,
            "structural_partition_feasible": False,
            "statistical_evaluation_ready": False,
            "model_evaluation_eligible": False,
            "reason": "No eligible records available to partition.",
            "dev_learners": [],
            "cal_learners": [],
            "eval_learners": [],
            "dev_records": [],
            "cal_records": [],
            "eval_records": [],
        }

    learner_ids = sorted(list(set(r["user_id"] for r in records)))
    k = len(learner_ids)

    if k < 3:
        return {
            "feasible": False,
            "structural_partition_feasible": False,
            "statistical_evaluation_ready": False,
            "model_evaluation_eligible": False,
            "reason": f"Insufficient distinct learners (K = {k} < 3). Disjoint development, calibration, and evaluation partitions require at least 3 unique learners.",
            "dev_learners": [],
            "cal_learners": [],
            "eval_learners": [],
            "dev_records": [],
            "cal_records": [],
            "eval_records": [],
        }

    # Deterministic split: ~60% dev, ~20% cal, ~20% eval (minimum 1 each)
    n_eval = max(1, int(round(k * 0.20)))
    n_cal = max(1, int(round(k * 0.20)))
    n_dev = k - n_cal - n_eval

    if n_dev < 1:
        n_dev = 1
        if n_cal > 1:
            n_cal -= 1
        elif n_eval > 1:
            n_eval -= 1

    dev_learners = set(learner_ids[:n_dev])
    cal_learners = set(learner_ids[n_dev:n_dev + n_cal])
    eval_learners = set(learner_ids[n_dev + n_cal:])

    # Strictly verify zero overlap
    assert len(dev_learners & cal_learners) == 0, "Leakage detected: dev and cal learners overlap"
    assert len(dev_learners & eval_learners) == 0, "Leakage detected: dev and eval learners overlap"
    assert len(cal_learners & eval_learners) == 0, "Leakage detected: cal and eval learners overlap"

    dev_records = [r for r in records if r["user_id"] in dev_learners]
    cal_records = [r for r in records if r["user_id"] in cal_learners]
    eval_records = [r for r in records if r["user_id"] in eval_learners]

    structural_feasible = True
    statistical_ready = (
        k >= thresholds.min_distinct_learners
        and len(eval_learners) >= thresholds.min_eval_cluster_learners
    )
    model_eval_eligible = (
        statistical_ready
        and len(dev_records) >= thresholds.min_model_samples
    )

    return {
        "feasible": structural_feasible,
        "structural_partition_feasible": structural_feasible,
        "statistical_evaluation_ready": statistical_ready,
        "model_evaluation_eligible": model_eval_eligible,
        "reason": (
            f"Successfully partitioned {k} learners into {len(dev_learners)} dev, {len(cal_learners)} cal, and {len(eval_learners)} eval clusters "
            f"({'STATISTICALLY UNREADY for evaluation' if not statistical_ready else 'READY for evaluation'})."
        ),
        "dev_learners": sorted(list(dev_learners)),
        "cal_learners": sorted(list(cal_learners)),
        "eval_learners": sorted(list(eval_learners)),
        "dev_records": dev_records,
        "cal_records": cal_records,
        "eval_records": eval_records,
    }


def prepare_track_b_partitions(records: list[dict], thresholds: EvaluationThresholds = EvaluationThresholds()) -> dict:
    """
    Prepares Track B: Existing learner chronological split.
    Guarantees no future information leakage:
    - Authoritative chronological field is session timestamp (RecommendationSession.created_at).
    - Timestamps are normalized to UTC across Asia/Calcutta (+05:30) and UTC offsets.
    - Deterministic tie-breakers: session_id, then outcome_id.
    - Evaluated records are strictly later than development records.
    - Explicitly distinguishes structural partition feasibility from statistical evaluation readiness.
    """
    if not records:
        return {
            "feasible": False,
            "structural_partition_feasible": False,
            "statistical_evaluation_ready": False,
            "model_evaluation_eligible": False,
            "reason": "No eligible records available to partition.",
            "eligible_learners_count": 0,
            "dev_records": [],
            "eval_records": [],
            "limitations": ["No eligible records found."],
        }

    by_user = {}
    for r in records:
        by_user.setdefault(r["user_id"], []).append(r)

    # Sort each user's records chronologically by:
    # 1. Authoritative timestamp (normalized to UTC)
    # 2. session_id (deterministic tie-breaker 1)
    # 3. outcome_id (deterministic tie-breaker 2)
    for u in by_user:
        by_user[u].sort(
            key=lambda x: (
                extract_record_timestamp(x),
                x.get("session_id", 0),
                x.get("outcome_id", 0)
            )
        )

    eligible_users = {
        u: recs for u, recs in by_user.items()
        if len(recs) >= thresholds.min_track_b_learner_sessions
    }

    if not eligible_users:
        return {
            "feasible": False,
            "structural_partition_feasible": False,
            "statistical_evaluation_ready": False,
            "model_evaluation_eligible": False,
            "reason": f"No learners have multiple chronological sessions (minimum {thresholds.min_track_b_learner_sessions} required per learner for chronological split).",
            "eligible_learners_count": 0,
            "dev_records": [],
            "eval_records": [],
            "limitations": [
                f"No learner satisfies the minimum session count (>= {thresholds.min_track_b_learner_sessions}) for chronological forecasting."
            ],
        }

    dev_records = []
    eval_records = []

    for u, recs in eligible_users.items():
        # Earliest records go to development; latest session(s) go to evaluation
        split_idx = max(1, len(recs) - 1)
        u_dev = recs[:split_idx]
        u_eval = recs[split_idx:]

        # Verify chronological ordering (strictly no future leakage)
        max_dev_time = extract_record_timestamp(u_dev[-1])
        min_eval_time = extract_record_timestamp(u_eval[0])
        assert max_dev_time <= min_eval_time, (
            f"Chronological timestamp leakage for user {u}: max_dev ({max_dev_time}) > min_eval ({min_eval_time})"
        )

        if max_dev_time == min_eval_time:
            max_dev_session = max(r.get("session_id", 0) for r in u_dev)
            min_eval_session = min(r.get("session_id", 0) for r in u_eval)
            assert max_dev_session <= min_eval_session, (
                f"Chronological session_id leakage for user {u}: max_dev ({max_dev_session}) > min_eval ({min_eval_session})"
            )

        dev_records.extend(u_dev)
        eval_records.extend(u_eval)

    structural_feasible = len(eligible_users) > 0
    k_learners = len(eligible_users)
    n_dev = len(dev_records)
    n_eval = len(eval_records)

    # Statistical evaluation readiness requires adequate sample size and learner coverage in evaluation
    statistical_ready = (
        structural_feasible
        and n_dev >= thresholds.min_model_samples
        and n_eval >= 20
        and k_learners >= thresholds.min_distinct_learners
    )

    model_eval_eligible = (
        statistical_ready
        and n_dev >= thresholds.min_model_samples
    )

    limitations = []
    if not statistical_ready:
        if n_eval < 20:
            limitations.append(
                f"Evaluation sample size (N_eval = {n_eval}) is below statistical evaluation threshold (N_eval >= 20)."
            )
        if k_learners < thresholds.min_distinct_learners:
            limitations.append(
                f"Eligible learners (K = {k_learners}) below platform evaluation threshold (K >= {thresholds.min_distinct_learners})."
            )
        if n_dev < thresholds.min_model_samples:
            limitations.append(
                f"Development history (N_dev = {n_dev}) below minimum model fitting threshold (N_dev >= {thresholds.min_model_samples})."
            )
        limitations.append(
            "Chronological partition is structurally feasible for sequencing, but statistically insufficient to claim model accuracy or educational effectiveness."
        )

    return {
        "feasible": structural_feasible,
        "structural_partition_feasible": structural_feasible,
        "statistical_evaluation_ready": statistical_ready,
        "model_evaluation_eligible": model_eval_eligible,
        "reason": (
            f"Chronological partitioning structurally feasible across {k_learners} learner(s) "
            f"({n_dev} dev, {n_eval} eval observations), but "
            f"{'STATISTICALLY UNREADY for evaluation' if not statistical_ready else 'READY for evaluation'}."
        ),
        "eligible_learners_count": k_learners,
        "dev_records": dev_records,
        "eval_records": eval_records,
        "limitations": limitations,
    }


class ZeroMasteryBaseline:
    """Regression Baseline 1: Null hypothesis of zero empirical mastery change."""
    def predict(self, sample: dict) -> float:
        return 0.0

    def evaluate(self, samples: list[dict]) -> float | None:
        if not samples:
            return None
        return round(mean(abs(s["mastery_change"] - 0.0) for s in samples), 4)


class GlobalMeanBaseline:
    """Regression Baseline 2: Development-set historical global mean."""
    def __init__(self):
        self.mean_: float | None = None
        self.fitted_samples_: int = 0

    def fit(self, dev_samples: list[dict]) -> "GlobalMeanBaseline":
        if not dev_samples:
            self.mean_ = None
            self.fitted_samples_ = 0
            return self
        self.fitted_samples_ = len(dev_samples)
        self.mean_ = round(mean(s["mastery_change"] for s in dev_samples), 4)
        return self

    def predict(self, sample: dict) -> float | None:
        return self.mean_

    def evaluate(self, samples: list[dict]) -> float | None:
        if not samples or self.mean_ is None:
            return None
        return round(mean(abs(s["mastery_change"] - self.mean_) for s in samples), 4)


class ActionSpecificMeanBaseline:
    """
    Regression Baseline 3: Development-set historical action-specific mean.
    Enforces minimum observation (N_dev,a >= 10) and learner (K_dev,a >= 5) support thresholds.
    Unsupported actions return None and are never assigned fabricated predictions.
    """
    def __init__(self):
        self.action_means_: dict[str, float] = {}
        self.action_support_: dict[str, dict] = {}
        self.fitted_samples_: int = 0

    def fit(
        self,
        dev_samples: list[dict],
        min_obs: int = 10,
        min_learners: int = 5
    ) -> "ActionSpecificMeanBaseline":
        self.fitted_samples_ = len(dev_samples)
        by_action = {}
        for s in dev_samples:
            by_action.setdefault(s["actual_action"], []).append(s)

        all_actions = sorted(list(set(CANONICAL_ACTIONS) | set(by_action.keys())))
        for action in all_actions:
            action_samples = by_action.get(action, [])
            count = len(action_samples)
            learners = len(set(s["user_id"] for s in action_samples))

            if count >= min_obs and learners >= min_learners:
                action_mean = round(mean(s["mastery_change"] for s in action_samples), 4)
                self.action_means_[action] = action_mean
                self.action_support_[action] = {
                    "count": count,
                    "learners": learners,
                    "supported": True,
                    "mean": action_mean,
                }
            else:
                self.action_support_[action] = {
                    "count": count,
                    "learners": learners,
                    "supported": False,
                    "mean": None,
                }

        return self

    def predict(self, sample: dict) -> float | None:
        action = sample.get("actual_action")
        if self.action_support_.get(action, {}).get("supported", False):
            return self.action_means_.get(action)
        return None

    def evaluate_intersection(self, samples: list[dict]) -> dict:
        """Evaluates MAE strictly on the eligible intersection where the action baseline is supported."""
        evaluated = []
        for s in samples:
            pred = self.predict(s)
            if pred is not None:
                evaluated.append(abs(s["mastery_change"] - pred))

        count = len(evaluated)
        mae = round(mean(evaluated), 4) if count > 0 else None

        return {
            "mae": mae,
            "evaluated_samples": count,
            "unsupported_samples_skipped": len(samples) - count,
        }


def generate_evaluation_readiness_report(
    db: Session,
    user_id: int | None = None,
    thresholds: EvaluationThresholds = EvaluationThresholds()
) -> dict:
    """
    Generates the comprehensive Phase 5 Step 4 Real-Data ML Evaluation Readiness Report.
    Produces both a machine-readable JSON structure and a formatted human-readable summary.
    """
    audit = audit_data_readiness(db, user_id=user_id)
    sufficiency = check_data_sufficiency(audit, thresholds=thresholds)
    track_a = prepare_track_a_partitions(audit["eligible_records"], thresholds=thresholds)
    track_b = prepare_track_b_partitions(audit["eligible_records"], thresholds=thresholds)

    # Baselines readiness analysis
    zero_baseline = ZeroMasteryBaseline()
    global_baseline = GlobalMeanBaseline()
    action_baseline = ActionSpecificMeanBaseline()

    # If dev records available from Track A or global records
    dev_pool = track_a["dev_records"] if track_a["feasible"] else audit["eligible_records"]
    global_baseline.fit(dev_pool)
    action_baseline.fit(
        dev_pool,
        min_obs=thresholds.min_baseline_action_obs,
        min_learners=thresholds.min_baseline_action_learners
    )

    supported_actions = [a for a, s in action_baseline.action_support_.items() if s["supported"]]
    unsupported_actions = [a for a, s in action_baseline.action_support_.items() if not s["supported"]]

    is_ready = sufficiency["is_ready_for_real_data_evaluation"]
    scope = f"Learner (user_id={user_id})" if user_id is not None else "Platform Global"

    blocked_claims = [
        "Real-world model accuracy claims (no model trained or authorized for deployment).",
        "Action-specific pedagogical effectiveness claims (adherence is self-reported, observational data lacks counterfactual controls).",
        "Learner generalization claims (insufficient cluster sample to guarantee coverage on unseen learners).",
        "Conformal prediction interval coverage guarantees (insufficient calibration clusters to form finite 95% quantiles).",
    ]

    causal_disclaimer = (
        "Observational prediction only. Associations between actions and empirical mastery changes "
        "reflect historical patterns and do not establish causal pedagogical effectiveness. "
        "Real-data model evaluation measures observational policy imitation, not counterfactual efficacy."
    )

    # Human-readable summary
    summary_lines = [
        f"# CWIP Real-Data ML Evaluation Readiness Report",
        f"**Audit Scope:** {scope}",
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
        f"**Overall Verdict:** {'READY' if is_ready else 'NOT READY FOR REAL-DATA ML EVALUATION'}",
        "",
        "## 1. Dataset Eligibility & Exclusions",
        f"- Total outcomes inspected: {audit['total_inspected']}",
        f"- Eligible real outcomes: {audit['eligible_count']}",
        f"- Excluded outcomes: {audit['excluded_count']}",
        f"  - Test/synthetic records: {audit['exclusion_reasons']['test_record']}",
        f"  - Unlinked outcomes: {audit['exclusion_reasons']['unlinked_outcome']}",
        f"  - Session mismatches / invalid snapshots: {sum(v for k, v in audit['exclusion_reasons'].items() if k not in {'test_record', 'unlinked_outcome'})}",
        f"- Distinct eligible learners: {len(audit['distinct_learners'])} (IDs: {audit['distinct_learners']})",
        f"- Distinct eligible skills: {len(audit['distinct_skills'])} (IDs: {audit['distinct_skills']})",
        "",
        "## 2. Action Coverage & Support",
    ]

    for action in CANONICAL_ACTIONS:
        count = audit["action_counts"].get(action, 0)
        learners = audit["learners_per_action"].get(action, 0)
        status = "Supported (N_a >= 20)" if count >= thresholds.min_action_observations else "Insufficient"
        summary_lines.append(f"- `{action}`: {count} observations across {learners} learners ({status})")

    summary_lines.extend([
        "",
        "## 3. Sufficiency Gates Status",
        f"- Model Training Gate (N >= {thresholds.min_model_samples}): {'PASSED' if sufficiency['gates']['model_fitting_gate']['passed'] else 'FAILED'}",
        f"- Total Observations Gate (N >= {thresholds.min_eval_observations}): {'PASSED' if sufficiency['gates']['total_observations_gate']['passed'] else 'FAILED'}",
        f"- Distinct Learners Gate (K >= {thresholds.min_distinct_learners}): {'PASSED' if sufficiency['gates']['distinct_learners_gate']['passed'] else 'FAILED'}",
        f"- Action Diversity Gate (>= {thresholds.min_action_diversity} actions): {'PASSED' if sufficiency['gates']['action_diversity_gate']['passed'] else 'FAILED'}",
        f"- Action Sample Support Gate (>= {thresholds.min_supported_actions} actions with N_a >= {thresholds.min_action_observations}): {'PASSED' if sufficiency['gates']['action_sample_support_gate']['passed'] else 'FAILED'}",
        f"- Evaluation Clusters Gate (K_eval >= {thresholds.min_eval_cluster_learners}): {'PASSED' if sufficiency['gates']['eval_cluster_gate']['passed'] else 'FAILED'}",
        "",
        "## 4. Evaluation Partitioning Feasibility & Statistical Readiness",
        f"- Track A (Unseen Learners - Disjoint Clusters):",
        f"  - Structural Partition Feasibility: {'FEASIBLE' if track_a.get('structural_partition_feasible', track_a['feasible']) else 'INFEASIBLE'} — {track_a['reason']}",
        f"  - Statistical Evaluation Readiness: {'READY' if track_a.get('statistical_evaluation_ready', False) else 'NOT READY'}",
        f"  - Model Evaluation Eligibility: {'ELIGIBLE' if track_a.get('model_evaluation_eligible', False) else 'INELIGIBLE'}",
        f"- Track B (Existing Learners - Chronological):",
        f"  - Structural Partition Feasibility: {'FEASIBLE' if track_b.get('structural_partition_feasible', track_b['feasible']) else 'INFEASIBLE'} — {track_b['reason']}",
        f"  - Statistical Evaluation Readiness: {'READY' if track_b.get('statistical_evaluation_ready', False) else 'NOT READY'}",
        f"  - Model Evaluation Eligibility: {'ELIGIBLE' if track_b.get('model_evaluation_eligible', False) else 'INELIGIBLE'}",
    ] + [f"    - Limitation: {lim}" for lim in track_b.get("limitations", [])] + [
        "",
        "## 5. Regression Baselines Support",
        f"- Baseline 1 (Zero Change Delta y = 0.0): SUPPORTED (Null baseline ready)",
        f"- Baseline 2 (Global Mean): {'SUPPORTED' if global_baseline.mean_ is not None else 'UNSUPPORTED'} (Mean = {global_baseline.mean_}, N_dev = {global_baseline.fitted_samples_})",
        f"- Baseline 3 (Action-Specific Mean): {len(supported_actions)} supported actions ({', '.join(supported_actions) if supported_actions else 'none'}), {len(unsupported_actions)} unsupported",
        "",
        "## 6. Blocking Reasons",
    ] + [f"- {r}" for r in sufficiency["blocking_reasons"]] + [
        "",
        "## 7. Governance & Causal Disclaimer",
        causal_disclaimer,
    ])

    return {
        "report_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_scope": scope,
        "is_ready_for_real_data_evaluation": is_ready,
        "verdict_status": "READY" if is_ready else "NOT_READY",
        "dataset_eligibility": {
            "total_inspected": audit["total_inspected"],
            "eligible_count": audit["eligible_count"],
            "excluded_count": audit["excluded_count"],
            "exclusion_reasons": audit["exclusion_reasons"],
            "distinct_learners": audit["distinct_learners"],
            "distinct_skills": audit["distinct_skills"],
        },
        "action_coverage": {
            "action_counts": audit["action_counts"],
            "learners_per_action": audit["learners_per_action"],
            "active_action_classes": len(audit["action_counts"]),
        },
        "sufficiency_gates": sufficiency["gates"],
        "blocking_reasons": sufficiency["blocking_reasons"],
        "partition_feasibility": {
            "track_a_unseen_learners": {
                "feasible": track_a["feasible"],
                "structural_partition_feasible": track_a.get("structural_partition_feasible", track_a["feasible"]),
                "statistical_evaluation_ready": track_a.get("statistical_evaluation_ready", False),
                "model_evaluation_eligible": track_a.get("model_evaluation_eligible", False),
                "reason": track_a["reason"],
                "dev_learners": track_a.get("dev_learners", []),
                "cal_learners": track_a.get("cal_learners", []),
                "eval_learners": track_a.get("eval_learners", []),
                "dev_samples_count": len(track_a.get("dev_records", [])),
                "cal_samples_count": len(track_a.get("cal_records", [])),
                "eval_samples_count": len(track_a.get("eval_records", [])),
            },
            "track_b_chronological": {
                "feasible": track_b["feasible"],
                "structural_partition_feasible": track_b.get("structural_partition_feasible", track_b["feasible"]),
                "statistical_evaluation_ready": track_b.get("statistical_evaluation_ready", False),
                "model_evaluation_eligible": track_b.get("model_evaluation_eligible", False),
                "reason": track_b["reason"],
                "eligible_learners_count": track_b.get("eligible_learners_count", 0),
                "dev_samples_count": len(track_b.get("dev_records", [])),
                "eval_samples_count": len(track_b.get("eval_records", [])),
                "limitations": track_b.get("limitations", []),
            },
        },
        "baseline_support": {
            "zero_mastery_baseline": {
                "supported": True,
                "description": "Zero empirical mastery change (Delta y = 0.0)",
            },
            "global_mean_baseline": {
                "supported": global_baseline.mean_ is not None,
                "fitted_samples": global_baseline.fitted_samples_,
                "mean_value": global_baseline.mean_,
            },
            "action_specific_mean_baseline": {
                "supported_actions": supported_actions,
                "unsupported_actions": unsupported_actions,
                "action_support_details": action_baseline.action_support_,
            },
        },
        "blocked_evaluation_claims": blocked_claims,
        "causal_disclaimer": causal_disclaimer,
        "human_readable_summary": "\n".join(summary_lines),
    }
