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
    """高熵只能持续减仓，绝不能把任何 beta 拉回更高风险。"""
    controller = EntropyController()

    assert controller.apply_haircut(1.2, 0.0) == pytest.approx(1.2)
    assert controller.apply_haircut(1.2, 1.0) < 1.2
    assert controller.apply_haircut(0.6, 1.0) < 0.6


def test_entropy_haircut_is_threshold_free_and_never_increases_risk():
    """全概率系统下，风险定价不应依赖任意阈值，也绝不能把防御 beta 往上抬。"""
    loose = EntropyController(threshold=0.20)
    tight = EntropyController(threshold=0.80)

    loose_beta = loose.apply_haircut(0.60, 0.90)
    tight_beta = tight.apply_haircut(0.60, 0.90)

    assert loose_beta == pytest.approx(tight_beta)
    assert loose_beta < 0.60


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


def test_gaussian_nb_feature_weights_can_silence_unreliable_dimensions():
    class StubGaussianNB:
        classes_ = np.array(["MID_CYCLE", "BUST"])
        theta_ = np.array([[0.0, 4.0], [0.0, 0.0]])
        var_ = np.array([[1.0, 1.0], [1.0, 1.0]])

    engine = BayesianInferenceEngine({}, {"MID_CYCLE": 0.5, "BUST": 0.5})
    evidence = np.array([[0.0, 0.0]])

    full_weight, _ = engine.infer_gaussian_nb_posterior(
        classifier=StubGaussianNB(),
        evidence_frame=__import__("pandas").DataFrame(evidence, columns=["signal", "breadth"]),
        runtime_priors={"MID_CYCLE": 0.5, "BUST": 0.5},
        weight_registry={"feature_weight_matrix": {"signal": 1.0, "breadth": 1.0}},
    )
    muted_breadth, _ = engine.infer_gaussian_nb_posterior(
        classifier=StubGaussianNB(),
        evidence_frame=__import__("pandas").DataFrame(evidence, columns=["signal", "breadth"]),
        runtime_priors={"MID_CYCLE": 0.5, "BUST": 0.5},
        weight_registry={"feature_weight_matrix": {"signal": 1.0, "breadth": 0.0}},
    )

    assert full_weight["BUST"] > full_weight["MID_CYCLE"]
    assert muted_breadth["MID_CYCLE"] == pytest.approx(0.5)
    assert muted_breadth["BUST"] == pytest.approx(0.5)
