import logging

import numpy as np
import pandas as pd
import yfinance as yf

from src.engine.baseline.data_loader import fetch_qqq_technical_signals, load_all_baseline_data
from src.engine.baseline.engine import (
    calculate_composites,
    predict_baseline_crisis_prob,
    train_baseline_model,
)
from src.engine.baseline.sidecar import (
    calculate_sidecar_composites,
    generate_sidecar_target,
    train_sidecar_model,
)
from src.engine.baseline.validation import generate_baseline_target

logger = logging.getLogger(__name__)


def validate_coefficients(model, feature_names: list) -> bool:
    """
    Audit coefficient directions against physical/economic reality.
    Redline: Stress must be POSITIVE (+Stress = +Prob)
    Redline: Growth must be NEGATIVE (+Growth = -Prob)
    """
    coefs = dict(zip(feature_names, model.coef_[0], strict=True))

    is_valid = True

    # 1. Stress Direction Check
    stress_key = [k for k in coefs if "stress" in k]
    if stress_key and coefs[stress_key[0]] < 0:
        logger.warning(
            f"!!! Audit Failed: {stress_key[0]} is {coefs[stress_key[0]]:.4f} (Expected +) !!! Details: {coefs}"
        )
        is_valid = False

    # 2. Growth Direction Check: +Growth -> -Prob (- Coeff)
    growth_key = [k for k in coefs if "growth" in k]
    if growth_key and coefs[growth_key[0]] > 0:
        logger.warning(
            f"!!! Audit Failed: {growth_key[0]} is {coefs[growth_key[0]]:.4f} (Expected -) !!! Details: {coefs}"
        )
        is_valid = False

    # 3. Liquidity Direction Check (Left Tail Risk Alignment): +Liquidity -> -Prob (- Coeff)
    liquidity_key = [k for k in coefs if "liquidity" in k]
    if liquidity_key and coefs[liquidity_key[0]] > 0:
        logger.warning(
            f"!!! Audit Failed: {liquidity_key[0]} is {coefs[liquidity_key[0]]:.4f} (Expected -) !!! Details: {coefs}"
        )
        is_valid = False

    return is_valid


