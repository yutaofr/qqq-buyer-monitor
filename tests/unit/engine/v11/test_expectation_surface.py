from src.engine.v11.core.expectation_surface import allocate_reference_path


def test_allocate_reference_path_supports_qld_bucket_below_1x_beta():
    allocation = allocate_reference_path(0.80, bucket="QLD", reference_capital=100_000.0)

    assert allocation["qld_notional_dollars"] == 40_000.0
    assert allocation["qqq_dollars"] == 0.0
    assert allocation["cash_dollars"] == 60_000.0


def test_allocate_reference_path_preserves_existing_qqq_mapping():
    allocation = allocate_reference_path(0.80, bucket="QQQ", reference_capital=100_000.0)

    assert allocation["qld_notional_dollars"] == 0.0
    assert allocation["qqq_dollars"] == 80_000.0
    assert allocation["cash_dollars"] == 20_000.0
