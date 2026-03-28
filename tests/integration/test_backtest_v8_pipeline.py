from __future__ import annotations

import pandas as pd

from src.backtest import Backtester
from src.collector.historical_macro_seeder import HistoricalMacroSeeder


def _canonical_macro_frame(
    dates: pd.DatetimeIndex,
    spreads: list[float],
    *,
    erps: list[float] | None = None,
) -> pd.DataFrame:
    erp_values = erps if erps is not None else [3.5] * len(dates)
    forward_pe = [
        None if erp is None else 100.0 / (float(erp) + 1.25)
        for erp in erp_values
    ]
    return pd.DataFrame(
        {
            "observation_date": [d.strftime("%Y-%m-%d") for d in dates],
            "effective_date": [d.strftime("%Y-%m-%d") for d in dates],
            "credit_spread_bps": spreads,
            "credit_acceleration_pct_10d": [0.0] * len(dates),
            "forward_pe": forward_pe,
            "erp_pct": erp_values,
            "real_yield_10y_pct": [1.25] * len(dates),
            "net_liquidity_usd_bn": [250.0] * len(dates),
            "liquidity_roc_pct_4w": [0.0] * len(dates),
            "funding_stress_flag": [0] * len(dates),
            "source_credit_spread": ["fred:BAMLH0A0HYM2"] * len(dates),
            "source_forward_pe": ["damodaran:histimpl"] * len(dates),
            "source_erp": ["damodaran:histimpl"] * len(dates),
            "source_real_yield": ["fred:DFII10"] * len(dates),
            "source_net_liquidity": ["derived"] * len(dates),
            "source_funding_stress": ["fred:NFCI"] * len(dates),
            "build_version": ["v7.0-class-a-research-r1"] * len(dates),
        }
    )


def test_v10_backtest_records_late_cycle_and_bust_with_qld_locked():
    dates = pd.date_range("2024-01-02", periods=12, freq="B")
    prices = pd.Series([100.0, 97.0, 93.0, 88.0, 84.0, 82.0, 81.0, 79.0, 78.0, 77.0, 76.0, 75.0], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(
        dates,
        [470.0] * 6 + [680.0] * 6,
        erps=[2.1] * 6 + [3.0] * 6,
    )
    seeder = HistoricalMacroSeeder(mock_df=macro)

    summary = Backtester(initial_capital=10_000).simulate_portfolio(
        ohlcv,
        macro_seeder=seeder,
        enable_dynamic_search=True,
    )

    late = summary.daily_timeseries[summary.daily_timeseries["cycle_regime"] == "LATE_CYCLE"]
    bust = summary.daily_timeseries[summary.daily_timeseries["cycle_regime"] == "BUST"]

    assert not late.empty
    assert not bust.empty
    assert (late["qld_share_ceiling"] == 0.0).all()
    assert (bust["qld_share_ceiling"] == 0.0).all()
    assert (late["advised_target_beta"] <= 0.81).all()
    assert (bust["advised_target_beta"] <= 0.51).all()
    assert {"raw_target_beta", "advised_target_beta"} <= set(summary.daily_timeseries.columns)
    assert "cycle_regime" in summary.daily_timeseries.columns
    assert "qld_share_ceiling" in summary.daily_timeseries.columns
    assert set(bust["risk_state"]) == {"RISK_EXIT"}
    assert set(bust["selected_candidate_id"]) == {"exit-floor-001"}


def test_v8_backtest_tracks_authorized_crisis_blood_chip_overrides_without_changing_beta_floor():
    dates = pd.date_range("2024-01-02", periods=25, freq="B")
    prices = pd.Series([100.0 - (i * 1.25) for i in range(25)], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(
        dates,
        [320.0] * 20 + [680.0] * 5,
        erps=[3.5] * 20 + [3.0] * 5,
    )
    macro["credit_acceleration_pct_10d"] = [0.0] * 20 + [-1.0] * 5
    macro["liquidity_roc_pct_4w"] = [0.0] * 20 + [1.0] * 5
    seeder = HistoricalMacroSeeder(mock_df=macro)

    summary = Backtester(initial_capital=10_000).simulate_portfolio(
        ohlcv,
        macro_seeder=seeder,
        enable_dynamic_search=True,
    )

    crisis = summary.daily_timeseries[summary.daily_timeseries["tier0_regime"] == "CRISIS"]

    assert not crisis.empty
    assert "blood_chip_override_active" in summary.daily_timeseries.columns
    assert "deployment_reason_rule" in summary.daily_timeseries.columns
    assert "deployment_reason_path" in summary.daily_timeseries.columns
    assert "cycle_regime" in summary.daily_timeseries.columns
    assert (crisis["cycle_regime"] == "BUST").all()
    assert (crisis["qld_share_ceiling"] == 0.0).all()
    assert (crisis["target_beta"] <= 0.51).all()
    assert (crisis.loc[crisis["blood_chip_override_active"], "deployment_state"] == "DEPLOY_FAST").all()
    assert (
        crisis.loc[crisis["blood_chip_override_active"], "deployment_reason_path"]
        == "liquidity_reversal"
    ).all()
    assert (
        crisis.loc[~crisis["blood_chip_override_active"], "deployment_state"] == "DEPLOY_PAUSE"
    ).all()


def test_v10_backtest_capitulation_unlocks_limited_qld_candidate():
    dates = pd.date_range("2024-01-02", periods=25, freq="B")
    prices = pd.Series([100.0 - (i * 1.10) for i in range(25)], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(
        dates,
        [620.0] * 25,
        erps=[5.1] * 25,
    )
    macro["credit_acceleration_pct_10d"] = [-1.0] * 25
    macro["liquidity_roc_pct_4w"] = [1.0] * 25
    seeder = HistoricalMacroSeeder(mock_df=macro)

    summary = Backtester(initial_capital=10_000).simulate_portfolio(
        ohlcv,
        macro_seeder=seeder,
        enable_dynamic_search=True,
    )

    capitulation = summary.daily_timeseries[summary.daily_timeseries["cycle_regime"] == "CAPITULATION"]

    assert not capitulation.empty
    assert (capitulation["risk_state"] == "RISK_ON").all()
    assert (capitulation["qld_share_ceiling"] == 0.25).all()
    assert (capitulation["selected_candidate_id"] == "capitulation-max-001").all()
    assert (capitulation["advised_target_beta"] >= 1.19).all()
