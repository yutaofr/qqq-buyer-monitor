from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.backtest import Backtester
from src.collector.historical_macro_seeder import HistoricalMacroSeeder


def _canonical_macro_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03"],
            "effective_date": ["2024-01-03", "2024-01-04"],
            "credit_spread_bps": [350.0, 360.0],
            "credit_acceleration_pct_10d": [0.0, 0.8],
            "real_yield_10y_pct": [1.25, 1.20],
            "net_liquidity_usd_bn": [250.0, 249.0],
            "liquidity_roc_pct_4w": [0.0, -0.4],
            "funding_stress_flag": [0, 1],
            "source_credit_spread": ["fred:BAMLH0A0HYM2", "fred:BAMLH0A0HYM2"],
            "source_real_yield": ["fred:DFII10", "fred:DFII10"],
            "source_net_liquidity": ["derived:WALCL-WDTGAL-RRPONTSYD", "derived:WALCL-WDTGAL-RRPONTSYD"],
            "source_funding_stress": ["fred:NFCI", "fred:NFCI"],
            "build_version": ["v7.0-class-a-research-r1", "v7.0-class-a-research-r1"],
        }
    )


def _legacy_macro_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03"],
            "BAMLH0A0HYM2": [3.5, 3.6],
            "liquidity_roc": [-3.0, -2.5],
            "is_funding_stressed": [True, True],
        }
    )


def test_backtester_can_use_canonical_macro_seeder(tmp_path):
    prices = pd.Series(
        [100.0, 101.0, 102.0],
        index=pd.date_range("2024-01-02", periods=3, freq="B"),
    )
    ohlcv = pd.DataFrame({"Close": prices}, index=prices.index)
    csv_path = tmp_path / "canonical_macro.csv"
    _canonical_macro_frame().to_csv(csv_path, index=False)
    seeder = HistoricalMacroSeeder(csv_path=str(csv_path))

    summary = Backtester(initial_capital=10000).simulate_portfolio(ohlcv, macro_seeder=seeder)

    assert len(summary.daily_timeseries) == 3
    assert summary.daily_timeseries["nav"].notna().all()
    assert summary.daily_timeseries["state"].notna().all()


def test_legacy_macro_file_is_rejected_by_seeder(tmp_path):
    csv_path = tmp_path / "legacy_macro.csv"
    _legacy_macro_frame().to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="credit_spread_bps"):
        HistoricalMacroSeeder(csv_path=str(csv_path))
