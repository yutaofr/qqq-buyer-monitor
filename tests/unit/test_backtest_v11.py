import numpy as np
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


def test_run_v11_audit_refits_model_for_each_evaluation_day(tmp_path, monkeypatch):
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    pd.DataFrame(
        {
            "observation_date": dates,
            "erp_pct": [0.02, 0.021, 0.022, 0.023, 0.024, 0.025],
            "real_yield_10y_pct": [0.01, 0.011, 0.012, 0.013, 0.014, 0.015],
            "credit_spread_bps": [300, 320, 340, 360, 380, 400],
            "net_liquidity_usd_bn": [5000, 5010, 5020, 5030, 5040, 5050],
        }
    ).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE", "MID_CYCLE", "LATE_CYCLE", "LATE_CYCLE", "BUST", "BUST"],
        }
    ).to_csv(regime_path, index=False)

    class FakeGaussianNB:
        fit_calls = 0

        def __init__(self, *args, **kwargs):
            self.classes_ = ["BUST", "LATE_CYCLE", "MID_CYCLE"]
            self.theta_ = np.zeros((3, 6))
            self.var_ = np.ones((3, 6))
            self.class_prior_ = np.full(3, 1.0 / 3.0)

        def fit(self, X, y):
            type(self).fit_calls += 1
            self.classes_ = sorted(set(map(str, y)))
            feature_count = len(X.columns)
            class_count = len(self.classes_)
            self.theta_ = np.zeros((class_count, feature_count))
            self.var_ = np.ones((class_count, feature_count))
            self.class_prior_ = np.full(class_count, 1.0 / class_count)
            return self

        def predict_proba(self, evidence):
            return [[1.0 / len(self.classes_)] * len(self.classes_)]

    class InlineExecutor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, fn, tasks):
            return [fn(task) for task in tasks]

    monkeypatch.setattr("sklearn.naive_bayes.GaussianNB", FakeGaussianNB)
    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", InlineExecutor)
    monkeypatch.setattr(backtest_module, "_load_price_history", lambda _: pd.DataFrame({"Close": [100, 101, 102, 103, 104, 105]}, index=dates))
    monkeypatch.setattr("src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.output.backtest_plots.save_v11_probabilistic_audit_figure", lambda *args, **kwargs: None)

    backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2024-01-04",
    )

    assert FakeGaussianNB.fit_calls >= 3
