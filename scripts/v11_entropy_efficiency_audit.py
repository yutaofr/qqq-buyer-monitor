#!/usr/bin/env python3
"""v11 Research: Full-Factor Entropy Efficiency Audit.
Evaluates how different factor combinations affect Bayesian Entropy and Information Gain.
"""
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.neighbors import KernelDensity
from scipy.stats import entropy

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_signal(df, factor, window):
    """Normalized optimal horizon signal."""
    # Custom directions based on registry findings
    low_is_stress = ["erp", "liquidity", "yield", "pe", "breadth", "vix3m"]
    direction = -1.0 if any(x in factor.lower() for x in low_is_stress) else 1.0
    smoothed = df[factor].ewm(span=window).mean()
    diff = direction * smoothed.diff(window)
    return (diff - diff.rolling(252).mean()) / diff.rolling(252).std()

def evaluate_entropy_performance(args):
    """Inference engine simulation to measure resulting entropy."""
    df_eval, feature_bundle, target_col = args
    
    # 1. Prepare Features
    X = df_eval[feature_bundle].dropna()
    if len(X) < 1000: return None
    
    # Temporal Split
    split_idx = int(len(X) * 0.7)
    train_df = X.iloc[:split_idx]
    test_df = X.iloc[split_idx:]
    y_train = df_eval.loc[train_df.index, target_col]
    y_test = df_eval.loc[test_df.index, target_col]
    
    # 2. PCA & KDE (v11 Core Logic)
    pca = PCA(n_components=min(3, len(feature_bundle)))
    X_train_pca = pca.fit_transform(train_df)
    X_test_pca = pca.transform(test_df)
    
    regimes = y_train.unique()
    kde_models = {r: KernelDensity(bandwidth='scott').fit(X_train_pca[y_train == r]) for r in regimes if (y_train == r).sum() > 20}
    priors = y_train.value_counts(normalize=True).to_dict()
    
    # 3. Predict & Measure Entropy
    entropies = []
    correct_p = []
    
    for i in range(len(X_test_pca)):
        obs = X_test_pca[i:i+1]
        log_probs = {}
        for r, kde in kde_models.items():
            log_probs[r] = kde.score_samples(obs)[0] + np.log(priors.get(r, 1e-6))
        
        # Softmax
        max_log = max(log_probs.values())
        probs = np.exp([lp - max_log for lp in log_probs.values()])
        probs /= probs.sum()
        
        # Calculate Shannon Entropy
        h = entropy(probs, base=2)
        entropies.append(h)
        
        # Probability of actual regime
        actual_r = y_test.iloc[i]
        r_idx = list(kde_models.keys()).index(actual_r) if actual_r in kde_models else -1
        correct_p.append(probs[r_idx] if r_idx != -1 else 0.0)

    # Metrics
    mean_h = np.mean(entropies)
    # Entropy Spike Potential: Ratio of entropy during stress vs non-stress
    stress_mask = y_test.isin(["BUST", "LATE_CYCLE"]).values
    h_stress = np.mean(np.array(entropies)[stress_mask]) if any(stress_mask) else 0
    h_normal = np.mean(np.array(entropies)[~stress_mask]) if not all(stress_mask) else 0
    
    return {
        "bundle": feature_bundle,
        "mean_entropy": mean_h,
        "entropy_discrimination": h_stress / h_normal if h_normal > 0 else 0,
        "confidence_score": np.mean(correct_p),
        "pca_variance": sum(pca.explained_variance_ratio_)
    }

def run_entropy_audit():
    # 1. Load Everything
    data_path = Path("data/v11_poc_phase1_results.csv")
    macro_path = Path("data/macro_historical_dump.csv")
    df = pd.read_csv(data_path)
    macro_df = pd.read_csv(macro_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    macro_df["observation_date"] = pd.to_datetime(macro_df["observation_date"])
    
    # 2. Re-calculate signals using verified registry windows
    registry = {
        "credit_spread_bps": 21,
        "credit_acceleration_pct_10d": 126,
        "breadth_proxy": 252,
        "vix": 63,
        "net_liquidity_usd_bn": 252,
        "forward_pe": 252,
        "erp_pct": 63,
        "real_yield_10y_pct": 252
    }
    
    df_signals = pd.DataFrame({"observation_date": df["observation_date"], "regime": df["regime"]})
    for factor, window in registry.items():
        source = df if factor in df.columns else macro_df
        if factor in source.columns:
            temp_df = source[["observation_date", factor]].copy()
            temp_df = temp_df.sort_values("observation_date")
            df_signals[f"{factor}_sig"] = get_signal(temp_df, factor, window)
            
    df_signals = df_signals.sort_values("observation_date").ffill().dropna()
    
    # 3. Define Test Bundles
    bundles = [
        ["credit_spread_bps_sig", "vix_sig", "breadth_proxy_sig"], # Baseline
        ["credit_spread_bps_sig", "credit_acceleration_pct_10d_sig", "vix_sig"], # Credit Heavy
        ["credit_spread_bps_sig", "vix_sig", "erp_pct_sig", "forward_pe_sig"], # Valuation Heavy
        ["credit_spread_bps_sig", "vix_sig", "breadth_proxy_sig", "real_yield_10y_pct_sig"], # The 11.5 Candidate
        # The "Everything" Bundle - Testing for Information Overload
        list(df_signals.columns[2:]) 
    ]
    
    logger.info(f"Auditing entropy efficiency for {len(bundles)} feature bundles...")
    
    with ProcessPoolExecutor() as executor:
        tasks = [(df_signals, b, "regime") for b in bundles]
        results = list(executor.map(evaluate_entropy_performance, tasks))
        
    # 4. Final Report
    print("\n" + "="*95)
    print(f"{'Feature Bundle':<50} | {'Mean H':<8} | {'Discrim':<8} | {'Conf':<8}")
    print("-" * 95)
    for res in results:
        if res:
            name = "+".join([f.split("_")[0] for f in res['bundle'][:4]]) + ("..." if len(res['bundle']) > 4 else "")
            print(f"{name:<50} | {res['mean_entropy']:.4f} | {res['entropy_discrimination']:.4f} | {res['confidence_score']:.2%}")
    print("="*95)
    print("Note: Mean H (Entropy) - Lower is better. Discrim (Stress H / Normal H) - Higher is better.")

if __name__ == "__main__":
    run_entropy_audit()
