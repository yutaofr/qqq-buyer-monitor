#!/usr/bin/env python3
"""v11 Research: ERP Momentum vs Real Yield vs Baseline.
Comprehensive evaluation of Accuracy and Brier Score using Parallel KDE Inference.
"""
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score
from sklearn.neighbors import KernelDensity

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def calculate_features(df, factor_name, window=252):
    """Calculate Water Level and Derivative for a factor."""
    # Water Level: Percentile Rank
    df[f"{factor_name}_level"] = df[factor_name].rolling(window, min_periods=60).rank(pct=True)

    # Derivative: 10-day Change Z-Score
    diff = df[factor_name].diff(10)
    rolling_mean = diff.rolling(window, min_periods=60).mean()
    rolling_std = diff.rolling(window, min_periods=60).std().replace(0, np.nan)
    df[f"{factor_name}_deriv"] = (diff - rolling_mean) / rolling_std
    return df

def evaluate_probabilistic_performance(args):
    """Worker function: Evaluates Accuracy and Brier Score for a feature set."""
    df_eval, features, target_col = args

    # Drop rows with NaNs in features or target
    clean_df = df_eval[features + [target_col]].dropna()
    if len(clean_df) < 1000:
        return None

    # Split into Train (Historical Calibration) and Test (Out-of-sample simulation)
    # We use a temporal split to simulate production reality
    split_idx = int(len(clean_df) * 0.7)
    train_df = clean_df.iloc[:split_idx]
    test_df = clean_df.iloc[split_idx:]

    regimes = train_df[target_col].unique()
    kde_models = {}
    priors = train_df[target_col].value_counts(normalize=True).to_dict()

    # 1. PCA Reduction
    pca = PCA(n_components=min(3, len(features)))
    X_train_pca = pca.fit_transform(train_df[features])
    X_test_pca = pca.transform(test_df[features])

    # 2. KDE Likelihood Calibration
    for r in regimes:
        r_mask = train_df[target_col] == r
        r_data = X_train_pca[r_mask]
        if len(r_data) < 20:
            continue

        kde = KernelDensity(bandwidth="scott").fit(r_data)
        kde_models[r] = kde

    # 3. Bayesian Inference on Test Set
    results = []
    y_true_binary = [] # For Brier Score (one-vs-rest)
    y_prob_top1 = []   # Probability of the true regime

    for i in range(len(X_test_pca)):
        obs = X_test_pca[i:i+1]
        log_probs = {}
        for r, kde in kde_models.items():
            log_probs[r] = kde.score_samples(obs)[0] + np.log(priors.get(r, 1e-6))

        # Softmax to get probabilities
        max_log = max(log_probs.values())
        probs = {r: np.exp(lp - max_log) for r, lp in log_probs.items()}
        sum_p = sum(probs.values())
        probs = {r: p / sum_p for r, p in probs.items()}

        actual_regime = test_df.iloc[i][target_col]
        pred_regime = max(probs, key=probs.get)

        results.append(pred_regime)
        y_prob_top1.append(probs.get(actual_regime, 0.0))
        # For multi-class Brier, we simplify to mean squared error across all classes
        # Sum((p_i - y_i)^2)
        brier_sum = 0
        for r in regimes:
            y_i = 1.0 if r == actual_regime else 0.0
            p_i = probs.get(r, 0.0)
            brier_sum += (p_i - y_i)**2
        y_true_binary.append(brier_sum)

    accuracy = accuracy_score(test_df[target_col], results)
    mean_brier = np.mean(y_true_binary) # Multi-class Brier Score (lower is better)

    return {
        "features": features,
        "accuracy": accuracy,
        "brier_score": mean_brier,
        "pca_var": sum(pca.explained_variance_ratio_),
        "samples": len(test_df)
    }

def run_research():
    # 1. Load data
    data_path = Path("data/v11_poc_phase1_results.csv")
    macro_path = Path("data/macro_historical_dump.csv")
    if not data_path.exists() or not macro_path.exists():
        logger.error("Data missing. Ensure Phase 1 and Macro dump exist.")
        return

    df = pd.read_csv(data_path)
    macro_df = pd.read_csv(macro_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    macro_df["observation_date"] = pd.to_datetime(macro_df["observation_date"])

    # 2. Merge and Calculate Momentum for Class A
    available = [c for c in ["real_yield_10y_pct", "erp_pct", "erp", "nfci_raw"] if c in macro_df.columns]
    df = pd.merge(df, macro_df[["observation_date"] + available], on="observation_date", how="left", suffixes=("", "_macro"))
    df = df.sort_values("observation_date")

    # Standardize column names
    if "erp_pct_macro" in df.columns:
        df["erp_pct"] = df["erp_pct_macro"]
    if "erp" in df.columns and "erp_pct" not in df.columns:
        df["erp_pct"] = df["erp"]
    if "real_yield_10y_pct_macro" in df.columns:
        df["real_yield_10y_pct"] = df["real_yield_10y_pct_macro"]

    # Calculate Extended Class A features
    valid_factors = []
    for factor in ["real_yield_10y_pct", "erp_pct"]:
        if factor in df.columns and df[factor].notna().sum() > 500:
            df = calculate_features(df, factor)
            valid_factors.append(factor)
            logger.info(f"Calculated level/deriv for {factor}")

    # 3. Parallel Backtest Comparison
    test_suites = [
        ["vix_pct", "dd_pct", "breadth_pct"], # Baseline
    ]
    if "erp_pct_level" in df.columns:
        test_suites.append(["vix_pct", "dd_pct", "breadth_pct", "erp_pct_level"])
        test_suites.append(["vix_pct", "dd_pct", "breadth_pct", "erp_pct_deriv"])

    if "real_yield_10y_pct_deriv" in df.columns:
        test_suites.append(["vix_pct", "dd_pct", "breadth_pct", "real_yield_10y_pct_deriv"])

    if "erp_pct_deriv" in df.columns and "real_yield_10y_pct_deriv" in df.columns:
        test_suites.append(["vix_pct", "dd_pct", "breadth_pct", "erp_pct_deriv", "real_yield_10y_pct_deriv"])

    logger.info(f"Starting complete probabilistic comparison of {len(test_suites)} feature sets...")

    with ProcessPoolExecutor() as executor:
        tasks = [(df, suite, "regime") for suite in test_suites]
        results = list(executor.map(evaluate_probabilistic_performance, tasks))

    # 4. Final Comparison Report
    print("\n" + "="*80)
    print(f"{'Feature Set':<60} | {'Acc':<6} | {'Brier':<6} | {'PCA':<6}")
    print("-" * 80)
    for res in results:
        if res:
            feat_str = "+".join([f.replace("_pct", "").replace("_level", "").replace("_deriv", " (M)") for f in res['features']])
            print(f"{feat_str:<60} | {res['accuracy']:.2%} | {res['brier_score']:.4f} | {res['pca_var']:.4f}")
    print("="*80)
    print("Note: Brier Score is Multi-class (Sum of Squares). Lower is better.")

if __name__ == "__main__":
    run_research()
