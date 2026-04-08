from __future__ import annotations

import pandas as pd

from src.research.stabilizer_release_forensics import (
    classify_release_failure,
    summarize_release_failures,
)


def test_classify_release_failure_flags_posterior_trapped_in_bust():
    row = pd.Series(
        {
            "benchmark_regime": "RECOVERY",
            "raw_regime": "BUST",
            "stable_regime": "BUST",
            "price_topology_regime": "RECOVERY",
            "prob_BUST": 0.52,
            "prob_RECOVERY": 0.31,
            "price_topology_confidence": 0.33,
            "price_topology_bearish_divergence": 0.04,
            "price_topology_recovery_prob_acceleration": 0.02,
            "stabilizer_barrier": 0.6,
            "stabilizer_evidence": 0.2,
        }
    )

    assert classify_release_failure(row) == "posterior_trapped_in_bust"


def test_classify_release_failure_flags_bearish_divergence_drag_before_barrier_hold():
    row = pd.Series(
        {
            "benchmark_regime": "RECOVERY",
            "raw_regime": "RECOVERY",
            "stable_regime": "BUST",
            "price_topology_regime": "RECOVERY",
            "prob_BUST": 0.33,
            "prob_RECOVERY": 0.40,
            "price_topology_confidence": 0.29,
            "price_topology_bearish_divergence": 0.34,
            "price_topology_recovery_prob_acceleration": -0.01,
            "stabilizer_barrier": 0.82,
            "stabilizer_evidence": 0.41,
        }
    )

    assert classify_release_failure(row) == "bearish_divergence_drag"


def test_classify_release_failure_flags_stabilizer_barrier_hold_for_confirmed_recovery():
    row = pd.Series(
        {
            "benchmark_regime": "RECOVERY",
            "raw_regime": "RECOVERY",
            "stable_regime": "BUST",
            "price_topology_regime": "RECOVERY",
            "prob_BUST": 0.31,
            "prob_RECOVERY": 0.42,
            "price_topology_confidence": 0.41,
            "price_topology_bearish_divergence": 0.02,
            "price_topology_recovery_prob_acceleration": 0.03,
            "stabilizer_barrier": 0.98,
            "stabilizer_evidence": 0.71,
        }
    )

    assert classify_release_failure(row) == "stabilizer_barrier_hold"


def test_summarize_release_failures_counts_root_causes():
    frame = pd.DataFrame(
        [
            {
                "date": "2023-03-07",
                "benchmark_regime": "RECOVERY",
                "raw_regime": "BUST",
                "stable_regime": "BUST",
                "price_topology_regime": "RECOVERY",
                "prob_BUST": 0.52,
                "prob_RECOVERY": 0.31,
                "price_topology_confidence": 0.33,
                "price_topology_bearish_divergence": 0.04,
                "price_topology_recovery_prob_acceleration": 0.02,
                "stabilizer_barrier": 0.6,
                "stabilizer_evidence": 0.2,
            },
            {
                "date": "2023-03-08",
                "benchmark_regime": "RECOVERY",
                "raw_regime": "RECOVERY",
                "stable_regime": "BUST",
                "price_topology_regime": "RECOVERY",
                "prob_BUST": 0.33,
                "prob_RECOVERY": 0.40,
                "price_topology_confidence": 0.29,
                "price_topology_bearish_divergence": 0.34,
                "price_topology_recovery_prob_acceleration": -0.01,
                "stabilizer_barrier": 0.82,
                "stabilizer_evidence": 0.41,
            },
            {
                "date": "2023-03-09",
                "benchmark_regime": "RECOVERY",
                "raw_regime": "RECOVERY",
                "stable_regime": "BUST",
                "price_topology_regime": "RECOVERY",
                "prob_BUST": 0.31,
                "prob_RECOVERY": 0.42,
                "price_topology_confidence": 0.41,
                "price_topology_bearish_divergence": 0.02,
                "price_topology_recovery_prob_acceleration": 0.03,
                "stabilizer_barrier": 0.98,
                "stabilizer_evidence": 0.71,
            },
        ]
    )

    summary = summarize_release_failures(frame)

    assert summary["failure_rows"] == 3
    assert summary["by_cause"]["posterior_trapped_in_bust"] == 1
    assert summary["by_cause"]["bearish_divergence_drag"] == 1
    assert summary["by_cause"]["stabilizer_barrier_hold"] == 1
