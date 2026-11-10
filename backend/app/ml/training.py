import pandas as pd

ACTION_MAP = {
    "practice_current": 0,
    "practice_prerequisite": 1,
    "review_concept": 2,
    "easy_practice": 3,
    "hard_practice": 4,
    "take_assessment": 5
}


def prepare_training_dataframe(dataset):

    rows = []

    for sample in dataset:

        action = sample["recommended_action"]

        if action not in ACTION_MAP:
            continue

        row = {
            **sample["features"],
            "action": ACTION_MAP[action],
            "mastery_change": sample["mastery_change"],
            "outcome": sample["outcome"],
            "is_synthetic": sample.get("is_synthetic", False)
        }

        rows.append(row)

    return pd.DataFrame(rows)
