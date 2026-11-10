import pandas as pd
from .model import FEATURE_COLUMNS, load_action_model
from .training import ACTION_MAP


def predict_action(features):
    model = load_action_model()

    if model is None:
        return None

    missing = set(FEATURE_COLUMNS) - set(features.keys())

    if missing:
        raise ValueError(
            f"Missing features: {sorted(missing)}"
        )

    input_data = pd.DataFrame(
        [{key: features[key] for key in FEATURE_COLUMNS}],
        columns=FEATURE_COLUMNS
    )

    prediction = int(model.predict(input_data)[0])

    reverse_map = {
        value: key for key, value in ACTION_MAP.items()
    }

    return reverse_map.get(prediction)
