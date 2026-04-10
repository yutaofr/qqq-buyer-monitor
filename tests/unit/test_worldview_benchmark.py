from __future__ import annotations

import numpy as np
import pandas as pd

from src.research.worldview_benchmark import build_worldview_benchmark


def _series_frame(close: np.ndarray, volume: np.ndarray | None = None) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=len(close))
    if volume is None:
        volume = np.full(len(close), 1_000_000.0)
    return pd.DataFrame({"Close": close, "Volume": volume}, index=dates)


def test_worldview_benchmark_prefers_mid_cycle_in_persistent_uptrend():
    close = np.linspace(100.0, 180.0, 320)
    volume = np.linspace(900_000.0, 1_100_000.0, 320)

    benchmark = build_worldview_benchmark(_series_frame(close, volume))
    latest = benchmark.iloc[-1]

    assert latest["benchmark_regime"] == "MID_CYCLE"
    assert latest["benchmark_prob_MID_CYCLE"] > latest["benchmark_prob_LATE_CYCLE"]
    assert latest["benchmark_expected_beta"] > 0.9
    assert latest["benchmark_transition_intensity"] < 0.45
    assert latest["benchmark_entropy"] < 0.45


def test_worldview_benchmark_prefers_bust_in_death_cross_and_drawdown():
    close = np.concatenate([np.linspace(100.0, 165.0, 200), np.linspace(165.0, 92.0, 120)])
    volume = np.concatenate(
        [np.linspace(900_000.0, 1_000_000.0, 200), np.linspace(1_100_000.0, 1_600_000.0, 120)]
    )

    benchmark = build_worldview_benchmark(_series_frame(close, volume))
    latest = benchmark.iloc[-1]

    assert latest["benchmark_regime"] == "BUST"
    assert latest["benchmark_prob_BUST"] > 0.45
    assert latest["benchmark_expected_beta"] <= 0.65
    assert latest["benchmark_entropy"] > 0.30


def test_worldview_benchmark_prefers_recovery_after_rebound():
    close = np.concatenate(
        [
            np.linspace(100.0, 160.0, 180),
            np.linspace(160.0, 108.0, 70),
            np.linspace(108.0, 148.0, 70),
        ]
    )
    volume = np.concatenate(
        [
            np.linspace(950_000.0, 1_050_000.0, 180),
            np.linspace(1_200_000.0, 1_700_000.0, 70),
            np.linspace(1_600_000.0, 1_250_000.0, 70),
        ]
    )

    benchmark = build_worldview_benchmark(_series_frame(close, volume))
    latest = benchmark.iloc[-1]

    assert latest["benchmark_regime"] == "RECOVERY"
    assert latest["benchmark_prob_RECOVERY"] > latest["benchmark_prob_BUST"]
    assert 0.8 <= latest["benchmark_expected_beta"] <= 1.0
    assert latest["benchmark_entropy"] < 0.50


def test_worldview_benchmark_emits_late_cycle_momentum_on_price_volume_divergence():
    close = np.concatenate([np.linspace(100.0, 155.0, 260), np.linspace(155.0, 168.0, 60)])
    volume = np.concatenate(
        [np.linspace(1_200_000.0, 1_180_000.0, 260), np.linspace(1_100_000.0, 650_000.0, 60)]
    )

    benchmark = build_worldview_benchmark(_series_frame(close, volume))
    latest = benchmark.iloc[-1]

    assert latest["benchmark_prob_LATE_CYCLE"] > latest["benchmark_prob_BUST"]
    assert latest["benchmark_prob_delta_LATE_CYCLE"] > 0.0
    assert benchmark["benchmark_prob_acceleration_LATE_CYCLE"].tail(60).max() > 0.0
    assert latest["benchmark_entropy"] > 0.25


def test_worldview_benchmark_emits_multiframe_rsi_and_transition_bands():
    close = np.concatenate(
        [
            np.linspace(100.0, 155.0, 220),
            np.linspace(155.0, 158.0, 40),
            np.linspace(158.0, 150.0, 40),
        ]
    )
    volume = np.concatenate(
        [
            np.linspace(1_100_000.0, 1_050_000.0, 220),
            np.linspace(1_000_000.0, 700_000.0, 40),
            np.linspace(720_000.0, 760_000.0, 40),
        ]
    )

    benchmark = build_worldview_benchmark(_series_frame(close, volume))
    latest = benchmark.iloc[-1]

    assert "benchmark_weekly_rsi" in benchmark.columns
    assert "benchmark_monthly_rsi" in benchmark.columns
    assert "benchmark_transition_intensity" in benchmark.columns
    assert "benchmark_entropy" in benchmark.columns
    assert "benchmark_entropy_lower" in benchmark.columns
    assert "benchmark_entropy_upper" in benchmark.columns
    assert "benchmark_recent_damage" in benchmark.columns
    assert "benchmark_recovery_impulse" in benchmark.columns
    assert "benchmark_bust_pressure" in benchmark.columns
    assert "benchmark_prob_lower_LATE_CYCLE" in benchmark.columns
    assert "benchmark_prob_upper_LATE_CYCLE" in benchmark.columns
    assert latest["benchmark_transition_intensity"] >= 0.0
    assert latest["benchmark_recovery_impulse"] >= 0.0
    assert latest["benchmark_prob_upper_LATE_CYCLE"] >= latest["benchmark_prob_LATE_CYCLE"]


def test_worldview_benchmark_entropy_drops_once_trend_is_confirmed():
    close = np.concatenate(
        [
            np.linspace(100.0, 132.0, 120),
            np.linspace(132.0, 134.0, 20),
            np.linspace(134.0, 182.0, 180),
        ]
    )
    volume = np.concatenate(
        [
            np.linspace(1_050_000.0, 1_000_000.0, 120),
            np.linspace(980_000.0, 780_000.0, 20),
            np.linspace(820_000.0, 900_000.0, 180),
        ]
    )

    benchmark = build_worldview_benchmark(_series_frame(close, volume))

    transition_slice = benchmark.iloc[120:150]
    stable_slice = benchmark.iloc[-40:]

    assert transition_slice["benchmark_transition_intensity"].mean() > 0.25
    assert stable_slice["benchmark_regime"].mode().iloc[0] == "MID_CYCLE"
    assert stable_slice["benchmark_entropy"].mean() < transition_slice["benchmark_entropy"].mean()
    assert (
        stable_slice["benchmark_entropy_upper"].mean()
        < transition_slice["benchmark_entropy_upper"].mean()
    )


def test_worldview_benchmark_emits_context_columns_for_conditional_process_audit():
    close = np.concatenate(
        [
            np.linspace(100.0, 155.0, 220),
            np.linspace(155.0, 158.0, 40),
            np.linspace(158.0, 150.0, 40),
        ]
    )
    volume = np.concatenate(
        [
            np.linspace(1_100_000.0, 1_050_000.0, 220),
            np.linspace(1_000_000.0, 700_000.0, 40),
            np.linspace(720_000.0, 760_000.0, 40),
        ]
    )

    benchmark = build_worldview_benchmark(_series_frame(close, volume))

    assert "benchmark_uncertainty" in benchmark.columns
    assert "benchmark_trend_strength" in benchmark.columns
    assert "benchmark_conflict_score" in benchmark.columns
    assert benchmark["benchmark_uncertainty"].between(0.0, 1.0).all()
    assert benchmark["benchmark_trend_strength"].between(0.0, 1.0).all()
    assert benchmark["benchmark_conflict_score"].between(0.0, 1.0).all()
