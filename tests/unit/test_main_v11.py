import json
from argparse import Namespace

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
        build_version="v11_live_feedback",
        credit_spread=342.0,
        credit_spread_source="proxy:nfci",
        forward_pe=24.38,
        forward_pe_source="fallback:institutional_consensus",
        net_liquidity=5818.9,
        net_liquidity_source="derived:fred:WALCL-WDTGAL-RRPONTSYD",
        liquidity_roc=0.78,
        vix=30.6,
        vix3m=None,
        price=558.0,
        drawdown_pct=-0.02,
        breadth_proxy=0.51,
        breadth_source="unavailable:breadth",
        breadth_quality_score=0.0,
        fear_greed=50.0,
        fear_greed_source="default:fear_greed",
        erp_pct_points=2.0,
        erp_source="proxy:derived:erp[fallback:institutional_consensus|proxy:treasury_xml]",
        real_yield_pct_points=2.1,
        real_yield_source="proxy:treasury_xml",
        reference_capital=100000.0,
        current_nav=100000.0,
    ).iloc[0]

    assert row["erp_pct"] == 0.02
    assert row["real_yield_10y_pct"] == 0.021
    assert row["forward_pe"] == 24.38
    assert row["credit_spread_bps"] == 342.0
    assert row["build_version"] == "v11_live_feedback"
    assert row["source_credit_spread"] == "proxy:nfci"
    assert row["source_forward_pe"] == "fallback:institutional_consensus"
    assert row["source_net_liquidity"] == "derived:fred:WALCL-WDTGAL-RRPONTSYD"
    assert row["source_erp"].startswith("proxy:derived:erp")
    assert row["source_real_yield"] == "proxy:treasury_xml"
    assert row["source_breadth"] == "unavailable:breadth"
    assert row["breadth_quality_score"] == 0.0


def test_run_v11_pipeline_stops_when_cloud_pull_fails(monkeypatch):
    class _FatalCloudBridge:
        def __init__(self):
            self.is_ci = True

        def pull_state(self, local_files):
            return False

    monkeypatch.setattr(main_module, "CloudPersistenceBridge", _FatalCloudBridge)
    monkeypatch.setattr("src.collector.price.fetch_price_data", lambda: (_ for _ in ()).throw(AssertionError("should not fetch")))

    with pytest.raises(RuntimeError, match="Cloud state pull failed"):
        main_module.run_v11_pipeline(
            Namespace(
                json=False,
                notify_discord=False,
                no_save=True,
                no_color=True,
            )
        )
