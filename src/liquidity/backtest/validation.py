"""Independent validation anchors for FPR computation.

SRD v1.2 Section 7.5: Treasury Settlement Fails (T-10) and SOFR Volume
(T-1) are physically independent indicators used to label stress periods.

ARCHITECTURE IRON LAW: This module MUST NOT import anything from
src.liquidity.signal/ or src.liquidity.engine/. Validation data is
NOT part of the signal path. Mixing them would create a self-referential
loop that invalidates the independence of the FPR metric.

Pure functions — no state, no I/O, no BOCPD dependency.
"""

from __future__ import annotations

import pandas as pd


def label_stress_periods(
    treas_fails: pd.Series,
    sofr_volume: pd.Series,
    fails_threshold_pct: float = 0.90,
    sofr_threshold_pct: float = 0.95,
) -> pd.DataFrame:
    """Label each trading day as stress or calm based on independent anchors.

    Args:
        treas_fails:        Daily Treasury Settlement Fails (PiT-aligned,
                            already offset by T-10).
        sofr_volume:        Daily SOFR Volume (PiT-aligned, offset T-1).
        fails_threshold_pct: Percentile threshold for fails. Default 90th.
        sofr_threshold_pct:  Percentile threshold for SOFR vol. Default 95th.

    Returns:
        DataFrame with columns:
            treas_fails_elevated — bool
            sofr_vol_spike       — bool
            is_stress_period     — bool (OR of above)
    """
    # Expanding percentile: use all history up to t (no lookahead)
    fails_q = treas_fails.expanding().quantile(fails_threshold_pct)
    sofr_q  = sofr_volume.expanding().quantile(sofr_threshold_pct)

    treas_elevated = treas_fails > fails_q
    sofr_spike     = sofr_volume > sofr_q

    return pd.DataFrame(
        {
            "treas_fails_elevated": treas_elevated,
            "sofr_vol_spike":       sofr_spike,
            "is_stress_period":     treas_elevated | sofr_spike,
        },
        index=treas_fails.index,
    )


def compute_fpr(
    p_cp_series: pd.Series,
    stress_labels: pd.DataFrame,
    threshold: float = 0.30,
) -> dict:
    """Compute false positive rate against independent stress labels.

    FPR = (false alarms in calm period) / (total calm days)

    Args:
        p_cp_series:   Series of p_cp values from BOCPD, same index as labels.
        stress_labels: DataFrame from label_stress_periods().
        threshold:     p_cp threshold for system "alarm". Default 0.30.

    Returns:
        dict with keys:
            fpr             — false positive rate (float in [0, 1])
            calm_days       — number of calm days
            false_alarms    — number of false alarms in calm period
            stress_days     — number of stress days
            true_alarms     — number of true alarms in stress period
            detection_rate  — true alarms / stress days (recall)
    """
    # Align indices
    common = p_cp_series.index.intersection(stress_labels.index)
    p_cp   = p_cp_series.loc[common]
    labels = stress_labels.loc[common]

    is_stress = labels["is_stress_period"]
    alarm     = p_cp > threshold

    calm_days     = int((~is_stress).sum())
    stress_days   = int(is_stress.sum())
    false_alarms  = int((alarm & ~is_stress).sum())
    true_alarms   = int((alarm & is_stress).sum())

    fpr = float(false_alarms / calm_days) if calm_days > 0 else 0.0
    detection_rate = float(true_alarms / stress_days) if stress_days > 0 else 0.0

    return {
        "fpr":             fpr,
        "calm_days":       calm_days,
        "false_alarms":    false_alarms,
        "stress_days":     stress_days,
        "true_alarms":     true_alarms,
        "detection_rate":  detection_rate,
    }
