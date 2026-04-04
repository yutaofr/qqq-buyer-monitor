from __future__ import annotations

import datetime
import json

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
            "build_version": ["v12.synthetic-dna"] * len(dates),
            "forward_pe": [np.nan] * len(dates),
            "erp_pct": [np.nan] * len(dates),
            "source_forward_pe": ["deprecated:v12"] * len(dates),
            "source_erp": ["deprecated:v12"] * len(dates),
        }
    )


def test_load_price_history_fails_closed_when_cache_missing_in_acceptance_mode(tmp_path):
    missing_cache = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        backtest_module._load_price_history(
            str(missing_cache),
            allow_download=False,
            end_date="2026-03-31",
        )


def test_run_v11_audit_emits_v13_overlay_execution_trace(tmp_path, monkeypatch):
    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"
    artifact_dir = tmp_path / "audit"
    cache_path = tmp_path / "qqq_cache.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)
    pd.DataFrame(
        {
            "Close": np.linspace(100.0, 130.0, len(dates)),
            "Volume": np.linspace(1_000_000.0, 2_000_000.0, len(dates)),
        },
        index=dates,
    ).to_csv(cache_path)

    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    summary = backtest_module.run_v11_audit(
        dataset_path=str(macro_path),
        regime_path=str(regime_path),
        evaluation_start="2025-01-02",
        artifact_dir=str(artifact_dir),
        experiment_config={
            "price_cache_path": str(cache_path),
            "allow_price_download": False,
            "price_end_date": "2026-03-31",
        },
    )

    assert "top1_accuracy" in summary
    execution_trace = pd.read_csv(artifact_dir / "execution_trace.csv")
    assert "protected_beta" in execution_trace.columns
    assert "overlay_beta" in execution_trace.columns
    assert "beta_overlay_multiplier" in execution_trace.columns
    assert "deployment_overlay_multiplier" in execution_trace.columns

    summary_payload = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary_payload["experiment_config"]["allow_price_download"] is False


def test_run_v11_audit_supports_overlay_mode_matrix_without_mutating_raw_beta(
    tmp_path, monkeypatch
):
    dates = pd.bdate_range("2024-01-01", periods=320)
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"
    cache_path = tmp_path / "qqq_cache.csv"

    _build_v12_macro_frame(dates).to_csv(macro_path, index=False)
    pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * 80,
        }
    ).to_csv(regime_path, index=False)
    pd.DataFrame(
        {
            "Close": np.linspace(100.0, 130.0, len(dates)),
            "Volume": np.linspace(1_000_000.0, 2_000_000.0, len(dates)),
        },
        index=dates,
    ).to_csv(cache_path)

    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_fidelity_figure", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.output.backtest_plots.save_v11_probabilistic_audit_figure",
        lambda *args, **kwargs: None,
    )

    traces: dict[str, pd.DataFrame] = {}
    for mode in ["DISABLED", "SHADOW", "NEGATIVE_ONLY", "FULL"]:
        artifact_dir = tmp_path / f"audit_{mode.lower()}"
        backtest_module.run_v11_audit(
            dataset_path=str(macro_path),
            regime_path=str(regime_path),
            evaluation_start="2025-01-02",
            artifact_dir=str(artifact_dir),
            experiment_config={
                "price_cache_path": str(cache_path),
                "allow_price_download": False,
                "price_end_date": "2026-03-31",
                "overlay_mode": mode,
            },
        )
        traces[mode] = pd.read_csv(artifact_dir / "execution_trace.csv")

    assert traces["DISABLED"]["raw_target_beta"].equals(traces["FULL"]["raw_target_beta"])
    assert traces["DISABLED"]["target_beta"].equals(traces["SHADOW"]["target_beta"])
    assert (traces["NEGATIVE_ONLY"]["deployment_overlay_multiplier"] <= 1.0).all()
    assert (traces["FULL"]["beta_overlay_multiplier"] <= 1.0).all()


def test_acceptance_mode_fails_on_missing_price_cache():
    """Verify Fail-closed: --acceptance requires --price-cache-path."""
    with pytest.raises((ValueError, SystemExit)):
        backtest_module.main(
            ["--evaluation-start", "2024-01-01", "--acceptance", "--price-end-date", "2026-03-31"]
        )


def test_acceptance_mode_fails_on_missing_price_end_date():
    """Verify Fail-closed: --acceptance requires --price-end-date."""
    with pytest.raises((ValueError, SystemExit)):
        backtest_module.main(
            [
                "--evaluation-start",
                "2024-01-01",
                "--acceptance",
                "--price-cache-path",
                "data/dummy_cache.csv",
            ]
        )


def test_acceptance_mode_blocks_today_date():
    """Verify Fail-closed: --acceptance rejects today's date (lookahead prevention)."""
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    with pytest.raises((ValueError, SystemExit)):
        backtest_module.main(
            [
                "--evaluation-start",
                "2024-01-01",
                "--acceptance",
                "--price-cache-path",
                "data/dummy_cache.csv",
                "--price-end-date",
                today,
            ]
        )


def test_acceptance_hard_forces_no_download(monkeypatch):
    """Verify that --acceptance forces allow_price_download=False in the backend."""
    called_config = {}

    def mock_run_v11_audit(**kwargs):
        called_config.update(kwargs.get("experiment_config", {}))
        return {"top1_accuracy": 0.0, "mean_brier": 0.0, "mean_entropy": 0.0, "lock_incidence": 0.0}

    monkeypatch.setattr(backtest_module, "run_v11_audit", mock_run_v11_audit)

    # Even if we try to sneak in allowing download, acceptance should override it
    backtest_module.main(
        [
            "--evaluation-start",
            "2024-01-01",
            "--acceptance",
            "--price-cache-path",
            "data/dummy_cache.csv",
            "--price-end-date",
            "2026-03-27",
        ]
    )

    assert called_config["allow_price_download"] is False
