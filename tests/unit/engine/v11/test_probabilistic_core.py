import json
from pathlib import Path

import numpy as np
import pytest
import pandas as pd

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.price_topology import (
    blend_posteriors_with_topology,
    infer_price_topology_state,
    topology_likelihood_penalties,
)
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase


@pytest.fixture
def base_priors():
    return {"MID_CYCLE": 0.8, "RECOVERY": 0.1, "LATE_CYCLE": 0.05, "BUST": 0.05}


@pytest.fixture
def mock_classifier():
    class MockGNB:
        classes_ = np.array(["MID_CYCLE", "RECOVERY", "LATE_CYCLE", "BUST"])
        theta_ = np.zeros((4, 6))
        var_ = np.ones((4, 6))
    return MockGNB()


def test_bayesian_inference_priors(mock_classifier, base_priors):
    """验证推断引擎能够输出归一化的后验概率"""
    engine = BayesianInferenceEngine(base_priors)
    evidence = __import__("pandas").DataFrame(
        [[0.1, -0.2, 0.5, 0.1, -0.1, 0.0]],
        columns=["f1", "f2", "f3", "f4", "f5", "f6"]
    )

    probs, diag = engine.infer_gaussian_nb_posterior(
        classifier=mock_classifier,
        evidence_frame=evidence,
        runtime_priors=base_priors,
        feature_values={}
    )

    assert sum(probs.values()) == pytest.approx(1.0)
    assert "MID_CYCLE" in probs
    assert len(probs) == len(base_priors)


def test_entropy_calculation():
    """验证信息熵计算准确性"""
    controller = EntropyController()

    # 极度确定的状态 (Entropy 应当接近 0)
    certain_probs = {"A": 0.99, "B": 0.01}
    assert controller.calculate_normalized_entropy(certain_probs) < 0.1

    # 极度不确定的状态 (Entropy 应当接近 1)
    uncertain_probs = {"A": 0.5, "B": 0.5}
    assert controller.calculate_normalized_entropy(uncertain_probs) == pytest.approx(1.0)


def test_entropy_calculation_matches_raw_shannon_for_high_conviction_four_state_distribution():
    controller = EntropyController()
    probs = {"MID_CYCLE": 0.0133, "LATE_CYCLE": 0.0133, "BUST": 0.96, "RECOVERY": 0.0134}

    entropy = controller.calculate_normalized_entropy(probs)

    assert entropy == pytest.approx(0.1528, abs=1e-3)


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

    engine = BayesianInferenceEngine({"MID_CYCLE": 0.5, "BUST": 0.5})
    evidence = np.array([[0.0, 0.0]])

    full_weight, _ = engine.infer_gaussian_nb_posterior(
        classifier=StubGaussianNB(),
        evidence_frame=__import__("pandas").DataFrame(evidence, columns=["signal", "breadth"]),
        runtime_priors={"MID_CYCLE": 0.5, "BUST": 0.5},
        weight_registry={"feature_weight_matrix": {"signal": 1.0, "breadth": 1.0}},
        feature_values={"spread_21d": 2.0, "move_21d": 2.0},
    )
    muted_breadth, _ = engine.infer_gaussian_nb_posterior(
        classifier=StubGaussianNB(),
        evidence_frame=__import__("pandas").DataFrame(evidence, columns=["signal", "breadth"]),
        runtime_priors={"MID_CYCLE": 0.5, "BUST": 0.5},
        weight_registry={"feature_weight_matrix": {"signal": 1.0, "breadth": 0.0}},
        feature_values={"spread_21d": 2.0, "move_21d": 2.0},
    )

    assert full_weight["BUST"] > full_weight["MID_CYCLE"]
    assert muted_breadth["MID_CYCLE"] == pytest.approx(0.5)
    assert muted_breadth["BUST"] == pytest.approx(0.5)


