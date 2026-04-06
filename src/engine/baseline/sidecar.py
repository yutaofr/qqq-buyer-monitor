import logging

import numpy as np
import pandas as pd

from src.engine.baseline.engine import calculate_composites, rolling_zscore, train_baseline_model
from src.engine.baseline.targets import align_target_inputs

logger = logging.getLogger(__name__)


def calculate_sidecar_composites(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 5-axis composites for the QQQ Sidecar.
    1. growth_composite (Macro Growth)
    2. liquidity_composite (Macro Liquidity)
    3. stress_composite_extreme (Max(VIX, VXN, Spread) Z-scores)
    4. vxn_acceleration (Non-linear volatility pressure)
    5. qqq_spy_relative_heat (Sector overcrowding pressure)
    """
    # 1. Base Composites (Growth, Liquidity)
    base = calculate_composites(data)

    # 2. Stress Composite Extreme (Max Retention)
    stress_cols = []
    for col in ["BAMLH0A0HYM2", "VIXCLS", "^VXN"]:
        if col in data.columns:
            stress_cols.append(rolling_zscore(data[col]))

    if stress_cols:
        stress_extreme = pd.concat(stress_cols, axis=1).max(axis=1)
    else:
        stress_extreme = base["stress_composite"]

    # 3. VXN Acceleration Refined (3-day Jump)
    # V_accel = RollingZScore(VXN - VXN.shift(3), 252)
    vxn_accel = pd.Series(np.nan, index=data.index)
    if "^VXN" in data.columns:
        jump = data["^VXN"] - data["^VXN"].shift(3)
        vxn_accel = rolling_zscore(jump, window=252)

    # 4. QQQ/SPY Relative Heat (adapted for Weakness/Reversal)
    # RS = QQQ / SPY, Z_RS = RollingZScore(log(RS), 252)
    # Feature = Min(0, Z_RS)
    rel_heat_weakness = pd.Series(np.nan, index=data.index)
    if "SPY" in data.columns and "QQQ" in data.columns:
        rs = data["QQQ"] / data["SPY"]
        z_rs = rolling_zscore(np.log(rs), window=252)
        rel_heat_weakness = z_rs.clip(upper=0.0)

    return pd.DataFrame(
        {
            "growth_composite": base["growth_composite"],
            "liquidity_composite": base["liquidity_composite"],
            "stress_composite_extreme": stress_extreme,
            "vxn_acceleration": vxn_accel,
            "qqq_spy_relative_weakness": rel_heat_weakness,
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


def audit_sidecar_coeffs(model, feature_names: list[str]) -> bool:
    """
    Check if the trained model coefficients satisfy physical intuition rules.
    Rules:
    - growth: <= 0
    - stress: >= 0
    - liquidity: <= 0
    - vxn_acceleration: >= 0
    - relative_weakness: <= 0
    """
    coeffs = model.coef_[0]
    rules = {
        "growth_composite": lambda x: x <= 0,
        "stress_composite_extreme": lambda x: x >= 0,
        "liquidity_composite": lambda x: x <= 0,
        "vxn_acceleration": lambda x: x >= 0,
        "qqq_spy_relative_weakness": lambda x: x <= 0,
    }

    for i, name in enumerate(feature_names):
        if name in rules:
            rule = rules[name]
            val = coeffs[i]
            if not rule(val):
                logger.debug(f"!!! Audit Failed: {name} is {val:.4f} (Expected {rule}) !!!")
                return False
    return True


def train_sidecar_model(X: pd.DataFrame, y: pd.Series):
    """
    Train the Sidecar Ridge Logistic model with Cross-Validation and Physical Audit.
    Leverages the centralized engine fallback to ConstrainedLogisticRegression.
    """
    # Define bounds for each feature
    bounds = {
        "growth_composite": (None, 0.0),
        "stress_composite_extreme": (0.0, None),
        "liquidity_composite": (None, 0.0),
        "vxn_acceleration": (0.0, None),
        "qqq_spy_relative_weakness": (None, 0.0),
    }

    return train_baseline_model(X, y, audit_fn=audit_sidecar_coeffs, bounds=bounds)
