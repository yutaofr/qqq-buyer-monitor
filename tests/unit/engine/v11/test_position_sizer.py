import math

from src.engine.v11.core.position_sizer import ProbabilisticPositionSizer


def test_position_sizer_shrinks_target_beta_when_entropy_rises():
    sizer = ProbabilisticPositionSizer()

    concentrated = {
        "BUST": 0.05,
        "LATE_CYCLE": 0.05,
        "MID_CYCLE": 0.10,
        "RECOVERY": 0.10,
        "CAPITULATION": 0.70,
    }
    uncertain = {name: 0.20 for name in concentrated}

    low_entropy = sizer.size_positions(
        posteriors=concentrated,
        reference_capital=100_000.0,
        current_nav=100_000.0,
        previous_target_beta=0.80,
    )
    high_entropy = sizer.size_positions(
        posteriors=uncertain,
        reference_capital=100_000.0,
        current_nav=100_000.0,
        previous_target_beta=0.80,
    )

    assert low_entropy.target_beta > high_entropy.target_beta
    assert low_entropy.entropy < high_entropy.entropy


def test_position_sizer_anchors_risk_to_reference_capital_after_drawdown():
    sizer = ProbabilisticPositionSizer()
    posteriors = {
        "BUST": 0.0,
        "LATE_CYCLE": 0.0,
        "MID_CYCLE": 0.0,
        "RECOVERY": 0.0,
        "CAPITULATION": 1.0,
    }

    result = sizer.size_positions(
        posteriors=posteriors,
        reference_capital=100_000.0,
        current_nav=60_000.0,
        previous_target_beta=1.05,
    )

    assert result.reference_capital == 100_000.0
    assert result.current_nav == 60_000.0
    assert result.risk_budget_dollars <= 115_000.0
    assert math.isclose(
        result.cash_dollars + result.qqq_dollars + result.qld_notional_dollars,
        result.current_nav,
        rel_tol=1e-6,
    )


def test_position_sizer_caps_daily_beta_shift():
    sizer = ProbabilisticPositionSizer(max_daily_beta_shift=0.10)
    posteriors = {
        "BUST": 0.0,
        "LATE_CYCLE": 0.0,
        "MID_CYCLE": 0.0,
        "RECOVERY": 0.0,
        "CAPITULATION": 1.0,
    }

    result = sizer.size_positions(
        posteriors=posteriors,
        reference_capital=100_000.0,
        current_nav=100_000.0,
        previous_target_beta=0.40,
    )

    assert result.target_beta == 0.50
