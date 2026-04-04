import logging

import numpy as np
import pandas as pd

from src.engine.baseline.engine import calculate_composites, rolling_zscore, train_baseline_model
from src.engine.baseline.targets import align_target_inputs

logger = logging.getLogger(__name__)


def calculate_sidecar_composites(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 3-axis composites for the QQQ Sidecar.
    Maintains Growth and Liquidity from Base Tractor.
    Merges VXN and MA Cross into a single QQQ Stress axis (Sensor Fusion).
    """
    # 1. Base Composites (Growth, Liquidity)
    base = calculate_composites(data)

    # 2. Enhanced Stress Composite (Max Retention)
    # C_stress_qqq = Max(Z_Spread, Z_VIX, Z_VXN, MA_Cross_Z_Proxy)
    stress_cols = []
    for col in ["BAMLH0A0HYM2", "VIXCLS", "^VXN"]:
        if col in data.columns:
            stress_cols.append(rolling_zscore(data[col]))

    if stress_cols:
        stress_qqq = pd.concat(stress_cols, axis=1).max(axis=1)
    else:
        stress_qqq = base["stress_composite"]

    # RETURNS STRICTLY 3 DIMENSIONS TO PREVENT OVERFITTING
    return pd.DataFrame(
        {
            "growth_composite": base["growth_composite"],
            "liquidity_composite": base["liquidity_composite"],
            "stress_composite_qqq": stress_qqq,
        },
        index=data.index,
    ).dropna()


def generate_sidecar_target(
    price_series: pd.Series, vxn_series: pd.Series, horizon: int = 20
) -> pd.Series:
    """
    Sidecar Target Y_qqq=1 if QQQ MDD > 10% or VXN > 35 in next 20 days.
    Samples are marked NaN when the forward VXN window is incomplete, so the
    target remains a single full-target object rather than a mixed drawdown-only proxy.
    """
    aligned = align_target_inputs(price_series, vxn_series)
    price_series = aligned["price"]
    vxn_series = aligned["stress"]
    n = len(price_series)
    y = pd.Series(0.0, index=price_series.index)

    for i in range(n - horizon):
        window = price_series.iloc[i + 1 : i + 1 + horizon]
        vxn_window = vxn_series.iloc[i + 1 : i + 1 + horizon]

        if window.isna().any() or vxn_window.isna().any():
            y.iloc[i] = np.nan
            continue

        p_start = price_series.iloc[i]
        p_min = window.min()
        mdd = (p_start - p_min) / p_start

        if mdd > 0.10 or vxn_window.max() > 35:
            y.iloc[i] = 1

    y.iloc[-horizon:] = np.nan
    return y


def train_sidecar_model(X: pd.DataFrame, y: pd.Series):
    """
    Train the Sidecar Ridge Logistic model with Cross-Validation.
    """
    return train_baseline_model(X, y)
