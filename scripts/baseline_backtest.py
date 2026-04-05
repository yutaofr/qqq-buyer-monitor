from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from src.engine.baseline.data_loader import load_all_baseline_data
from src.engine.baseline.execution import calculate_baseline_oos_series
from src.engine.baseline.sidecar import generate_sidecar_target
from src.engine.baseline.validation import (
    generate_baseline_target,
    run_ac2_leakage_detection,
)

logger = logging.getLogger(__name__)

# --- Architectural Constants ---
OOS_START_DEFAULT = "2011-01-01"  # Shifted from 2010 to allow training hydration from regime start
PRICE_HISTORY_START = "1999-03-10"

def _get_close_series(df: pd.DataFrame) -> pd.Series:
    """Helper to extract a clean Close series from yfinance MultiIndex or Flat frame."""
    if df.empty:
        return pd.Series(dtype=float)

    # Handle MultiIndex columns (Ticker, Field)
    if isinstance(df.columns, pd.MultiIndex):
        # Prefer 'Close' from the first level if it exists
        if "Close" in df.columns.get_level_values(0):
            ser = df["Close"]
        else:
            ser = df.iloc[:, 0]
    else:
        # Flat columns
        close_col = next((c for c in ["Close", "Adj Close"] if c in df.columns), df.columns[0])
        ser = df[close_col]

    if isinstance(ser, pd.DataFrame):
        ser = ser.iloc[:, 0]

    ser.index = pd.to_datetime(ser.index).tz_localize(None)
    return ser

def collect_panorama_oos_artifacts(
    oos_start: str = OOS_START_DEFAULT,
    timeout: int = 15
) -> dict[str, Any]:
    """
    Primary architectural bridge for v14 Panorama Matrix.
    Realizes the walk-forward OOS baseline series (Tractor + Sidecar)
    with strict PIT integrity and fail-closed logic.
    """
    logger.info(f"Collecting Panorama OOS artifacts starting from {oos_start}...")

    # 1. Load PIT-aligned Macro Data (FRED + YFinance Sensors)
    data = load_all_baseline_data(timeout=timeout)
    if data.empty:
        raise ValueError("Baseline macro data is empty. Check FRED/YFinance connectivity.")

    metadata = data.attrs.get("metadata", {})
    logger.info(f"Macro Data Loaded. Realtime Vintage: {metadata.get('vintage_mode', 'UNKNOWN')}")
    if metadata.get("degraded"):
        logger.warning(f"Degraded Sensors Detected: {metadata['degraded']}")

    # 2. Fetch Price History for Target Generation
    # We need SPY for the Tractor (Mud Tractor) and QQQ for the Sidecar
    logger.info("Fetching SPY/QQQ price history for target generation...")
    spy_raw = yf.download("SPY", start=PRICE_HISTORY_START, progress=False)
    qqq_raw = yf.download("QQQ", start=PRICE_HISTORY_START, progress=False)

    spy_close = _get_close_series(spy_raw)
    qqq_close = _get_close_series(qqq_raw)

    if spy_close.empty or qqq_close.empty:
        raise ValueError("Price history download failed.")

    # 3. Generate Crisis Targets (Non-Overlapping, Forward-Looking)
    # Tractor: SPY MDD > 8% or VIX > 30 in next 20 days
    # Sidecar: QQQ MDD > 10% or VXN > 35 in next 20 days
    vix = data["VIXCLS"]
    vxn = data.get("^VXN", pd.Series(np.nan, index=data.index))

    logger.info("Generating PIT targets...")
    target_spy = generate_baseline_target(spy_close, vix)
    target_qqq = generate_sidecar_target(qqq_close, vxn)

    # 4. Execute Multi-decadal Walk-Forward OOS
    # This runs monthly re-training windows to simulate live production reality.
    logger.info("Starting Walk-Forward OOS Execution...")
    oos_results = calculate_baseline_oos_series(
        data,
        target_spy,
        target_qqq,
        start_date=oos_start
    )

    # 5. Result Integrity Audit
    nan_count = oos_results["sidecar_prob"].isna().sum()
    if nan_count > 0:
        logger.warning(f"OOS Sidecar Integrity: {nan_count} gaps identified (Fail-Closed).")

    # 6. AC-2 Leakage Detection Audit
    logger.info("Executing AC-2 Leakage Detection (Synthetic Audit)...")
    leak_results = run_ac2_leakage_detection()

    return {
        "oos_results": oos_results,
        "metadata": metadata,
        "oos_start": oos_start,
        "data_count": len(data),
        "target_spy": target_spy,
        "target_qqq": target_qqq,
        "leak_results": leak_results,
    }

