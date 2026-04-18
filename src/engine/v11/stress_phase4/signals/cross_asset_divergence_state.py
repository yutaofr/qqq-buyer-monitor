from __future__ import annotations

import pandas as pd


def _col(frame: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(frame[name], errors="coerce").fillna(0.0) if name in frame else pd.Series(0.0, index=frame.index)


def build_cross_asset_divergence_state(frame: pd.DataFrame) -> pd.DataFrame:
    """Cross-asset divergence placeholder using available beta and regime disagreement proxies."""

    expected_beta = _col(frame, "expected_target_beta")
    raw_beta = _col(frame, "raw_target_beta")
    beta_dislocation = ((expected_beta - raw_beta).abs() / 1.2).clip(0.0, 1.0)
    growth_defensive_divergence = _col(frame, "benchmark_conflict_score").clip(0.0, 1.0)
    rates_equity_proxy = ((-_col(frame, "benchmark_ma_gap")) / 0.18).clip(0.0, 1.0)
    divergence_state = (0.36 * beta_dislocation + 0.34 * growth_defensive_divergence + 0.30 * rates_equity_proxy).clip(0.0, 1.0)
    return pd.DataFrame(
        {
            "cross_asset_divergence": divergence_state,
            "beta_dislocation": beta_dislocation,
            "growth_defensive_divergence": growth_defensive_divergence,
            "rates_equity_divergence_proxy": rates_equity_proxy,
        },
        index=frame.index,
    )
