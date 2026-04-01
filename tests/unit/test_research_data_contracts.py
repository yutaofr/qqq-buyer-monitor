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
            "effective_date": ["2024-01-03", "2024-01-04", "2024-01-05"],
            "credit_spread_bps": [350.0, 355.0, 360.0],
            "real_yield_10y_pct": [0.0125, 0.0120, 0.0115],
            "net_liquidity_usd_bn": [250.0, 249.0, 248.5],
            "treasury_vol_21d": [0.006, 0.0065, 0.0070],
            "copper_gold_ratio": [0.18, 0.181, 0.183],
            "breakeven_10y": [0.022, 0.021, 0.020],
            "core_capex_mm": [12.0, 12.0, 12.0],
            "usdjpy": [148.0, 147.5, 147.0],
            "erp_ttm_pct": [0.038, 0.038, 0.038],
            "source_credit_spread": ["fred:BAMLH0A0HYM2"] * 3,
            "source_real_yield": ["fred:DFII10"] * 3,
            "source_net_liquidity": ["derived:FRED"] * 3,
            "source_treasury_vol": ["direct:fred_dgs10"] * 3,
            "source_copper_gold": ["direct:yfinance"] * 3,
            "source_breakeven": ["direct:fred_t10yie"] * 3,
            "source_core_capex": ["direct:fred_neworder"] * 3,
            "source_usdjpy": ["direct:yfinance"] * 3,
            "source_erp_ttm": ["direct:shiller"] * 3,
            "build_version": ["v12.0-r1"] * 3,
            "forward_pe": [None, None, None],
            "erp_pct": [None, None, None],
            "source_forward_pe": ["deprecated:v12"] * 3,
            "source_erp": ["deprecated:v12"] * 3,
        }
    )


@pytest.fixture
def expectation_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "expected_target_beta": [1.0, 0.8, 0.5],
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
        "real_yield_10y_pct",
        "net_liquidity_usd_bn",
        "treasury_vol_21d",
        "copper_gold_ratio",
        "breakeven_10y",
        "core_capex_mm",
        "usdjpy",
        "erp_ttm_pct",
        "source_credit_spread",
        "source_real_yield",
        "source_net_liquidity",
        "source_treasury_vol",
        "source_copper_gold",
        "source_breakeven",
        "source_core_capex",
        "source_usdjpy",
        "source_erp_ttm",
        "build_version",
    ]


def test_required_signal_expectation_columns_are_stable():
    assert list(SIGNAL_EXPECTATION_REQUIRED_COLUMNS) == ["date"]


def test_validate_historical_macro_frame_accepts_v12_canonical_schema(canonical_frame):
    validate_historical_macro_frame(canonical_frame)


def test_validate_historical_macro_frame_accepts_deprecated_v11_columns_as_extras(canonical_frame):
    validate_historical_macro_frame(canonical_frame.loc[:, canonical_frame.columns])


def test_validate_historical_macro_frame_rejects_missing_required_column(canonical_frame):
    bad = canonical_frame.drop(columns=["source_erp_ttm"])
    with pytest.raises(ValueError, match="source_erp_ttm"):
        validate_historical_macro_frame(bad)


def test_validate_historical_macro_frame_rejects_bad_effective_date_order(canonical_frame):
    bad = canonical_frame.copy()
    bad.loc[1, "effective_date"] = "2024-01-01"
    with pytest.raises(ValueError, match="effective_date"):
        validate_historical_macro_frame(bad)


def test_validate_historical_macro_frame_rejects_duplicate_effective_dates(canonical_frame):
    bad = canonical_frame.copy()
    bad.loc[2, "effective_date"] = "2024-01-04"
    with pytest.raises(ValueError, match="Duplicate effective_date"):
        validate_historical_macro_frame(bad)


def test_summarize_historical_macro_coverage_reports_basic_metrics(canonical_frame):
    summary = summarize_historical_macro_coverage(canonical_frame)

    assert summary["rows"] == 3
    assert summary["first_observation_date"] == pd.Timestamp("2024-01-02")
    assert summary["last_observation_date"] == pd.Timestamp("2024-01-04")
    assert summary["coverage"]["credit_spread_bps"] == 1.0
    assert summary["coverage"]["treasury_vol_21d"] == 1.0
    assert summary["coverage"]["erp_ttm_pct"] == 1.0


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


def test_validate_signal_expectation_frame_rejects_beta_outside_runtime_band(expectation_frame):
    bad = expectation_frame.copy()
    bad.loc[2, "expected_target_beta"] = 0.3
    with pytest.raises(ValueError, match="between 0.5 and 1.2"):
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
