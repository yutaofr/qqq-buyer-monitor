import pandas as pd

import src.backtest as backtest_module


def test_backtest_routes_v11_mode(monkeypatch):
    called = {}

    def fake_run_v11_audit(**kwargs):
        called["kwargs"] = kwargs

    monkeypatch.setattr(backtest_module, "run_v11_audit", fake_run_v11_audit)

    rc = backtest_module.main([])

    assert rc == 0
    assert "kwargs" in called
    assert called["kwargs"]["dataset_path"] == "data/macro_historical_dump.csv"


def test_v11_inference_task_uses_labeled_regime_and_curated_features():
    class FakeModel:
        def predict_proba(self, evidence):
            assert list(evidence.columns) == ["spread_absolute"]
            return [[0.8, 0.2]]

    row = pd.Series(
        {
            "observation_date": pd.Timestamp("2026-03-30"),
            "regime": "LATE_CYCLE",
            "spread_absolute": 1.5,
            "qqq_close": 100.0,
        }
    )
    source_row = pd.Series({"observation_date": pd.Timestamp("2026-03-30")})

    result = backtest_module._v11_inference_task(
        (row, source_row, FakeModel(), ["LATE_CYCLE", "MID_CYCLE"], ["spread_absolute"])
    )

    assert result["actual_regime"] == "LATE_CYCLE"