def test_bayesian_inference_does_not_anchor_mid_cycle_through_confirmed_recovery_window(
    monkeypatch,
):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    snapshot_path = Path(
        "/Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/artifacts/v14_panorama/mainline/mainline_snapshots/snapshot_2023-04-14.json"
    )
    price_path = Path(
        "/Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/data/qqq_history_cache.csv"
    )
    registry_path = Path(
        "/Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/resources/v13_4_weights_registry.json"
    )
    constraints_path = Path(
        "/Users/weizhang/w/cycle-monitor-workspace/verify-QLD-Point/src/engine/v11/resources/logical_constraints.json"
    )

    snapshot = json.loads(snapshot_path.read_text())
    price = pd.read_csv(price_path, index_col=0)
    price.index = pd.to_datetime(price.index)
    topology = infer_price_topology_state(price.loc[: "2023-04-14"])

    prior_store = PriorKnowledgeBase(
        storage_path="/tmp/v11_probabilistic_core_prior.json",
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=["BUST"] * 8 + ["LATE_CYCLE"] * 4 + ["RECOVERY"] * 3,
    )
    prior_store.counts = {
        "MID_CYCLE": 12.0,
        "LATE_CYCLE": 16.0,
        "BUST": 30.0,
        "RECOVERY": 18.0,
    }
    prior_store.last_posterior = {
        "MID_CYCLE": 0.16,
        "LATE_CYCLE": 0.31,
        "BUST": 0.13,
        "RECOVERY": 0.40,
    }
    runtime_priors, _ = prior_store.runtime_priors(
        macro_values={
            "spread_21d": 0.7,
            "move_21d": 0.6,
            "qqq_ma_ratio": -0.14,
            "liquidity_velocity": -0.12,
            "credit_acceleration": 0.18,
            "dynamic_beta_inertia_matrix": {
                "MID_CYCLE": 0.80,
                "LATE_CYCLE": 0.80,
                "BUST": 0.70,
                "RECOVERY": 0.70,
                "DEFAULT": 0.80,
            },
            "price_topology_regime": topology.regime,
            "price_topology_confidence": topology.confidence,
            "price_topology_transition_intensity": topology.transition_intensity,
            "price_topology_repair_persistence": topology.repair_persistence,
            "price_topology_recovery_impulse": topology.recovery_impulse,
            "price_topology_damage_memory": topology.damage_memory,
            "price_topology_recovery_prob_delta": topology.recovery_prob_delta,
            "price_topology_recovery_prob_acceleration": topology.recovery_prob_acceleration,
        }
    )

    class MockClassifier:
        classes_ = np.array(snapshot["gaussian_nb"]["classes"])
        theta_ = np.array(snapshot["gaussian_nb"]["theta"], dtype=float)
        var_ = np.array(snapshot["gaussian_nb"]["var"], dtype=float)

    feature_row = {k: v for k, v in snapshot["feature_vector"][0].items() if k != "observation_date"}
    feature_values = dict(feature_row)
    feature_values.update(
        {
            "price_topology_regime": topology.regime,
            "price_topology_confidence": topology.confidence,
            "price_topology_transition_intensity": topology.transition_intensity,
            "price_topology_repair_persistence": topology.repair_persistence,
            "price_topology_recovery_impulse": topology.recovery_impulse,
            "price_topology_damage_memory": topology.damage_memory,
            "price_topology_recovery_prob_delta": topology.recovery_prob_delta,
            "price_topology_recovery_prob_acceleration": topology.recovery_prob_acceleration,
        }
    )
    engine = BayesianInferenceEngine(runtime_priors)
    posteriors, diagnostics = engine.infer_gaussian_nb_posterior(
        classifier=MockClassifier(),
        evidence_frame=pd.DataFrame([feature_row], columns=feature_row.keys()),
        runtime_priors=runtime_priors,
        weight_registry=json.loads(registry_path.read_text()),
        feature_quality_weights={k: 1.0 for k in feature_row.keys()},
        feature_values=feature_values,
        tau=1.5,
        logical_constraints=json.loads(constraints_path.read_text()),
        regime_penalties=topology_likelihood_penalties(topology),
    )

    assert diagnostics["evidence_dist"]["MID_CYCLE"] < 0.9
    assert posteriors["RECOVERY"] > posteriors["MID_CYCLE"]


def test_infer_price_topology_state_keeps_nontrivial_blend_weight_in_fuzzy_transition(
    monkeypatch,
):
    benchmark = pd.DataFrame(
        {
            "Close": [100.0],
            "Volume": [1_000_000.0],
            "benchmark_regime": ["RECOVERY"],
            "benchmark_expected_beta": [1.02],
            "benchmark_transition_intensity": [0.88],
            "benchmark_recovery_impulse": [0.38],
            "benchmark_recent_damage": [0.58],
            "benchmark_bust_pressure": [0.24],
            "benchmark_bullish_rsi_divergence": [0.20],
            "benchmark_bearish_rsi_divergence": [0.05],
            "benchmark_prob_delta_RECOVERY": [0.011],
            "benchmark_prob_acceleration_RECOVERY": [0.004],
            "benchmark_prob_MID_CYCLE": [0.26],
            "benchmark_prob_LATE_CYCLE": [0.20],
            "benchmark_prob_BUST": [0.25],
            "benchmark_prob_RECOVERY": [0.29],
        },
        index=pd.to_datetime(["2024-05-10"]),
    )
    monkeypatch.setattr(
        "src.engine.v11.core.price_topology.build_worldview_benchmark",
        lambda _frame: benchmark,
    )

    topology = infer_price_topology_state(
        pd.DataFrame(
            {
                "Close": [100.0],
                "Volume": [1_000_000.0],
            },
            index=pd.to_datetime(["2024-05-10"]),
        )
    )

    assert topology.regime == "RECOVERY"
    assert topology.posterior_blend_weight >= 0.08

    posteriors = {
        "MID_CYCLE": 0.985,
        "LATE_CYCLE": 0.01,
        "BUST": 0.003,
        "RECOVERY": 0.002,
    }
    blended = blend_posteriors_with_topology(posteriors, topology)

    assert blended["RECOVERY"] > posteriors["RECOVERY"]
    controller = EntropyController()
    assert controller.calculate_normalized_entropy(blended) > 0.20
