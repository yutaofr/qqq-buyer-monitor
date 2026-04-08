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


def test_regime_stabilizer_can_release_from_bust_into_recovery_with_confirmed_repair():
    stabilizer = RegimeStabilizer(initial_regime="BUST")
    release_hint = {
        "topology_regime": "RECOVERY",
        "recovery_impulse": 0.46,
        "damage_memory": 0.82,
        "bust_pressure": 0.39,
        "bearish_divergence": 0.0,
        "transition_intensity": 0.61,
    }

    first = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.01,
            "LATE_CYCLE": 0.10,
            "BUST": 0.52,
            "RECOVERY": 0.37,
        },
        entropy=0.72,
        release_hint=release_hint,
    )
    second = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.02,
            "LATE_CYCLE": 0.11,
            "BUST": 0.50,
            "RECOVERY": 0.37,
        },
        entropy=0.74,
        release_hint=release_hint,
    )

    assert first["raw_regime"] == "BUST"
    assert first["stable_regime"] == "BUST"
    assert second["raw_regime"] == "BUST"
    assert second["stable_regime"] == "RECOVERY"
    assert second["switched"] is True


def test_regime_stabilizer_does_not_release_without_repair_confirmation():
    stabilizer = RegimeStabilizer(initial_regime="BUST")
    release_hint = {
        "topology_regime": "BUST",
        "recovery_impulse": 0.08,
        "damage_memory": 0.12,
        "bust_pressure": 0.71,
        "bearish_divergence": 0.33,
        "transition_intensity": 0.22,
    }

    result = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.03,
            "LATE_CYCLE": 0.13,
            "BUST": 0.49,
            "RECOVERY": 0.35,
        },
        entropy=0.74,
        release_hint=release_hint,
    )

    assert result["raw_regime"] == "BUST"
    assert result["stable_regime"] == "BUST"
    assert result["switched"] is False


def test_regime_stabilizer_preserves_release_evidence_through_bust_retests():
    stabilizer = RegimeStabilizer(initial_regime="BUST")
    release_hint = {
        "topology_regime": "RECOVERY",
        "recovery_impulse": 0.48,
        "damage_memory": 0.84,
        "bust_pressure": 0.33,
        "bearish_divergence": 0.0,
        "transition_intensity": 0.72,
    }

    first = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.01,
            "LATE_CYCLE": 0.08,
            "BUST": 0.49,
            "RECOVERY": 0.42,
        },
        entropy=0.85,
        release_hint=release_hint,
    )
    second = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.02,
            "LATE_CYCLE": 0.10,
            "BUST": 0.53,
            "RECOVERY": 0.35,
        },
        entropy=0.88,
        release_hint=release_hint,
    )
    third = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.02,
            "LATE_CYCLE": 0.10,
            "BUST": 0.47,
            "RECOVERY": 0.41,
        },
        entropy=0.87,
        release_hint=release_hint,
    )

    assert first["stable_regime"] == "BUST"
    assert second["stable_regime"] == "BUST"
    assert third["raw_regime"] == "BUST"
    assert third["stable_regime"] == "RECOVERY"
    assert third["switched"] is True


def test_regime_stabilizer_releases_when_recovery_is_fully_confirmed_but_barrier_is_still_high():
    stabilizer = RegimeStabilizer(initial_regime="BUST")
    release_hint = {
        "topology_regime": "RECOVERY",
        "topology_confidence": 0.42,
        "recovery_impulse": 0.35,
        "damage_memory": 0.82,
        "bust_pressure": 0.12,
        "bearish_divergence": 0.0,
        "transition_intensity": 0.31,
        "repair_persistence": 0.45,
    }

    result = stabilizer.update(
        posteriors={
            "MID_CYCLE": 0.07,
            "LATE_CYCLE": 0.26,
            "BUST": 0.28,
            "RECOVERY": 0.39,
        },
        entropy=0.89,
        release_hint=release_hint,
    )

    assert result["raw_regime"] == "RECOVERY"
    assert result["stable_regime"] == "RECOVERY"
    assert result["switched"] is True
