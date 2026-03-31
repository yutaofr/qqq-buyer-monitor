import src.engine.v11.core.position_sizer as position_sizer


def test_legacy_probabilistic_position_sizer_is_retired():
    assert not hasattr(position_sizer, "ProbabilisticPositionSizer")
