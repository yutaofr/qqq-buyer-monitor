from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


def _load_script_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load script module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_deployment_pacing_report_writes_artifacts(tmp_path):
    script_path = Path("scripts/run_deployment_pacing_report.py")
    module = _load_script_module(script_path)

    dates = pd.date_range("2024-01-02", periods=30, freq="B")
    qqq = pd.DataFrame({"Close": [100.0 - (i * 0.75) for i in range(30)]}, index=dates)
    cache_path = tmp_path / "qqq_history_cache.csv"
    qqq.to_csv(cache_path)

    macro = pd.DataFrame(
        {
            "observation_date": [d.strftime("%Y-%m-%d") for d in dates],
            "effective_date": [d.strftime("%Y-%m-%d") for d in dates],
            "credit_spread_bps": [320.0] * 10 + [520.0] * 10 + [680.0] * 10,
            "credit_acceleration_pct_10d": [0.0] * len(dates),
            "forward_pe": [24.0] * len(dates),
            "erp_pct": [3.5] * len(dates),
            "real_yield_10y_pct": [1.25] * len(dates),
            "net_liquidity_usd_bn": [250.0] * len(dates),
            "liquidity_roc_pct_4w": [0.0] * len(dates),
            "funding_stress_flag": [0] * len(dates),
            "source_credit_spread": ["fred:BAMLH0A0HYM2"] * len(dates),
            "source_forward_pe": ["damodaran:histimpl"] * len(dates),
            "source_erp": ["damodaran:histimpl"] * len(dates),
            "source_real_yield": ["fred:DFII10"] * len(dates),
            "source_net_liquidity": ["derived:WALCL-WDTGAL-RRPONTSYD"] * len(dates),
            "source_funding_stress": ["fred:NFCI"] * len(dates),
            "build_version": ["v7.0-class-a-research-r1"] * len(dates),
        }
    )
    macro_path = tmp_path / "macro_historical_dump.csv"
    macro.to_csv(macro_path, index=False)

    save_dir = tmp_path / "pacing_report"
    docs_image_path = tmp_path / "docs" / "images" / "deployment_pacing_backtest.png"

    exit_code = module.main(
        [
            "--cache-path",
            str(cache_path),
            "--macro-path",
            str(macro_path),
            "--registry-path",
            "data/candidate_registry_v7.json",
            "--save-dir",
            str(save_dir),
            "--docs-image-path",
            str(docs_image_path),
        ]
    )

    assert exit_code == 0
    assert (save_dir / "deployment_pacing_summary.json").exists()
    assert (save_dir / "deployment_pacing_daily.csv").exists()
    assert (save_dir / "deployment_pacing_windows.csv").exists()
    assert (save_dir / "deployment_pacing_backtest.png").exists()
    assert docs_image_path.exists()

    summary = json.loads((save_dir / "deployment_pacing_summary.json").read_text())
    assert summary["pacing"]["compared_points"] > 0
    assert 0.0 <= summary["pacing"]["within_tolerance_ratio"] <= 1.0


def test_window_summary_uses_only_compared_pacing_rows(tmp_path):
    script_path = Path("scripts/run_deployment_pacing_report.py")
    module = _load_script_module(script_path)

    dates = pd.date_range("2024-01-02", periods=5, freq="B")
    signals = pd.DataFrame(
        {
            "deployment_multiplier": [1.0, 1.0, 1.0, 0.5, 0.5],
            "expected_deployment_multiplier": [1.0, None, None, 0.5, None],
            "deployment_pacing_error": [0.0, None, None, 0.0, None],
            "actual_deployment_cash": [100.0, None, None, 50.0, None],
            "expected_deployment_cash": [100.0, None, None, 50.0, None],
        },
        index=dates,
    )

    summary = module._window_summary(signals, "2024-01-02", "2024-01-08", tolerance=0.25)

    assert summary["rows"] == 2
    assert summary["within_tolerance_ratio"] == 1.0
    assert summary["actual_cash_total"] == 150.0