def main():
    """Standalone execution logic for v14 hardening diagnostics."""
    from sklearn.metrics import roc_auc_score
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        artifacts = collect_panorama_oos_artifacts()
        results = artifacts["oos_results"]

        print("\n--- v14 Baseline OOS Results ---")
        print(f"OOS Start:  {artifacts['oos_start']}")
        print(f"OOS End:    {results.index[-1].date()}")
        print(f"Total Days: {len(results)}")
        print(f"Tractor Active Share: {(results['tractor_prob'] > 0.5).mean():.1%}")

        valid_sidecar = results[results["sidecar_valid"]]
        if not valid_sidecar.empty:
            print(f"Sidecar Active Share (when valid): {(valid_sidecar['sidecar_prob'] > 0.5).mean():.1%}")
            print(f"Sidecar Data Coverage: {len(valid_sidecar)/len(results):.1%}")
        else:
            print("Sidecar Data Coverage: 0.0% (CRITICAL DEGRADATION)")

        # 7. Real-world Performance Audit (OOS AUC)
        print("\n--- Real-world OOS Performance Audit ---")
        y_spy = artifacts["target_spy"]
        y_qqq = artifacts["target_qqq"]

        # Tractor AUC
        t_idx = results.index.intersection(y_spy.dropna().index)
        t_auc = roc_auc_score(y_spy.loc[t_idx], results.loc[t_idx, "tractor_prob"])
        print(f"Tractor OOS AUC: {t_auc:.4f}")

        # Sidecar AUC
        s_idx = valid_sidecar.index.intersection(y_qqq.dropna().index)
        if not s_idx.empty:
            s_auc = roc_auc_score(y_qqq.loc[s_idx], results.loc[s_idx, "sidecar_prob"])
            print(f"Sidecar OOS AUC: {s_auc:.4f} (Goal: 0.60+)")
        else:
            print("Sidecar OOS AUC: N/A (Insufficient valid sample)")

        print("\n--- AC-2 Pipeline Integrity Audit (Synthetic) ---")
        leak = artifacts["leak_results"]
        print(f"PIT-Safe AUC (Synthetic): {leak['pit_safe_auc']:.4f}")
        print(f"Leaky AUC (Synthetic):    {leak['leaky_auc']:.4f}")

        # Integrity Pass: The detector MUST distinguish between PIT-safe and Leaky handlers
        integrity_passed = leak["leakage_detected"] and (leak["pit_safe_auc"] < 0.65)
        verdict = "PASSED" if integrity_passed else "FAILED (INTEGRITY BREACH)"
        print(f"Pipeline Audit: {verdict}")

        if not integrity_passed:
            logger.error("AC-2 Pipeline Integrity Audit FAILED. Blocking artifact generation.")
            exit(1)

        # Export for inspection
        os.makedirs("artifacts/v14_panorama", exist_ok=True)
        results.to_csv("artifacts/v14_panorama/baseline_oos_trace.csv")
        logger.info("Baseline OOS trace saved to artifacts/v14_panorama/baseline_oos_trace.csv")

    except Exception as e:
        logger.error(f"Backtest execution failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
