import argparse

from backend.app.database import SessionLocal
from .real_training import (
    fetch_real_training_data,
    prepare_real_training_dataframe,
)
from .model import train_action_model, MODEL_PATH

REAL_MODEL_PATH = MODEL_PATH.replace(
    "action_model.joblib",
    "real_action_model.joblib"
)


def main(user_id):
    db = SessionLocal()

    try:
        dataset = fetch_real_training_data(db, user_id)
        print("Eligible real samples:", len(dataset))

        df = prepare_real_training_dataframe(dataset)
        print("Dataset shape:", df.shape)

        print("\nAction distribution:")
        print(df["action"].value_counts().sort_index())

        model, metrics = train_action_model(
            df,
            model_path=REAL_MODEL_PATH,
            data_type="real_learner_data"
        )

        print("\nReal-data model evaluation")
        print("--------------------------")
        print("Accuracy:", metrics["accuracy"])
        print("Training samples:", metrics["training_samples"])
        print("Testing samples:", metrics["testing_samples"])
        print("Classes:", metrics["classes"])

        print("\nReal-data model saved successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="User ID whose real learning records will be used."
    )

    args = parser.parse_args()
    main(args.user_id)
