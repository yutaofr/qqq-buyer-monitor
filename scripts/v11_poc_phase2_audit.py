#!/usr/bin/env python3
"""v11 POC Phase 2: Purged Walk-Forward Audit."""
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.neighbors import KernelDensity
from sklearn.metrics import brier_score_loss
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Regime-aware Embargo Days (Howard's Recommendation)
EMBARGO_DAYS = {
    "BUST": 60,
    "LATE_CYCLE": 45,
    "CAPITULATION": 30,
    "RECOVERY": 20,
    "MID_CYCLE": 10
}

def calculate_brier_score(y_true, y_prob, label):
    """Calculate Brier Score for a specific label."""
    binary_true = (y_true == label).astype(int)
    return brier_score_loss(binary_true, y_prob)

def run_audit():
    results_path = "data/v11_poc_phase1_results.csv"
    if not Path(results_path).exists():
        logger.error("Phase 1 results missing. Run scripts/v11_poc_phase1.py first.")
        return

    df = pd.read_csv(results_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df = df.sort_values("observation_date").reset_index(drop=True)

    # Walk-Forward Settings
    start_date = df["observation_date"].min()
    end_date = df["observation_date"].max()
    
    # 10 years initial training
    train_end_date = start_date + pd.DateOffset(years=10)
    test_window_months = 12
    
    audit_results = []
    
    evidence_cols = ["vix_pct", "dd_pct", "breadth_pct"]
    regimes = ["MID_CYCLE", "BUST", "CAPITULATION", "RECOVERY", "LATE_CYCLE"]

    logger.info(f"Starting Purged Walk-Forward Audit from {train_end_date.date()}...")

    while train_end_date < end_date:
        test_start_date = train_end_date
        test_end_date = test_start_date + pd.DateOffset(months=test_window_months)
        
        # Determine Embargo based on the regime at the end of training
        last_regime = df[df["observation_date"] <= train_end_date]["regime"].iloc[-1]
        embargo_delta = pd.DateOffset(days=EMBARGO_DAYS.get(last_regime, 20))
        
        # Purged Training Set: Up to (test_start - embargo)
        train_df = df[df["observation_date"] <= (test_start_date - embargo_delta)].copy()
        test_df = df[(df["observation_date"] >= test_start_date) & (df["observation_date"] < test_end_date)].copy()
        
        if test_df.empty:
            break
            
        logger.info(f"Auditing Window: {test_start_date.date()} to {test_end_date.date()} | Embargo: {embargo_delta.days}d ({last_regime})")

        # 1. Fit PCA on Training Percentiles
        pca = PCA(n_components=2)
        X_train = train_df[evidence_cols].values
        pca.fit(X_train)
        
        train_pca = pca.transform(X_train)
        X_test_pca = pca.transform(test_df[evidence_cols].values)
        
        # 2. Compute Priors from Training Set
        priors = train_df["regime"].value_counts(normalize=True).to_dict()
        for r in regimes:
            priors.setdefault(r, 1e-6) # Laplacian smoothing

        # 3. Train KDE Likelihoods on Training Set
        kde_models = {}
        for r in regimes:
            r_data = train_pca[train_df["regime"] == r]
            if len(r_data) > 5:
                # Simplified bandwidth for audit speed, could be optimized
                kde = KernelDensity(bandwidth=0.1, kernel='gaussian')
                kde.fit(r_data)
                kde_models[r] = kde

        # 4. Bayesian Inference on Test Set
        # P(Regime | Evidence) ~ P(Evidence | Regime) * P(Regime)
        window_preds = []
        for i, obs in enumerate(X_test_pca):
            posteriors = {}
            total_likelihood = 0
            
            for r in regimes:
                if r in kde_models:
                    # score_samples returns log-likelihood
                    log_likelihood = kde_models[r].score_samples([obs])[0]
                    likelihood = np.exp(log_likelihood)
                else:
                    likelihood = 1e-9 # Penalty for missing/sparse regimes
                
                posteriors[r] = likelihood * priors[r]
                total_likelihood += posteriors[r]
            
            # Normalize
            if total_likelihood > 0:
                for r in regimes:
                    posteriors[r] /= total_likelihood
            else:
                # Fallback to priors if likelihood is zero everywhere (extremely rare)
                posteriors = priors.copy()
            
            posteriors["observation_date"] = test_df.iloc[i]["observation_date"]
            posteriors["actual_regime"] = test_df.iloc[i]["regime"]
            window_preds.append(posteriors)
            
        audit_results.extend(window_preds)
        train_end_date = test_end_date

    # Final Evaluation
    audit_df = pd.DataFrame(audit_results)
    logger.info(f"Audit Complete. Total samples evaluated: {len(audit_df)}")
    
    # 5. Metrics Calculation
    performance = {}
    for r in regimes:
        # P(Regime) Brier Score
        brier = calculate_brier_score(audit_df["actual_regime"], audit_df[r], r)
        
        # Climatological Baseline Brier Score (predicting historical mean frequency)
        baseline_prob = df["regime"].value_counts(normalize=True).get(r, 0)
        baseline_brier = calculate_brier_score(audit_df["actual_regime"], np.full(len(audit_df), baseline_prob), r)
        
        performance[r] = {
            "v11_brier": round(brier, 5),
            "baseline_brier": round(baseline_brier, 5),
            "improvement_pct": round((baseline_brier - brier) / baseline_brier * 100, 2) if baseline_brier > 0 else 0
        }
        logger.info(f"Regime {r:12}: Brier={brier:.5f} | Baseline={baseline_brier:.5f} | Gain={performance[r]['improvement_pct']}%")

    # Overall Metrics
    # (Simplified overall Brier)
    
    # Save Audit Results
    audit_df.to_csv("data/v11_poc_phase2_audit_results.csv", index=False)
    logger.info("Audit results saved to data/v11_poc_phase2_audit_results.csv")

if __name__ == "__main__":
    run_audit()
