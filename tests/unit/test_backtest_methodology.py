from __future__ import annotations

import importlib
import inspect

import pandas as pd
import pytest

backtest = importlib.import_module("src.backtest")


def test_methodology_surface_excludes_synthetic_inputs() -> None:
    assert getattr(backtest, "FWD_HORIZONS", None) == (5, 20, 60)

    source = inspect.getsource(backtest.run_backtest)
    assert "Synthetic Fear & Greed" not in source
    assert "fg_synthetic" not in source
    assert "simulate_short_ratio" not in source
    assert "ShortVolRatio" not in source
    assert "capture rate" not in source.lower()


def test_methodology_helpers_are_testable_and_explicit() -> None:
    assert callable(getattr(backtest, "compute_forward_returns", None))
    assert callable(getattr(backtest, "compute_max_adverse_excursion", None))
    assert callable(getattr(backtest, "simulate_allocator", None))
    assert callable(getattr(backtest, "summarize_backtest_methodology", None))


def test_methodology_reports_forward_returns_and_drawdown_pain() -> None:
    prices = pd.Series(
        [100.0, 95.0, 97.0, 110.0, 120.0, 130.0, 140.0],
        index=pd.date_range("2024-01-01", periods=7, freq="B"),
    )

    forward_returns = backtest.compute_forward_returns(prices, prices.index[0], horizons=(1, 3, 5))
    assert forward_returns[1] == pytest.approx(-0.05)
    assert forward_returns[3] == pytest.approx(0.10)
    assert forward_returns[5] == pytest.approx(0.30)

    mae = backtest.compute_max_adverse_excursion(prices, prices.index[0], lookahead=5)
    assert mae == pytest.approx(-0.05)


def test_methodology_summary_uses_allocator_and_excludes_synthetic_inputs() -> None:
    prices = pd.Series(
        [100.0 - i for i in range(30)] + [70.0 + (50.0 * i / 49.0) for i in range(50)],
        index=pd.date_range("2024-01-01", periods=80, freq="B"),
    )
    tactical_states = pd.Series(
        [backtest.AllocationState.FAST_ACCUMULATE] * 30
        + [backtest.AllocationState.BASE_DCA] * 50,
        index=prices.index,
    )

    summary = backtest.summarize_backtest_methodology(prices, tactical_states=tactical_states, interval=5)

    assert set(summary.forward_returns_by_horizon) == {5, 20, 60}
    assert summary.max_adverse_excursion is not None
    assert summary.max_adverse_excursion <= 0
    assert summary.average_cost_improvement_vs_baseline_dca > 0
    assert 0.0 <= summary.fraction_capital_deployed_before_final_low <= 1.0
    assert "fear_greed" in summary.excluded_features
    assert summary.feature_policy["short_vol_ratio"].startswith("excluded")


def test_methodology_marks_chasing_risk_in_rising_markets() -> None:
    prices = pd.Series(
        [100.0, 104.0, 109.0, 115.0, 122.0, 131.0, 142.0, 155.0, 171.0, 190.0],
        index=pd.date_range("2024-01-01", periods=10, freq="B"),
    )

    states = backtest.derive_tactical_state_series(prices)
    assert backtest.AllocationState.PAUSE_CHASING in set(states.iloc[-4:])


def test_pause_chasing_slows_deployment_relative_to_base_dca() -> None:
    prices = pd.Series(
        [100.0 + i for i in range(40)],
        index=pd.date_range("2024-01-01", periods=40, freq="B"),
    )

    base_states = pd.Series(
        [backtest.AllocationState.BASE_DCA] * len(prices),
        index=prices.index,
    )
    pause_states = pd.Series(
        [backtest.AllocationState.PAUSE_CHASING] * len(prices),
        index=prices.index,
    )

    base_summary = backtest.summarize_backtest_methodology(prices, tactical_states=base_states, interval=5)
    pause_summary = backtest.summarize_backtest_methodology(prices, tactical_states=pause_states, interval=5)

    assert pause_summary.events[0].units < base_summary.events[0].units
    assert pause_summary.total_capital_units < base_summary.total_capital_units


def test_methodology_weights_forward_returns_by_allocation_units() -> None:
    prices = pd.Series(
        [100.0, 95.0, 90.0, 85.0, 80.0, 82.0, 84.0, 86.0, 88.0, 90.0, 92.0, 94.0, 96.0, 98.0, 100.0],
        index=pd.date_range("2024-01-01", periods=15, freq="B"),
    )
    tactical_states = pd.Series(
        [backtest.AllocationState.FAST_ACCUMULATE] * 5
        + [backtest.AllocationState.BASE_DCA] * 5
        + [backtest.AllocationState.PAUSE_CHASING] * 5,
        index=prices.index,
    )

    summary = backtest.summarize_backtest_methodology(prices, tactical_states=tactical_states, interval=5)
    weighted_forward_return_5 = sum(
        event.forward_returns[5] * event.units
        for event in summary.events
        if event.forward_returns[5] is not None
    ) / sum(event.units for event in summary.events if event.forward_returns[5] is not None)

    assert summary.forward_returns_by_horizon[5] == pytest.approx(weighted_forward_return_5)
