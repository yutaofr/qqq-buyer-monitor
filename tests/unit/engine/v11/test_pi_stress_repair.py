from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from src.engine.v11.conductor import V11Conductor
from src.engine.v11.core.mahalanobis_guard import MahalanobisGuard
from src.engine.v11.core.price_topology import PriceTopologyState
from src.engine.v11.stress.diagnostics.stress_attribution import StressAttributor
from src.engine.v11.stress.engine import StressPosteriorEngine
from src.engine.v11.stress.models.stress_calibrator import StressCalibrator
from src.engine.v11.stress.models.stress_combiner import StressCombiner
from src.engine.v11.stress.models.threshold_policy import ThresholdPolicyEvaluator
from src.engine.v11.stress.signals.macro_anomaly import MacroAnomalyScorer
from src.engine.v11.stress.signals.market_stress import MarketStressScorer
from src.engine.v11.stress.signals.persistence import PersistenceScorer
from src.engine.v11.stress.signals.price_damage import PriceDamageScorer


def _topology(**overrides) -> PriceTopologyState:
    payload = {
        "regime": "LATE_CYCLE",
        "probabilities": {
            "MID_CYCLE": 0.35,
            "LATE_CYCLE": 0.35,
            "BUST": 0.18,
            "RECOVERY": 0.12,
        },
        "expected_beta": 0.8,
        "confidence": 0.42,
        "posterior_blend_weight": 0.12,
        "beta_anchor_weight": 0.14,
        "transition_intensity": 0.45,
        "recovery_impulse": 0.08,
        "damage_memory": 0.52,
        "bust_pressure": 0.40,
        "bullish_divergence": 0.05,
        "bearish_divergence": 0.24,
        "recovery_prob_delta": 0.01,
        "recovery_prob_acceleration": 0.0,
        "repair_persistence": 0.22,
        "benchmark_entropy": 0.62,
    }
    payload.update(overrides)
    return PriceTopologyState(**payload)


def test_stress_component_scores_are_bounded_and_explainable():
    topology = _topology()
    feature_frame = pd.DataFrame(
        {
            "move_21d": [0.1, 0.4, 1.7],
            "qqq_pv_divergence_z": [0.0, -0.5, -1.4],
            "spread_21d": [0.2, 0.5, 1.3],
        },
        index=pd.bdate_range("2023-01-02", periods=3),
    )

    components = [
        PriceDamageScorer().score(topology),
        MarketStressScorer().score(topology=topology, feature_history=feature_frame),
        PersistenceScorer(half_life_days=4).score(price_score=0.7, market_score=0.4, macro_score=0.3),
    ]

    for component in components:
        assert 0.0 <= component.value <= 1.0
        assert np.isfinite(component.value)
        assert component.subcomponents


def test_market_stress_uses_runtime_market_internals_without_conductor_gates():
    topology = _topology(transition_intensity=0.30, benchmark_entropy=0.35)
    feature_frame = pd.DataFrame(
        {
            "move_21d": [0.2, 0.5, 0.8],
            "spread_21d": [0.1, 0.4, 0.7],
            "credit_acceleration": [0.0, 0.2, 1.6],
            "move_spread_corr_21d": [0.1, 0.35, 0.82],
            "adv_dec_ratio": [0.58, 0.46, 0.24],
            "breadth_quality_score": [1.0, 1.0, 1.0],
            "vix_3m_1m_ratio": [0.98, 1.02, 1.22],
        },
        index=pd.bdate_range("2022-01-03", periods=3),
    )

    score = MarketStressScorer().score(topology_state=topology, feature_history=feature_frame)

    assert score.value > 0.55
    assert score.subcomponents["breadth_compression"] > 0.50
    assert score.subcomponents["correlation_stress"] > 0.50
    assert score.subcomponents["term_structure_stress"] > 0.50


def test_macro_anomaly_reuses_robust_mahalanobis_geometry_without_becoming_posterior():
    dates = pd.bdate_range("2022-01-03", periods=80)
    frame = pd.DataFrame(
        {
            "pmi_momentum": np.linspace(-0.3, 0.4, len(dates)),
            "labor_slack": np.linspace(0.2, -0.2, len(dates)),
            "liquidity_velocity": np.sin(np.linspace(0.0, 3.0, len(dates))),
        },
        index=dates,
    )
    guard = MahalanobisGuard()
    guard.fit_baseline(frame)

    score = MacroAnomalyScorer().score(
        current_vector=np.array([2.5, -2.0, 2.2]),
        mahalanobis_guard=guard,
        stress_probability=0.0,
    )

    assert 0.0 <= score.value <= 1.0
    assert score.kind == "S_macro_anom"
    assert score.subcomponents["is_posterior"] is False
    assert score.subcomponents["adjusted_mahalanobis_distance"] > 0.0


