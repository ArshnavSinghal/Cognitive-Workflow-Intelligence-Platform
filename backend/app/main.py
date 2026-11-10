from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from statistics import mean, pstdev
import math
from datetime import datetime, timezone

from .database import Base, engine, SessionLocal
from .models import (
    User,
    Activity,
    Skill,
    UserSkill,
    SkillDependency,
    LearningOutcome,
    RecommendationSession
)
from .schemas import (
    UserCreate,
    UserLogin,
    ActivityCreate,
    SkillCreate,
    UserSkillCreate,
    SkillDependencyCreate,
    LearningOutcomeCreate,
    PrerequisiteResponse,
    DescendantsResponse,
    PrerequisiteDiagnosisResponse,
    DependencyPathResponse
)
from .auth import hash_password, verify_password, create_token, verify_token
from .ml.features import (
    build_skill_features,
    build_v2_feature_snapshot,
    adapt_legacy_snapshot,
    extract_numeric_features_from_snapshot
)
from .ml.actions import ACTIONS
from backend.app.ml.actions import is_valid_action
from .ml.predict import predict_action
from .ml.real_training import validate_and_extract_training_record
from .ml.evaluation import generate_evaluation_readiness_report, EvaluationThresholds
from .ml.skill_graph import (
    build_skill_graph,
    validate_dependency_addition,
    get_direct_prerequisites,
    get_transitive_prerequisites,
    get_direct_dependents,
    get_transitive_dependents,
    get_dependency_path,
    get_topological_order,
    diagnose_prerequisites
)
from backend.app.config import is_test_mode

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CWIP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials is None:
        raise HTTPException(
            status_code=403,
            detail="Not authenticated"
        )

    data = verify_token(credentials.credentials)

    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == data["user_id"]).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.get("/")
def home():
    return {"message": "CWIP API is running"}


@app.get("/ml/actions")
def get_actions():
    return {"actions": ACTIONS}


