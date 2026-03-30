
from src.engine.v11.signal.regime_stabilizer import RegimeStabilizer


def test_regime_stabilizer_holds_state_under_high_entropy_noise():
    stabilizer = RegimeStabilizer(initial_regime="MID_CYCLE")

    result = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.28,
            "LATE_CYCLE": 0.31,
            "BUST": 0.14,
            "CAPITULATION": 0.13,
            "RECOVERY": 0.14,
        },
        entropy=0.96,
    )

    assert result["raw_regime"] == "LATE_CYCLE"
    assert result["stable_regime"] == "MID_CYCLE"
    assert result["switched"] is False


def test_regime_stabilizer_switches_when_evidence_is_decisive():
    stabilizer = RegimeStabilizer(initial_regime="MID_CYCLE")

    first = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.15,
            "LATE_CYCLE": 0.72,
            "BUST": 0.04,
            "CAPITULATION": 0.04,
            "RECOVERY": 0.05,
        },
        entropy=0.42,
    )

    assert first["stable_regime"] == "LATE_CYCLE"
    assert first["switched"] is True
