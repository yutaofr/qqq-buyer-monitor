"""Locked factor-domain feature builder for the recovery HMM research track."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "hy_ig_spread",
    "curve_10y_2y",
    "chicago_fci",
    "real_yield_10y",
    "ism_new_orders",
    "ism_inventories",
    "vix_3m_1m_ratio",
    "qqq_skew_20d_mean",
}


def build_feature_space(raw_frame: pd.DataFrame) -> pd.DataFrame:
    """Build the sealed Level/Velocity/Sentiment factor frame for shadow research."""
    frame = raw_frame.copy()
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError("Missing required recovery HMM columns: " + ", ".join(missing))

    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.sort_index()

    out = pd.DataFrame(index=frame.index)
    out["L1_hy_ig_spread"] = pd.to_numeric(frame["hy_ig_spread"], errors="coerce")
    out["L2_curve_10y_2y"] = pd.to_numeric(frame["curve_10y_2y"], errors="coerce")
    out["L3_chicago_fci"] = pd.to_numeric(frame["chicago_fci"], errors="coerce")
    out["V1_spread_compression_velocity"] = (
        pd.to_numeric(frame["hy_ig_spread"], errors="coerce").diff(13) * -1.0
    )
    out["V2_real_yield_velocity"] = pd.to_numeric(frame["real_yield_10y"], errors="coerce").diff(13)
    out["V3_orders_inventory_gap"] = pd.to_numeric(
        frame["ism_new_orders"], errors="coerce"
    ) - pd.to_numeric(frame["ism_inventories"], errors="coerce")
    out["S1_vix_term_ratio"] = pd.to_numeric(frame["vix_3m_1m_ratio"], errors="coerce")
    out["S2_qqq_skew_mean"] = pd.to_numeric(frame["qqq_skew_20d_mean"], errors="coerce")
    return out.dropna()
