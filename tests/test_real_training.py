import pytest

from backend.app.models import LearningOutcome, RecommendationSession
from backend.app.ml.real_training import fetch_real_training_data
from backend.app.ml import train_real_model as real_model_module


def valid_features():
    return {
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


def create_outcome(user, skill, is_test=False, features=None):
    return LearningOutcome(
        user_id=user.id,
        skill_id=skill.id,
        recommended_action="hard_practice",
        actual_action="hard_practice",
        before_mastery=0.6,
        after_mastery=0.65,
        mastery_change=0.05,
        outcome="positive",
        is_test=is_test,
        feature_snapshot=features,
    )


def test_fetch_real_training_data_returns_real_records(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    skill = test_environment["regression"]

    features = valid_features()
    session = RecommendationSession(
        user_id=user.id,
        skill_id=skill.id,
        recommended_action="hard_practice",
        before_mastery=0.6,
        feature_snapshot=features,
        status="completed",
    )
    db.add(session)
    db.commit()

    outcome = create_outcome(user, skill, features=features)
    outcome.recommendation_session_id = session.id
    db.add(outcome)
    db.commit()

    dataset = fetch_real_training_data(db, user.id)

    assert len(dataset) == 1
    assert dataset[0]["is_synthetic"] is False
    assert dataset[0]["recommended_action"] == "hard_practice"


def test_fetch_real_training_data_excludes_test_records(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    skill = test_environment["regression"]

    db.add(
        create_outcome(
            user, skill, is_test=True, features=valid_features()
        )
    )
    db.commit()

    dataset = fetch_real_training_data(db, user.id)

    assert dataset == []


def test_fetch_real_training_data_excludes_other_users(test_environment):
    db = test_environment["db"]
    other_user = test_environment["other_user"]
    skill = test_environment["regression"]

    db.add(
        create_outcome(
            other_user, skill, features=valid_features()
        )
    )
    db.commit()

    dataset = fetch_real_training_data(
        db, test_environment["user"].id
    )

    assert dataset == []


def test_fetch_real_training_data_skips_invalid_snapshot(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    skill = test_environment["regression"]

    db.add(
        create_outcome(
            user, skill, features={"mastery": 0.6}
        )
    )
    db.commit()

    dataset = fetch_real_training_data(db, user.id)

    assert dataset == []


def test_fetch_real_training_data_uses_session_snapshot(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    skill = test_environment["regression"]

    session = RecommendationSession(
        user_id=user.id,
        skill_id=skill.id,
        recommended_action="hard_practice",
        before_mastery=0.6,
        feature_snapshot=valid_features(),
        status="completed",
    )
    db.add(session)
    db.commit()

    outcome = create_outcome(user, skill, features=None)
    outcome.recommendation_session_id = session.id
    db.add(outcome)
    db.commit()

    dataset = fetch_real_training_data(db, user.id)

    assert len(dataset) == 1
    assert dataset[0]["features"]["mastery"] == 0.6


def create_real_sample(action="hard_practice"):
    return {
        "features": {
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
        },
        "recommended_action": action,
        "actual_action": action,
        "mastery_change": 0.05,
        "outcome": "positive",
        "is_synthetic": False,
    }


def test_real_model_training_rejects_insufficient_data(monkeypatch):
    class FakeDB:
        closed = False

        def close(self):
            self.closed = True

    fake_db = FakeDB()

    monkeypatch.setattr(
        real_model_module,
        "SessionLocal",
        lambda: fake_db
    )
    monkeypatch.setattr(
        real_model_module,
        "fetch_real_training_data",
        lambda db, user_id: [create_real_sample()]
    )

    with pytest.raises(ValueError, match="At least 30 real samples"):
        real_model_module.main(1)

    assert fake_db.closed is True


def test_real_model_training_uses_separate_model_path(
    monkeypatch, tmp_path
):
    class FakeDB:
        closed = False

        def close(self):
            self.closed = True

    fake_db = FakeDB()

    dataset = [
        create_real_sample("hard_practice"),
        create_real_sample("practice_current"),
    ] * 15

    captured = {}

    def fake_train(df, model_path, data_type):
        captured["model_path"] = model_path
        captured["data_type"] = data_type
        return object(), {
            "accuracy": 0.8,
            "training_samples": 22,
            "testing_samples": 8,
            "classes": [0, 4],
        }

    monkeypatch.setattr(
        real_model_module,
        "SessionLocal",
        lambda: fake_db
    )
    monkeypatch.setattr(
        real_model_module,
        "fetch_real_training_data",
        lambda db, user_id: dataset
    )
    monkeypatch.setattr(
        real_model_module,
        "train_action_model",
        fake_train
    )

    separate_path = str(tmp_path / "real_action_model.joblib")
    monkeypatch.setattr(
        real_model_module,
        "REAL_MODEL_PATH",
        separate_path
    )

    real_model_module.main(1)

    assert captured["model_path"] == separate_path
    assert captured["data_type"] == "real_learner_data"
    assert fake_db.closed is True
    assert real_model_module.REAL_MODEL_PATH != (
        real_model_module.MODEL_PATH
    )


def test_real_model_training_closes_database_on_error(monkeypatch):
    class FakeDB:
        closed = False

        def close(self):
            self.closed = True

    fake_db = FakeDB()

    monkeypatch.setattr(
        real_model_module,
        "SessionLocal",
        lambda: fake_db
    )
    monkeypatch.setattr(
        real_model_module,
        "fetch_real_training_data",
        lambda db, user_id: []
    )

    with pytest.raises(ValueError, match="No real training samples"):
        real_model_module.main(1)

    assert fake_db.closed is True
