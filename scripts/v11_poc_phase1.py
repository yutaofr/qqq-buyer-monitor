#!/usr/bin/env python3
"""v11 POC Phase 1: Feature Engineering & Likelihood Calibration."""
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.neighbors import KernelDensity
from sklearn.model_selection import GridSearchCV
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_phase1():
    # 1. Load Data
    macro_path = "data/macro_historical_dump.csv"
    price_vix_path = "data/v11_price_vix_history.csv"
    
    if not Path(macro_path).exists() or not Path(price_vix_path).exists():
        logger.error("Required data files missing. Run build_historical_macro_dataset.py and fetch_v11_historical_data.py first.")
        return

    macro_df = pd.read_csv(macro_path)
    price_df = pd.read_csv(price_vix_path)
    
    macro_df["observation_date"] = pd.to_datetime(macro_df["observation_date"])
    price_df["observation_date"] = pd.to_datetime(price_df["observation_date"])
    
    # Merge on observation_date
    df = pd.merge(macro_df, price_df, on="observation_date", how="inner")
    df = df.sort_values("observation_date")
    
    logger.info(f"Merged dataset: {len(df)} rows from {df['observation_date'].min()} to {df['observation_date'].max()}")

    # 2. Calculate Percentile Ranks (20yr Rolling)
    window = 252 * 20
    logger.info(f"Calculating rolling {window}d percentiles...")
    
    # Labeling Signals (Macro)
    df["spread_pct"] = df["credit_spread_bps"].rolling(window, min_periods=252).rank(pct=True)
    df["erp_pct"] = df["erp_pct"].rolling(window, min_periods=252).rank(pct=True)
    df["spread_accel"] = df["credit_acceleration_pct_10d"] # Already a rate
    
    # Evidence Signals (Price/Tactical)
    df["vix_pct"] = df["vix"].rolling(window, min_periods=252).rank(pct=True)
    df["dd_pct"] = df["drawdown_pct"].rolling(window, min_periods=252).rank(pct=True)
    # Breadth Proxy: pct_change of relative strength (already done in fetch script)
    df["breadth_pct"] = df["breadth_proxy"].rolling(window, min_periods=252).rank(pct=True)
    
    df = df.dropna(subset=["spread_pct", "vix_pct", "dd_pct"]).copy()
    logger.info(f"Usable rows after percentile calculation: {len(df)}")

    # 3. Labeling Priority Protocol
    logger.info("Applying Labeling Priority Protocol...")
    
    def label_regime(row):
        # 1. BUST: Spread_pct >= 0.90 (Priority 1)
        if row["spread_pct"] >= 0.90:
            return "BUST"
        # 2. CAPITULATION: Spread_pct >= 0.80 AND Accel <= 0 AND Liquidity_ROC > 0
        if row["spread_pct"] >= 0.80 and row["credit_acceleration_pct_10d"] <= 0 and row["liquidity_roc_pct_4w"] > 0:
            return "CAPITULATION"
        # 3. LATE_CYCLE: ERP_pct <= 0.15 AND Spread_pct > 0.65
        if row["erp_pct"] <= 0.15 and row["spread_pct"] > 0.65:
            return "LATE_CYCLE"
        # 4. RECOVERY: Spread_20d_delta < -30bps AND Liquidity_ROC > 0
        # (Need 20d delta of bps)
        return "MID_CYCLE"

    # Pre-calculate spread_20d_delta for Recovery
    df["spread_20d_delta"] = df["credit_spread_bps"].diff(20)
    
    def label_regime_final(row):
        if row["spread_pct"] >= 0.90:
            return "BUST"
        if row["spread_pct"] >= 0.80 and row["credit_acceleration_pct_10d"] <= 0 and row["liquidity_roc_pct_4w"] > 0:
            return "CAPITULATION"
        if row["erp_pct"] <= 0.15 and row["spread_pct"] > 0.65:
            return "LATE_CYCLE"
        if row["spread_20d_delta"] < -30 and row["liquidity_roc_pct_4w"] > 0:
            return "RECOVERY"
        return "MID_CYCLE"

    df["regime"] = df.apply(label_regime_final, axis=1)
    logger.info(f"Regime counts:\n{df['regime'].value_counts()}")

    # 4. Likelihood via Percentile-PCA & KDE
    logger.info("Performing PCA and KDE Likelihood Calibration...")
    
    # Evidence Vector: [vix_pct, dd_pct, breadth_pct]
    evidence_cols = ["vix_pct", "dd_pct", "breadth_pct"]
    df = df.dropna(subset=evidence_cols).copy()
    X = df[evidence_cols].values
    
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)
    df["pca1"] = X_pca[:, 0]
    df["pca2"] = X_pca[:, 1]
    
    logger.info(f"PCA Variance Explained: {pca.explained_variance_ratio_}")

    # Build KDE for each Regime
    regimes = df["regime"].unique()
    kde_models = {}
    
    for r in regimes:
        r_data = df[df["regime"] == r][["pca1", "pca2"]].values
        if len(r_data) < 5:
            logger.warning(f"Insufficient data for regime {r}: {len(r_data)} rows. Skipping KDE.")
            continue
            
        # Optimize bandwidth via GridSearch
        params = {"bandwidth": np.logspace(-2, 0, 20)}
        grid = GridSearchCV(KernelDensity(), params)
        grid.fit(r_data)
        kde = grid.best_estimator_
        kde_models[r] = kde
        logger.info(f"KDE for {r}: bandwidth={kde.bandwidth:.4f}, samples={len(r_data)}")

    # 5. Save Results
    output_path = "data/v11_poc_phase1_results.csv"
    df.to_csv(output_path, index=False)
    logger.info(f"POC Phase 1 results saved to {output_path}")

if __name__ == "__main__":
    run_phase1()
