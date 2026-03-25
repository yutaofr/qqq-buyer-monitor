import pandas as pd
import pytest

from src.research.data_contracts import (
    REQUIRED_HISTORICAL_MACRO_COLUMNS,
    summarize_historical_macro_coverage,
    validate_historical_macro_frame,
)


@pytest.fixture
def canonical_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "effective_date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "credit_spread_bps": [350.0, 355.0, 360.0],
            "credit_acceleration_pct_10d": [0.0, 0.5, 0.2],
            "real_yield_10y_pct": [1.25, 1.20, 1.15],
            "net_liquidity_usd_bn": [250.0, 249.0, 248.5],
            "liquidity_roc_pct_4w": [0.0, -0.4, -0.6],
            "funding_stress_flag": [False, 0, 1],
            "source_credit_spread": ["fred:BAMLH0A0HYM2"] * 3,
            "source_real_yield": ["fred:DFII10"] * 3,
            "source_net_liquidity": ["derived:FRED"] * 3,
            "source_funding_stress": ["fred:NFCI"] * 3,
            "build_version": ["v7.0-r1"] * 3,
        }
    )


def test_required_historical_macro_columns_are_stable():
    assert list(REQUIRED_HISTORICAL_MACRO_COLUMNS) == [
        "observation_date",
        "effective_date",
        "credit_spread_bps",
        "credit_acceleration_pct_10d",
        "real_yield_10y_pct",
        "net_liquidity_usd_bn",
        "liquidity_roc_pct_4w",
        "funding_stress_flag",
        "source_credit_spread",
        "source_real_yield",
        "source_net_liquidity",
        "source_funding_stress",
        "build_version",
    ]


def test_validate_historical_macro_frame_accepts_canonical_schema(canonical_frame):
    validate_historical_macro_frame(canonical_frame)


def test_validate_historical_macro_frame_rejects_missing_required_column(canonical_frame):
    bad = canonical_frame.drop(columns=["effective_date"])
    with pytest.raises(ValueError, match="effective_date"):
        validate_historical_macro_frame(bad)


def test_validate_historical_macro_frame_rejects_bad_effective_date_order(canonical_frame):
    bad = canonical_frame.copy()
    bad.loc[1, "effective_date"] = "2024-01-01"
    with pytest.raises(ValueError, match="effective_date"):
        validate_historical_macro_frame(bad)


def test_validate_historical_macro_frame_rejects_invalid_funding_flag(canonical_frame):
    bad = canonical_frame.copy()
    bad.loc[2, "funding_stress_flag"] = "yes"
    with pytest.raises(ValueError, match="funding_stress_flag"):
        validate_historical_macro_frame(bad)


def test_summarize_historical_macro_coverage_reports_basic_metrics(canonical_frame):
    summary = summarize_historical_macro_coverage(canonical_frame)

    assert summary["rows"] == 3
    assert summary["first_observation_date"] == pd.Timestamp("2024-01-02")
    assert summary["last_observation_date"] == pd.Timestamp("2024-01-04")
    assert summary["coverage"]["credit_spread_bps"] == 1.0
    assert summary["coverage"]["funding_stress_flag"] == 1.0
