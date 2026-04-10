from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.engine.aggregator import FullPanoramaAggregator
from src.research.regime_process_audit import compute_regime_process_alignment

PROCESS_GATE_MINIMA: dict[str, float] = {
    "posterior_vs_benchmark_process": 0.67,
    "stable_vs_benchmark_regime": 0.67,
    "probability_within_band_share": 0.47,
    "delta_within_band_share": 0.70,
    "acceleration_within_band_share": 0.55,
    "transition_probability_within_band_share": 0.63,
    "entropy_within_band_share": 0.55,
}


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    if "date" in normalized.columns:
        normalized["date"] = pd.to_datetime(normalized["date"]).dt.tz_localize(None)
        normalized = normalized.set_index("date")
    else:
        normalized.index = pd.to_datetime(normalized.index).tz_localize(None)
    return normalized.sort_index()


def build_panorama_scenario_frame(
    trace: pd.DataFrame,
    diagnostics: pd.DataFrame,
    *,
    beta_floor: float = FullPanoramaAggregator.BETA_FLOOR,
    beta_ceiling: float = FullPanoramaAggregator.BETA_CEILING_AGGRESSIVE,
    tractor_risk_threshold: float = FullPanoramaAggregator.TRACTOR_RISK_THRESHOLD,
    sidecar_risk_threshold: float = FullPanoramaAggregator.SIDECAR_RISK_THRESHOLD,
    calm_threshold: float = FullPanoramaAggregator.CALM_THRESHOLD,
) -> pd.DataFrame:
    trace_df = _normalize_frame(trace)
    diag_df = _normalize_frame(diagnostics)
    joined = trace_df.join(diag_df[["tractor_prob", "sidecar_prob", "sidecar_valid"]], how="inner")

    joined["standard_beta"] = pd.to_numeric(joined["target_beta"], errors="coerce")
    joined["tractor_prob"] = pd.to_numeric(joined["tractor_prob"], errors="coerce").fillna(0.0)
    joined["sidecar_prob"] = pd.to_numeric(joined["sidecar_prob"], errors="coerce")
    joined["sidecar_valid"] = (
        joined["sidecar_valid"].fillna(joined["sidecar_prob"].notna()).astype(bool)
    )

    joined["tractor_risk"] = joined["tractor_prob"] > tractor_risk_threshold
    joined["sidecar_risk"] = joined["sidecar_valid"] & (
        joined["sidecar_prob"] > sidecar_risk_threshold
    )
    joined["all_calm"] = (
        (joined["tractor_prob"] < calm_threshold)
        & joined["sidecar_valid"]
        & (joined["sidecar_prob"] < calm_threshold)
    )

    joined["s4_sidecar_beta"] = np.where(
        joined["sidecar_risk"], beta_floor, joined["standard_beta"]
    )
    joined["s5_tractor_beta"] = np.where(
        joined["tractor_risk"], beta_floor, joined["standard_beta"]
    )
    joined["panorama_beta"] = np.where(
        joined["tractor_risk"] | joined["sidecar_risk"],
        beta_floor,
        np.where(
            joined["all_calm"],
            np.maximum(joined["standard_beta"], beta_ceiling),
            joined["standard_beta"],
        ),
    )
    return joined


def compute_execution_metrics(trace: pd.DataFrame, beta_col: str) -> dict[str, float]:
    close = pd.to_numeric(trace.get("close"), errors="coerce")
    beta = pd.to_numeric(trace.get(beta_col), errors="coerce").clip(lower=0.0).fillna(0.0)
    qqq_ret = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    portfolio_ret = beta.shift(1).fillna(beta.iloc[0] if not beta.empty else 0.0) * qqq_ret
    equity = (1.0 + portfolio_ret).cumprod()
    rolling_peak = equity.cummax().replace(0.0, np.nan)
    drawdown = (equity / rolling_peak) - 1.0
    left_tail_cutoff = float(qqq_ret.quantile(0.05)) if not qqq_ret.empty else 0.0
    left_tail_mask = qqq_ret <= left_tail_cutoff
    metrics = {
        "rows": float(len(trace)),
        "approx_total_return": float(equity.iloc[-1] - 1.0) if not equity.empty else 0.0,
        "approx_max_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
        "mean_target_beta": float(beta.mean()) if not beta.empty else 0.0,
        "mean_turnover": float(beta.diff().abs().fillna(0.0).mean()) if not beta.empty else 0.0,
        "left_tail_mean_beta": float(beta[left_tail_mask].mean()) if left_tail_mask.any() else 0.0,
    }
    expected_beta = pd.to_numeric(trace.get("expected_target_beta"), errors="coerce")
    if expected_beta is not None and not expected_beta.dropna().empty:
        metrics["mean_expected_beta"] = float(expected_beta.dropna().mean())
        aligned = pd.concat(
            [beta.rename("beta"), expected_beta.rename("expected")], axis=1
        ).dropna()
        if not aligned.empty:
            error = aligned["beta"] - aligned["expected"]
            metrics["beta_expectation_mae"] = float(error.abs().mean())
            metrics["beta_expectation_rmse"] = float(np.sqrt((error.pow(2)).mean()))
            metrics["beta_expectation_within_5pct"] = float((error.abs() <= 0.05).mean())
    raw_beta = pd.to_numeric(trace.get("raw_target_beta"), errors="coerce")
    if raw_beta is not None and not raw_beta.dropna().empty:
        metrics["mean_raw_beta"] = float(raw_beta.dropna().mean())
        if expected_beta is not None and not expected_beta.dropna().empty:
            aligned_raw = pd.concat(
                [raw_beta.rename("raw_beta"), expected_beta.rename("expected")], axis=1
            ).dropna()
            if not aligned_raw.empty:
                raw_error = aligned_raw["raw_beta"] - aligned_raw["expected"]
                metrics["raw_beta_expected_mae"] = float(raw_error.abs().mean())
                metrics["raw_beta_expected_within_5pct"] = float((raw_error.abs() <= 0.05).mean())
    standard_beta = pd.to_numeric(trace.get("standard_beta"), errors="coerce")
    if standard_beta is not None and not standard_beta.dropna().empty:
        metrics["mean_standard_beta"] = float(standard_beta.dropna().mean())
        if expected_beta is not None and not expected_beta.dropna().empty:
            aligned_standard = pd.concat(
                [standard_beta.rename("standard_beta"), expected_beta.rename("expected")], axis=1
            ).dropna()
            if not aligned_standard.empty:
                standard_error = aligned_standard["standard_beta"] - aligned_standard["expected"]
                metrics["standard_beta_expected_mae"] = float(standard_error.abs().mean())
                metrics["standard_beta_expected_within_5pct"] = float(
                    (standard_error.abs() <= 0.05).mean()
                )
    process_metrics = _compute_process_metrics(trace)
    if process_metrics:
        metrics.update(process_metrics)
    return metrics


