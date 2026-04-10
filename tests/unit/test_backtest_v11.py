import numpy as np
import pandas as pd
import pytest

import src.backtest as backtest_module


def _build_v12_macro_frame(dates: pd.DatetimeIndex) -> pd.DataFrame:
    monthly_block = np.repeat(np.linspace(8.0, 18.0, 100), 30)[: len(dates)]
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


def test_run_v11_audit_rejects_model_config_overrides(tmp_path, monkeypatch):
    dates = pd.bdate_range("2014-01-01", periods=3000)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * (len(dates) - 240)
            + ["RECOVERY"] * 80
            + ["LATE_CYCLE"] * 80
            + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame(
            {"Close": np.linspace(100.0, 130.0, len(dates))}, index=dates
        ),
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(ValueError, match="Disallowed overrides: probability_seeder, var_smoothing"):
        backtest_module.run_v11_audit(
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


def test_run_v11_audit_rejects_audit_overrides(tmp_path, monkeypatch):
    dates = pd.bdate_range("2014-01-01", periods=3000)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * (len(dates) - 240)
            + ["RECOVERY"] * 80
            + ["LATE_CYCLE"] * 80
            + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame(
            {"Close": np.linspace(100.0, 130.0, len(dates))}, index=dates
        ),
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(ValueError, match="Disallowed overrides: audit_overrides"):
        backtest_module.run_v11_audit(
            dataset_path=str(macro_path),
            regime_path=str(regime_path),
            evaluation_start="2024-01-02",
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


def test_run_v11_audit_rejects_posterior_mode_override(tmp_path, monkeypatch):
    dates = pd.bdate_range("2014-01-01", periods=3000)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * (len(dates) - 240)
            + ["RECOVERY"] * 80
            + ["LATE_CYCLE"] * 80
            + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame(
            {"Close": np.linspace(100.0, 130.0, len(dates))}, index=dates
        ),
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(ValueError, match="Disallowed overrides: posterior_mode"):
        backtest_module.run_v11_audit(
            dataset_path=str(macro_path),
            regime_path=str(regime_path),
            evaluation_start="2024-01-02",
            artifact_dir=str(tmp_path / "audit_artifacts"),
            experiment_config={"posterior_mode": "classifier_only"},
        )


def test_run_v11_audit_emits_expectation_and_pacing_alignment_columns(tmp_path, monkeypatch):
    # v14.9 Industrial Hardening: Provide 10 years of data
    dates = pd.bdate_range("2014-01-01", periods=3000)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"
    artifact_dir = tmp_path / "audit_artifacts"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * (len(dates) - 200) + ["RECOVERY"] * 60 + ["LATE_CYCLE"] * 80 + ["BUST"] * 60,
        }
    ).to_csv(regime_path, index=False)

    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "Close": np.linspace(100.0, 130.0, len(dates)),
                "Volume": np.linspace(1_000_000.0, 2_000_000.0, len(dates)),
            },
            index=dates,
        ),
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2024-01-02",
        artifact_dir=str(artifact_dir),
        experiment_config={
            "allow_price_download": False,
            "price_end_date": "2025-12-31",
        },
    )

    execution_trace = pd.read_csv(artifact_dir / "execution_trace.csv")
    summary = pd.read_json(artifact_dir / "summary.json", typ="series")
    forensic_trace = (artifact_dir / "forensic_trace.jsonl").read_text(encoding="utf-8")

    assert "beta_expectation" in execution_trace.columns
    assert "expected_target_beta" in execution_trace.columns
    assert "expected_deployment_state" in execution_trace.columns
    assert "deployment_multiplier" in execution_trace.columns
    assert "expected_deployment_multiplier" in execution_trace.columns
    assert "deployment_pacing_error" in execution_trace.columns
    assert "price_topology_regime" in execution_trace.columns
    assert "price_topology_expected_beta" in execution_trace.columns
    assert "price_topology_confidence" in execution_trace.columns
    assert "forensic_snapshot_path" in execution_trace.columns
    assert "forensic_stress_score" in execution_trace.columns
    assert "forensic_mid_cycle_penalty" in execution_trace.columns
    assert "deployment_pacing_abs_error_mean" in summary.index
    assert "deployment_pacing_signed_mean" in summary.index
    assert "raw_floor_breach_rate" in summary.index
    assert "expectation_floor_breach_rate" in summary.index
    assert "raw_beta_min" in summary.index
    assert "target_beta_min" in summary.index
    assert "beta_expectation_min" in summary.index
    assert "raw_beta_within_5pct_expected" in summary.index
    assert "target_beta_within_5pct_expected" in summary.index
    assert "active_features" in summary.index
    assert "forensic_snapshot_count" in summary.index
    assert '"v13_4_diagnostics"' in forensic_trace
    assert '"regime_stabilizer"' in forensic_trace
    assert '"bearish_divergence"' in forensic_trace
    assert '"recovery_prob_acceleration"' in forensic_trace


