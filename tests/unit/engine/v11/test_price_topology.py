from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine.v11.core.price_topology import (
    PriceTopologyState,
    align_posteriors_with_recovery_process,
    anchor_beta_with_topology,
    blend_posteriors_with_topology,
    infer_price_topology_state,
    price_topology_payload,
    topology_likelihood_penalties,
)


def _context_frame(close: np.ndarray, volume: np.ndarray) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=len(close))
    return pd.DataFrame(
        {
            "observation_date": dates,
            "qqq_close": close,
            "qqq_volume": volume,
        }
    )


def test_price_topology_delevers_bust_structure():
    close = np.concatenate([np.linspace(100.0, 165.0, 200), np.linspace(165.0, 92.0, 120)])
    volume = np.concatenate(
        [np.linspace(900_000.0, 1_000_000.0, 200), np.linspace(1_100_000.0, 1_600_000.0, 120)]
    )
    topology = infer_price_topology_state(_context_frame(close, volume))

    base_posteriors = {
        "MID_CYCLE": 0.65,
        "LATE_CYCLE": 0.20,
        "BUST": 0.10,
        "RECOVERY": 0.05,
    }
    blended = blend_posteriors_with_topology(base_posteriors, topology)
    anchored_beta = anchor_beta_with_topology(0.98, topology)

    assert topology.regime == "BUST"
    assert topology.confidence > 0.0
    assert blended["BUST"] > base_posteriors["BUST"]
    assert anchored_beta < 0.98
    assert anchored_beta >= 0.5


def test_price_topology_reaccelerates_recovery_structure():
    close = np.concatenate(
        [
            np.linspace(100.0, 160.0, 180),
            np.linspace(160.0, 108.0, 70),
            np.linspace(108.0, 148.0, 70),
        ]
    )
    volume = np.concatenate(
        [
            np.linspace(950_000.0, 1_050_000.0, 180),
            np.linspace(1_200_000.0, 1_700_000.0, 70),
            np.linspace(1_600_000.0, 1_250_000.0, 70),
        ]
    )
    topology = infer_price_topology_state(_context_frame(close, volume))

    base_posteriors = {
        "MID_CYCLE": 0.15,
        "LATE_CYCLE": 0.45,
        "BUST": 0.25,
        "RECOVERY": 0.15,
    }
    blended = blend_posteriors_with_topology(base_posteriors, topology)
    anchored_beta = anchor_beta_with_topology(0.72, topology)

    assert topology.regime == "RECOVERY"
    assert blended["RECOVERY"] > base_posteriors["RECOVERY"]
    assert anchored_beta > 0.72


def test_price_topology_edge_regimes_receive_amplified_coupling():
    close = np.concatenate(
        [
            np.linspace(100.0, 160.0, 180),
            np.linspace(160.0, 108.0, 70),
            np.linspace(108.0, 148.0, 70),
        ]
    )
    volume = np.concatenate(
        [
            np.linspace(950_000.0, 1_050_000.0, 180),
            np.linspace(1_200_000.0, 1_700_000.0, 70),
            np.linspace(1_600_000.0, 1_250_000.0, 70),
        ]
    )
    topology = infer_price_topology_state(_context_frame(close, volume))

    assert topology.regime == "RECOVERY"
    assert topology.posterior_blend_weight > 0.25 * topology.confidence
    assert topology.beta_anchor_weight > 0.35 * topology.confidence


def test_price_topology_edge_regime_receives_likelihood_bonus():
    close = np.concatenate(
        [
            np.linspace(100.0, 160.0, 180),
            np.linspace(160.0, 108.0, 70),
            np.linspace(108.0, 148.0, 70),
        ]
    )
    volume = np.concatenate(
        [
            np.linspace(950_000.0, 1_050_000.0, 180),
            np.linspace(1_200_000.0, 1_700_000.0, 70),
            np.linspace(1_600_000.0, 1_250_000.0, 70),
        ]
    )
    topology = infer_price_topology_state(_context_frame(close, volume))
    penalties = topology_likelihood_penalties(topology)

    assert topology.regime == "RECOVERY"
    assert penalties["RECOVERY"] > 1.0


def test_price_topology_is_neutral_without_price_columns():
    dates = pd.bdate_range("2024-01-01", periods=40)
    frame = pd.DataFrame({"observation_date": dates, "credit_spread_bps": np.linspace(300.0, 350.0, 40)})

    topology = infer_price_topology_state(frame)
    blended = blend_posteriors_with_topology(
        {"MID_CYCLE": 0.6, "LATE_CYCLE": 0.2, "BUST": 0.1, "RECOVERY": 0.1},
        topology,
    )

    assert topology.confidence == 0.0
    assert topology.posterior_blend_weight == 0.0
    assert topology.beta_anchor_weight == 0.0
    assert blended["MID_CYCLE"] == 0.6


