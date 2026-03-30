import pandas as pd
import numpy as np
import logging
from src.engine.v11.conductor import V11Conductor

logging.basicConfig(level=logging.INFO)

def run_diagnostic():
    print("=== v11.5 Probability Diagnostic ===")
    
    # 1. Load Conductor
    cond = V11Conductor()
    
    # 2. Get current macro data from the dump
    macro_df = pd.read_csv("data/macro_historical_dump.csv", index_col="observation_date", parse_dates=True)
    features = cond.seeder.generate_features(macro_df)
    latest_vector = features.iloc[-1:]
    
    # 3. Inspect the GNB Model
    print(f"\nModel Classes: {cond.gnb.classes_}")
    print(f"Priors (log): {cond.gnb.class_prior_}")
    
    # 4. Probabilities for latest evidence
    probs = cond.gnb.predict_proba(latest_vector)[0]
    posteriors = {str(k): float(v) for k, v in zip(cond.gnb.classes_, probs)}
    
    print("\n--- Current Posteriors ---")
    for r, p in sorted(posteriors.items(), key=lambda x: x[1], reverse=True):
        print(f"{r:20}: {p:.10%}")
        
    # 5. Internal Likelihoods (P(E|R))
    # GaussianNB stores means in theta_ and variances in var_
    print("\n--- Feature Distributions (theta_ / var_) ---")
    for i, regime in enumerate(cond.gnb.classes_):
        print(f"\nRegime: {regime}")
        for j, feat in enumerate(features.columns):
            mean = cond.gnb.theta_[i, j]
            var = cond.gnb.var_[i, j]
            val = latest_vector.values[0, j]
            # Prob density
            z = (val - mean) / np.sqrt(var) if var > 0 else 0
            density = (1 / (np.sqrt(2 * np.pi * var))) * np.exp(-0.5 * z**2) if var > 0 else 0
            print(f"  {feat:25}: mean={mean:+.4f}, var={var:+.4f}, current={val:+.4f}, z={z:+.2f}, density={density:.2e}")

if __name__ == "__main__":
    run_diagnostic()
