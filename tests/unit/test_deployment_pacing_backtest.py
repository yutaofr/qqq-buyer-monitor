from __future__ import annotations

import pandas as pd
import pytest

from src.backtest import Backtester


def test_backtest_deployment_pacing_alignment_scores_continuous_pace(monkeypatch):
    dates = pd.date_range("2024-01-02", periods=4, freq="B")
    ohlcv = pd.DataFrame({"Close": [100.0, 101.0, 99.0, 98.0]}, index=dates)
    aligned = pd.DataFrame(
        {
            "close": [100.0, 101.0, 99.0, 98.0],
            "funding_event": [True, True, True, True],
            "available_new_cash": [100.0, 100.0, 100.0, 100.0],
            "deployment_state": [
                "DEPLOY_BASE",
                "DEPLOY_SLOW",
                "DEPLOY_FAST",
                "DEPLOY_PAUSE",
            ],
            "deployment_multiplier": [1.0, 0.5, 2.0, 0.0],
            "expected_deployment_state": [
                "DEPLOY_BASE",
                "DEPLOY_BASE",
                "DEPLOY_FAST",
                "DEPLOY_PAUSE",
            ],
            "expected_deployment_multiplier": [1.0, 1.0, 2.0, 0.0],
        },
        index=dates,
    )

    def fake_build_signal_timeseries(self, *args, **kwargs):
        return aligned.copy()

    monkeypatch.setattr(Backtester, "build_signal_timeseries", fake_build_signal_timeseries)

    summary = Backtester().backtest_deployment_pacing_alignment(
        ohlcv,
        expected_matrix=aligned,
        tolerance=0.25,
    )

    assert summary.compared_points == 4
    assert summary.mean_error == pytest.approx(-0.125)
    assert summary.mean_absolute_error == pytest.approx(0.125)
    assert summary.rmse == pytest.approx(0.25)
    assert summary.error_variance == pytest.approx(0.046875)
    assert summary.error_std_dev == pytest.approx(0.21650635)
    assert summary.within_tolerance_ratio == pytest.approx(0.75)
    assert summary.actual_mean_pacing == pytest.approx(0.875)
    assert summary.expected_mean_pacing == pytest.approx(1.0)
    assert summary.cash_mean_absolute_error == pytest.approx(12.5)
    assert summary.cash_rmse == pytest.approx(25.0)

    daily = summary.daily_timeseries
    assert list(daily["actual_deployment_cash"]) == [100.0, 50.0, 200.0, 0.0]
    assert list(daily["expected_deployment_cash"]) == [100.0, 100.0, 200.0, 0.0]
    assert daily.loc[dates[1], "deployment_pacing_error"] == pytest.approx(-0.5)
    assert daily.loc[dates[-1], "cumulative_actual_deployment_cash"] == pytest.approx(350.0)


def test_backtest_deployment_pacing_alignment_requires_expected_pacing_signal(monkeypatch):
    dates = pd.date_range("2024-01-02", periods=2, freq="B")
    ohlcv = pd.DataFrame({"Close": [100.0, 101.0]}, index=dates)
    aligned = pd.DataFrame(
        {
            "close": [100.0, 101.0],
            "funding_event": [True, True],
            "available_new_cash": [100.0, 100.0],
            "deployment_state": ["DEPLOY_BASE", "DEPLOY_BASE"],
            "deployment_multiplier": [1.0, 1.0],
        },
        index=dates,
    )

    def fake_build_signal_timeseries(self, *args, **kwargs):
        return aligned.copy()

    monkeypatch.setattr(Backtester, "build_signal_timeseries", fake_build_signal_timeseries)

    with pytest.raises(ValueError, match="expected_deployment_multiplier"):
        Backtester().backtest_deployment_pacing_alignment(
            ohlcv,
            expected_matrix=aligned,
        )
