from __future__ import annotations

import numpy as np
import pandas as pd

from src.engine.v11.core.price_topology import (
    anchor_beta_with_topology,
    blend_posteriors_with_topology,
    infer_price_topology_state,
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
