from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)
import joblib
import os

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

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "action_model.joblib"
)


def train_action_model(
    df,
    model_path=None,
    data_type="synthetic_development_data"
):

    if len(df) < 30:
        raise ValueError(
            "At least 30 samples are required for this development run."
        )

    missing = set(FEATURE_COLUMNS + ["action"]) - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    X = df[FEATURE_COLUMNS]
    y = df["action"]

    if y.nunique() < 2:
        raise ValueError("Training requires at least two action classes.")

    # Stratify only when every class has enough samples
    counts = y.value_counts()
    stratify = y if counts.min() >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=stratify
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    metrics = {
        "accuracy": round(accuracy_score(y_test, predictions), 3),
        "classification_report": classification_report(
            y_test,
            predictions,
            zero_division=0,
            output_dict=True
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions
        ).tolist(),
        "training_samples": len(X_train),
        "testing_samples": len(X_test),
        "classes": sorted(y.unique().tolist()),
        "data_type": data_type
    }

    target_path = model_path or MODEL_PATH
    joblib.dump(model, target_path)

    return model, metrics


def load_action_model(model_path=None):
    target_path = model_path or MODEL_PATH
    if not os.path.exists(target_path):
        return None
    return joblib.load(target_path)
