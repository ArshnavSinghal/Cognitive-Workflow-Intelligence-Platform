import pandas as pd
import pytest

from backend.app.ml import predict as predict_module
from backend.app.ml.model import FEATURE_COLUMNS, MODEL_PATH, train_action_model
from backend.app.ml.training import ACTION_MAP, prepare_training_dataframe
from backend.app.ml import train_model as train_model_module
from backend.app.ml.real_training import prepare_real_training_dataframe


def test_predict_action_returns_none_when_model_unavailable(monkeypatch):
    """predict_action returns None when no saved model file exists."""
    monkeypatch.setattr(predict_module, "load_action_model", lambda: None)

    features = {column: 0.5 for column in FEATURE_COLUMNS}

    result = predict_module.predict_action(features)

    assert result is None


def test_predict_action_rejects_missing_features(monkeypatch):
    """predict_action raises ValueError when a feature column is absent."""

    class FakeModel:
        def predict(self, data):
            return [0]

    monkeypatch.setattr(predict_module, "load_action_model", lambda: FakeModel())

    # Drop the first feature column to trigger the validation check.
    features = {
        column: 0.5
        for column in FEATURE_COLUMNS
        if column != FEATURE_COLUMNS[0]
    }

    with pytest.raises(ValueError, match="Missing features"):
        predict_module.predict_action(features)


def test_predict_action_maps_prediction_to_action(monkeypatch):
    """predict_action builds the correct DataFrame and maps the predicted
    class index back to a human-readable action code."""

    expected_index = next(iter(ACTION_MAP.values()))
    expected_action = next(iter(ACTION_MAP.keys()))

    class FakeModel:
        def predict(self, data):
            # Verify the DataFrame structure before returning a prediction.
            assert isinstance(data, pd.DataFrame)
            assert list(data.columns) == FEATURE_COLUMNS
            assert len(data) == 1
            return [expected_index]

    monkeypatch.setattr(predict_module, "load_action_model", lambda: FakeModel())

    features = {column: 0.5 for column in FEATURE_COLUMNS}

    result = predict_module.predict_action(features)

    assert result == expected_action


def test_prepare_training_dataframe_maps_action():
    dataset = [
        {
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
            "recommended_action": "practice_current",
            "mastery_change": 0.1,
            "outcome": "positive",
            "is_synthetic": True,
        }
    ]

    df = prepare_training_dataframe(dataset)

    assert len(df) == 1
    assert df.iloc[0]["action"] == ACTION_MAP["practice_current"]
    assert df.iloc[0]["is_synthetic"] == True


def test_train_action_model_rejects_small_dataset():
    df = pd.DataFrame({
        **{column: [0.5] * 10 for column in FEATURE_COLUMNS},
        "action": [0, 1] * 5,
    })

    with pytest.raises(ValueError, match="At least 30 samples"):
        train_action_model(df)


def test_train_action_model_rejects_missing_columns():
    df = pd.DataFrame({
        "average_score": [50.0] * 30,
        "action": [0, 1] * 15,
    })

    with pytest.raises(ValueError, match="Missing columns"):
        train_action_model(df)


def test_train_action_model_success(monkeypatch, tmp_path):
    from backend.app.ml import model as model_module

    monkeypatch.setattr(
        model_module,
        "MODEL_PATH",
        str(tmp_path / "test_action_model.joblib"),
    )

    rows = []
    for i in range(60):
        row = {
            column: float((i % 10) / 10)
            for column in FEATURE_COLUMNS
        }
        row["action"] = i % 2
        rows.append(row)

    df = pd.DataFrame(rows)

    model, metrics = train_action_model(df)

    assert model is not None
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["training_samples"] + metrics["testing_samples"] == 60
    assert set(metrics["classes"]) == {0, 1}
    assert "classification_report" in metrics
    assert "confusion_matrix" in metrics
    assert (tmp_path / "test_action_model.joblib").exists()


def test_development_training_rejects_real_data(monkeypatch):
    dataset = [
        {
            "features": {
                column: 0.5 for column in FEATURE_COLUMNS
            },
            "recommended_action": "practice_current",
            "mastery_change": 0.1,
            "outcome": "positive",
            "is_synthetic": False,
        }
    ]

    monkeypatch.setattr(
        train_model_module,
        "generate_synthetic_dataset",
        lambda n_samples, seed: dataset,
    )

    with pytest.raises(
        ValueError,
        match="This training run must use synthetic data only",
    ):
        train_model_module.main()


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


def test_real_training_rejects_synthetic_data():
    dataset = [create_real_sample()]
    dataset[0]["is_synthetic"] = True

    with pytest.raises(ValueError, match="Synthetic records"):
        prepare_real_training_dataframe(dataset)


def test_real_training_rejects_small_dataset():
    dataset = [create_real_sample() for _ in range(10)]

    with pytest.raises(ValueError, match="At least 30 real samples"):
        prepare_real_training_dataframe(dataset)


def test_real_training_rejects_single_action_class():
    dataset = [create_real_sample() for _ in range(30)]

    with pytest.raises(ValueError, match="two action classes"):
        prepare_real_training_dataframe(dataset)


def test_real_training_accepts_valid_dataset():
    dataset = [
        create_real_sample("hard_practice"),
        create_real_sample("practice_current"),
    ] * 15

    df = prepare_real_training_dataframe(dataset)

    assert len(df) == 30
    assert not df["is_synthetic"].any()
    assert df["action"].nunique() == 2