def test_run_v11_audit_rejects_feature_subset_overrides_when_raw_quality_fields_exist(
    tmp_path, monkeypatch
):
    # v14.9 Industrial Hardening: Provide 10 years of data
    dates = pd.bdate_range("2014-01-01", periods=3000)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"

    macro = _build_v12_macro_frame(dates)
    macro["credit_spread_bps"] = np.r_[
        np.full(len(dates) - 160, 180.0),
        np.full(80, 320.0),
        np.full(80, 520.0),
    ] + np.random.normal(0, 0.01, len(dates))
    macro["erp_ttm_pct"] = 0.03 + np.sin(np.linspace(0.0, 12.0, len(dates))) * 0.0005
    macro["source_credit_spread"] = "direct"
    macro["source_erp_ttm"] = "direct"
    macro.to_csv(macro_path, index=False)

    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * (len(dates) - 240)
            + ["RECOVERY"] * 80
            + ["LATE_CYCLE"] * 80
            + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "Close": np.linspace(100.0, 130.0, len(dates)),
                "Volume": np.linspace(1_000_000.0, 2_000_000.0, len(dates)),
            },
            index=dates,
        ),
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(ValueError, match="Disallowed overrides: probability_seeder"):
        backtest_module.run_v11_audit(
            dataset_path=str(macro_path),
            regime_path=str(regime_path),
            evaluation_start="2024-01-02",
            artifact_dir=str(tmp_path / "audit_spread"),
            experiment_config={
                "allow_price_download": False,
                "price_end_date": "2025-12-31",
                "save_plots": False,
                "probability_seeder": {"selected_features": ["spread_absolute"]},
            },
        )


def test_run_v11_audit_uses_mainline_black_box_when_canonical_pipeline_enabled(
    tmp_path, monkeypatch
):
    dates = pd.bdate_range("2024-01-01", periods=100)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"
    artifact_dir = tmp_path / "audit_artifacts"
    cache_path = tmp_path / "qqq_cache.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 20
            + ["RECOVERY"] * 20
            + ["LATE_CYCLE"] * 20
            + ["BUST"] * 40,
        }
    ).to_csv(regime_path, index=False)
    pd.DataFrame(
        {
            "Close": np.linspace(100.0, 120.0, len(dates)),
            "Volume": np.linspace(1_000_000.0, 1_400_000.0, len(dates)),
        },
        index=dates,
    ).to_csv(cache_path)

    calls: list[dict[str, object]] = []

    class FakeConductor:
        def __init__(self, *args, **kwargs):
            calls.append(dict(kwargs))

        def daily_run(self, raw_t0_data):
            dt = pd.Timestamp(raw_t0_data.index[-1])
            return {
                "date": dt,
                "priors": {
                    "MID_CYCLE": 0.60,
                    "LATE_CYCLE": 0.25,
                    "BUST": 0.10,
                    "RECOVERY": 0.05,
                },
                "prior_details": {
                    "base_weight": 0.05,
                    "posterior_weight": 0.60,
                    "transition_weight": 0.35,
                },
                "probabilities": {
                    "MID_CYCLE": 0.55,
                    "LATE_CYCLE": 0.25,
                    "BUST": 0.15,
                    "RECOVERY": 0.05,
                },
                "probability_dynamics": {},
                "price_topology": {
                    "regime": "LATE_CYCLE",
                    "expected_beta": 0.8,
                    "confidence": 0.7,
                    "posterior_blend_weight": 0.2,
                    "beta_anchor_weight": 0.3,
                    "probabilities": {
                        "MID_CYCLE": 0.20,
                        "LATE_CYCLE": 0.60,
                        "BUST": 0.15,
                        "RECOVERY": 0.05,
                    },
                },
                "raw_regime": "MID_CYCLE",
                "stable_regime": "MID_CYCLE",
                "entropy": 0.45,
                "protected_beta": 0.82,
                "overlay_beta": 0.78,
                "overlay": {
                    "beta_overlay_multiplier": 1.0,
                    "deployment_overlay_multiplier": 1.0,
                    "overlay_state": "NEUTRAL",
                },
                "target_beta": 0.78,
                "raw_target_beta": 0.90,
                "beta_expectation": 0.90,
                "deployment_readiness": 0.5,
                "deployment_readiness_overlay": 0.5,
                "cdr_sharpe": 0.4,
                "erp_percentile": 0.6,
                "target_allocation": {
                    "qqq_dollars": 78_000.0,
                    "qld_notional_dollars": 0.0,
                    "cash_dollars": 22_000.0,
                },
                "deployment": {
                    "deployment_state": "DEPLOY_BASE",
                    "deployment_multiplier": 1.0,
                },
                "feature_values": {
                    "credit_spread": 320.0,
                    "price_topology_confidence": 0.7,
                    "price_topology_expected_beta": 0.8,
                },
                "data_quality": 1.0,
                "quality_audit": {"quality_score": 1.0},
                "v11_execution": {"lock_active": False, "target_bucket": "QQQ"},
            }

    monkeypatch.setattr("src.engine.v11.conductor.V11Conductor", FakeConductor)
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2024-02-15",
        artifact_dir=str(artifact_dir),
        experiment_config={
            "use_canonical_pipeline": True,
            "price_cache_path": str(cache_path),
            "allow_price_download": False,
            "save_plots": False,
        },
    )

    assert calls
    assert all("training_cutoff" in payload for payload in calls)
    assert all(str(artifact_dir) in str(payload["prior_state_path"]) for payload in calls)