def run_baseline_inference(price_history: pd.Series = None) -> dict:
    """
    Entry point for src/main.py to run dual baseline inference:
    1. V_Baseline (Mud Tractor) - SPY Target
    2. V_Sidecar (QQQ Native) - QQQ Target
    """
    logger.info("Mud Tractor: Initializing Dual Inference (Tractor + Sidecar)...")
    results = {
        "tractor": {"prob": 0.0, "status": "init"},
        "sidecar": {"prob": 0.0, "status": "init"},
    }

    try:
        # 1. Broad Macro Data (FRED) - Now PIT-safe aligned by effective_date
        data = load_all_baseline_data(timeout=10)
        metadata = data.attrs.get("metadata", {"degraded": []})

        if data.empty:
            logger.warning("Mud Tractor: No macro data returned from FRED.")
            return {"prob": 0.0, "status": "no_macro_data"}

        # 2. QQQ Technicals for Sidecar
        tech = fetch_qqq_technical_signals()
        if not tech.empty:
            tech = tech.loc[:, [column for column in tech.columns if column not in data.columns]]
            if not tech.empty:
                data = data.join(tech, how="left").ffill()

        # --- A. MUD TRACTOR (SPY) ---
        try:
            X_tractor = calculate_composites(data)
            # Fetch SPY for Tractor target if not passed
            spy = yf.download("SPY", start="1990-01-01", progress=False)
            spy.index = spy.index.tz_localize(None)
            spy_close = spy["Close"]
            if isinstance(spy_close, pd.DataFrame):
                spy_close = spy_close.iloc[:, 0]

            y_tractor = generate_baseline_target(spy_close, data["VIXCLS"])
            c_idx = X_tractor.index.intersection(y_tractor.index)
            if len(c_idx) > 100:
                # v14.8 Hardening: Enable constrained fallback for Mud Tractor
                bounds_t = {
                    "growth_composite": (None, 0.0),
                    "liquidity_composite": (None, 0.0),
                    "stress_composite": (0.0, None),
                }
                model_t = train_baseline_model(
                    X_tractor.loc[c_idx],
                    y_tractor.loc[c_idx],
                    audit_fn=validate_coefficients,
                    bounds=bounds_t,
                )

                tractor_window = X_tractor.iloc[-2:] if len(X_tractor) >= 2 else X_tractor.iloc[[-1]]
                tractor_probs = predict_baseline_crisis_prob(model_t, tractor_window)
                prob_t = float(tractor_probs.iloc[-1])
                prev_prob_t = float(tractor_probs.iloc[-2]) if len(tractor_probs) >= 2 else prob_t
                status_t = "success"
                if getattr(model_t, "constrained_flag", False):
                    status_t = "success_constrained_audit"
                if "BAMLH0A0HYM2" in metadata["degraded"] or "VIXCLS" in metadata["degraded"]:
                    status_t = "degraded_inputs"
                results["tractor"] = {
                    "prob": prob_t,
                    "prev_prob": prev_prob_t,
                    "delta_1d": prob_t - prev_prob_t,
                    "status": status_t,
                }
            else:
                results["tractor"]["status"] = "insufficient_sample"
        except Exception as e:
            logger.error(f"Mud Tractor inference failed: {e}")
            results["tractor"]["status"] = f"error: {str(e)}"

        # --- B. QQQ SIDECAR ---
        try:
            X_sidecar = calculate_sidecar_composites(data)
            # Use price_history (QQQ) or fetch
            if price_history is None or price_history.empty:
                qqq_close = data["qqq_close"] if "qqq_close" in data.columns else tech["qqq_close"]
            else:
                qqq_close = price_history
                if qqq_close.index.tz is not None:
                    qqq_close.index = qqq_close.index.tz_localize(None)

            if "^VXN" in data.columns and not data["^VXN"].isna().all():
                vxn = data["^VXN"]
            else:
                # VXN is missing - NO SYNTHETIC PROXY
                vxn = pd.Series(np.nan, index=data.index)
                metadata["degraded"].append("^VXN")

            y_sidecar = generate_sidecar_target(qqq_close, vxn)
            y_sidecar_valid = y_sidecar.dropna()
            c_idx_s = X_sidecar.index.intersection(y_sidecar_valid.index)

            if len(c_idx_s) > 100:
                # If VXN is missing, we must NOT train a valid sidecar model or we must mark it degraded
                model_s = train_sidecar_model(X_sidecar.loc[c_idx_s], y_sidecar.loc[c_idx_s])
                # Physical Audit
                if validate_coefficients(model_s, X_sidecar.columns.tolist()):
                    sidecar_window = X_sidecar.iloc[-2:] if len(X_sidecar) >= 2 else X_sidecar.iloc[[-1]]
                    sidecar_probs = predict_baseline_crisis_prob(model_s, sidecar_window)
                    prob_s = float(sidecar_probs.iloc[-1])
                    prev_prob_s = float(sidecar_probs.iloc[-2]) if len(sidecar_probs) >= 2 else prob_s
                    status_s = "success"
                else:
                    status_s = "audit_failed_overfitting"

                if "^VXN" in metadata["degraded"] or "^VXN" not in data.columns:
                    status_s = "degraded_missing_vxn"

                results["sidecar"] = {
                    "prob": prob_s if "prob_s" in locals() else 0.0,
                    "prev_prob": prev_prob_s if "prev_prob_s" in locals() else 0.0,
                    "delta_1d": (
                        (prob_s - prev_prob_s)
                        if "prob_s" in locals() and "prev_prob_s" in locals()
                        else 0.0
                    ),
                    "status": status_s,
                }
            else:
                status_s = "insufficient_sample"
                if "^VXN" in metadata["degraded"] or "^VXN" not in data.columns:
                    status_s = "degraded_missing_vxn"
                results["sidecar"]["status"] = status_s
        except Exception as e:
            logger.error(f"QQQ Sidecar inference failed: {e}")
            results["sidecar"]["status"] = f"error: {str(e)}"

        # Legacy compatibility for main.py (before I update main.py)
        results["prob"] = results["tractor"]["prob"]
        results["status"] = results["tractor"]["status"]

        return results

    except Exception as e:
        logger.error(f"Dual baseline inference failed: {e}")
        return {"prob": 0.0, "status": f"error: {str(e)}"}


