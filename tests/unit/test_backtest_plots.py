from __future__ import annotations

from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pandas as pd

from src.output.backtest_plots import build_beta_backtest_figure, save_beta_backtest_figure


def _daily_timeseries(use_signal_beta: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-02", periods=6, freq="B")
    data: dict[str, list[object]] = {
        "close": [100.0, 101.0, 99.0, 102.0, 104.0, 105.0],
        "tier0_regime": [
            "NEUTRAL",
            "NEUTRAL",
            "RICH_TIGHTENING",
            "RICH_TIGHTENING",
            "CRISIS",
            "CRISIS",
        ],
        "risk_state": [
            "RISK_NEUTRAL",
            "RISK_NEUTRAL",
            "RISK_REDUCED",
            "RISK_REDUCED",
            "RISK_EXIT",
            "RISK_EXIT",
        ],
    }
    if use_signal_beta:
        data["signal_target_beta"] = [1.2, 1.2, 0.8, 0.5, 0.5, 0.5]
    else:
        data["target_beta"] = [1.2, 1.2, 0.8, 0.5, 0.5, 0.5]
    return pd.DataFrame(data, index=dates)


def test_build_beta_backtest_figure_uses_target_beta_and_close():
    daily_ts = _daily_timeseries()
    summary = SimpleNamespace(signal_beta=0.78, realized_beta=0.61, mean_interval_beta_deviation=0.0432)

    fig = build_beta_backtest_figure(daily_ts, summary=summary)
    try:
        assert len(fig.axes) == 2
        top_price_axis = next(ax for ax in fig.axes if ax.get_ylabel() == "QQQ Price ($)")
        top_beta_axis = next(ax for ax in fig.axes if ax.get_ylabel() == "Target Beta")

        assert top_price_axis.get_ylabel() == "QQQ Price ($)"
        assert top_beta_axis.get_ylabel() == "Target Beta"
        assert any(line.get_label() == "QQQ Close" for line in top_price_axis.lines)
        assert any(line.get_label() == "Target Beta" for line in top_beta_axis.lines)
        assert any(collection.get_label() == "Beta Change Point" for collection in top_beta_axis.collections)
        assert "Average Signal Beta: 0.78" in top_price_axis.get_title()
    finally:
        plt.close(fig)


def test_build_beta_backtest_figure_supports_signal_beta_fallback():
    daily_ts = _daily_timeseries(use_signal_beta=True)

    fig = build_beta_backtest_figure(daily_ts)
    try:
        top_price_axis = next(ax for ax in fig.axes if ax.get_ylabel() == "QQQ Price ($)")
        top_beta_axis = next(ax for ax in fig.axes if ax.get_ylabel() == "Target Beta")
        assert any(line.get_label() == "QQQ Close" for line in top_price_axis.lines)
        assert any(line.get_label() == "Target Beta" for line in top_beta_axis.lines)
        assert any(collection.get_label() == "Beta Change Point" for collection in top_beta_axis.collections)
    finally:
        plt.close(fig)


def test_save_beta_backtest_figure_writes_all_paths(tmp_path):
    daily_ts = _daily_timeseries()
    summary = SimpleNamespace(signal_beta=0.78, realized_beta=0.61, mean_interval_beta_deviation=0.0432)
    out_a = tmp_path / "artifacts" / "beta.png"
    out_b = tmp_path / "docs" / "images" / "beta.png"

    saved_paths = save_beta_backtest_figure(daily_ts, summary, [out_a, out_b])

    assert saved_paths == [out_a, out_b]
    assert out_a.exists()
    assert out_b.exists()
