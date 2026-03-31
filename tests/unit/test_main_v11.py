import json
import pandas as pd
import pytest
import src.main as main_module


def test_main_routes_v11_engine(monkeypatch, capsys):
    called = {}

    def fake_run(args):
        called["engine"] = "v11"
        print(json.dumps({"engine_version": "v11", "target_beta": 0.83}))

    monkeypatch.setattr(main_module, "run_v11_pipeline", fake_run)

    main_module.main(["--engine", "v11", "--json", "--no-save"])

    out = json.loads(capsys.readouterr().out)
    assert called["engine"] == "v11"
    assert out["engine_version"] == "v11"


def test_build_v11_signal_result_uses_v11_contract():
    runtime = {
        "date": "2026-03-30",
        "signal": {"target_bucket": "QQQ", "reason": "hold", "lock_active": False},
        "probabilities": {"MID_CYCLE": 0.8, "LATE_CYCLE": 0.2},
        "stable_regime": "MID_CYCLE",
        "entropy": 0.25,
        "target_beta": 0.91,
        "target_allocation": {
            "qqq_dollars": 91000.0,
            "qld_notional_dollars": 0.0,
            "cash_dollars": 9000.0,
        },
        "feature_values": {"credit_spread": 320.0},
        "deployment_readiness": 0.64,
    }

    result = main_module._build_v11_signal_result(runtime, price=100.0)

    assert result.target_beta == 0.91
    assert result.stable_regime == "MID_CYCLE"
    assert result.metadata["deployment_readiness"] == 0.64
    assert result.target_allocation.target_qqq_pct == 0.91


def test_build_v11_live_macro_row_normalizes_units():
    row = main_module._build_v11_live_macro_row(
        observation_date=pd.Timestamp("2026-03-30"),
        credit_spread=342.0,
        net_liquidity=5818.9,
        liquidity_roc=0.78,
        vix=30.6,
        vix3m=None,
        price=558.0,
        drawdown_pct=-0.02,
        breadth_proxy=0.51,
        fear_greed=50.0,
        erp_pct_points=2.0,
        real_yield_pct_points=2.1,
        reference_capital=100000.0,
        current_nav=100000.0,
    ).iloc[0]

    assert row["erp_pct"] == 0.02
    assert row["real_yield_10y_pct"] == 0.021
    assert row["credit_spread_bps"] == 342.0
