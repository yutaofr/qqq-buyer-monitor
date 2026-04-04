from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.engine.v11.conductor import V11Conductor


def _build_v12_macro_frame_with_overlay(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    monthly_block = np.repeat(np.linspace(10.0, 20.0, 12), 30)[: len(dates)]
    erp_curve = 0.035 + np.sin(np.linspace(0.0, 10.0, len(dates))) * 0.004
    close = 100.0 + np.linspace(0.0, 40.0, len(dates))
    volume = 1_000_000.0 + np.linspace(0.0, 300_000.0, len(dates))

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
            "qqq_close": close,
            "source_qqq_close": ["direct:yfinance"] * len(dates),
            "qqq_close_quality_score": [1.0] * len(dates),
            "qqq_volume": volume,
            "source_qqq_volume": ["direct:yfinance"] * len(dates),
            "qqq_volume_quality_score": [1.0] * len(dates),
            "adv_dec_ratio": np.linspace(0.58, 0.52, len(dates)),
            "source_breadth_proxy": ["observed:^ADD"] * len(dates),
            "breadth_quality_score": [1.0] * len(dates),
            "ndx_concentration": np.linspace(0.01, 0.03, len(dates)),
            "source_ndx_concentration": ["derived:qqq-qqew"] * len(dates),
            "ndx_concentration_quality_score": [1.0] * len(dates),
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
            "reference_capital": [100_000.0] * len(dates),
            "current_nav": [100_000.0] * len(dates),
        }
    )


def _build_regime_frame(dates: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * (len(dates) - 240),
        }
    )


def test_conductor_exports_overlay_block_and_v13_snapshot(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"
    snapshot_dir = tmp_path / "snapshots"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame_with_overlay(dates)
    regime_df = _build_regime_frame(dates)
    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
        snapshot_dir=str(snapshot_dir),
    )

    t0 = macro_df.tail(1).set_index("observation_date")
    result = conductor.daily_run(t0)

    assert "overlay" in result
    assert result["overlay"]["beta_overlay_multiplier"] <= 1.0
    assert result["overlay"]["deployment_overlay_multiplier"] >= 0.5
    assert result["overlay_beta"] == pytest.approx(
        result["protected_beta"] * result["overlay"]["beta_overlay_multiplier"]
    )

    snapshot_path = snapshot_dir / f"snapshot_{t0.index[-1].date().isoformat()}.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["snapshot_version"] == "v13_runtime_snapshot.v1"
    assert "execution_overlay" in snapshot


def test_conductor_overlay_preserves_raw_beta_and_penalizes_only_execution_surface(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_a = tmp_path / "prior_a.json"
    prior_b = tmp_path / "prior_b.json"

    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_df = _build_v12_macro_frame_with_overlay(dates)
    regime_df = _build_regime_frame(dates)
    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    benign = macro_df.tail(1).copy().set_index("observation_date")
    stressed = benign.copy()
    stressed["adv_dec_ratio"] = 0.18
    stressed["ndx_concentration"] = 0.16
    stressed["qqq_close"] = float(stressed["qqq_close"].iloc[0]) * 1.04
    stressed["qqq_volume"] = float(stressed["qqq_volume"].iloc[0]) * 0.55

    benign_conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_a),
    )
    stressed_conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_b),
    )

    benign_result = benign_conductor.daily_run(benign)
    stressed_result = stressed_conductor.daily_run(stressed)

    assert stressed_result["raw_target_beta"] == pytest.approx(benign_result["raw_target_beta"])
    assert (
        stressed_result["overlay"]["negative_score"] >= benign_result["overlay"]["negative_score"]
    )
    assert stressed_result["overlay_beta"] <= benign_result["overlay_beta"]
