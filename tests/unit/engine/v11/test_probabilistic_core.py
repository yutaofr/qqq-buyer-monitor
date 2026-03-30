import numpy as np
import pytest

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.entropy_controller import EntropyController


@pytest.fixture
def mock_kde_models():
    class MockKDE:
        def score_samples(self, X):
            # Return some fake log-likelihood
            return np.array([-5.0])
    return {"MID_CYCLE": MockKDE(), "BUST": MockKDE()}

@pytest.fixture
def base_priors():
    return {"MID_CYCLE": 0.8, "BUST": 0.2}

def test_bayesian_inference_priors(mock_kde_models, base_priors):
    """验证推断引擎能够输出归一化的后验概率"""
    engine = BayesianInferenceEngine(mock_kde_models, base_priors)
    evidence = np.array([0.1, -0.2, 0.5, 0.1, -0.1, 0.0]) # 6-factor vector

    probs = engine.infer_posterior(evidence)

    assert sum(probs.values()) == pytest.approx(1.0)
    assert "MID_CYCLE" in probs
    assert "BUST" in probs

def test_entropy_calculation():
    """验证信息熵计算准确性"""
    controller = EntropyController()

    # 极度确定的状态 (Entropy 应当接近 0)
    certain_probs = {"A": 0.99, "B": 0.01}
    assert controller.calculate_normalized_entropy(certain_probs) < 0.1

    # 极度不确定的状态 (Entropy 应当接近 1)
    uncertain_probs = {"A": 0.5, "B": 0.5}
    assert controller.calculate_normalized_entropy(uncertain_probs) == pytest.approx(1.0)

def test_entropy_beta_haircut():
    """验证当熵值过高时，Beta 能够正确切削回 1.0 (中性)"""
    controller = EntropyController(threshold=0.75)

    # 低熵，不切削
    low_entropy = 0.2
    assert controller.apply_haircut(1.2, low_entropy) == 1.2

    # 极高熵 (1.0)，强制切削回 1.0
    high_entropy = 1.0
    assert controller.apply_haircut(1.2, high_entropy) == 1.0
    assert controller.apply_haircut(0.6, high_entropy) == 1.0


def test_classifier_posteriors_can_be_reweighted_by_runtime_priors():
    """运行时先验必须能稳定地重加权分类器输出，而不是被训练期先验锁死。"""
    engine = BayesianInferenceEngine({}, {"MID_CYCLE": 0.5, "BUST": 0.5})

    classifier_posteriors = {"MID_CYCLE": 0.60, "BUST": 0.40}
    training_priors = {"MID_CYCLE": 0.80, "BUST": 0.20}
    runtime_priors = {"MID_CYCLE": 0.30, "BUST": 0.70}

    adjusted = engine.reweight_probabilities(
        classifier_posteriors=classifier_posteriors,
        training_priors=training_priors,
        runtime_priors=runtime_priors,
    )

    assert sum(adjusted.values()) == pytest.approx(1.0)
    assert adjusted["BUST"] > adjusted["MID_CYCLE"]
