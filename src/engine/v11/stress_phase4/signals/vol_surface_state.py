from __future__ import annotations

import numpy as np
import pandas as pd


def _col(frame: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(frame[name], errors="coerce").fillna(0.0) if name in frame else pd.Series(0.0, index=frame.index)


def build_vol_surface_state(frame: pd.DataFrame) -> pd.DataFrame:
    """Volatility panic-structure proxy built from realized volatility and uncertainty telemetry."""

    vol_z = _col(frame, "phase3_vol_z")
    short_vol_stress = ((vol_z + 0.2) / 2.5).clip(0.0, 1.0)
    convexity_demand = np.maximum(short_vol_stress, _col(frame, "benchmark_uncertainty").clip(0.0, 1.0))
    term_structure_distortion = (short_vol_stress - _col(frame, "benchmark_trend_strength").clip(0.0, 1.0) * 0.25).clip(0.0, 1.0)
    panic_structure = (0.42 * short_vol_stress + 0.34 * convexity_demand + 0.24 * term_structure_distortion).clip(0.0, 1.0)
    return pd.DataFrame(
        {
            "vol_surface_panic": panic_structure,
            "short_vol_stress": short_vol_stress,
            "convexity_demand": convexity_demand,
            "term_structure_distortion": term_structure_distortion,
        },
        index=frame.index,
    )
