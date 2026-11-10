from .synthetic import generate_synthetic_dataset
from .training import prepare_training_dataframe
from .model import train_action_model


def main():

    dataset = generate_synthetic_dataset(
        n_samples=600,
        seed=42
    )

    df = prepare_training_dataframe(dataset)

    if df.empty:
        raise ValueError("The generated dataset is empty.")

    if not df["is_synthetic"].all():
        raise ValueError(
            "This training run must use synthetic data only."
        )

    print("Dataset shape:", df.shape)

    print("\nAction distribution:")
    print(df["action"].value_counts().sort_index())

    print("\nSynthetic rows:", df["is_synthetic"].sum())

    model, metrics = train_action_model(df)

    print("\nModel evaluation")
    print("----------------")
    print("Accuracy:", metrics["accuracy"])
    print("Training samples:", metrics["training_samples"])
    print("Testing samples:", metrics["testing_samples"])
    print("Classes:", metrics["classes"])

    print("\nClassification report:")
    for label, values in metrics["classification_report"].items():
        if isinstance(values, dict):
            print(
                f"{label}: "
                f"precision={values['precision']:.3f}, "
                f"recall={values['recall']:.3f}, "
                f"f1={values['f1-score']:.3f}"
            )

    print("\nConfusion matrix:")
    for row in metrics["confusion_matrix"]:
        print(row)

    print("\nModel saved successfully.")


if __name__ == "__main__":
    main()
