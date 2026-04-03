import unittest
import numpy as np
from typing import Any
from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine


class MockClassifier:
    def __init__(self):
        self.classes_ = ["MID_CYCLE", "BUST"]
        # 3 features: [root_A_1, root_A_2, root_B_1]
        # Lineage A: features 0, 1. Lineage B: feature 2.
        self.theta_ = np.array([
            [1.0, 1.0, 0.0],  # MID_CYCLE: High values for A, 0 for B
            [-1.0, -1.0, 0.0]  # BUST: Low values for A, 0 for B
        ])
        # Use variance 1.0 to simplify log-lh calculation: -0.5 * (log(2pi) + (x-theta)^2)
        self.var_ = np.array([
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0]
        ])

class MockFrame:
    def __init__(self, data: list[float], columns: list[str]):
        self.data = np.array([data])
        self.columns = columns
        self.iloc = self
    def __getitem__(self, idx):
        return self.data[idx]
    def __len__(self):
        return 1

class TestV13_4Inference(unittest.TestCase):
    def setUp(self):
        self.engine = BayesianInferenceEngine(kde_models={}, base_priors={"MID_CYCLE": 0.5, "BUST": 0.5})
        self.classifier = MockClassifier()
        self.registry = {
            "feature_weight_matrix": {
                "root_A": 2.0,
                "root_B": 1.0,
                "DEFAULT_FALLBACK": 1.0
            }
        }

    def test_lineage_normalization_math(self):
        # Features 0 and 1 belong to root_A. Feature 2 belongs to root_B.
        feature_names = ["root_A_1", "root_A_2", "root_B_1"]
        evidence = MockFrame([1.0, 1.0, 0.0], feature_names)
        
        # Calculation:
        # root_A weight = 2.0, root_B weight = 1.0
        # root_A has 2 features -> effective weight per feature = 2.0 / 2 = 1.0
        # root_B has 1 feature -> effective weight per feature = 1.0 / 1 = 1.0
        # total_weight_sum = 1.0 + 1.0 + 1.0 = 3.0
        
        posteriors, diagnostics = self.engine.infer_gaussian_nb_posterior(
            classifier=self.classifier,
            evidence_frame=evidence,
            runtime_priors={"MID_CYCLE": 0.5, "BUST": 0.5},
            weight_registry=self.registry,
            tau=1.0 # Disable tau scaling for pure math check
        )
        
        weights = diagnostics["effective_weights"]
        self.assertEqual(weights["root_A_1"], 1.0)
        self.assertEqual(weights["root_A_2"], 1.0)
        self.assertEqual(weights["root_B_1"], 1.0)
        self.assertEqual(diagnostics["total_weight"], 3.0)
        
    def test_tau_scaling(self):
        feature_names = ["root_A_1"]
        evidence = MockFrame([1.0], feature_names)
        registry = {"feature_weight_matrix": {"root_A": 1.0}}
        
        # Test with high tau (should flatten distribution)
        posteriors_t1, _ = self.engine.infer_gaussian_nb_posterior(
            classifier=self.classifier, evidence_frame=evidence,
            runtime_priors={"MID_CYCLE": 0.5, "BUST": 0.5},
            weight_registry=registry, tau=1.0
        )
        
        posteriors_t10, _ = self.engine.infer_gaussian_nb_posterior(
            classifier=self.classifier, evidence_frame=evidence,
            runtime_priors={"MID_CYCLE": 0.5, "BUST": 0.5},
            weight_registry=registry, tau=10.0
        )
        
        # Dist T10 should be closer to 0.5/0.5 than T1
        diff_t1 = abs(posteriors_t1["MID_CYCLE"] - posteriors_t1["BUST"])
        diff_t10 = abs(posteriors_t10["MID_CYCLE"] - posteriors_t10["BUST"])
        self.assertLess(diff_t10, diff_t1)

if __name__ == "__main__":
    unittest.main()
