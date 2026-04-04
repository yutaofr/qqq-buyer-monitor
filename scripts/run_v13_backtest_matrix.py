"""Run the frozen v13 execution-overlay backtest matrix and summarize non-regression."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import os
import pandas as pd
from src.backtest import run_v11_audit

MODES = ["DISABLED", "SHADOW", "NEGATIVE_ONLY", "FULL"]


def judge_acceptance(
    current: dict[str, Any], baseline: dict[str, Any]
) -> tuple[bool, str]:
    """Ruthless juror for V13.8 Industrial Hardening."""
    # 1. Canonical Protection: No drift allowed in raw_target_beta vs DISABLED
    raw_delta = float(current.get("max_raw_target_beta_delta_vs_disabled", 0.0))
    if raw_delta > 1e-7:
        return False, f"FAIL: Canonical Drift ({raw_delta:.6f})"

    # 2. Defensive Asymmetry: Left tail risk must be <= baseline
    current_lt = float(current.get("left_tail_mean_beta", 0.0))
    baseline_lt = float(baseline.get("left_tail_mean_beta", 0.0))
    if current_lt > baseline_lt + 1e-7:
        return (
            False,
            f"FAIL: Defensive Violation (LtBeta: {current_lt:.4f} > Base: {baseline_lt:.4f})",
        )

    # 3. Optimism Bias: Rewards (long expansion) must not exceed Penalties (defensive contraction)
    rewards = float(current.get("reward_days", 0.0))
    penalties = float(current.get("penalty_days", 0.0))
    if rewards > penalties + 1e-7:
        return False, f"FAIL: Optimism Bias (Reward: {rewards} > Penalty: {penalties})"

    return True, "PASS"


def _read_trace(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)


def _compute_execution_metrics(trace: pd.DataFrame) -> dict[str, float]:
    close = pd.to_numeric(trace.get("close"), errors="coerce")
    target_beta = (
        pd.to_numeric(trace.get("target_beta"), errors="coerce").clip(lower=0.0).fillna(0.0)
    )
    raw_beta = pd.to_numeric(trace.get("raw_target_beta"), errors="coerce").fillna(0.0)

    qqq_ret = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    portfolio_ret = (
        target_beta.shift(1).fillna(target_beta.iloc[0] if not target_beta.empty else 0.0) * qqq_ret
    )
    equity = (1.0 + portfolio_ret).cumprod()
    rolling_peak = equity.cummax().replace(0.0, np.nan)
    drawdown = (equity / rolling_peak) - 1.0

    left_tail_cutoff = float(qqq_ret.quantile(0.05)) if not qqq_ret.empty else 0.0
    left_tail_mask = qqq_ret <= left_tail_cutoff

    return {
        "rows": float(len(trace)),
        "approx_total_return": float(equity.iloc[-1] - 1.0) if not equity.empty else 0.0,
        "approx_max_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
        "mean_target_beta": float(target_beta.mean()) if not target_beta.empty else 0.0,
        "mean_raw_target_beta": float(raw_beta.mean()) if not raw_beta.empty else 0.0,
        "mean_turnover": float(target_beta.diff().abs().fillna(0.0).mean())
        if not target_beta.empty
        else 0.0,
        "left_tail_mean_beta": float(target_beta[left_tail_mask].mean())
        if left_tail_mask.any()
        else 0.0,
        "penalty_days": float(
            (
                pd.to_numeric(trace.get("beta_overlay_multiplier"), errors="coerce").fillna(1.0)
                < 0.999999
            ).sum()
        ),
        "reward_days": float(
            (
                pd.to_numeric(trace.get("deployment_overlay_multiplier"), errors="coerce").fillna(
                    1.0
                )
                > 1.000001
            ).sum()
        ),
    }


def _run_mode(
    *,
    mode: str,
    dataset_path: str,
    regime_path: str,
    evaluation_start: str,
    output_dir: Path,
    price_cache_path: str,
    price_end_date: str,
) -> dict[str, Any]:
    artifact_dir = output_dir / mode.lower()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary = run_v11_audit(
        dataset_path=dataset_path,
        regime_path=regime_path,
        evaluation_start=evaluation_start,
        artifact_dir=str(artifact_dir),
        experiment_config={
            "overlay_mode": mode,
            "price_cache_path": price_cache_path,
            "allow_price_download": False,
            "price_end_date": price_end_date,
        },
    )
    trace = _read_trace(artifact_dir / "execution_trace.csv")
    return {
        "mode": mode,
        "artifact_dir": str(artifact_dir),
        "summary": summary,
        "trace": trace,
        "execution_metrics": _compute_execution_metrics(trace),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the v13 frozen backtest experiment matrix.")
    parser.add_argument("--dataset-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    parser.add_argument("--evaluation-start", default="2018-01-01")
    parser.add_argument("--price-cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--price-end-date", required=True)
    parser.add_argument("--output-dir", default="artifacts/v13_matrix")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    runs = [
        _run_mode(
            mode=mode,
            dataset_path=args.dataset_path,
            regime_path=args.regime_path,
            evaluation_start=args.evaluation_start,
            output_dir=output_dir,
            price_cache_path=args.price_cache_path,
            price_end_date=args.price_end_date,
        )
        for mode in MODES
    ]

    disabled_trace = runs[0]["trace"]
    rows: list[dict[str, Any]] = []
    for run in runs:
        trace = run["trace"]
        raw_beta_delta = (
            pd.to_numeric(trace["raw_target_beta"], errors="coerce").fillna(0.0)
            - pd.to_numeric(disabled_trace["raw_target_beta"], errors="coerce").fillna(0.0)
        ).abs()
        target_beta_delta = (
            pd.to_numeric(trace["target_beta"], errors="coerce").fillna(0.0)
            - pd.to_numeric(disabled_trace["target_beta"], errors="coerce").fillna(0.0)
        ).abs()

        row = {
            "mode": run["mode"],
            "top1_accuracy": run["summary"]["top1_accuracy"],
            "mean_brier": run["summary"]["mean_brier"],
            "mean_entropy": run["summary"]["mean_entropy"],
            "lock_incidence": run["summary"]["lock_incidence"],
            "max_raw_target_beta_delta_vs_disabled": float(raw_beta_delta.max())
            if not raw_beta_delta.empty
            else 0.0,
            "mean_target_beta_delta_vs_disabled": float(target_beta_delta.mean())
            if not target_beta_delta.empty
            else 0.0,
            **run["execution_metrics"],
        }
        
        # Apply the Ruthless Automated Judge
        passed, reason = judge_acceptance(row, rows[0] if rows else row)
        row["acceptance_pass"] = passed
        row["acceptance_fail_reason"] = reason
        rows.append(row)

    report = pd.DataFrame(rows)
    report.to_csv(output_dir / "matrix_summary.csv", index=False)
    (output_dir / "matrix_summary.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(report.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
