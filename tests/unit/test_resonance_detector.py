import pytest

from src.engine.v11.signal.resonance_detector import ResonanceDetector


@pytest.fixture
def detector():
    return ResonanceDetector()

def test_triple_resonance_triggers_buy_qld_after_risk_cliff_entropy_waterfall_and_mid_cycle_surge(
    detector,
):
    posteriors = {"MID_CYCLE": 0.58, "LATE_CYCLE": 0.18, "BUST": 0.08, "RECOVERY": 0.16}
    dynamics = {
        "MID_CYCLE": {"delta_1d": 0.16, "acceleration_1d": 0.09},
        "LATE_CYCLE": {"delta_1d": -0.06, "acceleration_1d": -0.03},
        "BUST": {"delta_1d": -0.14, "acceleration_1d": -0.08},
    }

    result = detector.evaluate(
        posteriors=posteriors,
        dynamics=dynamics,
        effective_entropy=0.32,
        high_entropy_streak=0,
        tractor_prob=0.05,
        sidecar_prob=0.04,
        previous_effective_entropy=0.86,
        risk_context={"tractor_prev": 0.41, "sidecar_prev": 0.34},
    )

    assert result["action"] == "BUY_QLD"
    assert result["confidence"] >= 0.8
    assert result["reason_code"] == "TRIPLE_RESONANCE_BUY"
    assert "QLD" in result["prompt"]


def test_late_cycle_takeover_triggers_sell_qld(detector):
    result = detector.evaluate(
        posteriors={"MID_CYCLE": 0.24, "LATE_CYCLE": 0.51, "BUST": 0.12, "RECOVERY": 0.13},
        dynamics={
            "MID_CYCLE": {"delta_1d": -0.07, "acceleration_1d": -0.03},
            "LATE_CYCLE": {"delta_1d": 0.09, "acceleration_1d": 0.04},
        },
        effective_entropy=0.46,
        high_entropy_streak=0,
        tractor_prob=0.04,
        sidecar_prob=0.03,
        previous_effective_entropy=0.40,
        risk_context={"tractor_prev": 0.03, "sidecar_prev": 0.03},
    )
    assert result["action"] == "SELL_QLD"
    assert result["reason_code"] == "LATE_CYCLE_OVERWHELM"


def test_left_tail_risk_spike_triggers_sell_qld(detector):
    result = detector.evaluate(
        posteriors={"MID_CYCLE": 0.41, "LATE_CYCLE": 0.23, "BUST": 0.18, "RECOVERY": 0.18},
        dynamics={},
        effective_entropy=0.52,
        high_entropy_streak=0,
        tractor_prob=0.18,
        sidecar_prob=0.04,
        previous_effective_entropy=0.49,
        risk_context={"tractor_prev": 0.04, "sidecar_prev": 0.03},
    )
    assert result["action"] == "SELL_QLD"
    assert result["reason_code"] == "LEFT_TAIL_RISK_SPIKE"


def test_entropy_fog_rebuild_triggers_sell_qld(detector):
    result = detector.evaluate(
        posteriors={"MID_CYCLE": 0.31, "LATE_CYCLE": 0.28, "BUST": 0.22, "RECOVERY": 0.19},
        dynamics={},
        effective_entropy=0.81,
        high_entropy_streak=6,
        tractor_prob=0.04,
        sidecar_prob=0.04
    )
    assert result["action"] == "SELL_QLD"
    assert result["reason_code"] == "ENTROPY_FOG"


def test_messy_state_triggers_hold(detector):
    result = detector.evaluate(
        posteriors={"MID_CYCLE": 0.36, "LATE_CYCLE": 0.28, "BUST": 0.21, "RECOVERY": 0.15},
        dynamics={
            "MID_CYCLE": {"delta_1d": 0.01, "acceleration_1d": 0.0},
            "LATE_CYCLE": {"delta_1d": -0.01, "acceleration_1d": 0.0},
            "BUST": {"delta_1d": -0.01, "acceleration_1d": 0.0},
        },
        effective_entropy=0.67,
        previous_effective_entropy=0.70,
        high_entropy_streak=0,
        tractor_prob=0.07,
        sidecar_prob=0.05,
        risk_context={"tractor_prev": 0.08, "sidecar_prev": 0.06},
    )
    assert result["action"] == "HOLD"
