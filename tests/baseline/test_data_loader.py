from unittest.mock import MagicMock

import pandas as pd
import pytest

# Refactored to avoid global sys.modules pollution
from src.engine.baseline.data_loader import fetch_baseline_series, load_all_baseline_data


@pytest.fixture
def mock_macro(monkeypatch):
    """Fixture to mock src.collector.macro locally for each test."""
    mock = MagicMock()
    # Ensure ALFRED path is also mocked to avoid hitting real API/cache
    monkeypatch.setattr(
        "src.engine.baseline.data_loader.fetch_fred_api", lambda *args, **kwargs: None
    )
    # Use monkeypatch to safely mock the dependency in the module where it's used
    monkeypatch.setattr("src.engine.baseline.data_loader.fetch_fred_data", mock)
    return mock


def test_fetch_baseline_series_success(mock_macro):
    # Daily series should have 1-day lag
    mock_df = pd.DataFrame({"observation_date": ["2020-01-01"], "VIXCLS": [15.0]})
    mock_macro.return_value = mock_df

    df = fetch_baseline_series("VIXCLS")
    assert not df.empty
    # Effective date should be next business day
    assert df.index[0] == pd.Timestamp("2020-01-02")
    assert df.iloc[0]["VIXCLS"] == 15.0
    assert df.iloc[0]["observation_date"] == pd.Timestamp("2020-01-01")


def test_fetch_baseline_series_uses_alfred_vintage(monkeypatch):
    vintage = pd.DataFrame(
        {
            "observation_date": ["2020-01-01", "2020-01-01"],
            "realtime_start": ["2020-01-08", "2020-01-15"],
            "realtime_end": ["2020-01-14", "2262-04-11"],
            "IPMAN": [50.0, 55.0],
        }
    )

    def api_side_effect(series_id, **kwargs):
        if series_id == "IPMAN":
            return vintage
        return None

    monkeypatch.setattr("src.engine.baseline.data_loader.fetch_fred_api", api_side_effect)
    monkeypatch.setattr(
        "src.engine.baseline.data_loader.fetch_fred_data",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("fallback path should not run")
        ),
    )

    df = fetch_baseline_series("IPMAN")

    assert df.attrs["vintage_mode"] == "ALFRED"
    assert list(df.index) == [pd.Timestamp("2020-01-08"), pd.Timestamp("2020-01-15")]
    assert df.loc[pd.Timestamp("2020-01-08"), "IPMAN"] == 50.0
    assert df.loc[pd.Timestamp("2020-01-15"), "IPMAN"] == 55.0


def test_load_all_baseline_data_pit(mock_macro):
    # IPMAN (Monthly) observed on 2020-01-01
    ipman = pd.DataFrame({"observation_date": ["2020-01-01"], "IPMAN": [50.0]})
    # VIXCLS (Daily) observed on 2020-01-01, 2020-01-02
    vix = pd.DataFrame(
        {
            "observation_date": ["2020-01-01", "2020-01-02", "2020-02-03"],
            "VIXCLS": [15.0, 16.0, 17.0],
        }
    )

    def side_effect(series_id, **kwargs):
        if series_id == "IPMAN":
            return ipman
        if series_id == "VIXCLS":
            return vix
        return None

    mock_macro.side_effect = side_effect

    df = load_all_baseline_data()

    # 1. IPMAN (Monthly) has 22-day lag. Observation 2020-01-01 -> Effective ~2020-02-03
    # 2. VIX (Daily) has 1-day lag. Observation 2020-01-01 -> Effective 2020-01-02

    # On 2020-01-02, VIX should be 15.0, but IPMAN should be NaN (not yet effective)
    assert df.loc["2020-01-02", "VIXCLS"] == 15.0
    assert pd.isna(df.loc["2020-01-02", "IPMAN"])

    # IPMAN (2020-01-01 observation) becomes effective 22 business days later
    # 2020-01-01 + 22 BDays approx Feb 3rd
    assert df.loc["2020-02-04", "IPMAN"] == 50.0
    assert df.loc["2020-02-04", "VIXCLS"] == 17.0
