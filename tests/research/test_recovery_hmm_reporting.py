from __future__ import annotations

import pandas as pd

from src.research.recovery_hmm.reporting import build_performance_summary


def test_build_performance_summary_compares_shadow_qqq_and_production():
    dates = pd.date_range("2023-01-03", periods=5, freq="B")
    frame = pd.DataFrame(
        {
            "date": dates,
            "close": [100.0, 102.0, 101.0, 104.0, 106.0],
            "w_final": [0.5, 0.7, 0.8, 0.9, 1.0],
            "target_beta": [0.6, 0.65, 0.7, 0.75, 0.8],
        }
    )

    summary = build_performance_summary(frame)

    assert summary["shadow"]["total_return"] is not None
    assert summary["qqq"]["max_drawdown"] is not None
    assert summary["production"]["sharpe"] is not None
    assert summary["turnover"]["mean_abs_daily_change"] > 0.0

