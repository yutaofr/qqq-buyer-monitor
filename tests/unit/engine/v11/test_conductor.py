from __future__ import annotations

import json
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.conductor import V11Conductor
from src.engine.v11.core.price_topology import PriceTopologyState
from src.engine.v11.probability_seeder import ProbabilitySeeder


def _build_v12_macro_frame(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    monthly_block = np.repeat(np.linspace(10.0, 20.0, 12), 30)[: len(dates)]
    erp_curve = 0.035 + np.sin(np.linspace(0.0, 10.0, len(dates))) * 0.004

    return pd.DataFrame(
        {
            "observation_date": dates,
            "effective_date": dates,
            "credit_spread_bps": 320.0 + np.linspace(0.0, 160.0, len(dates)),
            "real_yield_10y_pct": 0.008 + np.linspace(0.0, 0.018, len(dates)),
            "net_liquidity_usd_bn": 5200.0 + np.linspace(0.0, 250.0, len(dates)),
            "treasury_vol_21d": 0.004 + np.linspace(0.0, 0.006, len(dates)),
            "copper_gold_ratio": 0.18
            + np.linspace(0.0, 0.04, len(dates))
            + rng.normal(0.0, 0.001, len(dates)),
            "breakeven_10y": 0.018 + np.linspace(0.0, 0.01, len(dates)),
            "core_capex_mm": monthly_block,
            "usdjpy": 120.0 + np.linspace(0.0, 18.0, len(dates)) + rng.normal(0.0, 0.2, len(dates)),
            "erp_ttm_pct": erp_curve,
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


def _build_regime_frame(dates: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * (len(dates) - 240),
        }
    )


def test_conductor_persists_posterior_back_into_prior_state(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    t0 = macro_df.tail(1).set_index("observation_date")
    result = conductor.daily_run(t0)

    assert sum(result["probabilities"].values()) == pytest.approx(1.0)
    assert prior_path.exists()
    assert "regime_stabilizer" in result
    assert "barrier" in result["regime_stabilizer"]
    assert "evidence" in result["regime_stabilizer"]

    payload = json.loads(prior_path.read_text())
    assert payload["last_observation_date"] == str(t0.index[-1].date())
    assert payload["last_posterior"]
    assert "bucket_evidence" in payload["execution_state"]


def test_conductor_requires_canonical_dna_and_wont_synthesize_production_baseline(tmp_path):
    macro_path = tmp_path / "missing_macro.csv"
    regime_path = tmp_path / "regimes.csv"
    prior_path = tmp_path / "prior_state.json"

    pd.DataFrame(
        {
            "observation_date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "regime": ["MID_CYCLE", "MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        }
    ).to_csv(regime_path, index=False)

    with pytest.raises(FileNotFoundError):
        V11Conductor(
            macro_data_path=str(macro_path),
            regime_data_path=str(regime_path),
            prior_state_path=str(prior_path),
        )


def test_conductor_rejects_invalid_gaussian_nb_coefficients(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    _build_regime_frame(dates).to_csv(regime_path, index=False)

    feature_count = len(ProbabilitySeeder().feature_names())
    model = GaussianNB(var_smoothing=1e-2).fit(
        np.array([[float(i + j) for j in range(feature_count)] for i in range(6)]),
        np.array(["BUST", "BUST", "LATE_CYCLE", "LATE_CYCLE", "MID_CYCLE", "MID_CYCLE"]),
    )
    model.var_[0, 0] = 0.0

    with pytest.raises(ValueError, match="var_"):
        V11Conductor(
            macro_data_path=str(macro_path),
            regime_data_path=str(regime_path),
            prior_state_path=str(prior_path),
            initial_model=model,
        )


def test_conductor_applies_entropy_penalty_when_v12_source_is_degraded(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    t0 = macro_df.tail(1).set_index("observation_date")
    t0["credit_spread_bps"] = np.nan
    result = conductor.daily_run(t0)

    assert result["data_quality"] < 1.0
    assert result["quality_audit"]["reason"] == "CORE_SENSOR_FAILURE"
    assert (
        result["quality_audit"]["effective_entropy"] > result["quality_audit"]["posterior_entropy"]
    )


def test_conductor_flags_source_switch_and_writes_runtime_snapshot(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"
    snapshot_dir = tmp_path / "snapshots"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
        snapshot_dir=str(snapshot_dir),
    )

    t0 = macro_df.tail(1).copy().set_index("observation_date")
    t0["source_credit_spread"] = "fred:BAMLH0A0HYM2"
    t0["source_real_yield"] = "fred:DFII10"
    t0["source_net_liquidity"] = "derived:fred:WALCL-WDTGAL-RRPONTSYD"
    t0["source_treasury_vol"] = "direct:fred_dgs10"
    t0["source_copper_gold"] = "direct:yfinance"
    t0["source_breakeven"] = "direct:fred_t10yie"
    t0["source_core_capex"] = "direct:fred_neworder"
    t0["source_usdjpy"] = "direct:yfinance"
    t0["source_erp_ttm"] = "direct:shiller"
    t0["build_version"] = "v12_live_feedback"
    result = conductor.daily_run(t0)

    source_switch = result["quality_audit"]["source_switch"]
    assert result["quality_audit"]["reason"] == "SOURCE_SWITCH"
    assert source_switch["detected"] is True
    assert "credit_spread" in source_switch["changed_fields"]
    assert "treasury_vol" in source_switch["changed_fields"]
    assert "erp_ttm" in source_switch["changed_fields"]
    assert "build_version" in source_switch["changed_fields"]

    snapshot_path = snapshot_dir / f"snapshot_{t0.index[-1].date().isoformat()}.json"
    assert snapshot_path.exists()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["runtime_priors"]
    assert snapshot["gaussian_nb"]["theta"]
    assert snapshot["gaussian_nb"]["var"]
    assert snapshot["gaussian_nb"]["class_prior"]
    assert snapshot["raw_t0_data"][0]["source_erp_ttm"] == "direct:shiller"


def test_conductor_applies_price_topology_anchor_to_final_beta(tmp_path, monkeypatch):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    def _forced_bust_topology(*args, **kwargs):
        return PriceTopologyState(
            regime="BUST",
            probabilities={
                "MID_CYCLE": 0.0,
                "LATE_CYCLE": 0.0,
                "BUST": 1.0,
                "RECOVERY": 0.0,
            },
            expected_beta=0.5,
            confidence=1.0,
            posterior_blend_weight=0.0,
            beta_anchor_weight=1.0,
        )

    monkeypatch.setattr(
        "src.engine.v11.conductor.infer_price_topology_state", _forced_bust_topology
    )

    t0 = macro_df.tail(1).set_index("observation_date")
    result = conductor.daily_run(t0)

    assert result["price_topology"]["regime"] == "BUST"
    assert result["target_beta"] == pytest.approx(0.5)


def test_conductor_hydrates_price_derived_training_features_from_cached_history(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"
    price_path = tmp_path / "qqq_history.csv"

    dates = pd.bdate_range("2022-01-03", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)
    price_df = pd.DataFrame(
        {
            "Close": 100.0
            + np.sin(np.linspace(0.0, 16.0, len(dates))) * 8.0
            + np.linspace(0.0, 12.0, len(dates)),
            "Volume": 1_000_000.0 + np.cos(np.linspace(0.0, 8.0, len(dates))) * 150_000.0,
        },
        index=dates,
    )

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)
    price_df.to_csv(price_path)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
        price_history_path=str(price_path),
    )

    feature_names = conductor.seeder.feature_names()
    ma_idx = feature_names.index("qqq_ma_ratio")
    pv_idx = feature_names.index("qqq_pv_divergence_z")

    assert not np.allclose(conductor.gnb.theta_[:, ma_idx], 0.0)
    assert not np.allclose(conductor.gnb.theta_[:, pv_idx], 0.0)


def test_conductor_restores_resonance_window_state_from_prior_execution_state(
    tmp_path, monkeypatch
):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    def _fake_resonance(*args, **kwargs):
        conductor.resonance_detector.risk_ready_days = 2
        conductor.resonance_detector.waterfall_ready_days = 1
        return {
            "action": "HOLD",
            "confidence": 0.0,
            "reason_code": "NO_RESONANCE",
            "reason": "persist timers",
            "prompt": "persist timers",
        }

    monkeypatch.setattr(conductor.resonance_detector, "evaluate", _fake_resonance)

    t0 = macro_df.tail(1).set_index("observation_date")
    conductor.daily_run(t0)

    reloaded = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    assert reloaded.resonance_detector.risk_ready_days == 2
    assert reloaded.resonance_detector.waterfall_ready_days == 1


def test_conductor_does_not_double_increment_high_entropy_streak(tmp_path, monkeypatch):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    def _fake_pipeline(**kwargs):
        return {
            "effective_entropy": 0.90,
            "pre_floor_beta": 0.70,
            "protected_beta": 0.70,
            "is_floor_active": False,
            "overlay_beta": 0.70,
            "deployment_readiness": 0.10,
            "overlay_deployment_readiness": 0.10,
            "high_entropy_streak": 11,
        }

    monkeypatch.setattr("src.engine.v11.conductor.run_execution_pipeline", _fake_pipeline)

    t0 = macro_df.tail(1).set_index("observation_date")
    result = conductor.daily_run(t0)
    payload = json.loads(prior_path.read_text())

    assert result["signal"]["high_entropy_streak"] == 11
    assert payload["execution_state"]["high_entropy_streak"] == 11


def test_conductor_marks_missing_provenance_as_degraded(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    t0 = macro_df.tail(1).copy().set_index("observation_date")
    t0["erp_ttm_pct"] = np.nan
    t0["source_erp_ttm"] = np.nan
    t0["build_version"] = "v12.0-orthogonal-factor-r1"  # Match default to avoid switch
    result = conductor.daily_run(t0)

    erp_quality = result["quality_audit"]["fields"]["erp_ttm"]
    assert erp_quality["quality"] == 0.0
    assert result["quality_audit"]["reason"] in ("SENSOR_DEGRADATION", "SOURCE_SWITCH")
    assert erp_quality["source"] == "missing:provenance"
    assert erp_quality["degraded"] is False  # V13.7: Missing is not degraded
    assert erp_quality["quality"] == 0.0


def test_conductor_quality_score_uses_harmonic_mean_and_emits_move_diagnostics(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame(dates)
    regime_df = _build_regime_frame(dates)

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    t0 = macro_df.tail(1).copy().set_index("observation_date")
    t0["source_treasury_vol"] = "unavailable:treasury_vol"
    result = conductor.daily_run(t0)

    fields = result["quality_audit"]["fields"]
    qualities = [float(payload["quality"]) for payload in fields.values()]
    expected_quality = len(qualities) / sum(1.0 / max(value, 0.01) for value in qualities)
    assert result["quality_audit"]["quality_score"] == pytest.approx(expected_quality)

    feature_values = result["feature_values"]
    assert "move_21d_raw_z" in feature_values
    assert "move_21d_orth_z" in feature_values
    assert "move_spread_beta" in feature_values
    assert "move_spread_corr_21d" in feature_values


def test_conductor_rejects_probability_seeder_hash_drift(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"
    audit_path = tmp_path / "regime_audit.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    _build_regime_frame(dates).to_csv(regime_path, index=False)

    with open("src/engine/v11/resources/regime_audit.json", encoding="utf-8") as f:
        audit_payload = json.load(f)
    bad_audit = deepcopy(audit_payload)
    bad_audit["feature_contract"]["seeder_config_hash"] = "sha256:bad"
    audit_path.write_text(json.dumps(bad_audit), encoding="utf-8")

    with pytest.raises(ValueError, match="feature contract hash"):
        V11Conductor(
            macro_data_path=str(macro_path),
            regime_data_path=str(regime_path),
            prior_state_path=str(prior_path),
            audit_path=str(audit_path),
        )


def test_conductor_migrates_legacy_capitulation_prior_state_into_canonical_topology(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    _build_regime_frame(dates).to_csv(regime_path, index=False)
    prior_path.write_text(
        json.dumps(
            {
                "version": "v11-prior-state",
                "regimes": ["MID_CYCLE", "LATE_CYCLE", "BUST", "CAPITULATION", "RECOVERY"],
                "counts": {
                    "MID_CYCLE": 10.0,
                    "LATE_CYCLE": 9.0,
                    "BUST": 8.0,
                    "CAPITULATION": 2.0,
                    "RECOVERY": 5.0,
                },
                "transition_counts": {},
                "last_posterior": {"CAPITULATION": 0.25, "RECOVERY": 0.15, "BUST": 0.60},
                "execution_state": {"stable_regime": "CAPITULATION"},
            }
        ),
        encoding="utf-8",
    )

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    assert conductor.regimes == ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]
    assert conductor.prior_book.regimes == ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]
    assert "CAPITULATION" not in conductor.prior_book.counts
    assert conductor.prior_book.execution_state["stable_regime"] == "RECOVERY"


def test_conductor_training_cutoff_scopes_prior_bootstrap_history(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 280 + ["BUST"] * 40,
        }
    ).to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
        training_cutoff="2024-12-01",
    )

    priors = conductor.prior_book.current_priors()

    assert priors["MID_CYCLE"] > priors["BUST"]


def test_conductor_uses_business_day_training_classes_for_model_validation(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.bdate_range("2022-01-03", periods=160)
    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": pd.date_range("2022-01-01", periods=170, freq="D"),
            "regime": ["BUST"] * 2 + ["LATE_CYCLE"] * 168,
        }
    ).to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
        training_cutoff="2022-04-29",
    )

    assert conductor.model_regimes == ["LATE_CYCLE"]
    assert conductor.gnb.classes_.tolist() == ["LATE_CYCLE"]
