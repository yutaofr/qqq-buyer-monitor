import numpy as np
import pandas as pd

from src.collector import macro


def test_stale_data_decay_logic():
    # This is a conceptual test for the decay logic we want to implement
    # We'll likely implement this in a new utility or within the beta mapper

    def calculate_decay(age_days, nominal_period_days, half_life_days=7):
        if age_days <= nominal_period_days:
            return 1.0
        excess_age = age_days - nominal_period_days
        return np.exp(-excess_age * np.log(2) / half_life_days)

    # Test cases
    assert calculate_decay(5, 30) == 1.0  # Not stale
    assert calculate_decay(30, 30) == 1.0 # Exactly at period

    decay_7d = calculate_decay(37, 30) # 7 days excess (one half-life)
    assert np.isclose(decay_7d, 0.5)

    decay_14d = calculate_decay(44, 30) # 14 days excess (two half-lives)
    assert np.isclose(decay_14d, 0.25)

def test_published_date_preservation_in_normalization():
    raw = pd.DataFrame({
        "observation_date": ["2024-01-01"],
        "published_date": ["2024-01-05"],
        "UNRATE": [3.5]
    })
    # normalize_fred_history_frame should preserve published_date if present
    normalized = macro.normalize_fred_history_frame(raw, "UNRATE")
    assert "published_date" in normalized.columns
    assert normalized["published_date"].iloc[0] == pd.Timestamp("2024-01-05")
