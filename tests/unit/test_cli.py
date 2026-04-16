from __future__ import annotations

from datetime import date

from src.models import SignalResult, TargetAllocationState
from src.output.cli import print_signal


def test_print_signal_includes_probability_dynamics(capsys):
    result = SignalResult(
        date=date(2026, 4, 6),
        price=500.0,
        target_beta=0.8,
        probabilities={"MID_CYCLE": 0.35, "LATE_CYCLE": 0.30, "BUST": 0.20, "RECOVERY": 0.15},
        priors={"MID_CYCLE": 0.25, "LATE_CYCLE": 0.25, "BUST": 0.25, "RECOVERY": 0.25},
        entropy=0.88,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.2, 0.8, 0.0, 0.8),
        logic_trace=[],
        explanation="demo",
        metadata={
            "probability_dynamics": {
                "MID_CYCLE": {"delta_1d": -0.05, "acceleration_1d": 0.05, "trend": "FALLING"},
                "LATE_CYCLE": {"delta_1d": 0.05, "acceleration_1d": 0.0, "trend": "RISING"},
            }
        },
    )

    print_signal(result, use_color=False)
    out = capsys.readouterr().out

    assert "Probability Dynamics" in out
    assert "MID_CYCLE" in out
    assert "dP=-5.0%" in out


def test_print_signal_uses_canonical_decision_for_top_action(capsys):
    result = SignalResult(
        date=date(2026, 4, 16),
        price=637.47,
        target_beta=1.599,
        probabilities={"LATE_CYCLE": 0.54, "BUST": 0.43, "RECOVERY": 0.03},
        priors={},
        entropy=0.58,
        stable_regime="LATE_CYCLE",
        target_allocation=TargetAllocationState(0.0, 0.401, 0.599, 1.599),
        logic_trace=[],
        explanation="demo",
        metadata={
            "v14_standard_beta": 0.58,
            "canonical_decision": {
                "source": "v16_topology",
                "reason": "V16 topology process is clean.",
            },
        },
    )

    print_signal(result, use_color=False)
    out = capsys.readouterr().out

    assert "Action:  Official Beta 1.60x (v16_topology)" in out
    assert "[S4 Protective" in out
