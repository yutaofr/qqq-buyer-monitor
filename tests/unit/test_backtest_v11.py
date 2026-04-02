import numpy as np
import pandas as pd
import pytest

import src.backtest as backtest_module


def _build_v12_macro_frame(dates: pd.DatetimeIndex) -> pd.DataFrame:
    monthly_block = np.repeat(np.linspace(8.0, 18.0, 14), 30)[: len(dates)]
    return pd.DataFrame(
        {
            "observation_date": dates,
            "effective_date": dates,
            "credit_spread_bps": 300.0 + np.linspace(0.0, 220.0, len(dates)),
            "real_yield_10y_pct": 0.008 + np.linspace(0.0, 0.02, len(dates)),
            "net_liquidity_usd_bn": 5000.0 + np.linspace(0.0, 300.0, len(dates)),
            "treasury_vol_21d": 0.004 + np.linspace(0.0, 0.008, len(dates)),
            "copper_gold_ratio": 0.18 + np.linspace(0.0, 0.03, len(dates)),
            "breakeven_10y": 0.017 + np.linspace(0.0, 0.012, len(dates)),
            "core_capex_mm": monthly_block,
            "usdjpy": 118.0 + np.linspace(0.0, 24.0, len(dates)),
            "erp_ttm_pct": 0.034 + np.sin(np.linspace(0.0, 12.0, len(dates))) * 0.003,
            "source_credit_spread": ["synthetic_dna"] * len(dates),
            "source_real_yield": ["synthetic_dna"] * len(dates),
            "source_net_liquidity": ["synthetic_dna"] * len(dates),
            "source_treasury_vol": ["synthetic_dna"] * len(dates),
            "source_copper_gold": ["synthetic_dna"] * len(dates),
            "source_breakeven": ["synthetic_dna"] * len(dates),
            "source_core_capex": ["synthetic_dna"] * len(dates),
            "source_usdjpy": ["synthetic_dna"] * len(dates),
            "source_erp_ttm": ["synthetic_dna"] * len(dates),
            "forward_pe": [np.nan] * len(dates),
            "erp_pct": [np.nan] * len(dates),
            "source_forward_pe": ["deprecated:v12"] * len(dates),
            "source_erp": ["deprecated:v12"] * len(dates),
            "build_version": ["v12.synthetic-dna"] * len(dates),
        }
    )


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
    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    class FakeGaussianNB:
        fit_calls = 0
        init_var_smoothing: list[float] = []

        def __init__(self, *args, **kwargs):
            type(self).init_var_smoothing.append(float(kwargs.get("var_smoothing", 0.0)))
            self.classes_ = ["BUST", "LATE_CYCLE", "MID_CYCLE"]
            self.theta_ = np.zeros((3, 10))
            self.var_ = np.ones((3, 10))
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

    monkeypatch.setattr("sklearn.naive_bayes.GaussianNB", FakeGaussianNB)
    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame({"Close": np.linspace(100.0, 130.0, len(dates))}, index=dates),
    )
    monkeypatch.setattr("src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.output.backtest_plots.save_v11_probabilistic_audit_figure", lambda *args, **kwargs: None)

    summary = backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2025-01-02",
        artifact_dir=str(tmp_path / "audit_artifacts"),
        experiment_config={
            "var_smoothing": 1e-3,
            "probability_seeder": {
                "config_overrides": {
                    "copper_gold_roc_126d": {"diff": (21,), "min_periods": 21},
                },
                "clip_range": (-6.0, 6.0),
                "orthogonalization_mode": "none",
            },
        },
    )

    assert FakeGaussianNB.fit_calls >= 3
    assert FakeGaussianNB.init_var_smoothing[0] == pytest.approx(1e-3)
    assert "top1_accuracy" in summary
    assert summary["audit_regimes"] == ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]
    assert sorted(summary["state_support"]["unsupported_audit_regimes"]) == ["RECOVERY"]
    assert summary["feature_contract_validation"].startswith("override:")


def test_run_v11_audit_accepts_audit_overrides(tmp_path, monkeypatch):
    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    class FakeGaussianNB:
        def __init__(self, *args, **kwargs):
            self.classes_ = ["BUST", "LATE_CYCLE", "MID_CYCLE"]
            self.theta_ = np.zeros((3, 10))
            self.var_ = np.ones((3, 10))
            self.class_prior_ = np.full(3, 1.0 / 3.0)

        def fit(self, X, y):
            self.classes_ = sorted(set(map(str, y)))
            feature_count = len(X.columns)
            class_count = len(self.classes_)
            self.theta_ = np.zeros((class_count, feature_count))
            self.var_ = np.ones((class_count, feature_count))
            self.class_prior_ = np.full(class_count, 1.0 / class_count)
            return self

        def predict_proba(self, evidence):
            return [[1.0 / len(self.classes_)] * len(self.classes_)]

    monkeypatch.setattr("sklearn.naive_bayes.GaussianNB", FakeGaussianNB)
    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame({"Close": np.linspace(100.0, 130.0, len(dates))}, index=dates),
    )
    monkeypatch.setattr("src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.output.backtest_plots.save_v11_probabilistic_audit_figure", lambda *args, **kwargs: None)

    summary = backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2025-01-02",
        artifact_dir=str(tmp_path / "audit_artifacts"),
        experiment_config={
            "audit_overrides": {
                "base_betas": {
                    "BUST": 0.5,
                    "LATE_CYCLE": 0.8,
                    "MID_CYCLE": 1.0,
                },
                "regime_sharpes": {
                    "BUST": -0.8,
                    "LATE_CYCLE": 0.2,
                    "MID_CYCLE": 1.0,
                },
            }
        },
    )

    assert summary["state_support"]["unsupported_audit_regimes"] == []
    assert summary["audit_regimes"] == ["BUST", "LATE_CYCLE", "MID_CYCLE"]


def test_run_v11_audit_can_use_classifier_posteriors_directly(tmp_path, monkeypatch):
    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    class FakeGaussianNB:
        def __init__(self, *args, **kwargs):
            self.classes_ = ["BUST", "LATE_CYCLE", "MID_CYCLE"]
            self.theta_ = np.zeros((3, 10))
            self.var_ = np.ones((3, 10))
            self.class_prior_ = np.array([0.2, 0.3, 0.5])

        def fit(self, X, y):
            self.classes_ = sorted(set(map(str, y)))
            feature_count = len(X.columns)
            class_count = len(self.classes_)
            self.theta_ = np.zeros((class_count, feature_count))
            self.var_ = np.ones((class_count, feature_count))
            self.class_prior_ = np.full(class_count, 1.0 / class_count)
            return self

        def predict_proba(self, evidence):
            return [[0.6, 0.3, 0.1]]

    monkeypatch.setattr("sklearn.naive_bayes.GaussianNB", FakeGaussianNB)
    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame({"Close": np.linspace(100.0, 130.0, len(dates))}, index=dates),
    )
    monkeypatch.setattr("src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.output.backtest_plots.save_v11_probabilistic_audit_figure", lambda *args, **kwargs: None)

    summary = backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2025-01-02",
        artifact_dir=str(tmp_path / "audit_artifacts"),
        experiment_config={"posterior_mode": "classifier_only"},
    )

    assert summary["posterior_mode"] == "classifier_only"
