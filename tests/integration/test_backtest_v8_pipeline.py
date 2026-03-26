from __future__ import annotations

import pandas as pd

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


def test_v8_backtest_preserves_left_side_window_but_locks_crisis():
    dates = pd.date_range("2024-01-02", periods=12, freq="B")
    prices = pd.Series([100.0, 97.0, 93.0, 88.0, 84.0, 82.0, 81.0, 79.0, 78.0, 77.0, 76.0, 75.0], index=dates)
    ohlcv = pd.DataFrame({"Close": prices}, index=dates)
    macro = _canonical_macro_frame(dates, [320.0] * 6 + [520.0] * 6)
    seeder = HistoricalMacroSeeder(mock_df=macro)

    summary = Backtester(initial_capital=10_000).simulate_portfolio(
        ohlcv,
        macro_seeder=seeder,
        enable_dynamic_search=True,
    )

    rich = summary.daily_timeseries[summary.daily_timeseries["tier0_regime"] == "RICH_TIGHTENING"]
    crisis = summary.daily_timeseries[summary.daily_timeseries["tier0_regime"] == "CRISIS"]

    assert not rich.empty
    assert not crisis.empty
    assert (rich["target_beta"] <= 0.81).all()
    assert (crisis["target_beta"] <= 0.01).all()
    assert set(crisis["risk_state"]) == {"RISK_EXIT"}
    assert set(crisis["selected_candidate_id"]) == {"exit-cash-001"}
