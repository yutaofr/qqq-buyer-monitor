from src.utils.stats import calculate_zscore


def test_calculate_zscore_basic():
    # Provide 20 elements: 19 zeros and then 100
    series = [0] * 19 + [100]
    # Mean: 5, Std: 22.36
    # Z = (100 - 5) / 22.36 = 4.24
    zs = calculate_zscore(100, series)
    assert 4.0 <= zs <= 4.5


def test_calculate_zscore_empty():
    assert calculate_zscore(50, []) == 0.0


def test_calculate_zscore_insufficient():
    assert calculate_zscore(50, [1, 2, 3]) == 0.0


def test_calculate_zscore_zero_std():
    assert (
        calculate_zscore(
            10, [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        )
        == 0.0
    )