def test_backtest_module_imports_topology_alignment_helpers_for_replay_parity():
    assert callable(backtest_module.align_posteriors_with_recovery_process)
    assert callable(backtest_module.topology_likelihood_penalties)


def test_run_v11_audit_reports_oos_and_training_class_support(tmp_path, monkeypatch):
    dates = pd.bdate_range("2016-01-01", periods=400)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"
    artifact_dir = tmp_path / "audit_artifacts"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 200
            + ["RECOVERY"] * 40
            + ["LATE_CYCLE"] * 80
            + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)

    monkeypatch.setattr(
        backtest_module,
        "_load_price_history",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "Close": np.linspace(100.0, 130.0, len(dates)),
                "Volume": np.linspace(1_000_000.0, 2_000_000.0, len(dates)),
            },
            index=dates,
        ),
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    class FakeConductor:
        def __init__(self, **kwargs):
            cutoff = pd.Timestamp(kwargs["training_cutoff"])
            if cutoff < pd.Timestamp("2016-10-01"):
                classes = ["MID_CYCLE", "LATE_CYCLE"]
            else:
                classes = ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]
            self.gnb = type("FakeModel", (), {"classes_": classes})()

        def daily_run(self, t0_data):
            return {
                "probabilities": {
                    "MID_CYCLE": 0.7,
                    "LATE_CYCLE": 0.2,
                    "BUST": 0.1,
                    "RECOVERY": 0.0,
                },
                "probability_dynamics": {},
                "beta_expectation": 0.9,
                "protected_beta": 0.85,
                "overlay_beta": 0.85,
                "overlay": {
                    "beta_overlay_multiplier": 1.0,
                    "deployment_overlay_multiplier": 1.0,
                    "overlay_state": "NEUTRAL",
                },
                "target_beta": 0.8,
                "raw_target_beta": 0.9,
                "entropy": 0.4,
                "prior_details": {},
                "raw_regime": "MID_CYCLE",
                "stable_regime": "MID_CYCLE",
                "deployment": {"deployment_state": "DEPLOY_BASE", "deployment_multiplier": 1.0},
                "v11_execution": {"lock_active": False, "target_bucket": "QQQ"},
                "price_topology": {
                    "regime": "MID_CYCLE",
                    "expected_beta": 1.0,
                    "confidence": 0.4,
                    "posterior_blend_weight": 0.25,
                    "beta_anchor_weight": 0.35,
                },
                "v13_4_diagnostics": {"penalties_applied": {}},
                "forensic_snapshot_path": "",
                "signal": {
                    "resonance": {"action": "HOLD", "confidence": 0.0, "reason": "none"}
                },
            }

    monkeypatch.setattr("src.engine.v11.conductor.V11Conductor", FakeConductor)

    summary = backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2016-06-01",
        artifact_dir=str(artifact_dir),
        experiment_config={
            "allow_price_download": False,
            "price_end_date": "2017-06-01",
        },
    )

    assert summary["oos_compared_points"] > 0
    assert summary["training_min_class_count"] == 4
    assert summary["training_max_class_count"] == 4
    assert summary["training_rows_below_full_support"] == 0
    assert summary["training_first_full_support_date"] is not None
    assert summary["evaluation_start_effective"] == summary["training_first_full_support_date"]
    assert "stable_vs_benchmark_regime" in summary
    assert "probability_within_band_share" in summary
    assert "entropy_within_band_share" in summary