@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):

    existing = db.query(User).filter(User.email == user.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id
    }


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(
        user.password,
        db_user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_token({"user_id": db_user.id})
    print("Token length:", len(token))
    print("Token segments:", len(token.split(".")))

    return {"access_token": token,
        "token_type": "bearer"
    }


@app.post("/activities")
def create_activity(
    activity: ActivityCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # 1. Find the matching skill.
        skill = db.query(Skill).filter(
            Skill.name == activity.topic
        ).first()

        # 2. Validate the recommendation session first.
        recommendation_session = None

        if activity.recommendation_session_id is not None:
            session_query = db.query(
                RecommendationSession
            ).filter(
                RecommendationSession.id
                == activity.recommendation_session_id
            )
            # Explicit concurrency control via database row-level locking.
            # On PostgreSQL, SELECT ... FOR UPDATE acquires an exclusive row lock,
            # serializing concurrent activity submissions for the same session.
            # On SQLite, with_for_update() is supported natively under its transaction lock.
            # Database locking exceptions are not swallowed and safely trigger rollback.
            bind = db.get_bind()
            dialect_name = bind.dialect.name if bind is not None else ""
            if dialect_name in {"postgresql", "sqlite", "mysql", "oracle"}:
                session_query = session_query.with_for_update()
            else:
                session_query = session_query.with_for_update()

            recommendation_session = session_query.first()

            if not recommendation_session or recommendation_session.user_id != user.id:
                raise HTTPException(
                    status_code=404,
                    detail="Recommendation session not found"
                )

            if not skill or recommendation_session.skill_id != skill.id:
                raise HTTPException(
                    status_code=400,
                    detail="Session skill does not match activity skill"
                )

            if recommendation_session.status != "pending":
                raise HTTPException(
                    status_code=400,
                    detail="Recommendation session already evaluated"
                )

            existing_outcome = db.query(LearningOutcome).filter(
                LearningOutcome.recommendation_session_id
                == recommendation_session.id
            ).first()

            if existing_outcome:
                raise HTTPException(
                    status_code=400,
                    detail="Recommendation session already evaluated"
                )

        # 3. Record the activity.
        activity_data = activity.model_dump(
            exclude={"recommendation_session_id"}
        )
        new_activity = Activity(
            user_id=user.id,
            **activity_data
        )
        db.add(new_activity)
        db.flush()

        mastery_updated = False
        outcome_created = False
        learning_outcome = None

        # 4. Recalculate mastery and confidence.
        if skill:
            activities = db.query(Activity).filter(
                Activity.user_id == user.id,
                Activity.topic == skill.name
            ).order_by(Activity.timestamp.asc()).all()

            metrics = calculate_skill_metrics(activities)

            if metrics is not None:
                mastery = metrics["mastery"]
                confidence = metrics["confidence"]

                user_skill = db.query(UserSkill).filter(
                    UserSkill.user_id == user.id,
                    UserSkill.skill_id == skill.id
                ).first()

                if user_skill:
                    user_skill.mastery = mastery
                    user_skill.confidence = confidence
                    user_skill.last_updated = datetime.now(timezone.utc)
                else:
                    user_skill = UserSkill(
                        user_id=user.id,
                        skill_id=skill.id,
                        mastery=mastery,
                        confidence=confidence,
                        last_updated=datetime.now(timezone.utc)
                    )
                    db.add(user_skill)

                mastery_updated = True

                # 5. Record the outcome immediately.
                if recommendation_session:
                    before_mastery = recommendation_session.before_mastery
                    after_mastery = mastery
                    mastery_change = round(
                        after_mastery - before_mastery, 3
                    )

                    if mastery_change > 0.05:
                        result = "positive"
                    elif mastery_change < -0.05:
                        result = "negative"
                    else:
                        result = "neutral"

                    learning_outcome = LearningOutcome(
                        user_id=user.id,
                        skill_id=skill.id,
                        recommended_action=(
                            recommendation_session.recommended_action
                        ),
                        actual_action=activity.activity_type,
                        before_mastery=before_mastery,
                        after_mastery=after_mastery,
                        mastery_change=mastery_change,
                        outcome=result,
                        is_test=is_test_mode(),
                        feature_snapshot=(
                            recommendation_session.feature_snapshot
                        ),
                        recommendation_session_id=recommendation_session.id
                    )

                    db.add(learning_outcome)
                    recommendation_session.status = "evaluated"
                    outcome_created = True

        # 6. Commit all changes together.
        db.commit()
        db.refresh(new_activity)

        resp = {
            "message": "Activity recorded successfully",
            "activity_id": new_activity.id,
            "skill": skill.name if skill else None,
            "mastery_updated": mastery_updated,
            "outcome_created": outcome_created
        }
        if outcome_created and learning_outcome:
            resp["outcome_id"] = learning_outcome.id
            resp["recommendation_session_id"] = recommendation_session.id
            resp["mastery_change"] = learning_outcome.mastery_change
            resp["outcome"] = learning_outcome.outcome

        return resp

    except Exception:
        db.rollback()
        raise


@app.get("/activities")
def get_activities(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activities = db.query(Activity).filter(
        Activity.user_id == user.id
    ).order_by(
        Activity.timestamp.desc()
    ).limit(10).all()

    return {
        "total": len(activities),
        "activities": [
            {
                "id": item.id,
                "activity_type": item.activity_type,
                "subject": item.subject,
                "topic": item.topic,
                "duration": item.duration,
                "difficulty": item.difficulty,
                "score": item.score,
                "errors": item.errors,
                "timestamp": item.timestamp.isoformat()
                    if item.timestamp else None
            }
            for item in activities
        ]
    }


@app.post("/skills")
def create_skill(
    skill: SkillCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raise HTTPException(
        status_code=403,
        detail="Global skill creation is disabled. Administrative privileges required."
    )


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    if get_current_user in app.dependency_overrides:
        try:
            return app.dependency_overrides[get_current_user]()
        except Exception:
            pass
    if credentials is None:
        return None
    data = verify_token(credentials.credentials)
    if not data or "user_id" not in data:
        return None
    return db.query(User).filter(User.id == data["user_id"]).first()


@app.get("/skills")
def list_skills(
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    skills = db.query(Skill).order_by(Skill.id.asc()).all()
    user_skills_map = {}
    if user is not None:
        user_skills = db.query(UserSkill).filter(
            UserSkill.user_id == user.id
        ).all()
        user_skills_map = {us.skill_id: us for us in user_skills}

    result = []
    for s in skills:
        us = user_skills_map.get(s.id)
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "is_enrolled": us is not None,
            "mastery": round(us.mastery, 4) if us else None,
            "confidence": round(us.confidence, 4) if us else None,
            "last_updated": (
                us.last_updated.isoformat()
                if us and us.last_updated
                else None
            ),
        })
    return {"skills": result, "total": len(result)}


@app.get("/skills/{skill_id}")
def get_skill_details(
    skill_id: int,
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    user_skill = None
    if user is not None:
        user_skill = db.query(UserSkill).filter(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == skill_id
        ).first()

    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "is_enrolled": user_skill is not None,
        "mastery": round(user_skill.mastery, 4) if user_skill else None,
        "confidence": round(user_skill.confidence, 4) if user_skill else None,
        "last_updated": (
            user_skill.last_updated.isoformat()
            if user_skill and user_skill.last_updated
            else None
        ),
    }


@app.post("/skills/{skill_id}/enroll")
def enroll_in_skill(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Concurrency control: Acquire a PostgreSQL row-level lock on the authenticated learner's
    # user record using with_for_update() to serialize concurrent enrollment requests for this user.
    user_record = db.query(User).filter(User.id == user.id).with_for_update().first()
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == skill_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Learner is already enrolled in this skill"
        )

    new_user_skill = UserSkill(
        user_id=user.id,
        skill_id=skill_id,
        mastery=0.0,
        confidence=0.0,
        last_updated=datetime.now(timezone.utc)
    )

    try:
        db.add(new_user_skill)
        db.commit()
        db.refresh(new_user_skill)
    except IntegrityError as exc:
        db.rollback()
        pgcode = getattr(exc.orig, "pgcode", None) or getattr(exc.orig, "sqlstate", None)
        err_msg = str(exc).lower()
        if pgcode == "23505" or "unique" in err_msg or "duplicate" in err_msg:
            raise HTTPException(
                status_code=400,
                detail="Learner is already enrolled in this skill"
            )
        raise HTTPException(
            status_code=400,
            detail="Database integrity constraint violation"
        )
    except Exception:
        db.rollback()
        raise

    return {
        "message": f"Successfully enrolled in {skill.name}",
        "skill_id": skill.id,
        "skill_name": skill.name,
        "user_skill_id": new_user_skill.id,
        "is_enrolled": True,
        "mastery": 0.0,
        "confidence": 0.0
    }


@app.get("/skills/{skill_id}/profile")
def get_skill_profile(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == skill_id
    ).first()

    is_enrolled = user_skill is not None

    activities = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.topic == skill.name
    ).order_by(Activity.timestamp.asc()).all()

    total_activities = len(activities)

    recent_activity = None
    trend = "insufficient_data"

    if total_activities > 0:
        latest = activities[-1]
        recent_activity = {
            "id": latest.id,
            "activity_type": latest.activity_type,
            "score": latest.score,
            "duration": latest.duration,
            "difficulty": latest.difficulty,
            "timestamp": (
                latest.timestamp.isoformat()
                if latest.timestamp
                else None
            ),
        }
        metrics = calculate_skill_metrics(activities)
        if metrics:
            trend = metrics.get("trend", "stable")

    # Real evaluated learning outcomes for this user and skill
    real_outcomes = db.query(LearningOutcome).filter(
        LearningOutcome.user_id == user.id,
        LearningOutcome.skill_id == skill_id,
        LearningOutcome.is_test == False
    ).order_by(LearningOutcome.id.asc()).all()

    total_real_evaluated = len(real_outcomes)

    if total_real_evaluated > 0:
        positive_outcomes = sum(
            1 for o in real_outcomes if o.outcome == "positive"
        )
        neutral_outcomes = sum(
            1 for o in real_outcomes if o.outcome == "neutral"
        )
        negative_outcomes = sum(
            1 for o in real_outcomes if o.outcome == "negative"
        )
        avg_change = (
            sum(o.mastery_change for o in real_outcomes) / total_real_evaluated
        )
        average_mastery_change = round(avg_change, 4)

        recs_followed = sum(
            1 for o in real_outcomes
            if o.recommended_action == o.actual_action
        )
        recs_not_followed = total_real_evaluated - recs_followed
        adherence_rate = round(
            (recs_followed / total_real_evaluated) * 100, 2
        )
        adherence = {
            "recommendations_followed": recs_followed,
            "recommendations_not_followed": recs_not_followed,
            "adherence_rate": adherence_rate,
        }
    else:
        positive_outcomes = 0
        neutral_outcomes = 0
        negative_outcomes = 0
        average_mastery_change = None
        adherence = None

    return {
        "skill_id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "is_enrolled": is_enrolled,
        "enrolled_at": (
            user_skill.last_updated.isoformat()
            if (user_skill and user_skill.last_updated)
            else None
        ),
        "mastery": round(user_skill.mastery, 4) if user_skill else None,
        "confidence": round(user_skill.confidence, 4) if user_skill else None,
        "trend": trend,
        "total_activities": total_activities,
        "recent_activity": recent_activity,
        "total_real_evaluated": total_real_evaluated,
        "positive_outcomes": positive_outcomes,
        "neutral_outcomes": neutral_outcomes,
        "negative_outcomes": negative_outcomes,
        "average_mastery_change": average_mastery_change,
        "adherence": adherence,
    }


@app.post("/user-skills")
def create_user_skill(
    skill: UserSkillCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    new_user_skill = UserSkill(
        user_id=user.id,
        **skill.model_dump()
    )

    db.add(new_user_skill)
    db.commit()
    db.refresh(new_user_skill)

    return {
        "message": "User skill added successfully",
        "user_skill_id": new_user_skill.id
    }


@app.post("/skill-dependencies")
def create_dependency(
    dependency: SkillDependencyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raise HTTPException(
        status_code=403,
        detail="Global skill dependency creation is disabled. Administrative privileges required."
    )


@app.get("/skills/{skill_id}/prerequisites", response_model=PrerequisiteResponse)
def get_skill_prerequisites(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    G = build_skill_graph(db)
    direct = get_direct_prerequisites(G, skill_id)
    transitive = get_transitive_prerequisites(G, skill_id)

    return {
        "skill_id": skill.id,
        "skill_name": skill.name,
        "direct_prerequisites": direct,
        "transitive_prerequisites": transitive
    }


@app.get("/skills/{skill_id}/descendants", response_model=DescendantsResponse)
def get_skill_descendants(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    G = build_skill_graph(db)
    direct = get_direct_dependents(G, skill_id)
    transitive = get_transitive_dependents(G, skill_id)

    return {
        "skill_id": skill.id,
        "skill_name": skill.name,
        "direct_dependents": direct,
        "transitive_dependents": transitive
    }


@app.get("/skills/{skill_id}/diagnosis", response_model=PrerequisiteDiagnosisResponse)
def get_prerequisite_diagnosis(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return diagnose_prerequisites(db, user.id, skill_id)


@app.get("/skills/{source_skill_id}/path/{target_skill_id}", response_model=DependencyPathResponse)
def get_skill_dependency_path(
    source_skill_id: int,
    target_skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source = db.query(Skill).filter(Skill.id == source_skill_id).first()
    target = db.query(Skill).filter(Skill.id == target_skill_id).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Source skill (ID: {source_skill_id}) not found")
    if not target:
        raise HTTPException(status_code=404, detail=f"Target skill (ID: {target_skill_id}) not found")

    G = build_skill_graph(db)
    path_info = get_dependency_path(G, source_skill_id, target_skill_id)

    return {
        "source_id": source.id,
        "source_name": source.name,
        "target_id": target.id,
        "target_name": target.name,
        **path_info
    }


@app.get("/skills/graph/topological")
def get_graph_topological_order(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    G = build_skill_graph(db)
    order = get_topological_order(G)
    return {
        "is_acyclic": len(order) > 0 or len(G) == 0,
        "topological_order": order
    }


def calculate_skill_metrics(activities):

    scores = [
        a.score for a in activities
        if a.score is not None
    ]

    if not scores:
        return None

    avg_score = mean(scores)
    recent_avg = mean(scores[-3:])

    consistency = max(
        0,
        1 - (pstdev(scores) / 50)
    )

    total_errors = sum(a.errors for a in activities)
    total_duration = sum(a.duration for a in activities)

    error_burden = total_errors / max(total_duration, 1)

    error_score = max(
        0,
        1 - (error_burden * 10)
    )

    mastery = (
        (avg_score / 100) * 0.40 +
        (recent_avg / 100) * 0.30 +
        consistency * 0.20 +
        error_score * 0.10
    )

    confidence = min(
        1,
        (len(scores) / 5) * 0.6 +
        consistency * 0.4
    )

    if recent_avg > avg_score + 5:
        trend = "improving"
    elif recent_avg < avg_score - 5:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "activities_analyzed": len(activities),
        "average_score": round(avg_score, 2),
        "recent_average": round(recent_avg, 2),
        "consistency": round(consistency, 3),
        "error_burden": round(error_burden, 3),
        "mastery": round(mastery, 3),
        "confidence": round(confidence, 3),
        "trend": trend
    }


@app.get("/skills/{skill_id}/analysis")
def analyze_skill(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    activities = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.topic == skill.name
    ).order_by(Activity.timestamp.asc()).all()

    if not activities:
        raise HTTPException(
            status_code=404,
            detail="No activities found for this skill"
        )

    metrics = calculate_skill_metrics(activities)

    print("DEBUG: activity count =", len(activities))
    print("DEBUG: calculated metrics =", metrics)

    if metrics is None:
        raise HTTPException(
            status_code=400,
            detail="No scored activities available"
        )

    mastery = metrics["mastery"]
    confidence = metrics["confidence"]

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == skill_id
    ).first()

    if user_skill:
        user_skill.mastery = mastery
        user_skill.confidence = confidence
    else:
        user_skill = UserSkill(
            user_id=user.id,
            skill_id=skill_id,
            mastery=mastery,
            confidence=confidence
        )
        db.add(user_skill)

    db.commit()

    return {
        "skill": skill.name,
        **metrics
    }


@app.get("/skills/{skill_id}/gap-analysis")
def skill_gap_analysis(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()

    if not skill:
        raise HTTPException(
            status_code=404,
            detail="Skill not found"
        )

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == skill_id
    ).first()

    if not user_skill:
        raise HTTPException(
            status_code=404,
            detail="User skill data not found"
        )

    diagnosis = diagnose_prerequisites(db, user.id, skill_id)

    # Format prerequisites in backward-compatible structure with multi-hop metadata
    prerequisite_analysis = []
    for p in diagnosis["prerequisites"]:
        prerequisite_analysis.append({
            "skill": p["name"],
            "skill_id": p["skill_id"],
            "mastery": p["mastery"],
            "dependency_strength": p["dependency_strength"],
            "risk": p["risk"],
            "potential_gap": p["potential_gap"],
            "distance": p["distance"],
            "is_direct": p["is_direct"],
            "bottleneck_score": p["bottleneck_score"],
            "path_names": p["path_names"]
        })

    return {
        "skill": skill.name,
        "skill_mastery": round(user_skill.mastery, 3),
        "prerequisites": prerequisite_analysis,
        "primary_gap": diagnosis["primary_gap"],
        "diagnosis_summary": diagnosis["diagnosis_summary"]
    }


def save_recommendation_session(
    db: Session,
    user: User,
    skill: Skill,
    action: str,
    mastery: float,
    features: dict | None = None
):
    session = RecommendationSession(
        user_id=user.id,
        skill_id=skill.id,
        recommended_action=action,
        before_mastery=mastery,
        feature_snapshot=features,
        status="pending"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.get("/skills/{skill_id}/recommendation")
def generate_recommendation(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(
        Skill.id == skill_id
    ).first()

    if not skill:
        raise HTTPException(
            status_code=404,
            detail="Skill not found"
        )

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == skill_id
    ).first()

    if not user_skill:
        raise HTTPException(
            status_code=404,
            detail="User skill data not found"
        )

    # Multi-hop prerequisite intelligence powered by NetworkX DAG traversal
    diagnosis = diagnose_prerequisites(db, user.id, skill_id)

    # Pre-fetch activities for target skill
    target_activities = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.topic == skill.name
    ).order_by(Activity.timestamp.asc()).all()

    if diagnosis["primary_gap"]:
        top = diagnosis["primary_gap"]
        prerequisite = db.query(Skill).filter(
            Skill.id == top["skill_id"]
        ).first()

        prerequisite_skill = db.query(UserSkill).filter(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == top["skill_id"]
        ).first()

        mastery_val = prerequisite_skill.mastery if prerequisite_skill else 0.0
        prereq_confidence = prerequisite_skill.confidence if prerequisite_skill else 0.0

        prereq_activities = db.query(Activity).filter(
            Activity.user_id == user.id,
            Activity.topic == prerequisite.name
        ).order_by(Activity.timestamp.asc()).all()

        v2_snapshot = build_v2_feature_snapshot(
            target_skill=skill,
            target_mastery=user_skill.mastery,
            target_confidence=user_skill.confidence,
            target_activities=target_activities,
            recommended_action="practice_prerequisite",
            remediation_skill=prerequisite,
            remediation_mastery=mastery_val,
            remediation_confidence=prereq_confidence,
            remediation_activities=prereq_activities,
            engine_mode="rule_graph_v1",
            graph_diagnosis=diagnosis,
            provenance="server_generated"
        )

        recommendation_session = save_recommendation_session(
            db=db,
            user=user,
            skill=prerequisite,
            action="practice_prerequisite",
            mastery=mastery_val,
            features=v2_snapshot
        )

        chain_note = (
            f" (distance {top['distance']}, chain: {' -> '.join(top['path_names'])})"
            if not top["is_direct"]
            else ""
        )

        reason = (
            f"{top['name']} is a weak prerequisite for {skill.name}"
            if top["is_direct"]
            else f"{top['name']} is a weak foundational prerequisite for {skill.name}{chain_note}"
        )

        tracked_recommendation = {
            "action_code": "practice_prerequisite",
            "target_skill": top["name"],
            "requested_target_skill": skill.name,
            "requested_target_skill_id": skill.id,
            "remediation_skill": top["name"],
            "remediation_skill_id": top["skill_id"],
            "prerequisite_skill_id": top["skill_id"],
            "distance": top["distance"],
            "is_direct": top["is_direct"],
            "path_names": top["path_names"],
            "reason": reason,
            "mastery": round(top["mastery"], 3),
            "risk": round(top["risk"], 3),
            "message": f"Strengthen {top['name']} before advancing in {skill.name}.",
            "explanation": top["explanation"],
            "recommendation_session_id": recommendation_session.id
        }

        return {
            "target_skill": skill.name,
            "target_skill_id": skill.id,
            "remediation_skill": top["name"],
            "remediation_skill_id": top["skill_id"],
            "recommendation_status": "prerequisite_gap_detected",
            "recommendation_session_id": recommendation_session.id,
            "recommendations": [tracked_recommendation]
        }

    # --- ML-based recommendation ---
    ml_fallback_reason = None
    features = None
    activities = target_activities

    if activities:
        features = build_skill_features(
            activities,
            user_skill.mastery,
            user_skill.confidence
        )

    if not features:
        ml_fallback_reason = (
            "The ML model is unavailable or returned no prediction."
        )

    if features:
        action = predict_action(features)

        # Keep prerequisite recommendations rule-based.
        # The ML model cannot select a prerequisite target by itself.
        if action == "practice_prerequisite":
            ml_fallback_reason = (
                "The model predicted practice_prerequisite, "
                "but a valid prerequisite target was not selected."
            )
            action = None

        action_messages = {
            "practice_current": (
                f"Practice more {skill.name} problems "
                "to strengthen your understanding."
            ),
            "review_concept": (
                f"Review the key concepts of {skill.name}."
            ),
            "easy_practice": (
                f"Start with easier exercises in {skill.name}."
            ),
            "hard_practice": (
                f"Try more challenging problems in {skill.name}."
            ),
            "take_assessment": (
                f"Take an assessment to evaluate your "
                f"understanding of {skill.name}."
            )
        }

        if action is None:
            if ml_fallback_reason is None:
                ml_fallback_reason = (
                    "The ML model is unavailable or returned no prediction."
                )
        elif action not in action_messages:
            ml_fallback_reason = (
                f"The ML model returned an unsupported action: {action}."
            )
            action = None

        if action:
            # Prevent hard practice for very-low-mastery learners.
            if user_skill.mastery < 0.40 and action == "hard_practice":
                action = "practice_current"
                ml_fallback_reason = (
                    "Hard practice is blocked because mastery is below 0.40."
                )

            message = action_messages[action]

            v2_snapshot = build_v2_feature_snapshot(
                target_skill=skill,
                target_mastery=user_skill.mastery,
                target_confidence=user_skill.confidence,
                target_activities=activities,
                recommended_action=action,
                remediation_skill=skill,
                remediation_mastery=user_skill.mastery,
                remediation_confidence=user_skill.confidence,
                remediation_activities=activities,
                engine_mode="ml_action_model_v1",
                graph_diagnosis=diagnosis,
                provenance="server_generated"
            )

            recommendation_session = save_recommendation_session(
                db=db,
                user=user,
                skill=skill,
                action=action,
                mastery=user_skill.mastery,
                features=v2_snapshot
            )

            return {
                "target_skill": skill.name,
                "target_skill_id": skill.id,
                "remediation_skill": skill.name,
                "remediation_skill_id": skill.id,
                "recommendation_status": "ml_recommendation_generated",
                "recommendation_source":
                    "random_forest_synthetic_development_model",
                "recommendation_session_id": recommendation_session.id,
                "recommendations": [
                    {
                        "action_code": action,
                        "target_skill": skill.name,
                        "remediation_skill": skill.name,
                        "remediation_skill_id": skill.id,
                        "recommendation_session_id": recommendation_session.id,
                        "reason": (
                            "Action predicted by the trained "
                            "Random Forest development model."
                        ),
                        "mastery": round(user_skill.mastery, 3),
                        "risk": round(1 - user_skill.mastery, 3),
                        "message": message
                    }
                ]
            }

    if user_skill.mastery < 0.60:
        v2_snapshot = build_v2_feature_snapshot(
            target_skill=skill,
            target_mastery=user_skill.mastery,
            target_confidence=user_skill.confidence,
            target_activities=activities,
            recommended_action="practice_current",
            remediation_skill=skill,
            remediation_mastery=user_skill.mastery,
            remediation_confidence=user_skill.confidence,
            remediation_activities=activities,
            engine_mode="rule_graph_v1",
            graph_diagnosis=diagnosis,
            provenance="server_generated"
        )
        recommendation_session = save_recommendation_session(
            db=db,
            user=user,
            skill=skill,
            action="practice_current",
            mastery=user_skill.mastery,
            features=v2_snapshot
        )
        return {
            "target_skill": skill.name,
            "target_skill_id": skill.id,
            "remediation_skill": skill.name,
            "remediation_skill_id": skill.id,
            "recommendation_status": "skill_gap_detected",
            "recommendation_source": "rule_based_fallback",
            "fallback_reason": ml_fallback_reason,
            "recommendation_session_id": recommendation_session.id,
            "recommendations": [
                {
                    "action_code": "practice_current",
                    "target_skill": skill.name,
                    "remediation_skill": skill.name,
                    "remediation_skill_id": skill.id,
                    "recommendation_session_id": recommendation_session.id,
                    "reason": f"{skill.name} mastery is below the required threshold",
                    "mastery": round(user_skill.mastery, 3),
                    "risk": round(1 - user_skill.mastery, 3),
                    "message": f"Practice more {skill.name} problems to build mastery."
                }
            ]
        }

    v2_snapshot = build_v2_feature_snapshot(
        target_skill=skill,
        target_mastery=user_skill.mastery,
        target_confidence=user_skill.confidence,
        target_activities=activities,
        recommended_action="hard_practice",
        remediation_skill=skill,
        remediation_mastery=user_skill.mastery,
        remediation_confidence=user_skill.confidence,
        remediation_activities=activities,
        engine_mode="rule_graph_v1",
        graph_diagnosis=diagnosis,
        provenance="server_generated"
    )
    recommendation_session = save_recommendation_session(
        db=db,
        user=user,
        skill=skill,
        action="hard_practice",
        mastery=user_skill.mastery,
        features=v2_snapshot,
    )

    return {
        "target_skill": skill.name,
        "target_skill_id": skill.id,
        "remediation_skill": skill.name,
        "remediation_skill_id": skill.id,
        "recommendation_status": "no_major_gap",
        "recommendation_session_id": recommendation_session.id,
        "recommendation_source": "rule_based_fallback",
        "recommendations": [
            {
                "action_code": "hard_practice",
                "target_skill": skill.name,
                "remediation_skill": skill.name,
                "remediation_skill_id": skill.id,
                "recommendation_session_id": recommendation_session.id,
                "reason": (
                    f"{skill.name} mastery is satisfactory "
                    "— push to harder problems"
                ),
                "mastery": round(user_skill.mastery, 3),
                "risk": round(1 - user_skill.mastery, 3),
                "message": (
                    f"Continue practicing {skill.name} "
                    "with higher difficulty."
                ),
            }
        ],
    }


@app.get("/skills/{skill_id}/features")
def get_skill_features(
    skill_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.skill_id == skill_id
    ).first()

    if not user_skill:
        raise HTTPException(
            status_code=404,
            detail="User skill data not found. Run /analysis first."
        )

    activities = db.query(Activity).filter(
        Activity.user_id == user.id,
        Activity.topic == skill.name
    ).order_by(Activity.timestamp.asc()).all()

    if not activities:
        raise HTTPException(
            status_code=404,
            detail="No activities found for this skill"
        )

    features = build_skill_features(
        activities,
        user_skill.mastery,
        user_skill.confidence
    )

    if not features:
        raise HTTPException(
            status_code=400,
            detail="No scored activities available to build features"
        )

    return {
        "skill": skill.name,
        "features": features
    }


@app.post("/learning-outcomes")
def create_learning_outcome(
    outcome: LearningOutcomeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        skill = db.query(Skill).filter(
            Skill.id == outcome.skill_id
        ).first()

        if not skill:
            raise HTTPException(404, detail="Skill not found")

        recommendation_session = None

        if outcome.recommendation_session_id is not None:
            recommendation_session = db.query(
                RecommendationSession
            ).filter(
                RecommendationSession.id
                == outcome.recommendation_session_id,
                RecommendationSession.user_id == user.id
            ).first()

            if not recommendation_session:
                raise HTTPException(
                    404, detail="Recommendation session not found"
                )

            if recommendation_session.skill_id != skill.id:
                raise HTTPException(
                    400, detail="Session skill does not match outcome skill"
                )

            if (
                recommendation_session.recommended_action
                != outcome.recommended_action
            ):
                raise HTTPException(
                    400, detail="Recommended action does not match session"
                )

            if recommendation_session.status != "pending":
                raise HTTPException(
                    400, detail="Recommendation session already evaluated"
                )

            existing_outcome = db.query(LearningOutcome).filter(
                LearningOutcome.recommendation_session_id
                == recommendation_session.id
            ).first()

            if existing_outcome:
                raise HTTPException(
                    409, detail="An outcome already exists for this session"
                )

        before_mastery = (
            recommendation_session.before_mastery
            if recommendation_session
            else outcome.before_mastery
        )

        activities = db.query(Activity).filter(
            Activity.user_id == user.id,
            Activity.topic == skill.name
        ).order_by(Activity.timestamp.asc()).all()

        metrics = calculate_skill_metrics(activities)

        if metrics is None:
            raise HTTPException(
                400,
                detail="No scored activities available to calculate mastery"
            )

        after_mastery = metrics["mastery"]

        mastery_change = after_mastery - before_mastery

        if abs(mastery_change) < 1e-9:
            raise HTTPException(
                400,
                detail="No mastery change detected. Record another "
                       "scored activity before evaluating the outcome."
            )

        if mastery_change > 0.05:
            result = "positive"
        elif mastery_change < -0.05:
            result = "negative"
        else:
            result = "neutral"

        if recommendation_session:
            final_snapshot = recommendation_session.feature_snapshot
        elif outcome.feature_snapshot is not None and isinstance(outcome.feature_snapshot, dict):
            import copy
            final_snapshot = copy.deepcopy(outcome.feature_snapshot)
            meta = final_snapshot.get("_metadata", {})
            if not isinstance(meta, dict):
                meta = {}
            meta["provenance"] = "unverified_client"
            meta.setdefault("schema_version", "2.0")
            final_snapshot["_metadata"] = meta
        else:
            final_snapshot = None

        learning_outcome = LearningOutcome(
            user_id=user.id,
            skill_id=skill.id,
            recommended_action=outcome.recommended_action,
            actual_action=outcome.actual_action,
            before_mastery=before_mastery,
            after_mastery=after_mastery,
            mastery_change=round(mastery_change, 3),
            outcome=result,
            is_test=is_test_mode(),
            feature_snapshot=final_snapshot,
            recommendation_session_id=(
                recommendation_session.id
                if recommendation_session
                else None
            )
        )

        db.add(learning_outcome)

        if recommendation_session:
            recommendation_session.status = "evaluated"

        # Save the outcome and session status together.
        db.commit()
        db.refresh(learning_outcome)

        return {
            "message": "Learning outcome recorded successfully",
            "outcome_id": learning_outcome.id,
            "recommendation_session_id": (
                learning_outcome.recommendation_session_id
            ),
            "mastery_change": learning_outcome.mastery_change,
            "outcome": learning_outcome.outcome
        }

    except Exception:
        db.rollback()
        raise


@app.get("/learning-outcomes")
def get_learning_outcomes(
    is_test: bool | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(LearningOutcome).filter(
        LearningOutcome.user_id == user.id
    )

    if is_test is not None:
        query = query.filter(
            LearningOutcome.is_test == is_test
        )

    outcomes = query.order_by(
        LearningOutcome.id.desc()
    ).all()

    real_outcomes = db.query(LearningOutcome).filter(
        LearningOutcome.user_id == user.id,
        LearningOutcome.is_test == False
    ).all()

    total_evaluated = len(real_outcomes)

    recommendations_followed = sum(
        1 for item in real_outcomes
        if item.recommended_action == item.actual_action
    )

    adherence_rate = (
        (recommendations_followed / total_evaluated) * 100
        if total_evaluated > 0
        else 0
    )
    return {
        "total": len(outcomes),
        "filter": {"is_test": is_test},
        "total_real_evaluated": total_evaluated,
        "recommendations_followed": recommendations_followed,
        "recommendations_not_followed": (
            total_evaluated - recommendations_followed
        ),
        "adherence_rate": round(adherence_rate, 2),
        "outcomes": [
            {
                "outcome_id": item.id,
                "recommendation_session_id": item.recommendation_session_id,
                "skill_id": item.skill_id,
                "recommended_action": item.recommended_action,
                "actual_action": item.actual_action,
                "before_mastery": item.before_mastery,
                "after_mastery": item.after_mastery,
                "mastery_change": item.mastery_change,
                "outcome": item.outcome,
                "is_test": item.is_test
            }
            for item in outcomes
        ]
    }


@app.get("/analytics/effectiveness")
def get_learning_effectiveness(
    skill_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(LearningOutcome).filter(
        LearningOutcome.user_id == user.id,
        LearningOutcome.is_test == False
    )

    if skill_id is not None:
        query = query.filter(LearningOutcome.skill_id == skill_id)

    real_outcomes = query.order_by(LearningOutcome.id.asc()).all()

    total_evaluated = len(real_outcomes)

    def summarize_subset(subset):
        count = len(subset)
        if count == 0:
            return {
                "sample_count": 0,
                "average_mastery_change": 0.0,
                "positive_count": 0,
                "neutral_count": 0,
                "negative_count": 0
            }
        avg_change = sum(o.mastery_change for o in subset) / count
        return {
            "sample_count": count,
            "average_mastery_change": round(avg_change, 4),
            "positive_count": sum(1 for o in subset if o.outcome == "positive"),
            "neutral_count": sum(1 for o in subset if o.outcome == "neutral"),
            "negative_count": sum(1 for o in subset if o.outcome == "negative"),
        }

    if total_evaluated == 0:
        return {
            "total_real_evaluated": 0,
            "average_mastery_change": 0.0,
            "positive_outcomes": 0,
            "neutral_outcomes": 0,
            "negative_outcomes": 0,
            "by_skill": [],
            "by_recommended_action": [],
            "by_actual_action": [],
            "comparison_by_adherence": {
                "followed": summarize_subset([]),
                "not_followed": summarize_subset([])
            },
            "observational_caveat": (
                "Observational analytics only. Associations between actions "
                "and mastery changes reflect historical patterns and do not "
                "establish causal pedagogical effectiveness."
            )
        }

    overall_avg = sum(o.mastery_change for o in real_outcomes) / total_evaluated

    # 1. Group by skill
    skills_map = {s.id: s.name for s in db.query(Skill).all()}
    skill_groups = {}
    for o in real_outcomes:
        skill_groups.setdefault(o.skill_id, []).append(o)

    by_skill = []
    for s_id, s_outcomes in sorted(skill_groups.items()):
        stats = summarize_subset(s_outcomes)
        by_skill.append({
            "skill_id": s_id,
            "skill_name": skills_map.get(s_id, f"Skill {s_id}"),
            **stats
        })

    # 2. Group by recommended action
    rec_groups = {}
    for o in real_outcomes:
        rec_groups.setdefault(o.recommended_action, []).append(o)

    by_recommended_action = []
    for action, a_outcomes in sorted(rec_groups.items()):
        stats = summarize_subset(a_outcomes)
        by_recommended_action.append({
            "action": action,
            **stats
        })

    # 3. Group by actual action
    act_groups = {}
    for o in real_outcomes:
        act_groups.setdefault(o.actual_action, []).append(o)

    by_actual_action = []
    for action, a_outcomes in sorted(act_groups.items()):
        stats = summarize_subset(a_outcomes)
        by_actual_action.append({
            "action": action,
            **stats
        })

    # 4. Comparison between followed and non-followed recommendations
    followed_outcomes = [
        o for o in real_outcomes
        if o.recommended_action == o.actual_action
    ]
    not_followed_outcomes = [
        o for o in real_outcomes
        if o.recommended_action != o.actual_action
    ]

    return {
        "total_real_evaluated": total_evaluated,
        "average_mastery_change": round(overall_avg, 4),
        "positive_outcomes": sum(1 for o in real_outcomes if o.outcome == "positive"),
        "neutral_outcomes": sum(1 for o in real_outcomes if o.outcome == "neutral"),
        "negative_outcomes": sum(1 for o in real_outcomes if o.outcome == "negative"),
        "by_skill": by_skill,
        "by_recommended_action": by_recommended_action,
        "by_actual_action": by_actual_action,
        "comparison_by_adherence": {
            "followed": summarize_subset(followed_outcomes),
            "not_followed": summarize_subset(not_followed_outcomes)
        },
        "observational_caveat": (
            "Observational analytics only. Associations between actions "
            "and mastery changes reflect historical patterns and do not "
            "establish causal pedagogical effectiveness."
        )
    }


REQUIRED_TRAINING_FEATURES = {
    "average_score",
    "recent_score",
    "adjusted_score",
    "avg_difficulty_weight",
    "consistency",
    "error_rate",
    "mastery",
    "confidence",
    "activity_count",
    "trend",
}


@app.get("/ml/training-data")
def get_training_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    outcomes = db.query(LearningOutcome).filter(
        LearningOutcome.user_id == user.id,
        LearningOutcome.is_test == False
    ).order_by(
        LearningOutcome.id.asc()
    ).all()

    dataset = []
    skipped_missing_snapshot = 0

    for outcome in outcomes:
        record = validate_and_extract_training_record(outcome, db)
        if record is not None:
            dataset.append(record)
        else:
            skipped_missing_snapshot += 1

    return {
        "samples": len(dataset),
        "dataset": dataset,
        "skipped_missing_snapshot": skipped_missing_snapshot,
        "message": (
            "No eligible real training samples with valid snapshots."
            if not dataset
            else "Training data assembled from saved feature snapshots."
        )
    }


@app.get("/ml/evaluation/readiness")
def get_evaluation_readiness(
    scope: str = "learner",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates real-data ML evaluation readiness under Phase 5 Step 4 governance rules.
    - scope='learner': restricted to the authenticated user's records (default, enforces learner isolation).
    - scope='platform' or 'all': system-wide platform readiness audit across all learners.
    """
    effective_user_id = user.id if scope == "learner" else None
    return generate_evaluation_readiness_report(db, user_id=effective_user_id)


def calculate_feedback_loop_metrics(db: Session, user_id: int | None = None) -> dict:
    """
    Internal calculation engine for feedback loop metrics.
    When user_id is provided, metrics are strictly isolated to that learner.
    When user_id is None, metrics represent platform-wide aggregate context.
    """
    effective_user_id = user_id

    # 1. Activities query
    act_query = db.query(Activity)
    if effective_user_id is not None:
        act_query = act_query.filter(Activity.user_id == effective_user_id)
    activities = act_query.all()
    total_activities = len(activities)

    by_difficulty = {"easy": 0, "medium": 0, "hard": 0}
    by_type = {}
    for a in activities:
        diff = (a.difficulty or "").lower()
        if diff in by_difficulty:
            by_difficulty[diff] += 1
        t = a.activity_type
        by_type[t] = by_type.get(t, 0) + 1

    # 2. Recommendation Sessions query
    sess_query = db.query(RecommendationSession)
    if effective_user_id is not None:
        sess_query = sess_query.filter(RecommendationSession.user_id == effective_user_id)
    sessions = sess_query.all()
    total_sessions = len(sessions)
    pending_sessions = sum(1 for s in sessions if s.status == "pending")
    evaluated_sessions = sum(1 for s in sessions if s.status == "evaluated")

    # 3. Learning Outcomes query
    out_query = db.query(LearningOutcome)
    if effective_user_id is not None:
        out_query = out_query.filter(LearningOutcome.user_id == effective_user_id)
    outcomes = out_query.all()
    total_outcomes = len(outcomes)

    real_outcomes = [o for o in outcomes if not o.is_test]
    test_outcomes = [o for o in outcomes if o.is_test]

    real_count = len(real_outcomes)
    positive_count = sum(1 for o in real_outcomes if o.outcome == "positive")
    neutral_count = sum(1 for o in real_outcomes if o.outcome == "neutral")
    negative_count = sum(1 for o in real_outcomes if o.outcome == "negative")
    avg_mastery_change = (
        round(sum(o.mastery_change for o in real_outcomes) / real_count, 4)
        if real_count > 0 else 0.0
    )

    # 4. Adherence calculation (strictly self-reported by learner)
    followed_count = sum(
        1 for o in real_outcomes
        if o.recommended_action == o.actual_action
    )
    not_followed_count = real_count - followed_count
    adherence_rate = (
        round((followed_count / real_count) * 100, 2)
        if real_count > 0 else 0.0
    )

    # 5. Conversion funnel
    outcomes_with_session = sum(
        1 for o in outcomes if o.recommendation_session_id is not None
    )
    conversion_rate = (
        round((evaluated_sessions / total_sessions) * 100, 2)
        if total_sessions > 0 else 0.0
    )

    # 6. Evaluation readiness progress (reuses shared validator)
    eligible_real_samples = sum(
        1 for o in real_outcomes
        if validate_and_extract_training_record(o, db) is not None
    )
    readiness_pct = min(100.0, round((eligible_real_samples / 30) * 100, 1))

    return {
        "scope": "learner" if effective_user_id is not None else "platform",
        "activities": {
            "total": total_activities,
            "by_difficulty": by_difficulty,
            "by_type": by_type
        },
        "recommendation_sessions": {
            "total": total_sessions,
            "pending": pending_sessions,
            "evaluated": evaluated_sessions
        },
        "learning_outcomes": {
            "total": total_outcomes,
            "real_outcomes": real_count,
            "test_outcomes": len(test_outcomes),
            "positive": positive_count,
            "neutral": neutral_count,
            "negative": negative_count,
            "average_mastery_change": avg_mastery_change
        },
        "adherence": {
            "total_real_evaluated": real_count,
            "recommendations_followed": followed_count,
            "recommendations_not_followed": not_followed_count,
            "adherence_rate": adherence_rate,
            "adherence_label": "self-reported by learner"
        },
        "conversion_funnel": {
            "recommendations_generated": total_sessions,
            "sessions_evaluated": evaluated_sessions,
            "outcomes_linked": outcomes_with_session,
            "conversion_rate": conversion_rate
        },
        "evaluation_readiness_progress": {
            "eligible_real_samples": eligible_real_samples,
            "target_initial_threshold": 30,
            "target_comprehensive_threshold": 150,
            "progress_percentage": readiness_pct,
            "is_ready_for_evaluation": eligible_real_samples >= 30
        },
        "observational_caveat": (
            "Observational analytics only. Associations between recommended actions, "
            "adherence, and mastery changes reflect historical patterns and do not "
            "establish causal pedagogical effectiveness."
        )
    }


@app.get("/analytics/feedback-loop")
def get_feedback_loop_analytics(
    scope: str = "learner",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Provides feedback loop visibility and metrics across the recommendation-activity-outcome lifecycle.
    - scope='learner': user-isolated analytics for authenticated learner.
    - Platform-wide aggregation is restricted from client-facing requests (HTTP 403).
    """
    if scope != "learner":
        raise HTTPException(
            status_code=403,
            detail="Platform-wide aggregation is restricted to internal contexts. Ordinary learners may only access learner-scoped analytics."
        )

    return calculate_feedback_loop_metrics(db=db, user_id=user.id)

