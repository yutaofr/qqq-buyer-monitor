from __future__ import annotations

import numpy as np
import pandas as pd


def _col(frame: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(frame[name], errors="coerce").fillna(0.0) if name in frame else pd.Series(0.0, index=frame.index)


def build_cross_sectional_stress_state(frame: pd.DataFrame) -> pd.DataFrame:
    """Proxy cross-sectional breakage from available breadth-like telemetry."""

    dispersion_pressure = ((-_col(frame, "benchmark_price_volume_divergence")) / 0.35).clip(0.0, 1.0)
    panic_sync = np.maximum(((_col(frame, "benchmark_volume_ratio").abs() - 0.08) / 0.35).clip(0.0, 1.0), _col(frame, "benchmark_uncertainty"))
    leadership_instability = _col(frame, "benchmark_conflict_score").clip(0.0, 1.0)
    breadth_deterioration = dispersion_pressure.rolling(10, min_periods=1).mean().clip(0.0, 1.0)
    stress = (0.34 * breadth_deterioration + 0.30 * panic_sync + 0.22 * leadership_instability + 0.14 * _col(frame, "benchmark_transition_intensity")).clip(0.0, 1.0)
    return pd.DataFrame(
        {
            "cross_sectional_stress": stress,
            "breadth_deterioration": breadth_deterioration,
            "panic_synchronization": panic_sync,
            "leadership_instability": leadership_instability,
        },
        index=frame.index,
    )