def calculate_baseline_oos_series(
    data: pd.DataFrame,
    target_spy: pd.Series,
    target_qqq: pd.Series,
    start_date: str = "2018-01-01",
    horizon: int = 20,
) -> pd.DataFrame:
    """
    Batch helper for Full Panorama Backtest (v14.7).
    Runs a monthly walk-forward re-training to generate probabilities.
    Includes dimensionality compression and physical audit during re-training.
    """
    from src.engine.baseline.engine import (
        calculate_composites,
        predict_baseline_crisis_prob,
        train_baseline_model,
    )
    from src.engine.baseline.sidecar import calculate_sidecar_composites, train_sidecar_model

    logger.info(f"OOS Batch: Generating probabilities from {start_date}...")
    X_t = calculate_composites(data)
    X_s = calculate_sidecar_composites(data)
    target_qqq_valid = target_qqq.dropna()

    dates = data.index[data.index >= start_date].unique()
    res = pd.DataFrame(index=dates, columns=["tractor_prob", "sidecar_prob", "sidecar_valid"])
    res["sidecar_valid"] = False

    # Monthly Re-train Logic
    model_t, model_s = None, None

    for i, current_dt in enumerate(dates):
        # Re-train every 21 trading days (approx 1 month)
        if i % 21 == 0:
            # PIT-Audit (MAJOR): Purge temporal leakage by introducing a horizon gap.
            # If target at time t depends on data up to t + horizon,
            # then at inference time current_dt, we can only safely use targets
            # whose observation window is entirely in the PAST.
            # v14.8 Hardening: Use horizon + 3-day buffer for settlement/reporting safety.
            effective_cutoff = current_dt - pd.offsets.BDay(horizon + 3)

            train_idx_t = X_t.index[X_t.index <= effective_cutoff].intersection(target_spy.index)
            train_idx_s = X_s.index[X_s.index <= effective_cutoff].intersection(
                target_qqq_valid.index
            )

            # Minimum sample size requirement (inclusive threshold for first-window hydration)
            if len(train_idx_t) >= 250:
                bounds_t = {
                    "growth_composite": (None, 0.0),
                    "liquidity_composite": (None, 0.0),
                    "stress_composite": (0.0, None),
                }
                model_t = train_baseline_model(
                    X_t.loc[train_idx_t],
                    target_spy.loc[train_idx_t],
                    audit_fn=validate_coefficients,
                    bounds=bounds_t,
                )
            if len(train_idx_s) >= 250:
                model_s = train_sidecar_model(
                    X_s.loc[train_idx_s], target_qqq_valid.loc[train_idx_s]
                )

        # Predict T0 with the model trained on data UP TO T-1
        if model_t is not None:
            res.loc[current_dt, "tractor_prob"] = float(
                predict_baseline_crisis_prob(model_t, X_t.loc[[current_dt]]).iloc[0]
            )

        # Sidecar prediction only if model exists, the current feature is present,
        # and the forward target window is valid.
        if (
            model_s is not None
            and current_dt in target_qqq_valid.index
            and "^VXN" in data.columns
            and not pd.isna(data.loc[current_dt, "^VXN"])
        ):
            res.loc[current_dt, "sidecar_prob"] = float(
                predict_baseline_crisis_prob(model_s, X_s.loc[[current_dt]]).iloc[0]
            )
            res.loc[current_dt, "sidecar_valid"] = True
        else:
            res.loc[current_dt, "sidecar_prob"] = np.nan
            res.loc[current_dt, "sidecar_valid"] = False

    # Tractor prob should be ffilled as it is generally always available
    res["tractor_prob"] = res["tractor_prob"].ffill().fillna(0.0)
    # Sidecar prob should stay NaN if invalid for a given date

    return res