def test_price_topology_dampens_when_transition_band_is_wide(monkeypatch):
    dates = pd.bdate_range("2024-01-01", periods=5)
    frame = pd.DataFrame(
        {
            "observation_date": dates,
            "qqq_close": np.linspace(100.0, 110.0, len(dates)),
            "qqq_volume": np.linspace(1_000_000.0, 1_100_000.0, len(dates)),
        }
    )

    def _benchmark_with_transition(transition_intensity: float) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "benchmark_regime": ["RECOVERY"],
                "benchmark_expected_beta": [1.0],
                "benchmark_transition_intensity": [transition_intensity],
                "benchmark_prob_MID_CYCLE": [0.18],
                "benchmark_prob_LATE_CYCLE": [0.07],
                "benchmark_prob_BUST": [0.10],
                "benchmark_prob_RECOVERY": [0.65],
            },
            index=[dates[-1]],
        )

    monkeypatch.setattr(
        "src.engine.v11.core.price_topology.build_worldview_benchmark",
        lambda _: _benchmark_with_transition(0.05),
    )
    low_transition = infer_price_topology_state(frame)

    monkeypatch.setattr(
        "src.engine.v11.core.price_topology.build_worldview_benchmark",
        lambda _: _benchmark_with_transition(0.90),
    )
    high_transition = infer_price_topology_state(frame)

    assert high_transition.transition_intensity > low_transition.transition_intensity
    assert high_transition.confidence < low_transition.confidence
    assert high_transition.posterior_blend_weight < low_transition.posterior_blend_weight
    assert high_transition.beta_anchor_weight < low_transition.beta_anchor_weight


def test_price_topology_preserves_recovery_confidence_during_repair_confirmed_transition(monkeypatch):
    dates = pd.bdate_range("2024-01-01", periods=5)
    frame = pd.DataFrame(
        {
            "observation_date": dates,
            "qqq_close": np.linspace(100.0, 110.0, len(dates)),
            "qqq_volume": np.linspace(1_000_000.0, 1_100_000.0, len(dates)),
        }
    )

    benchmark = pd.DataFrame(
        {
            "benchmark_regime": ["RECOVERY"],
            "benchmark_expected_beta": [0.78],
            "benchmark_transition_intensity": [0.95],
            "benchmark_prob_MID_CYCLE": [0.03],
            "benchmark_prob_LATE_CYCLE": [0.09],
            "benchmark_prob_BUST": [0.42],
            "benchmark_prob_RECOVERY": [0.46],
            "benchmark_recovery_impulse": [0.38],
            "benchmark_recent_damage": [0.82],
            "benchmark_bust_pressure": [0.28],
            "benchmark_bullish_rsi_divergence": [0.0],
            "benchmark_bearish_rsi_divergence": [0.0],
            "benchmark_prob_delta_RECOVERY": [-0.01],
            "benchmark_prob_acceleration_RECOVERY": [0.01],
        },
        index=[dates[-1]],
    )

    monkeypatch.setattr(
        "src.engine.v11.core.price_topology.build_worldview_benchmark",
        lambda _: benchmark,
    )
    topology = infer_price_topology_state(frame)

    assert topology.regime == "RECOVERY"
    assert topology.repair_persistence > 0.30
    assert topology.confidence >= 0.12
    assert topology.posterior_blend_weight >= 0.015


def test_price_topology_promotes_recovery_when_bust_lead_is_only_transition_noise(monkeypatch):
    dates = pd.bdate_range("2024-01-01", periods=5)
    frame = pd.DataFrame(
        {
            "observation_date": dates,
            "qqq_close": np.linspace(100.0, 110.0, len(dates)),
            "qqq_volume": np.linspace(1_000_000.0, 1_100_000.0, len(dates)),
        }
    )

    benchmark = pd.DataFrame(
        {
            "benchmark_regime": ["BUST"],
            "benchmark_expected_beta": [0.76],
            "benchmark_transition_intensity": [0.95],
            "benchmark_prob_MID_CYCLE": [0.03],
            "benchmark_prob_LATE_CYCLE": [0.06],
            "benchmark_prob_BUST": [0.46],
            "benchmark_prob_RECOVERY": [0.45],
            "benchmark_recovery_impulse": [0.39],
            "benchmark_recent_damage": [0.82],
            "benchmark_bust_pressure": [0.28],
            "benchmark_bullish_rsi_divergence": [0.0],
            "benchmark_bearish_rsi_divergence": [0.0],
            "benchmark_prob_delta_RECOVERY": [-0.01],
            "benchmark_prob_acceleration_RECOVERY": [0.01],
        },
        index=[dates[-1]],
    )

    monkeypatch.setattr(
        "src.engine.v11.core.price_topology.build_worldview_benchmark",
        lambda _: benchmark,
    )
    topology = infer_price_topology_state(frame)

    assert topology.repair_persistence > 0.30
    assert topology.regime == "RECOVERY"
    assert topology.probabilities["RECOVERY"] > topology.probabilities["BUST"]


