from src.regime_dynamics import compute_probability_dynamics


def test_compute_probability_dynamics_tracks_delta_and_acceleration():
    current = {
        "MID_CYCLE": 0.35,
        "LATE_CYCLE": 0.30,
        "BUST": 0.20,
        "RECOVERY": 0.15,
    }
    previous = {
        "MID_CYCLE": 0.40,
        "LATE_CYCLE": 0.25,
        "BUST": 0.20,
        "RECOVERY": 0.15,
    }
    previous_previous = {
        "MID_CYCLE": 0.50,
        "LATE_CYCLE": 0.20,
        "BUST": 0.18,
        "RECOVERY": 0.12,
    }

    dynamics = compute_probability_dynamics(
        current,
        previous=previous,
        previous_previous=previous_previous,
    )

    assert dynamics["MID_CYCLE"]["probability"] == 0.35
    assert dynamics["MID_CYCLE"]["delta_1d"] == -0.05
    assert dynamics["MID_CYCLE"]["acceleration_1d"] == 0.05
    assert dynamics["MID_CYCLE"]["trend"] == "FALLING"

    assert dynamics["LATE_CYCLE"]["delta_1d"] == 0.05
    assert dynamics["LATE_CYCLE"]["acceleration_1d"] == 0.0
    assert dynamics["LATE_CYCLE"]["trend"] == "RISING"
