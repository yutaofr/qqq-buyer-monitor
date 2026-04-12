"""Controlled ablation workflow for the QLD permission layer."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd

PROCESS_KEYS: tuple[str, ...] = (
    "posterior_vs_benchmark_process",
    "probability_within_band_share",
    "delta_within_band_share",
    "acceleration_within_band_share",
    "transition_probability_within_band_share",
    "entropy_within_band_share",
)

WINDOWS: dict[str, tuple[str, str]] = {
    "2022_defense": ("2022-01-03", "2022-10-31"),
    "2023_rerisk": ("2023-02-01", "2023-06-30"),
}

DEFAULT_TOLERANCES: dict[str, float] = {
    "posterior_vs_benchmark_process": 0.01,
    "probability_within_band_share": 0.01,
    "delta_within_band_share": 0.01,
    "acceleration_within_band_share": 0.01,
    "transition_probability_within_band_share": 0.02,
    "entropy_within_band_share": 0.02,
    "2022_defense.mean_target_beta": 0.03,
    "2022_defense.qld_days": 3.0,
    "2023_rerisk.mean_target_beta": 0.05,
}


def build_qld_permission_ablation_scenarios(
    *,
    baseline_trace_path: str,
) -> list[dict[str, Any]]:
    common = {
        "baseline_trace_path": baseline_trace_path,
        "save_plots": False,
    }
    return [
        {
            "name": "parity_only",
            "description": "baseline trace parity only; all new QLD permission rules disabled",
            "experiment_config": {
                **common,
                "overlay_suppress_collinear": False,
                "qld_permission_toggles": {
                    "bind_resonance_sell": False,
                    "enable_fundamental_override": False,
                    "enable_sub1x_guard": False,
                },
            },
        },
        {
            "name": "bind_resonance_sell",
            "description": "bind SELL_QLD to execution while keeping other new guards off",
            "experiment_config": {
                **common,
                "overlay_suppress_collinear": False,
                "qld_permission_toggles": {
                    "bind_resonance_sell": True,
                    "enable_fundamental_override": False,
                    "enable_sub1x_guard": False,
                },
            },
        },
        {
            "name": "fundamental_override",
            "description": "enable PIT-safe fundamental override proxy on top of the sub-1x guard",
            "experiment_config": {
                **common,
                "overlay_suppress_collinear": False,
                "qld_permission_toggles": {
                    "bind_resonance_sell": False,
                    "enable_fundamental_override": True,
                    "enable_sub1x_guard": True,
                },
            },
        },
        {
            "name": "collinear_suppression",
            "description": "suppress QQQ/QQEW breadth-concentration double counting only",
            "experiment_config": {
                **common,
                "overlay_suppress_collinear": True,
                "qld_permission_toggles": {
                    "bind_resonance_sell": False,
                    "enable_fundamental_override": False,
                    "enable_sub1x_guard": False,
                },
            },
        },
        {
            "name": "sub1x_guard",
            "description": "require calm sidecar, entropy and override gates before sub-1x QLD",
            "experiment_config": {
                **common,
                "overlay_suppress_collinear": False,
                "qld_permission_toggles": {
                    "bind_resonance_sell": False,
                    "enable_fundamental_override": False,
                    "enable_sub1x_guard": True,
                },
            },
        },
        {
            "name": "all_on",
            "description": "all QLD permission hardening rules enabled",
            "experiment_config": {
                **common,
                "overlay_suppress_collinear": True,
                "qld_permission_toggles": {
                    "bind_resonance_sell": True,
                    "enable_fundamental_override": True,
                    "enable_sub1x_guard": True,
                },
            },
        },
    ]


def summarize_execution_window(
    execution_df: pd.DataFrame,
    *,
    start: str,
    end: str,
) -> dict[str, Any]:
    frame = execution_df.copy()
    if "date" not in frame.columns:
        raise ValueError("execution trace must include a `date` column")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values("date")
    window = frame[
        (frame["date"] >= pd.Timestamp(start)) & (frame["date"] <= pd.Timestamp(end))
    ].copy()
    qld_mask = window.get("target_bucket", pd.Series(dtype=object)).astype(str).eq("QLD")
    first_qld_date = (
        pd.Timestamp(window.loc[qld_mask, "date"].iloc[0]).date().isoformat()
        if bool(qld_mask.any())
        else None
    )
    return {
        "rows": int(len(window)),
        "mean_target_beta": float(pd.to_numeric(window.get("target_beta"), errors="coerce").mean())
        if not window.empty
        else 0.0,
        "mean_raw_target_beta": float(
            pd.to_numeric(window.get("raw_target_beta"), errors="coerce").mean()
        )
        if not window.empty
        else 0.0,
        "mean_overlay_beta": float(
            pd.to_numeric(window.get("overlay_beta"), errors="coerce").mean()
        )
        if not window.empty
        else 0.0,
        "qld_days": int(qld_mask.sum()) if not window.empty else 0,
        "qld_share": float(qld_mask.mean()) if not window.empty else 0.0,
        "first_qld_date": first_qld_date,
    }


def build_scenario_record(
    *,
    name: str,
    description: str,
    summary: dict[str, Any],
    execution_df: pd.DataFrame,
) -> dict[str, Any]:
    windows = {
        label: summarize_execution_window(execution_df, start=start, end=end)
        for label, (start, end) in WINDOWS.items()
    }
    process = {key: summary.get(key) for key in PROCESS_KEYS}
    return {
        "name": name,
        "description": description,
        "summary": dict(summary),
        "process": process,
        "windows": windows,
    }


def evaluate_no_regression(
    records: list[dict[str, Any]],
    *,
    baseline_name: str = "parity_only",
    tolerances: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    if not records:
        return []

    baseline = next((record for record in records if record["name"] == baseline_name), None)
    if baseline is None:
        raise ValueError(f"Baseline scenario `{baseline_name}` not found")

    tol = dict(DEFAULT_TOLERANCES)
    tol.update(dict(tolerances or {}))
    evaluated: list[dict[str, Any]] = []
    for record in records:
        checks: dict[str, bool] = {}
        if record["name"] == baseline_name:
            checks["baseline_defined"] = True
        else:
            for key in PROCESS_KEYS:
                baseline_value = baseline["process"].get(key)
                candidate_value = record["process"].get(key)
                checks[f"process.{key}"] = _not_worse_lower_bounded(
                    candidate_value,
                    baseline_value,
                    tol.get(key, 0.0),
                )

            checks["window.2022_defense.mean_target_beta"] = _not_worse_upper_bounded(
                record["windows"]["2022_defense"].get("mean_target_beta"),
                baseline["windows"]["2022_defense"].get("mean_target_beta"),
                tol.get("2022_defense.mean_target_beta", 0.0),
            )
            checks["window.2022_defense.qld_days"] = _not_worse_upper_bounded(
                record["windows"]["2022_defense"].get("qld_days"),
                baseline["windows"]["2022_defense"].get("qld_days"),
                tol.get("2022_defense.qld_days", 0.0),
            )
            checks["window.2023_rerisk.mean_target_beta"] = _not_worse_lower_bounded(
                record["windows"]["2023_rerisk"].get("mean_target_beta"),
                baseline["windows"]["2023_rerisk"].get("mean_target_beta"),
                tol.get("2023_rerisk.mean_target_beta", 0.0),
            )

        enriched = deepcopy(record)
        enriched["no_regression"] = {
            "baseline": baseline_name,
            "checks": checks,
            "passed": all(checks.values()),
        }
        evaluated.append(enriched)
    return evaluated


def flatten_records_for_csv(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        row: dict[str, Any] = {
            "scenario": record["name"],
            "description": record["description"],
            "no_regression_passed": record.get("no_regression", {}).get("passed"),
        }
        for key, value in record.get("process", {}).items():
            row[f"process_{key}"] = value
        for window_name, metrics in record.get("windows", {}).items():
            for metric_name, metric_value in metrics.items():
                row[f"{window_name}_{metric_name}"] = metric_value
        for check_name, check_value in record.get("no_regression", {}).get("checks", {}).items():
            row[f"check_{check_name}"] = check_value
        rows.append(row)
    return pd.DataFrame(rows)


def _not_worse_lower_bounded(
    candidate_value: Any,
    baseline_value: Any,
    tolerance: float,
) -> bool:
    if candidate_value is None or baseline_value is None:
        return False
    return float(candidate_value) >= (float(baseline_value) - float(tolerance))


def _not_worse_upper_bounded(
    candidate_value: Any,
    baseline_value: Any,
    tolerance: float,
) -> bool:
    if candidate_value is None or baseline_value is None:
        return False
    return float(candidate_value) <= (float(baseline_value) + float(tolerance))
