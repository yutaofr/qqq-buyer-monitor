from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from experiments.pi_stress_repair_runner import PiStressRepairRunner


def make_pi_stress_trace_csv(tmp_path: Path) -> Path:
    """Build a deterministic trace with the historical windows required by pi_stress tests."""
    dates = pd.bdate_range("2017-01-03", "2026-01-30")
    n = len(dates)
    idx = np.arange(n, dtype=float)
    trend = 100.0 * (1.00045**idx)

    drawdown = np.zeros(n, dtype=float)
    stress_level = np.zeros(n, dtype=float)
    recovery_level = np.zeros(n, dtype=float)
    ordinary_level = np.zeros(n, dtype=float)

    def set_window(start: str, end: str, dd: float, stress: float, recovery: float, ordinary: float) -> None:
        mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
        count = int(mask.sum())
        if count == 0:
            return
        ramp = np.linspace(0.35, 1.0, count)
        drawdown[mask] = np.minimum(drawdown[mask], dd * ramp)
        stress_level[mask] = np.maximum(stress_level[mask], stress)
        recovery_level[mask] = np.maximum(recovery_level[mask], recovery)
        ordinary_level[mask] = np.maximum(ordinary_level[mask], ordinary)

    set_window("2018-01-26", "2018-04-30", -0.08, 0.20, 0.05, 0.80)
    set_window("2018-10-01", "2018-12-24", -0.11, 0.35, 0.02, 0.80)
    set_window("2020-02-18", "2020-04-30", -0.32, 0.96, 0.00, 0.00)
    set_window("2020-04-01", "2020-09-30", -0.10, 0.24, 0.88, 0.10)
    set_window("2022-01-03", "2022-06-30", -0.23, 0.86, 0.04, 0.05)
    set_window("2022-07-01", "2022-12-30", -0.09, 0.30, 0.78, 0.20)
    set_window("2023-07-01", "2023-10-31", -0.08, 0.24, 0.06, 0.80)
    set_window("2025-02-15", "2025-05-30", -0.07, 0.18, 0.05, 0.85)

    close = trend * (1.0 + drawdown)
    transition = np.maximum(0.10 + 0.55 * ordinary_level, 0.30 * stress_level)
    bust_prob = np.clip(0.03 + 0.58 * stress_level + 0.10 * ordinary_level, 0.0, 1.0)
    recovery_prob = np.clip(0.04 + 0.62 * recovery_level, 0.0, 1.0)
    recent_damage = np.clip(-drawdown / 0.32, 0.0, 1.0)
    rebound = np.clip(recovery_level * 0.32, 0.0, 1.0)

    trace = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "close": close,
            "Close": close,
            "expected_target_beta": np.clip(0.98 - 0.25 * stress_level + 0.04 * recovery_level, 0.5, 1.05),
            "raw_target_beta": np.clip(0.95 - 0.65 * stress_level + 0.15 * recovery_level, 0.1, 1.05),
            "benchmark_prob_BUST": bust_prob,
            "benchmark_prob_RECOVERY": recovery_prob,
            "benchmark_recovery_impulse": np.clip(0.05 + 0.55 * recovery_level, 0.0, 1.0),
            "benchmark_rebound_from_trough": rebound,
            "benchmark_transition_intensity": np.clip(transition, 0.0, 1.0),
            "benchmark_recent_damage": recent_damage,
            "benchmark_recent_drawdown_depth": recent_damage,
            "benchmark_bust_pressure": np.clip(0.05 + 0.70 * stress_level, 0.0, 1.0),
            "benchmark_bearish_rsi_divergence": np.clip(0.10 + 0.45 * stress_level + 0.15 * ordinary_level, 0.0, 1.0),
            "benchmark_bullish_rsi_divergence": np.clip(0.08 + 0.55 * recovery_level, 0.0, 1.0),
            "benchmark_uncertainty": np.clip(0.12 + 0.50 * stress_level + 0.20 * ordinary_level, 0.0, 1.0),
            "benchmark_conflict_score": np.clip(0.10 + 0.45 * stress_level + 0.22 * ordinary_level, 0.0, 1.0),
            "benchmark_transition_tension": np.clip(0.08 + 0.55 * transition, 0.0, 1.0),
            "benchmark_entropy": np.clip(0.15 + 0.35 * stress_level + 0.25 * ordinary_level, 0.0, 1.0),
            "benchmark_price_volume_divergence": np.clip(-0.05 - 0.35 * stress_level - 0.12 * ordinary_level, -1.0, 1.0),
            "benchmark_volume_ratio": np.clip(0.02 + 0.36 * stress_level + 0.10 * ordinary_level, 0.0, 1.0),
            "benchmark_ma_gap": np.clip(-0.02 - 0.22 * stress_level - 0.06 * ordinary_level, -1.0, 1.0),
            "forensic_stress_score": np.clip(0.05 + 0.75 * stress_level, 0.0, 1.0),
            "forensic_bust_penalty": np.clip(0.03 + 0.70 * stress_level, 0.0, 1.0),
            "forensic_mid_cycle_penalty": np.clip(0.05 + 0.25 * ordinary_level, 0.0, 1.0),
            "S_price": np.clip(0.08 + 0.72 * stress_level + 0.20 * ordinary_level, 0.0, 1.0),
            "S_market": np.clip(0.08 + 0.60 * stress_level + 0.18 * ordinary_level, 0.0, 1.0),
            "S_macro_anom": np.clip(0.05 + 0.65 * stress_level + 0.10 * ordinary_level, 0.0, 1.0),
            "S_persist": np.clip(0.08 + 0.62 * stress_level + 0.15 * ordinary_level, 0.0, 1.0),
            "legacy_pi_stress": np.clip(0.08 + 0.66 * stress_level + 0.18 * ordinary_level, 0.0, 1.0),
        }
    )
    path = tmp_path / "regime_process_trace.csv"
    trace.to_csv(path, index=False)
    return path


def make_pi_stress_registry_json(tmp_path: Path, trace_path: Path) -> Path:
    output_dir = tmp_path / "registry"
    frame = pd.read_csv(trace_path)
    PiStressRepairRunner(output_dir=output_dir, report_dir=tmp_path / "registry_reports").run_component_frame(
        frame,
        max_candidates=9,
    )
    return output_dir / "experiment_registry.json"
