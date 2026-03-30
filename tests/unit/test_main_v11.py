import json

import pandas as pd
import pytest

import src.main as main_module


def test_main_routes_v11_engine(monkeypatch, capsys):
    called = {}

    def fake_run(args):
        called["engine"] = "v11"
        print(json.dumps({"engine_version": "v11", "target_beta": 0.83}))

    monkeypatch.setattr(main_module, "run_v11_pipeline", fake_run, raising=False)

    main_module.main(["--engine", "v11", "--json", "--no-save"])

    out = json.loads(capsys.readouterr().out)
    assert called["engine"] == "v11"
    assert out["engine_version"] == "v11"


def test_v11_runtime_sync_files_are_minimal_mutable_state():
    assert main_module._v11_runtime_sync_files() == [
        "data/signals.db",
        "data/macro_historical_dump.csv",
        "data/v11_prior_state.json",
    ]


def test_build_v11_signal_result_uses_v11_deployment_surface(monkeypatch):
    def fail(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("legacy deployment controller should not be used by v11")

    monkeypatch.setattr("src.engine.deployment_controller.decide_deployment_state", fail)

    runtime = {
        "date": "2026-03-30",
        "signal": {"target_bucket": "QQQ", "reason": "hold", "lock_active": False},
        "probabilities": {"MID_CYCLE": 0.2, "BUST": 0.1, "CAPITULATION": 0.2, "RECOVERY": 0.3, "LATE_CYCLE": 0.2},
        "stable_regime": "RECOVERY",
        "raw_regime": "RECOVERY",
        "entropy": 0.25,
        "target_beta": 0.91,
        "raw_target_beta": 0.96,
        "target_allocation": {
            "qqq_dollars": 91000.0,
            "qld_notional_dollars": 0.0,
            "cash_dollars": 9000.0,
        },
        "feature_values": {"credit_spread": 320.0, "erp": 0.04, "net_liquidity": 4200.0, "vix": 22.0},
        "data_quality": 1.0,
        "quality_audit": {},
        "deployment": {
            "deployment_state": "DEPLOY_FAST",
            "readiness_score": 0.82,
            "value_score": 0.77,
            "action_required": True,
            "reason": "REVERSAL_OPPORTUNITY",
            "scores": {"DEPLOY_FAST": 0.7, "DEPLOY_BASE": 0.2, "DEPLOY_SLOW": 0.05, "DEPLOY_PAUSE": 0.05},
        },
    }

    result = main_module._build_v11_signal_result(runtime, price=100.0)

    assert result.deployment_state.value == "DEPLOY_FAST"
    assert result.deployment_reasons[0]["rule"] == "v11_deployment_surface"
    assert result.cycle_regime == "RECOVERY"


def test_build_v11_live_macro_row_normalizes_percent_units():
    row = main_module._build_v11_live_macro_row(
        observation_date=pd.Timestamp("2026-03-30"),
        credit_spread=342.0,
        net_liquidity=5818.972,
        liquidity_roc=0.78,
        vix=30.61,
        vix3m=None,
        price=558.28,
        drawdown_pct=-0.02,
        breadth_proxy=0.51,
        fear_greed=50.0,
        erp_pct_points=1.9717227235438886,
        real_yield_pct_points=2.13,
        reference_capital=100000.0,
        current_nav=100000.0,
    ).iloc[0]

    assert row["erp_pct"] == pytest.approx(0.019717227235438886)
    assert row["real_yield_10y_pct"] == pytest.approx(0.0213)
    assert row["credit_spread_bps"] == 342.0
    assert row["net_liquidity_usd_bn"] == 5818.972


def test_upsert_v11_macro_feedback_preserves_canonical_schema(tmp_path):
    macro_path = tmp_path / "macro_historical_dump.csv"
    canonical = pd.DataFrame(
        [
            {
                "observation_date": "2026-03-29",
                "effective_date": "2026-03-29",
                "erp_pct": 0.044,
                "real_yield_10y_pct": 0.017,
                "credit_spread_bps": 248.9,
                "net_liquidity_usd_bn": 6087.9,
                "credit_acceleration_pct_10d": 0.0,
                "forward_pe": 897.7,
                "liquidity_roc_pct_4w": 0.0,
                "funding_stress_flag": False,
                "source_credit_spread": "synthetic_dna",
                "source_forward_pe": "synthetic_dna",
                "source_erp": "synthetic_dna",
                "source_real_yield": "synthetic_dna",
                "source_net_liquidity": "synthetic_dna",
                "source_funding_stress": "synthetic_dna",
                "build_version": "v11.x-dna-bootstrap",
            },
            {
                "observation_date": "2026-03-30",
                "effective_date": "2026-03-30",
                "erp_pct": 0.0485,
                "real_yield_10y_pct": 0.0170,
                "credit_spread_bps": 279.1,
                "net_liquidity_usd_bn": 6083.2,
                "credit_acceleration_pct_10d": 0.0,
                "forward_pe": 865.4,
                "liquidity_roc_pct_4w": 0.0,
                "funding_stress_flag": False,
                "source_credit_spread": "synthetic_dna",
                "source_forward_pe": "synthetic_dna",
                "source_erp": "synthetic_dna",
                "source_real_yield": "synthetic_dna",
                "source_net_liquidity": "synthetic_dna",
                "source_funding_stress": "synthetic_dna",
                "build_version": "v11.x-dna-bootstrap",
            },
        ]
    )
    canonical.to_csv(macro_path, index=False)

    raw_row = main_module._build_v11_live_macro_row(
        observation_date=pd.Timestamp("2026-03-30"),
        credit_spread=342.0,
        net_liquidity=5818.972,
        liquidity_roc=0.78,
        vix=30.61,
        vix3m=None,
        price=558.28,
        drawdown_pct=-0.02,
        breadth_proxy=0.51,
        fear_greed=50.0,
        erp_pct_points=1.9717227235438886,
        real_yield_pct_points=2.13,
        reference_capital=100000.0,
        current_nav=100000.0,
    )

    main_module._upsert_v11_macro_feedback(raw_row, str(macro_path))

    persisted = pd.read_csv(macro_path)
    assert list(persisted.columns) == list(canonical.columns)
    assert len(persisted) == 2

    latest = persisted.iloc[-1]
    assert latest["observation_date"] == "2026-03-30"
    assert latest["effective_date"] == "2026-03-30"
    assert latest["erp_pct"] == pytest.approx(0.019717227235438886)
    assert latest["real_yield_10y_pct"] == pytest.approx(0.0213)
    assert latest["credit_spread_bps"] == 342.0
    assert latest["net_liquidity_usd_bn"] == 5818.972
    assert latest["liquidity_roc_pct_4w"] == 0.78
    assert latest["source_erp"] == "live_runtime"
    assert latest["build_version"] == "v11_live_feedback"
