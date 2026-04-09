import json
from argparse import Namespace

import pandas as pd
import pytest

import src.main as main_module


def test_main_routes_v11_engine(monkeypatch, capsys):
    called = {}

    def fake_run(args):
        called["engine"] = "v11"
        print(json.dumps({"engine_version": "v12.0", "target_beta": 0.83}))

    monkeypatch.setattr(main_module, "run_v11_pipeline", fake_run)

    main_module.main(["--engine", "v11", "--json", "--no-save"])

    out = json.loads(capsys.readouterr().out)
    assert called["engine"] == "v11"
    assert out["engine_version"] == "v12.0"


def test_build_v11_signal_result_uses_v12_metadata_contract():
    runtime = {
        "date": "2026-03-30",
        "signal": {"target_bucket": "QQQ", "reason": "hold", "lock_active": False},
        "probabilities": {"MID_CYCLE": 0.8, "LATE_CYCLE": 0.2},
        "stable_regime": "MID_CYCLE",
        "entropy": 0.25,
        "protected_beta": 0.84,
        "overlay_beta": 0.79,
        "overlay": {
            "overlay_mode": "NEGATIVE_ONLY",
            "beta_overlay_multiplier": 0.94,
            "deployment_overlay_multiplier": 1.05,
            "diagnostic_beta_overlay_multiplier": 0.94,
            "diagnostic_deployment_overlay_multiplier": 1.05,
            "overlay_state": "MIXED",
            "overlay_summary": "MIXED: neg=0.200 pos=0.150",
        },
        "target_beta": 0.91,
        "target_allocation": {
            "qqq_dollars": 91000.0,
            "qld_notional_dollars": 0.0,
            "cash_dollars": 9000.0,
        },
        "feature_values": {"credit_spread": 320.0, "move_21d_orth_z": 1.2},
        "deployment_readiness": 0.64,
    }

    result = main_module._build_v11_signal_result(runtime, price=100.0)

    assert result.target_beta == 0.91
    assert result.stable_regime == "MID_CYCLE"
    assert result.metadata["deployment_readiness"] == 0.64
    assert result.metadata["protected_beta"] == 0.84
    assert result.metadata["overlay_beta"] == 0.79
    assert result.metadata["beta_overlay_multiplier"] == 0.94
    assert result.metadata["deployment_overlay_multiplier"] == 1.05
    assert result.metadata["overlay_mode"] == "NEGATIVE_ONLY"
    assert result.metadata["overlay_state"] == "MIXED"
    assert result.target_allocation.target_qqq_pct == 0.91
    assert result.metadata["engine_version"] == "v14.0-ULTIMA"
    assert any(step["step"] == "execution_overlay" for step in result.logic_trace)


def test_build_v12_live_macro_row_normalizes_units_and_deprecates_v11_fields():
    row = main_module._build_v12_live_macro_row(
        observation_date=pd.Timestamp("2026-03-30"),
        build_version="v12_live_feedback",
        credit_spread=342.0,
        credit_spread_source="proxy:nfci",
        real_yield_pct_points=2.1,
        real_yield_source="proxy:treasury_xml",
        net_liquidity=5818.9,
        net_liquidity_source="derived:fred:WALCL-WDTGAL-RRPONTSYD",
        treasury_vol=0.0081,
        treasury_vol_source="direct:fred_dgs10",
        copper_gold_ratio=0.201,
        copper_gold_source="direct:yfinance",
        breakeven_pct_points=2.3,
        breakeven_source="direct:fred_t10yie",
        core_capex=12.5,
        core_capex_source="direct:fred_neworder",
        usdjpy=151.2,
        usdjpy_source="direct:yfinance",
        erp_ttm_pct_points=4.2,
        erp_ttm_source="direct:shiller",
        reference_capital=100000.0,
        current_nav=100000.0,
    ).iloc[0]

    assert row["effective_date"] == pd.Timestamp("2026-03-30")
    assert row["credit_spread_bps"] == 342.0
    assert row["real_yield_10y_pct"] == 0.021
    assert row["breakeven_10y"] == 0.023
    assert row["erp_ttm_pct"] == 0.042
    assert row["treasury_vol_21d"] == 0.0081
    assert row["copper_gold_ratio"] == 0.201
    assert row["core_capex_mm"] == 12.5
    assert row["usdjpy"] == 151.2
    assert pd.isna(row["forward_pe"])
    assert pd.isna(row["erp_pct"])
    assert row["source_forward_pe"] == "deprecated:v12"
    assert row["source_erp"] == "deprecated:v12"
    assert row["source_treasury_vol"] == "direct:fred_dgs10"
    assert row["source_copper_gold"] == "direct:yfinance"
    assert row["source_breakeven"] == "direct:fred_t10yie"
    assert row["source_core_capex"] == "direct:fred_neworder"
    assert row["source_usdjpy"] == "direct:yfinance"
    assert row["source_erp_ttm"] == "direct:shiller"


