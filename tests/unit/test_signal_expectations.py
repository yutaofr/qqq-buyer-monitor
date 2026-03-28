from __future__ import annotations

import pandas as pd

from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.research.signal_expectations import build_market_expectation_matrix


def _canonical_macro_frame(
    dates: pd.DatetimeIndex,
    *,
    spreads: list[float],
    erps: list[float | None] | None = None,
    accelerations: list[float] | None = None,
    liquidity: list[float] | None = None,
    funding: list[int] | None = None,
) -> pd.DataFrame:
    size = len(dates)
    erp_values = erps if erps is not None else [3.5] * size
    forward_pe = [
        None if erp is None else 100.0 / (float(erp) + 1.25)
        for erp in erp_values
    ]
    return pd.DataFrame(
        {
            "observation_date": [d.strftime("%Y-%m-%d") for d in dates],
            "effective_date": [d.strftime("%Y-%m-%d") for d in dates],
            "credit_spread_bps": spreads,
            "credit_acceleration_pct_10d": accelerations or [0.0] * size,
            "forward_pe": forward_pe,
            "erp_pct": erp_values,
            "real_yield_10y_pct": [1.25] * size,
            "net_liquidity_usd_bn": [250.0] * size,
            "liquidity_roc_pct_4w": liquidity or [0.0] * size,
            "funding_stress_flag": funding or [0] * size,
            "source_credit_spread": ["fred:BAMLH0A0HYM2"] * size,
            "source_forward_pe": ["damodaran:histimpl"] * size,
            "source_erp": ["damodaran:histimpl"] * size,
            "source_real_yield": ["fred:DFII10"] * size,
            "source_net_liquidity": ["derived:WALCL-WDTGAL-RRPONTSYD"] * size,
            "source_funding_stress": ["fred:NFCI"] * size,
            "build_version": ["v7.0-class-a-research-r1"] * size,
        }
    )


def test_expectation_matrix_respects_beta_floor_and_cap():
    dates = pd.date_range("2024-01-02", periods=6, freq="B")
    prices = pd.DataFrame({"Close": [100.0, 101.0, 98.0, 94.0, 92.0, 93.0]}, index=dates)
    macro = _canonical_macro_frame(
        dates,
        spreads=[300.0, 300.0, 320.0, 520.0, 680.0, 420.0],
        accelerations=[0.0, 0.0, 0.0, 20.0, 0.0, -1.0],
        liquidity=[0.0, 0.0, 0.0, -6.0, -6.0, 0.0],
    )

    frame = build_market_expectation_matrix(
        prices,
        macro_seeder=HistoricalMacroSeeder(mock_df=macro),
    )

    assert set(frame.columns) >= {
        "date",
        "expected_target_beta",
        "expected_deployment_state",
        "rolling_drawdown",
        "available_new_cash",
        "capitulation_score",
        "tactical_stress_score",
    }
    assert frame["expected_target_beta"].between(0.5, 1.2).all()


def test_expectation_matrix_pauses_deployment_in_crisis():
    dates = pd.date_range("2024-01-02", periods=5, freq="B")
    prices = pd.DataFrame({"Close": [100.0, 92.0, 86.0, 80.0, 75.0]}, index=dates)
    macro = _canonical_macro_frame(dates, spreads=[320.0, 520.0, 680.0, 680.0, 680.0])

    frame = build_market_expectation_matrix(
        prices,
        macro_seeder=HistoricalMacroSeeder(mock_df=macro),
    )

    final_row = frame.iloc[-1]
    assert final_row["expected_target_beta"] == 0.5
    assert final_row["expected_deployment_state"] == "DEPLOY_PAUSE"


def test_expectation_matrix_unlocks_fast_deployment_during_crisis_liquidity_reversal():
    dates = pd.date_range("2024-01-02", periods=25, freq="B")
    prices = pd.DataFrame({"Close": [100.0 - (i * 1.25) for i in range(25)]}, index=dates)
    macro = _canonical_macro_frame(
        dates,
        spreads=[320.0] * 20 + [680.0] * 5,
        accelerations=[0.0] * 20 + [-1.0] * 5,
        liquidity=[0.0] * 20 + [1.0] * 5,
    )

    frame = build_market_expectation_matrix(
        prices,
        macro_seeder=HistoricalMacroSeeder(mock_df=macro),
    )

    final_row = frame.iloc[-1]
    assert final_row["expected_target_beta"] == 0.5
    assert final_row["expected_deployment_state"] == "DEPLOY_FAST"


def test_expectation_matrix_unlocks_risk_on_in_clean_tight_credit():
    dates = pd.date_range("2024-01-02", periods=25, freq="B")
    prices = pd.DataFrame({"Close": [100.0 + i for i in range(25)]}, index=dates)
    macro = _canonical_macro_frame(dates, spreads=[320.0] * len(dates))

    frame = build_market_expectation_matrix(
        prices,
        macro_seeder=HistoricalMacroSeeder(mock_df=macro),
    )

    assert frame.iloc[-1]["expected_target_beta"] == 1.0
    assert frame.iloc[-1]["expected_deployment_state"] == "DEPLOY_BASE"


def test_expectation_matrix_uses_unqualified_cycle_ceiling_when_erp_is_missing():
    dates = pd.date_range("2024-01-02", periods=6, freq="B")
    prices = pd.DataFrame({"Close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]}, index=dates)
    macro = _canonical_macro_frame(dates, spreads=[220.0] * len(dates), erps=[None] * len(dates))

    frame = build_market_expectation_matrix(
        prices,
        macro_seeder=HistoricalMacroSeeder(mock_df=macro),
    )

    assert set(frame["expected_target_beta"]) == {0.8}
