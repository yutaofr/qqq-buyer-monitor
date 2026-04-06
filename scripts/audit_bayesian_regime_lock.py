import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine

class MockClassifier:
    def __init__(self, regimes):
        self.classes_ = regimes
        self.theta_ = np.zeros((len(regimes), 2)) # 2 features
        self.var_ = np.ones((len(regimes), 2))

    def predict_log_proba(self, X):
        return np.zeros((X.shape[0], len(self.classes_)))

def audit_bayesian_regime_lock():
    print("--- BAYESIAN FORENSIC: REGIME LOCK & ANCHOR AUDIT ---")
    
    regimes = ["RECOVERY", "MID_CYCLE", "LATE_CYCLE", "BUST"]
    base_priors = {r: 0.25 for r in regimes}
    engine = BayesianInferenceEngine(base_priors=base_priors)
    
    classifier = MockClassifier(regimes)
    # Set MID_CYCLE to be very far from the origin (to force low likelihood normally)
    # feature 0: spread_21d, feature 1: move_21d
    mid_cycle_idx = regimes.index("MID_CYCLE")
    classifier.theta_[mid_cycle_idx] = [0.0, 0.0] 
    classifier.var_[mid_cycle_idx] = [0.1, 0.1] # Tight normal
    
    # Other regimes are also tight but elsewhere
    for i, r in enumerate(regimes):
        if r != "MID_CYCLE":
            classifier.theta_[i] = [5.0, 5.0]
            classifier.var_[i] = [0.1, 0.1]

    # TEST 1: The MID_CYCLE Anchor (Stable Market)
    print("\n[Scenario] Stable Market (sp_z=0, move_z=0)")
    # Evidence is [5.0, 5.0] – matches 'BUST' or others, far from MID_CYCLE [0.0, 0.0]
    evidence = pd.DataFrame([[5.0, 5.0]], columns=["spread_21d", "move_21d"])
    feature_values = {"spread_21d": 0.0, "move_21d": 0.0} # Stable
    
    registry = {"feature_weight_matrix": {"DEFAULT_FALLBACK": 1.0}, "inference_tau": 10.0}
    
    # Run with Anchor
    os.environ["DISABLE_MID_CYCLE_ANCHOR"] = "OFF"
    posteriors_anchor, diag_anchor = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        feature_values=feature_values,
        weight_registry=registry,
        tau=10.0
    )
    
    # Run without Anchor (Unit test mode usually disables it, but we can force it)
    os.environ["PYTEST_CURRENT_TEST"] = "fake_test" # This DISABLES it in the code (line 114)
    posteriors_no_anchor, diag_no_anchor = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        feature_values=feature_values,
        weight_registry=registry,
        tau=10.0
    )
    del os.environ["PYTEST_CURRENT_TEST"]

    print(f"  MID_CYCLE Prob (With Anchor): {posteriors_anchor['MID_CYCLE']:.6f}")
    print(f"  MID_CYCLE Prob (No Anchor):   {posteriors_no_anchor['MID_CYCLE']:.6e}")
    
    if posteriors_anchor['MID_CYCLE'] > posteriors_no_anchor['MID_CYCLE']:
        print("  PASS: Mid-Cycle Anchor successfully boosted probability in stable market.")
    else:
        print("  FAIL: Mid-Cycle Anchor ineffective.")

    # TEST 2: Bayesian Overdrive (Tau Scaling)
    print("\n[Scenario] Crisis Event (Overdrive ACTIVE)")
    # Evidence is [2.5, 2.5] – ambiguous
    evidence_ambig = pd.DataFrame([[2.5, 2.5]], columns=["spread_21d", "move_21d"])
    
    # Normal Tau
    post_normal, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence_ambig,
        feature_values=feature_values,
        weight_registry=registry,
        tau=10.0,
        is_overdrive=False
    )
    
    # Overdrive Tau (tau_factor=0.5 -> effective tau=5.0)
    post_overdrive, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence_ambig,
        feature_values=feature_values,
        weight_registry=registry,
        tau=10.0,
        is_overdrive=True,
        tau_factor=0.5
    )
    
    # Find entropy (shorthand: max probability)
    max_p_normal = max(post_normal.values())
    max_p_overdrive = max(post_overdrive.values())
    
    print(f"  Max Posterior Prob (Normal Tau=10):    {max_p_normal:.4f}")
    print(f"  Max Posterior Prob (Overdrive Tau=5): {max_p_overdrive:.4f}")
    
    if max_p_overdrive > max_p_normal:
        print("  PASS: Bayesian Overdrive (Tau Scaling) successfully sharpened the distribution.")
    else:
        print("  FAIL: Bayesian Overdrive did not sharpen distribution.")

if __name__ == "__main__":
    audit_bayesian_regime_lock()
