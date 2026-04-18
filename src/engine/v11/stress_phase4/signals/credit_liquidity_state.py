from __future__ import annotations

import pandas as pd


def _col(frame: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(frame[name], errors="coerce").fillna(0.0) if name in frame else pd.Series(0.0, index=frame.index)


def build_credit_liquidity_state(frame: pd.DataFrame) -> pd.DataFrame:
    """Credit/liquidity stress proxy from available macro anomaly and forensic stress telemetry."""

    credit_spread_proxy = (0.52 * _col(frame, "forensic_bust_penalty") + 0.48 * _col(frame, "S_macro_anom")).clip(0.0, 1.0)
    liquidity_withdrawal = (0.58 * _col(frame, "forensic_stress_score") + 0.42 * _col(frame, "forensic_mid_cycle_penalty")).clip(0.0, 1.0)
    acceleration = credit_spread_proxy.diff().fillna(0.0).clip(lower=0.0).rolling(5, min_periods=1).mean().clip(0.0, 1.0)
    credit_liquidity_stress = (0.44 * credit_spread_proxy + 0.38 * liquidity_withdrawal + 0.18 * acceleration).clip(0.0, 1.0)
    return pd.DataFrame(
        {
            "credit_liquidity_stress": credit_liquidity_stress,
            "credit_spread_proxy": credit_spread_proxy,
            "liquidity_withdrawal": liquidity_withdrawal,
            "credit_stress_acceleration": acceleration,
        },
        index=frame.index,
    )
