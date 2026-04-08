from __future__ import annotations

import pandas as pd

from src.research.recovery_hmm.data_adapter import build_local_readiness_report


def test_local_readiness_report_flags_missing_locked_columns(tmp_path):
    frame = pd.DataFrame(
        {
            "observation_date": ["2022-01-03", "2022-01-04"],
            "credit_spread_bps": [450.0, 430.0],
            "real_yield_10y_pct": [0.015, 0.014],
        }
    )
    path = tmp_path / "macro.csv"
    frame.to_csv(path, index=False)

    report = build_local_readiness_report(path)

    assert report.is_ready is False
    assert report.coverage["hy_ig_spread"] == 1.0
    assert report.coverage["real_yield_10y"] == 1.0
    assert "curve_10y_2y" in report.missing_columns
    assert "qqq_skew_20d_mean" in report.missing_columns
    assert report.incomplete_columns == ()
