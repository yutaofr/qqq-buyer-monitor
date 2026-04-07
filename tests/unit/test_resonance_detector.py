import pytest

from src.engine.v11.signal.resonance_detector import ResonanceDetector


@pytest.fixture
def detector():
    return ResonanceDetector()

def test_triple_resonance_triggers_buy_qld(detector):
    """
    BUY_QLD requirements:
    1. Risk Clearance: tractor + sidecar < 0.05 AND vix_ratio < 1.0
    2. Entropy Collapse: effective_entropy < 0.65 AND streak == 0
    3. Mid-Cycle Dominance: MID > 0.40 AND MID > LATE AND delta_1d(MID) > 0
    """
    posteriors = {"MID_CYCLE": 0.45, "LATE_CYCLE": 0.20, "BUST": 0.15, "RECOVERY": 0.20}
    dynamics = {
        "MID_CYCLE": {"delta_1d": 0.02, "acceleration_1d": 0.01},
        "LATE_CYCLE": {"delta_1d": -0.01, "acceleration_1d": -0.01}
    }

    result = detector.evaluate(
        posteriors=posteriors,
        dynamics=dynamics,
        effective_entropy=0.60,
        high_entropy_streak=0,
        tractor_prob=0.02,
        sidecar_prob=0.02
    )

    assert result["action"] == "BUY_QLD"
    assert result["confidence"] > 0.70

def test_single_risk_spike_triggers_sell_qld(detector):
    """
    SELL_QLD requirements:
    1. Risk Spike: tractor > 0.15 OR sidecar > 0.10
    OR Entropy Loss: entropy > 0.75
    OR Late Cycle Overwhelm: LATE > 0.40
    """
    # Case 1: Tractor Risk
    result = detector.evaluate(
        posteriors={"MID_CYCLE": 0.30, "LATE_CYCLE": 0.30, "BUST": 0.20, "RECOVERY": 0.20},
        dynamics={},
        effective_entropy=0.70,
        high_entropy_streak=0,
        tractor_prob=0.16,
        sidecar_prob=0.02
    )
    assert result["action"] == "SELL_QLD"

    # Case 2: Entropy Spike
    result = detector.evaluate(
        posteriors={"MID_CYCLE": 0.30, "LATE_CYCLE": 0.30, "BUST": 0.20, "RECOVERY": 0.20},
        dynamics={},
        effective_entropy=0.80,
        high_entropy_streak=5,
        tractor_prob=0.02,
        sidecar_prob=0.02
    )
    assert result["action"] == "SELL_QLD"

def test_messy_state_triggers_hold(detector):
    """
    Default to HOLD if resonance is not reached.
    """
    # High entropy but not yet SELL threshold
    result = detector.evaluate(
        posteriors={"MID_CYCLE": 0.30, "LATE_CYCLE": 0.30, "BUST": 0.20, "RECOVERY": 0.20},
        dynamics={},
        effective_entropy=0.70,
        high_entropy_streak=0,
        tractor_prob=0.04,
        sidecar_prob=0.04
    )
    assert result["action"] == "HOLD"