def test_logistic_combiner_has_explicit_positive_interactions_and_limits_macro_alone():
    combiner = StressCombiner()
    low = combiner.combine(
        S_price=0.15,
        S_market=0.10,
        S_macro_anom=0.95,
        S_persist=0.05,
    )
    confirmed = combiner.combine(
        S_price=0.75,
        S_market=0.70,
        S_macro_anom=0.65,
        S_persist=0.55,
    )

    assert low.raw_score < 0.45
    assert confirmed.raw_score > low.raw_score
    assert confirmed.terms["interaction_price_market"] > 0.0
    assert confirmed.terms["interaction_price_macro"] > 0.0
    assert confirmed.terms["interaction_market_macro"] > 0.0


def test_calibrators_are_causal_monotone_and_configurable():
    train_scores = np.array([0.05, 0.15, 0.35, 0.55, 0.75, 0.90])
    train_labels = np.array([0, 0, 0, 1, 1, 1])

    for method in ("platt", "isotonic"):
        calibrator = StressCalibrator(method=method)
        calibrator.fit(train_scores, train_labels)
        transformed = calibrator.transform(train_scores)

        assert np.all(np.diff(transformed) >= -1e-9)
        assert np.all((0.0 <= transformed) & (transformed <= 1.0))
        assert calibrator.fit_metadata["fit_rows"] == len(train_scores)


def test_episode_weighted_calibration_accepts_structural_weights():
    train_scores = np.array([0.05, 0.12, 0.22, 0.30, 0.42, 0.55, 0.70, 0.82])
    train_labels = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    weights = np.array([1.0, 1.0, 1.0, 1.0, 2.5, 2.5, 1.8, 1.8])

    calibrator = StressCalibrator(method="weighted_platt")
    calibrator.fit(train_scores, train_labels, sample_weight=weights)
    transformed = calibrator.transform(train_scores)

    assert np.all(np.diff(transformed) >= -1e-9)
    assert calibrator.fit_metadata["weighting"] == "sample_weight"
    assert transformed[-1] > transformed[0]


def test_threshold_policy_reports_curves_and_episode_capture():
    scores = np.array([0.10, 0.20, 0.35, 0.52, 0.65, 0.25, 0.58, 0.70])
    labels = np.array([0, 0, 0, 1, 1, 0, 1, 1])
    episode_ids = np.array(["n0", "n1", "n2", "e1", "e1", "n3", "e2", "e2"])

    policy = ThresholdPolicyEvaluator(thresholds=[0.3, 0.5, 0.7]).evaluate(
        scores=scores,
        labels=labels,
        episode_ids=episode_ids,
    )

    assert len(policy["threshold_curve"]) == 3
    assert policy["recommended_threshold"] in {0.3, 0.5, 0.7}
    assert policy["threshold_curve"][1]["episode_capture_rate"] == pytest.approx(1.0)


def test_attribution_reports_components_terms_and_top_contributors():
    combined = StressCombiner().combine(
        S_price=0.6,
        S_market=0.5,
        S_macro_anom=0.4,
        S_persist=0.3,
    )
    attribution = StressAttributor().explain(
        components={
            "S_price": 0.6,
            "S_market": 0.5,
            "S_macro_anom": 0.4,
            "S_persist": 0.3,
        },
        combined=combined,
        calibrated_score=0.42,
    )

    assert attribution["components"]["S_price"] == pytest.approx(0.6)
    assert attribution["raw_score"] == pytest.approx(combined.raw_score)
    assert attribution["calibrated_score"] == pytest.approx(0.42)
    assert "interaction_price_market" in attribution["terms"]
    assert len(attribution["top_contributors"]) == 3


def test_stress_posterior_engine_outputs_srd_contract_and_legacy_rollback():
    engine = StressPosteriorEngine()
    guard = MahalanobisGuard()
    history = pd.DataFrame(
        np.random.default_rng(7).normal(size=(90, 3)),
        columns=["pmi_momentum", "labor_slack", "liquidity_velocity"],
        index=pd.bdate_range("2021-01-01", periods=90),
    )
    guard.fit_baseline(history)

    scored = engine.score(
        topology_state=_topology(),
        latest_vector=history.iloc[-1].to_numpy(dtype=float),
        mahalanobis_guard=guard,
        feature_history=history,
    )

    assert set(scored.components) == {"S_price", "S_market", "S_macro_anom", "S_persist"}
    assert 0.0 <= scored.pi_stress_raw <= 1.0
    assert 0.0 <= scored.pi_stress_calibrated <= 1.0
    assert scored.attribution["components"]["S_macro_anom"] == pytest.approx(
        scored.components["S_macro_anom"]
    )

    legacy = StressPosteriorEngine(mode="legacy_topology").score(
        topology_state=_topology(bust_pressure=0.8),
        latest_vector=history.iloc[-1].to_numpy(dtype=float),
        mahalanobis_guard=guard,
        feature_history=history,
    )
    assert legacy.mode == "legacy_topology"
    assert legacy.pi_stress_calibrated == pytest.approx(legacy.pi_stress_raw)


def test_conductor_no_longer_uses_topology_only_stress_probability():
    source = inspect.getsource(V11Conductor.daily_run)
    assert "_topology_stress_probability" not in source
    assert "stress_posterior" in source
