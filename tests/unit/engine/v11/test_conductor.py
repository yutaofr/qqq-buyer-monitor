from __future__ import annotations

import json
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.conductor import V11Conductor
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
            "copper_gold_ratio": 0.18 + np.linspace(0.0, 0.04, len(dates)) + rng.normal(0.0, 0.001, len(dates)),
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
    t0["source_treasury_vol"] = "unavailable:treasury_vol"
    result = conductor.daily_run(t0)

    assert result["data_quality"] < 1.0
    assert result["quality_audit"]["reason"] == "DEGRADED_SOURCE"
    assert result["quality_audit"]["effective_entropy"] > result["quality_audit"]["posterior_entropy"]


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
    t0["source_erp_ttm"] = np.nan
    result = conductor.daily_run(t0)

    erp_quality = result["quality_audit"]["fields"]["erp_ttm"]
    assert result["quality_audit"]["reason"] == "DEGRADED_SOURCE"
    assert erp_quality["source"] == "missing:provenance"
    assert erp_quality["degraded"] is True
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
