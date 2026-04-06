import os
import unittest
import numpy as np
import pandas as pd
from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine

class MockClassifier:
    def __init__(self, regimes):
        self.classes_ = np.array(regimes)
        # 2 features: [spread_21d, move_21d]
        # BUST regime is centered at [10.0, 10.0] (Very far)
        # MID_CYCLE regime is centered at [0.0, 0.0]
        self.theta_ = np.array([
            [0.0, 0.0], # RECOVERY
            [0.0, 0.0], # MID_CYCLE
            [0.0, 0.0], # LATE_CYCLE
            [10.0, 10.0], # BUST
        ])
        self.var_ = np.array([
            [1.0, 1.0],
            [1.0, 1.0],
            [1.0, 1.0],
            [1.0, 1.0],
        ])

    def predict_log_proba(self, X):
        return np.zeros((X.shape[0], len(self.classes_)))

class TestAnchorTauHallucination(unittest.TestCase):
    def setUp(self):
        self.regimes = ["RECOVERY", "MID_CYCLE", "LATE_CYCLE", "BUST"]
        self.base_priors = {r: 0.25 for r in self.regimes}
        self.engine = BayesianInferenceEngine(base_priors=self.base_priors)
        self.classifier = MockClassifier(self.regimes)
        
        # Registry with Normal Tau = 10.0
        self.registry = {
            "feature_weight_matrix": {"spread_21d": 1.0, "move_21d": 1.0, "DEFAULT_FALLBACK": 1.0},
            "inference_tau": 10.0,
            "overdrive_tau_factor": 0.5
        }

    def test_stressed_hallucination_reproduction(self):
        """
        Reproduce the systemic failure where 'Stressed' Tau (0.5) causes 
        the likelihood floor to wash out real evidence differences.
        """
        # Evidence is [6.0, 6.0]
        # Distance to BUST [10,10] is 32.
        # Distance to MID_CYCLE [0,0] is 72.
        # BUST is much better evidence than MID_CYCLE.
        evidence = pd.DataFrame([[6.0, 6.0]], columns=["spread_21d", "move_21d"])
        
        # Market is 'stable' for the anchor logic (Z < 1.0)
        # Even though evidence is [3, 3], we mock feature_values to be stable 
        # to trigger the anchor. In real life, this happens when features are OOD.
        feature_values = {"spread_21d": 0.5, "move_21d": 0.5} 

        # 1. NORMAL CASE (Tau = 10.0)
        # Expect BUST to be the winner because evidence is strong.
        os.environ["PYTEST_CURRENT_TEST_OVERRIDE"] = "OFF" # Ensure internal is_test doesn't disable anchor
        probs_normal, _ = self.engine.infer_gaussian_nb_posterior(
            classifier=self.classifier,
            evidence_frame=evidence,
            feature_values=feature_values,
            weight_registry=self.registry,
            tau=10.0,
            is_overdrive=False
        )
        
        print(f"\n[Normal Tau=10] BUST: {probs_normal['BUST']:.4f}, MID_CYCLE: {probs_normal['MID_CYCLE']:.4f}")
        
        # 2. STRESSED CASE (Tau = 0.5)
        # Using a very low Tau to force logarithmic washout
        probs_stressed, _ = self.engine.infer_gaussian_nb_posterior(
            classifier=self.classifier,
            evidence_frame=evidence,
            feature_values=feature_values,
            weight_registry=self.registry,
            tau=1.0, # Stressing it hard
            is_overdrive=True,
            tau_factor=0.5
        )
        # Effective Tau = 0.5
        
        print(f"[Stress Tau=0.5] BUST: {probs_stressed['BUST']:.4f}, MID_CYCLE: {probs_stressed['MID_CYCLE']:.4f}")

        # The Failure: Under Tau=0.5, BUST log-likelihood is -32. MID_CYCLE is -72.
        # BOTH hit the anchor floor (-4.6) because they are compared AFTER scaling.
        # result: Tie (0.5 each). This is a Hallucination/Lock.
        self.assertTrue(probs_stressed['BUST'] > 0.6, 
                        f"Hallucination Detected: BUST probability ({probs_stressed['BUST']:.4f}) "
                        f"is washed out to {probs_stressed['BUST']:.4f} due to anchor floor!")

if __name__ == "__main__":
    unittest.main()
