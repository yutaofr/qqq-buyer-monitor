import pytest
import numpy as np
import pandas as pd
from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine

class MockClassifier:
    def __init__(self):
        self.classes_ = ["BULL", "BEAR"]
        self.theta_ = np.array([[1.0, 1.0], [-1.0, -1.0]])
        self.var_ = np.array([[0.1, 0.1], [0.1, 0.1]])

def test_quality_weight_1_preserves_existing_math():
    """Verify that quality=1.0 yields the same result as quality=None."""
    engine = BayesianInferenceEngine(kde_models={}, base_priors={"BULL": 0.5, "BEAR": 0.5})
    classifier = MockClassifier()
    evidence = pd.DataFrame([[0.5, 0.5]], columns=["f1", "f2"])
    
    # 1. No quality weights
    post1, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier, 
        evidence_frame=evidence,
        runtime_priors=None,
        weight_registry={"feature_weight_matrix": {"f1": 1.0, "f2": 1.0}},
        tau=1.0
    )
    
    # 2. Quality = 1.0 for all
    post2, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier, 
        evidence_frame=evidence,
        runtime_priors=None,
        weight_registry={"feature_weight_matrix": {"f1": 1.0, "f2": 1.0}},
        feature_quality_weights={"f1": 1.0, "f2": 1.0},
        tau=1.0
    )
    
    assert pytest.approx(post1["BULL"]) == post2["BULL"]
    assert pytest.approx(post1["BEAR"]) == post2["BEAR"]

def test_missing_feature_quality_0_removes_feature_contribution():
    """Verify that quality=0.0 makes the feature contribution zero."""
    engine = BayesianInferenceEngine(kde_models={}, base_priors={"BULL": 0.5, "BEAR": 0.5})
    classifier = MockClassifier()
    
    # Feature 1 is a strong BULL signal (val=1.0, BULL theta=1.0)
    # Feature 2 is a strong BEAR signal (val=-1.0, BEAR theta=-1.0)
    evidence = pd.DataFrame([[1.0, -1.0]], columns=["f1", "f2"])
    
    # If both features count, it should be balanced
    post_both, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        runtime_priors=None,
        weight_registry={"feature_weight_matrix": {"f1": 1.0, "f2": 1.0}},
        tau=1.0
    )
    
    # If f2 quality is 0, only f1 counts (strong BULL)
    post_gated, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        runtime_priors=None,
        weight_registry={"feature_weight_matrix": {"f1": 1.0, "f2": 1.0}},
        feature_quality_weights={"f1": 1.0, "f2": 0.0},
        tau=1.0
    )
    
    assert post_gated["BULL"] > post_both["BULL"]
    assert post_gated["BULL"] > 0.9  # Should be dominant

def test_degraded_feature_quality_reduces_confidence():
    """Verify that quality=0.5 reduces likelihood confidence (increases entropy)."""
    engine = BayesianInferenceEngine(kde_models={}, base_priors={"BULL": 0.5, "BEAR": 0.5})
    classifier = MockClassifier()
    
    # Strong BULL signal
    evidence = pd.DataFrame([[1.0, 1.0]], columns=["f1", "f2"])
    
    # 1. Perfect quality
    post_high, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        runtime_priors=None,
        weight_registry={"feature_weight_matrix": {"f1": 1.0, "f2": 1.0}},
        tau=1.0
    )
    
    # 2. Degraded quality (0.1)
    post_low, _ = engine.infer_gaussian_nb_posterior(
        classifier=classifier,
        evidence_frame=evidence,
        runtime_priors=None,
        weight_registry={"feature_weight_matrix": {"f1": 1.0, "f2": 1.0}},
        feature_quality_weights={"f1": 0.1, "f2": 0.1},
        tau=1.0
    )
    
    # Low quality should move probabilities closer to the prior (0.5/0.5)
    # i.e., BULL probability should drop towards 0.5
    assert post_high["BULL"] > post_low["BULL"]
    assert post_low["BULL"] > 0.5
