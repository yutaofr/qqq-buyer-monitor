from __future__ import annotations

import pandas as pd
import pytest

from src.backtest import Backtester
from src.collector.historical_macro_seeder import HistoricalMacroSeeder


def _canonical_macro_frame(dates: pd.DatetimeIndex, spreads: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": [d.strftime("%Y-%m-%d") for d in dates],
            "effective_date": [d.strftime("%Y-%m-%d") for d in dates],
            "credit_spread_bps": spreads,
            "credit_acceleration_pct_10d": [0.0] * len(dates),
            "real_yield_10y_pct": [1.25] * len(dates),
            "net_liquidity_usd_bn": [250.0] * len(dates),
            "liquidity_roc_pct_4w": [0.0] * len(dates),
            "funding_stress_flag": [0] * len(dates),
            "source_credit_spread": ["fred:BAMLH0A0HYM2"] * len(dates),
            "source_real_yield": ["fred:DFII10"] * len(dates),
            "source_net_liquidity": ["derived"] * len(dates),
            "source_funding_stress": ["fred:NFCI"] * len(dates),
            "build_version": ["v7.0-class-a-research-r1"] * len(dates),
        }
    )


def test_build_signal_timeseries_returns_pure_beta_and_deployment_signals():
    dates = pd.date_range("2024-01-02", periods=9, freq="B")
    prices = pd.Series([100.0, 89.0, 79.0, 75.0, 70.0, 68.0, 67.0, 66.0, 65.0], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(dates, [220.0, 220.0, 220.0, 320.0, 320.0, 520.0, 520.0, 520.0, 520.0])
    seeder = HistoricalMacroSeeder(mock_df=macro)

    signals = Backtester().build_signal_timeseries(ohlcv, macro_seeder=seeder)

    assert {
        "signal_target_beta",
        "expected_target_beta",
        "tier0_regime",
        "risk_state",
        "deployment_state",
        "deployment_multiplier",
        "selected_candidate_id",
    } <= set(signals.columns)
    assert signals["signal_target_beta"].tolist() == pytest.approx([1.0, 1.0, 1.0, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0])
    assert signals["deployment_state"].tolist() == [
        "DEPLOY_BASE",
        "DEPLOY_FAST",
        "DEPLOY_FAST",
        "DEPLOY_BASE",
        "DEPLOY_BASE",
        "DEPLOY_PAUSE",
        "DEPLOY_PAUSE",
        "DEPLOY_PAUSE",
        "DEPLOY_PAUSE",
    ]


def test_build_signal_timeseries_unlocks_euphoric_risk_on_when_erp_is_present():
    dates = pd.date_range("2024-01-02", periods=3, freq="B")
    prices = pd.Series([100.0, 101.0, 102.0], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(dates, [220.0, 220.0, 220.0])
    seeder = HistoricalMacroSeeder(mock_df=macro)
    expectations = pd.DataFrame(
        {
            "expected_target_beta": [1.1, 1.1, 1.1],
            "erp": [5.5, 5.5, 5.5],
        },
        index=dates,
    )

    signals = Backtester().build_signal_timeseries(
        ohlcv,
        macro_seeder=seeder,
        expected_matrix=expectations,
    )

    assert set(signals["tier0_regime"]) == {"EUPHORIC"}
    assert set(signals["risk_state"]) == {"RISK_ON"}
    assert (signals["signal_target_beta"] > 1.0).all()


def test_target_beta_alignment_backtest_scores_against_expected_series():
    dates = pd.date_range("2024-01-02", periods=9, freq="B")
    prices = pd.Series([100.0, 89.0, 79.0, 75.0, 70.0, 68.0, 67.0, 66.0, 65.0], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(dates, [220.0, 220.0, 220.0, 320.0, 320.0, 520.0, 520.0, 520.0, 520.0])
    seeder = HistoricalMacroSeeder(mock_df=macro)
    expected = pd.DataFrame(
        {"expected_target_beta": [1.0, 1.0, 1.0, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0]},
        index=dates,
    )

    summary = Backtester().backtest_target_beta_alignment(
        ohlcv,
        expected_matrix=expected,
        macro_seeder=seeder,
    )

    assert summary.compared_points == len(dates)
    assert summary.mean_absolute_error == pytest.approx(0.0)
    assert summary.rmse == pytest.approx(0.0)
    assert summary.within_tolerance_ratio == pytest.approx(1.0)
    assert summary.daily_timeseries["expected_target_beta"].tolist() == pytest.approx(expected["expected_target_beta"].tolist())


def test_deployment_alignment_backtest_scores_against_expected_series():
    dates = pd.date_range("2024-01-02", periods=9, freq="B")
    prices = pd.Series([100.0, 89.0, 79.0, 75.0, 70.0, 68.0, 67.0, 66.0, 65.0], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(dates, [220.0, 220.0, 220.0, 320.0, 320.0, 520.0, 520.0, 520.0, 520.0])
    seeder = HistoricalMacroSeeder(mock_df=macro)
    expected = pd.DataFrame(
        {
            "expected_deployment_state": [
                "DEPLOY_BASE",
                "DEPLOY_FAST",
                "DEPLOY_FAST",
                "DEPLOY_BASE",
                "DEPLOY_BASE",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
            ]
        },
        index=dates,
    )

    summary = Backtester().backtest_deployment_alignment(
        ohlcv,
        expected_matrix=expected,
        macro_seeder=seeder,
    )

    assert summary.compared_points == len(dates)
    assert summary.exact_match_ratio == pytest.approx(1.0)
    assert summary.mean_rank_abs_error == pytest.approx(0.0)
    assert summary.within_one_step_ratio == pytest.approx(1.0)
    assert summary.daily_timeseries["expected_deployment_state"].tolist() == expected["expected_deployment_state"].tolist()
