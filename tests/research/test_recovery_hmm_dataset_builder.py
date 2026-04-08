from __future__ import annotations

import pandas as pd

from src.research.recovery_hmm.dataset_builder import build_shadow_dataset


def _fred_frame(dates: list[str], column: str, values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"observation_date": pd.to_datetime(dates), column: values})


def test_build_shadow_dataset_emits_all_required_columns_with_lineage(tmp_path, monkeypatch):
    macro = pd.DataFrame(
        {
            "observation_date": pd.date_range("2020-01-01", periods=80, freq="B"),
            "credit_spread_bps": [350.0] * 80,
            "real_yield_10y_pct": [0.01] * 80,
        }
    )
    macro_path = tmp_path / "macro.csv"
    macro.to_csv(macro_path, index=False)

    qqq = pd.DataFrame(
        {
            "Date": pd.date_range("2020-01-01", periods=80, freq="B"),
            "Close": [200.0 + i for i in range(80)],
        }
    )
    qqq_path = tmp_path / "qqq.csv"
    qqq.to_csv(qqq_path, index=False)

    fred = {
        "T10Y2Y": _fred_frame(["2020-01-01", "2020-01-02"], "T10Y2Y", [0.5, 0.45]),
        "NFCI": _fred_frame(["2020-01-03", "2020-01-10"], "NFCI", [-0.2, -0.25]),
        "VIXCLS": _fred_frame(["2020-01-01", "2020-01-02"], "VIXCLS", [15.0, 16.0]),
        "VXVCLS": _fred_frame(["2020-01-01", "2020-01-02"], "VXVCLS", [17.0, 18.0]),
        "NEWORDER": _fred_frame(["2020-01-01", "2020-02-01"], "NEWORDER", [100.0, 102.0]),
        "MNFCTRIMSA": _fred_frame(["2020-01-01", "2020-02-01"], "MNFCTRIMSA", [95.0, 96.0]),
    }

    monkeypatch.setattr(
        "src.research.recovery_hmm.dataset_builder.fetch_historical_fred_series",
        lambda sid, timeout=15: fred[sid],
    )

    report = build_shadow_dataset(
        macro_dump_path=macro_path,
        qqq_history_path=qqq_path,
    )

    assert report.is_ready is True
    assert set(report.frame.columns) >= {
        "hy_ig_spread",
        "curve_10y_2y",
        "chicago_fci",
        "real_yield_10y",
        "ism_new_orders",
        "ism_inventories",
        "vix_3m_1m_ratio",
        "qqq_skew_20d_mean",
    }
    assert "curve_10y_2y" in report.source_notes
    assert "qqq_skew_20d_mean" in report.source_notes


def test_build_shadow_dataset_marks_proxy_fields_explicitly(tmp_path, monkeypatch):
    macro = pd.DataFrame(
        {
            "observation_date": pd.date_range("2021-01-01", periods=40, freq="B"),
            "credit_spread_bps": [300.0] * 40,
            "real_yield_10y_pct": [0.012] * 40,
        }
    )
    macro_path = tmp_path / "macro.csv"
    macro.to_csv(macro_path, index=False)

    qqq = pd.DataFrame(
        {
            "Date": pd.date_range("2021-01-01", periods=40, freq="B"),
            "Close": [300.0 + ((-1) ** i) * i for i in range(40)],
        }
    )
    qqq_path = tmp_path / "qqq.csv"
    qqq.to_csv(qqq_path, index=False)

    fred = {
        "T10Y2Y": _fred_frame(["2021-01-01"], "T10Y2Y", [0.8]),
        "NFCI": _fred_frame(["2021-01-01"], "NFCI", [-0.4]),
        "VIXCLS": _fred_frame(["2021-01-01"], "VIXCLS", [20.0]),
        "VXVCLS": _fred_frame(["2021-01-01"], "VXVCLS", [22.0]),
        "NEWORDER": _fred_frame(["2021-01-01", "2022-01-01"], "NEWORDER", [100.0, 110.0]),
        "MNFCTRIMSA": _fred_frame(["2021-01-01", "2022-01-01"], "MNFCTRIMSA", [90.0, 108.0]),
    }

    monkeypatch.setattr(
        "src.research.recovery_hmm.dataset_builder.fetch_historical_fred_series",
        lambda sid, timeout=15: fred[sid],
    )

    report = build_shadow_dataset(
        macro_dump_path=macro_path,
        qqq_history_path=qqq_path,
    )

    assert "proxy" in report.source_notes["ism_new_orders"].lower()
    assert "proxy" in report.source_notes["ism_inventories"].lower()
    assert "proxy" in report.source_notes["qqq_skew_20d_mean"].lower()