def test_recovery_process_alignment_moves_posterior_toward_confirmed_repair():
    topology = PriceTopologyState(
        regime="RECOVERY",
        probabilities={
            "MID_CYCLE": 0.17,
            "LATE_CYCLE": 0.12,
            "BUST": 0.16,
            "RECOVERY": 0.55,
        },
        expected_beta=0.95,
        confidence=0.55,
        posterior_blend_weight=0.18,
        beta_anchor_weight=0.22,
        transition_intensity=0.72,
        recovery_impulse=0.92,
        damage_memory=0.84,
        bust_pressure=0.18,
        bullish_divergence=0.63,
        bearish_divergence=0.08,
        recovery_prob_delta=0.045,
        recovery_prob_acceleration=0.018,
    )
    posteriors = {
        "MID_CYCLE": 0.22,
        "LATE_CYCLE": 0.31,
        "BUST": 0.29,
        "RECOVERY": 0.18,
    }

    corrected = align_posteriors_with_recovery_process(posteriors, topology)

    assert corrected["RECOVERY"] > posteriors["RECOVERY"]
    assert corrected["RECOVERY"] <= topology.probabilities["RECOVERY"]
    assert corrected["LATE_CYCLE"] < posteriors["LATE_CYCLE"]
    assert corrected["BUST"] < posteriors["BUST"]
    assert sum(corrected.values()) == pytest.approx(1.0)


def test_recovery_process_alignment_stays_neutral_without_repair_confirmation():
    topology = PriceTopologyState(
        regime="RECOVERY",
        probabilities={
            "MID_CYCLE": 0.16,
            "LATE_CYCLE": 0.14,
            "BUST": 0.20,
            "RECOVERY": 0.50,
        },
        expected_beta=0.9,
        confidence=0.4,
        posterior_blend_weight=0.12,
        beta_anchor_weight=0.16,
        transition_intensity=0.68,
        recovery_impulse=0.08,
        damage_memory=0.11,
        bust_pressure=0.76,
        bullish_divergence=0.05,
        bearish_divergence=0.44,
        recovery_prob_delta=-0.01,
        recovery_prob_acceleration=-0.01,
    )
    posteriors = {
        "MID_CYCLE": 0.24,
        "LATE_CYCLE": 0.30,
        "BUST": 0.27,
        "RECOVERY": 0.19,
    }

    corrected = align_posteriors_with_recovery_process(posteriors, topology)

    assert corrected == pytest.approx(posteriors)


def test_recovery_process_alignment_releases_bust_overhang_more_aggressively():
    topology = PriceTopologyState(
        regime="RECOVERY",
        probabilities={
            "MID_CYCLE": 0.10,
            "LATE_CYCLE": 0.14,
            "BUST": 0.28,
            "RECOVERY": 0.48,
        },
        expected_beta=0.78,
        confidence=0.24,
        posterior_blend_weight=0.03,
        beta_anchor_weight=0.05,
        transition_intensity=0.74,
        recovery_impulse=0.44,
        damage_memory=0.84,
        bust_pressure=0.29,
        bullish_divergence=0.0,
        bearish_divergence=0.0,
        recovery_prob_delta=0.026,
        recovery_prob_acceleration=-0.002,
    )
    posteriors = {
        "MID_CYCLE": 0.09,
        "LATE_CYCLE": 0.30,
        "BUST": 0.39,
        "RECOVERY": 0.22,
    }

    corrected = align_posteriors_with_recovery_process(posteriors, topology)

    assert corrected["RECOVERY"] > 0.45
    assert corrected["RECOVERY"] > corrected["BUST"] + 0.12
    assert corrected["LATE_CYCLE"] < 0.17


