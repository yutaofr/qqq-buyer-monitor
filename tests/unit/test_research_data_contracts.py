import pandas as pd
import pytest

from src.research.data_contracts import (
    REQUIRED_HISTORICAL_MACRO_COLUMNS,
    SIGNAL_EXPECTATION_REQUIRED_COLUMNS,
    summarize_historical_macro_coverage,
    summarize_signal_expectation_coverage,
    validate_historical_macro_frame,
    validate_signal_expectation_frame,
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


@pytest.fixture
def expectation_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "expected_target_beta": [1.0, 0.5, 0.0],
            "expected_deployment_state": ["DEPLOY_FAST", "DEPLOY_BASE", "DEPLOY_PAUSE"],
            "rolling_drawdown": [0.05, 0.15, 0.32],
            "available_new_cash": [1000.0, 1000.0, 1000.0],
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


def test_required_signal_expectation_columns_are_stable():
    assert list(SIGNAL_EXPECTATION_REQUIRED_COLUMNS) == ["date"]


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


def test_validate_signal_expectation_frame_accepts_dual_surface(expectation_frame):
    validate_signal_expectation_frame(expectation_frame)


def test_validate_signal_expectation_frame_rejects_missing_expectation_columns(expectation_frame):
    bad = expectation_frame.drop(columns=["expected_target_beta", "expected_deployment_state"])
    with pytest.raises(ValueError, match="expected_target_beta"):
        validate_signal_expectation_frame(bad)


def test_validate_signal_expectation_frame_rejects_unknown_deployment_state(expectation_frame):
    bad = expectation_frame.copy()
    bad.loc[1, "expected_deployment_state"] = "DEPLOY_YOLO"
    with pytest.raises(ValueError, match="Unknown deployment state"):
        validate_signal_expectation_frame(bad)


def test_validate_signal_expectation_frame_rejects_duplicate_dates(expectation_frame):
    bad = pd.concat([expectation_frame, expectation_frame.iloc[[1]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate date values"):
        validate_signal_expectation_frame(bad)


def test_summarize_signal_expectation_coverage_reports_basic_metrics(expectation_frame):
    summary = summarize_signal_expectation_coverage(expectation_frame)

    assert summary["rows"] == 3
    assert summary["first_date"] == pd.Timestamp("2024-01-02")
    assert summary["last_date"] == pd.Timestamp("2024-01-04")
    assert summary["coverage"]["expected_target_beta"] == 1.0
    assert summary["coverage"]["expected_deployment_state"] == 1.0