def judge_panorama_candidate(current: dict[str, Any], baseline: dict[str, Any]) -> tuple[bool, str]:
    process_failure = _process_contract_failure(current)
    if process_failure is not None:
        return False, process_failure
    if (
        float(current.get("left_tail_mean_beta", 0.0))
        > float(baseline.get("left_tail_mean_beta", 0.0)) + 1e-7
    ):
        return False, "Defensive Violation"
    if (
        float(current.get("approx_max_drawdown", 0.0))
        < float(baseline.get("approx_max_drawdown", 0.0)) - 1e-7
    ):
        return False, "Drawdown Regression"
    turnover_limit = max(
        float(baseline.get("mean_turnover", 0.0)) * 1.5,
        float(baseline.get("mean_turnover", 0.0)) + 0.02,
    )
    if float(current.get("mean_turnover", 0.0)) > turnover_limit + 1e-7:
        return False, "Turnover Regression"
    if (
        "beta_expectation_mae" in current
        and "beta_expectation_mae" in baseline
        and float(current.get("beta_expectation_mae", 0.0))
        > float(baseline.get("beta_expectation_mae", 0.0)) + 0.02
    ):
        return False, "Process Distortion"
    if (
        "beta_expectation_within_5pct" in current
        and "beta_expectation_within_5pct" in baseline
        and float(current.get("beta_expectation_within_5pct", 0.0)) + 1e-7
        < float(baseline.get("beta_expectation_within_5pct", 0.0)) - 0.02
    ):
        return False, "Process Distortion"
    return True, "PASS"


def _compute_process_metrics(trace: pd.DataFrame) -> dict[str, float]:
    benchmark = _extract_benchmark_trace(trace)
    if benchmark is None:
        return {}
    model_trace = trace.reset_index(drop=False).copy()
    model_trace = model_trace.drop(
        columns=[column for column in model_trace.columns if column.startswith("benchmark_")],
        errors="ignore",
    )
    try:
        _, summary = compute_regime_process_alignment(model_trace, benchmark)
    except ValueError:
        return {}
    overall = summary.get("overall", {})
    return {
        key: float(value)
        for key, value in overall.items()
        if isinstance(value, (int, float, np.floating))
        and key
        in {
            "posterior_vs_benchmark_process",
            "stable_vs_benchmark_regime",
            "probability_within_band_share",
            "delta_within_band_share",
            "acceleration_within_band_share",
            "transition_probability_within_band_share",
            "entropy_within_band_share",
            "entropy_mae",
            "transition_entropy_within_band_share",
        }
    }


def _extract_benchmark_trace(trace: pd.DataFrame) -> pd.DataFrame | None:
    benchmark_cols = [column for column in trace.columns if column.startswith("benchmark_")]
    if not benchmark_cols:
        return None
    benchmark = trace.reset_index(drop=False)[["date", *benchmark_cols]].copy()
    if "index" in benchmark.columns and "date" not in benchmark.columns:
        benchmark = benchmark.rename(columns={"index": "date"})
    benchmark["date"] = pd.to_datetime(benchmark["date"], errors="coerce")
    benchmark = benchmark.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
    return benchmark if not benchmark.empty else None


def _process_contract_failure(metrics: dict[str, Any]) -> str | None:
    for key, minimum in PROCESS_GATE_MINIMA.items():
        if key not in metrics:
            continue
        if float(metrics[key]) + 1e-9 < minimum:
            return f"Worldview Process Failure ({key})"
    return None


def choose_production_candidate(report: pd.DataFrame) -> dict[str, Any]:
    passed = report.loc[report["acceptance_pass"]].copy()
    if passed.empty:
        raise ValueError("No panorama scenario satisfied acceptance constraints.")
    ranked = passed.sort_values(
        by=["approx_total_return", "approx_max_drawdown", "left_tail_mean_beta", "mean_turnover"],
        ascending=[False, False, True, True],
    )
    return ranked.iloc[0].to_dict()
