import os


def get_cwip_data_mode() -> str:
    """Return the trusted server-side CWIP data mode."""
    mode = os.getenv("CWIP_DATA_MODE", "development").strip().lower()
    if mode not in {"development", "real"}:
        raise ValueError(
            "CWIP_DATA_MODE must be 'development' or 'real'"
        )
    return mode


def is_test_mode() -> bool:
    return get_cwip_data_mode() == "development"
