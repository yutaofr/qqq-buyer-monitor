import logging
import numpy as np
import pandas as pd
import pytest
from src.engine.baseline.data_loader import load_all_baseline_data
from src.engine.baseline.sidecar import calculate_sidecar_composites, train_sidecar_model, generate_sidecar_target
from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from sklearn.naive_bayes import GaussianNB
from src.engine.baseline.engine import _select_regularization_c, _valid_time_splits

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_future_blindness():
    """Forensic Test: Ensure features at date T do not depend on data at T+k."""
    logger.info("Running Future Blindness Test...")
    data = load_all_baseline_data()
    if data.empty:
        pytest.skip("No data available")
    
    T_idx = len(data) // 2
    T_date = data.index[T_idx]
    
    # 1. Base features at T using full dataset
    features_full = calculate_sidecar_composites(data)
    if features_full.empty:
        pytest.skip("Features dataframe is empty (likely due to rolling window length)")
    
    # Pick T_date from features_full to ensure it exists
    T_idx_feat = len(features_full) // 2
    T_date = features_full.index[T_idx_feat]
    
    val_at_T_full = features_full.loc[T_date]
    
    # 2. Base features at T using truncated dataset (only up to T)
    data_truncated = data.loc[:T_date]
    features_truncated = calculate_sidecar_composites(data_truncated)
    val_at_T_truncated = features_truncated.loc[T_date]
    
    # Check equality (with small epsilon for float precision)
    diff = (val_at_T_full - val_at_T_truncated).abs().max()
    logger.info(f"Max feature diff between full and truncated data: {diff}")
    assert diff < 1e-10, "FUTURE LEAKAGE DETECTED: Historical features changed when future data was added."

def test_regime_permutation_constraints():
    """Forensic Test: Ensure coefficient constraints hold across diverse regimes."""
    logger.info("Running Regime Permutation Test...")
    data = load_all_baseline_data()
    if data.empty:
        pytest.skip("No data available")
    
    # Define Regimes
    regimes = {
        "2008_Crisis": ("2007-01-01", "2009-12-31"),
        "2020_Covid": ("2019-01-01", "2021-01-01"),
        "2022_Inflation": ("2021-01-01", "2023-01-01"),
        "Full_Sample": (str(data.index.min()), str(data.index.max()))
    }
    
    for name, (start, end) in regimes.items():
        subset = data.loc[start:end]
        if len(subset) < 100:
            logger.warning(f"Regime {name} has too few samples ({len(subset)}), skipping.")
            continue
            
        X = calculate_sidecar_composites(subset)
        y = generate_sidecar_target(data["QQQ"], data["^VXN"]).reindex(X.index).fillna(0)
        
        # Train model
        model = train_sidecar_model(X, y)
        coeffs = model.coef_[0]
        feature_names = X.columns.tolist()
        
        rules = {
            "growth_composite": lambda x: x <= 0,
            "stress_composite_extreme": lambda x: x >= 0,
            "liquidity_composite": lambda x: x <= 0,
            "vxn_acceleration": lambda x: x >= 0,
            "qqq_spy_relative_weakness": lambda x: x <= 0,
        }
        
        logger.info(f"Audit Results for {name}:")
        for i, f_name in enumerate(feature_names):
            val = coeffs[i]
            passed = rules[f_name](val)
            logger.info(f"  {f_name:30}: {val:8.4f} [{'PASS' if passed else 'FAIL'}]")
            assert passed, f"PHYSICAL AUDIT FAILED for {f_name} in regime {name}"

def test_bayesian_integrity_multiplicative():
    """Forensic Test: Verify Bayesian update is multiplicative (Prior * Likelihood)."""
    logger.info("Running Bayesian Integrity Audit...")
    
    # Setup dummy GaussianNB to inspect log_lhs
    gnb = GaussianNB()
    X = np.array([[1.0, 2.0], [1.1, 2.1], [3.0, 4.0], [3.1, 4.1]])
    y = np.array([0, 0, 1, 1])
    gnb.fit(X, y)
    
    priors = {"0": 0.5, "1": 0.5}
    engine = BayesianInferenceEngine({}, priors)
    
    # evidence
    obs = pd.DataFrame([[1.0, 2.0]], columns=["f1", "f2"])
    
    # Using tau=1.0 for simplicity in manual trace
    # Ensure priors keys match strings
    posteriors, diagnostics = engine.infer_gaussian_nb_posterior(
        classifier=gnb,
        evidence_frame=obs,
        tau=1.0,
        runtime_priors={"0": 0.5, "1": 0.5}
    )
    
    if "error" in diagnostics:
        pytest.fail(f"Bayesian Inference failed: {diagnostics['error']}")

    # Trace Likelihoods (evidence_dist)
    ev_dist = diagnostics["evidence_dist"]
    
    # Manual unnormalized posterior: Prior * Likelihood
    for r in ["0", "1"]:
        likelihood = ev_dist[r]
        prior = priors[r]
        expected_unnorm = prior * likelihood
        
        # Note: infer_gaussian_nb_posterior normalizes twice, but the core logic should be multiplicative.
        # Check against the final posterior (normalized)
        total_unnorm = sum(priors[rk] * ev_dist[rk] for rk in priors)
        expected_post = expected_unnorm / total_unnorm
        
        assert abs(posteriors[r] - expected_post) < 1e-7, f"Bayesian integrity violation in regime {r}: {posteriors[r]} != {expected_post}"
    logger.info("Bayesian Integrity Audit passed (Multiplicative Identity Verified).")

def test_tau_sensitivity_analysis():
    """Forensic Audit: Tau Sensitivity Sweep."""
    logger.info("Running Tau Sensitivity Analysis...")
    # This would require real data and a trained classifier.
    # For now, we simulate scores or use a small slice of real data.
    # Goal: Report OOS relative Brier improvement.
    pass

if __name__ == "__main__":
    test_future_blindness()
    test_regime_permutation_constraints()
    test_bayesian_integrity_multiplicative()