def test_build_v12_live_macro_row_carries_v13_overlay_inputs():
    row = main_module._build_v12_live_macro_row(
        observation_date=pd.Timestamp("2026-03-30"),
        build_version="v12_live_feedback",
        credit_spread=342.0,
        real_yield_pct_points=2.1,
        net_liquidity=5818.9,
        treasury_vol=0.0081,
        copper_gold_ratio=0.201,
        breakeven_pct_points=2.3,
        core_capex=12.5,
        usdjpy=151.2,
        erp_ttm_pct_points=4.2,
        reference_capital=100000.0,
        current_nav=100000.0,
        qqq_close=512.34,
        qqq_close_source="direct:yfinance",
        qqq_close_quality_score=1.0,
        qqq_volume=123456789.0,
        qqq_volume_source="direct:yfinance",
        qqq_volume_quality_score=1.0,
        adv_dec_ratio=0.58,
        breadth_source="observed:^ADD",
        breadth_quality_score=1.0,
        ndx_concentration=0.034,
        ndx_concentration_source="derived:qqq-qqew",
        ndx_concentration_quality_score=1.0,
    ).iloc[0]

    assert row["qqq_close"] == 512.34
    assert row["source_qqq_close"] == "direct:yfinance"
    assert row["qqq_close_quality_score"] == 1.0
    assert row["qqq_volume"] == 123456789.0
    assert row["source_qqq_volume"] == "direct:yfinance"
    assert row["adv_dec_ratio"] == 0.58
    assert row["source_breadth_proxy"] == "observed:^ADD"
    assert row["ndx_concentration"] == 0.034


def test_run_v11_pipeline_stops_when_cloud_pull_fails(monkeypatch):
    class _FatalCloudBridge:
        def __init__(self):
            self.is_ci = True

        def pull_state(self, local_files):
            return False

    monkeypatch.setattr(main_module, "CloudPersistenceBridge", _FatalCloudBridge)
    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: (_ for _ in ()).throw(AssertionError("should not fetch")),
    )

    with pytest.raises(RuntimeError, match="Cloud state pull failed"):
        main_module.run_v11_pipeline(
            Namespace(
                json=False,
                notify_discord=False,
                no_save=True,
                no_color=True,
            )
        )


def test_materialize_prior_state_uses_canonical_seed_when_runtime_state_missing(tmp_path):
    seed_path = tmp_path / "canonical_seed.json"
    runtime_path = tmp_path / "runtime" / "prior_state.json"
    payload = {
        "version": "v11-prior-state",
        "regimes": ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        "counts": {"MID_CYCLE": 10.0, "LATE_CYCLE": 5.0, "BUST": 2.0, "RECOVERY": 3.0},
        "transition_counts": {},
        "execution_state": {"stable_regime": "MID_CYCLE", "hydration_anchor": "2018-01-01"},
        "bootstrap_fingerprint": "sha256:test",
    }
    seed_path.write_text(json.dumps(payload), encoding="utf-8")

    origin = main_module._materialize_prior_state(runtime_path, seed_path)

    assert origin == "canonical_seed"
    assert runtime_path.exists()
    assert json.loads(runtime_path.read_text(encoding="utf-8")) == payload


def test_materialize_prior_state_fails_closed_when_seed_is_missing(tmp_path):
    runtime_path = tmp_path / "runtime" / "prior_state.json"
    missing_seed = tmp_path / "missing_seed.json"

    with pytest.raises(FileNotFoundError, match="canonical hydrated prior seed"):
        main_module._materialize_prior_state(runtime_path, missing_seed)
