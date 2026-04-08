"""Comparison helpers for recovery HMM shadow vs production trace."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def compare_shadow_vs_production(
    *,
    production_trace_path: str | Path,
    shadow_trace_path: str | Path,
) -> dict[str, object]:
    production = pd.read_csv(production_trace_path, parse_dates=["date"])
    shadow = pd.read_csv(shadow_trace_path, parse_dates=["date"])
    merged = production.merge(shadow, on="date", how="inner")

    recovery_release_gap = merged.loc[
        (merged["shadow_state"] == "RECOVERY") & (merged["stable_regime"] != "RECOVERY")
    ]
    return {
        "rows_compared": int(len(merged)),
        "recovery_release_gap": int(len(recovery_release_gap)),
        "shadow_mean_weight": float(merged["w_final"].mean()),
        "production_mean_beta": float(merged["target_beta"].mean()),
    }
