from unittest.mock import MagicMock

import pandas as pd
import pytest

# Refactored to avoid global sys.modules pollution
from src.engine.baseline.data_loader import fetch_baseline_series, load_all_baseline_data


@pytest.fixture
def mock_macro(monkeypatch):
    """Fixture to mock src.collector.macro locally for each test."""
    mock = MagicMock()
    # Use monkeypatch to safely mock the dependency in the module where it's used
    monkeypatch.setattr("src.engine.baseline.data_loader.fetch_fred_data", mock)
    return mock


def test_fetch_baseline_series_success(mock_macro):
    mock_df = pd.DataFrame(
        {"observation_date": ["2020-01-01", "2020-02-01"], "VALUE": [100.0, 105.0]}
    )
    mock_macro.return_value = mock_df

    df = fetch_baseline_series("TEST_ID")
    assert not df.empty
    assert "TEST_ID" in df.columns
    assert isinstance(df.index, pd.DatetimeIndex)


def test_fetch_baseline_series_failure(mock_macro):
    mock_macro.return_value = None

    df = fetch_baseline_series("FAIL_ID")
    assert df is None


def test_load_all_baseline_data_pit(mock_macro):
    # Mock data for different frequencies
    ipman = pd.DataFrame({"observation_date": ["2020-01-01"], "IPMAN": [50.0]})
    vix = pd.DataFrame({"observation_date": ["2020-01-01", "2020-01-02"], "VIXCLS": [15.0, 16.0]})

    def side_effect(series_id, **kwargs):
        if series_id == "IPMAN":
            return ipman
        if series_id == "VIXCLS":
            return vix
        return None

    mock_macro.side_effect = side_effect

    df = load_all_baseline_data()
    # Check if monthly data (IPMAN) is forward-filled to daily
    assert len(df) == 2
    assert df.loc["2020-01-02", "IPMAN"] == 50.0
    assert df.loc["2020-01-02", "VIXCLS"] == 16.0
