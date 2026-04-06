import pytest

from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper


def test_inertial_beta_mapper_never_returns_below_business_floor():
    mapper = InertialBetaMapper(initial_beta=0.49)

    beta = mapper.calculate_inertial_beta(0.45, normalized_entropy=0.20)

    assert beta == pytest.approx(0.5)


def test_inertial_beta_mapper_can_escape_high_entropy_deleveraging_lock():
    mapper = InertialBetaMapper(initial_beta=0.75)

    beta = None
    for _ in range(4):
        beta = mapper.calculate_inertial_beta(0.5, normalized_entropy=0.85)

    assert beta is not None
    assert beta <= 0.55