def test_recovery_process_alignment_preserves_repair_persistence_through_mild_fade():
    topology = PriceTopologyState(
        regime="RECOVERY",
        probabilities={
            "MID_CYCLE": 0.14,
            "LATE_CYCLE": 0.14,
            "BUST": 0.18,
            "RECOVERY": 0.54,
        },
        expected_beta=0.84,
        confidence=0.32,
        posterior_blend_weight=0.08,
        beta_anchor_weight=0.12,
        transition_intensity=0.81,
        recovery_impulse=0.54,
        damage_memory=0.82,
        bust_pressure=0.24,
        bullish_divergence=0.18,
        bearish_divergence=0.0,
        recovery_prob_delta=0.018,
        recovery_prob_acceleration=-0.006,
    )
    posteriors = {
        "MID_CYCLE": 0.15,
        "LATE_CYCLE": 0.31,
        "BUST": 0.25,
        "RECOVERY": 0.29,
    }

    corrected = align_posteriors_with_recovery_process(posteriors, topology)

    assert corrected["RECOVERY"] >= 0.52
    assert corrected["LATE_CYCLE"] <= 0.15
    assert corrected["BUST"] <= 0.19


def test_recovery_process_alignment_flips_realistic_bust_overhang_when_repair_is_confirmed():
    topology = PriceTopologyState(
        regime="RECOVERY",
        probabilities={
            "MID_CYCLE": 0.08,
            "LATE_CYCLE": 0.26,
            "BUST": 0.285,
            "RECOVERY": 0.378,
        },
        expected_beta=0.75,
        confidence=0.27,
        posterior_blend_weight=0.04,
        beta_anchor_weight=0.06,
        transition_intensity=0.77,
        recovery_impulse=0.21,
        damage_memory=0.82,
        bust_pressure=0.17,
        bullish_divergence=0.0,
        bearish_divergence=0.0,
        recovery_prob_delta=-0.009,
        recovery_prob_acceleration=-0.027,
        repair_persistence=0.33,
    )
    posteriors = {
        "MID_CYCLE": 0.078,
        "LATE_CYCLE": 0.165,
        "BUST": 0.379,
        "RECOVERY": 0.378,
    }

    corrected = align_posteriors_with_recovery_process(posteriors, topology)

    assert corrected["RECOVERY"] > corrected["BUST"]
    assert corrected["RECOVERY"] >= 0.40
    assert corrected["BUST"] <= 0.355


def test_recovery_process_alignment_extends_recovery_edge_through_mild_negative_acceleration():
    topology = PriceTopologyState(
        regime="RECOVERY",
        probabilities={
            "MID_CYCLE": 0.084,
            "LATE_CYCLE": 0.325,
            "BUST": 0.188,
            "RECOVERY": 0.403,
        },
        expected_beta=0.78,
        confidence=0.44,
        posterior_blend_weight=0.06,
        beta_anchor_weight=0.10,
        transition_intensity=0.80,
        recovery_impulse=0.267,
        damage_memory=0.82,
        bust_pressure=0.13,
        bullish_divergence=0.0,
        bearish_divergence=0.0,
        recovery_prob_delta=0.0013,
        recovery_prob_acceleration=-0.0233,
        repair_persistence=0.359,
    )
    posteriors = {
        "MID_CYCLE": 0.084,
        "LATE_CYCLE": 0.187,
        "BUST": 0.325,
        "RECOVERY": 0.403,
    }

    corrected = align_posteriors_with_recovery_process(posteriors, topology)

    assert corrected["RECOVERY"] >= 0.44
    assert corrected["RECOVERY"] - corrected["BUST"] >= 0.12


def test_price_topology_payload_exposes_release_diagnostics():
    topology = PriceTopologyState(
        regime="RECOVERY",
        probabilities={
            "MID_CYCLE": 0.18,
            "LATE_CYCLE": 0.14,
            "BUST": 0.21,
            "RECOVERY": 0.47,
        },
        expected_beta=0.88,
        confidence=0.42,
        posterior_blend_weight=0.11,
        beta_anchor_weight=0.17,
        transition_intensity=0.61,
        recovery_impulse=0.29,
        damage_memory=0.73,
        bust_pressure=0.22,
        bullish_divergence=0.41,
        bearish_divergence=0.06,
        recovery_prob_delta=0.032,
        recovery_prob_acceleration=0.014,
    )

    payload = price_topology_payload(topology)

    assert payload["bullish_divergence"] == pytest.approx(0.41)
    assert payload["bearish_divergence"] == pytest.approx(0.06)
    assert payload["recovery_prob_delta"] == pytest.approx(0.032)
    assert payload["recovery_prob_acceleration"] == pytest.approx(0.014)
    assert payload["repair_persistence"] > 0.0
