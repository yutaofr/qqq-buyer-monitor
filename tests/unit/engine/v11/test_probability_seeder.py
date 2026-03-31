import numpy as np
import pandas as pd
import pytest

from src.engine.v11.probability_seeder import ProbabilitySeeder


@pytest.fixture
def sample_macro_df():
    dates = pd.date_range("2020-01-01", periods=1000, freq="D")
    df = pd.DataFrame(index=dates)
    # Generate some synthetic random walk data
    df["erp_pct"] = np.random.normal(0, 1, 1000).cumsum() + 3.0
    df["real_yield_10y_pct"] = np.random.normal(0, 0.1, 1000).cumsum() + 1.5
    df["credit_spread_bps"] = np.random.normal(0, 5, 1000).cumsum() + 500
    df["net_liquidity_usd_bn"] = np.random.normal(0, 10, 1000).cumsum() + 4000
    df.index.name = "date"
    return df

def test_seeder_factor_generation(sample_macro_df):
    """验证 Seeder 只生成当前生产允许的低噪声核心因子。"""
    seeder = ProbabilitySeeder()
    # 注入数据并生成特征
    features_df = seeder.generate_features(sample_macro_df)

    expected_cols = [
        "spread_21d",
        "liquidity_252d",
        "real_yield_structural_z",
        "erp_absolute",
        "spread_absolute",
        "yield_absolute",
    ]

    assert list(features_df.columns) == expected_cols
    for col in expected_cols:
        assert col in features_df.columns
        # 验证无 NaN
        assert not features_df[col].isna().any()
        assert features_df[col].between(-8.0, 8.0).all()

def test_seeder_timezone_alignment():
    """验证 Seeder 强制执行 tz-naive 对齐以防回测偏差"""
    seeder = ProbabilitySeeder()
    df_utc = pd.DataFrame(
        {"erp_pct": [3.0, 3.1]},
        index=pd.to_datetime(["2020-01-01", "2020-01-02"], utc=True)
    )

    processed = seeder._normalize_index(df_utc)
    assert processed.index.tz is None
    assert processed.index[0].hour == 0

def test_seeder_look_ahead_prevention(sample_macro_df):
    """验证 Seeder 使用动态滚动窗口，不含未来信息"""
    seeder = ProbabilitySeeder()
    # 切割数据到特定日期
    limit_date = pd.to_datetime("2020-06-01")
    full_features = seeder.generate_features(sample_macro_df)

    half_macro = sample_macro_df[sample_macro_df.index <= limit_date]
    half_features = seeder.generate_features(half_macro)

    # 在 limit_date 这一天的值应当完全一致
    pd.testing.assert_series_equal(
        full_features.loc[limit_date],
        half_features.loc[limit_date],
        check_names=False
    )


def test_seeder_is_deterministic(sample_macro_df):
    """同一份输入重复执行时，特征种子必须严格一致。"""
    seeder = ProbabilitySeeder()

    first = seeder.generate_features(sample_macro_df)
    second = seeder.generate_features(sample_macro_df)

    pd.testing.assert_frame_equal(first, second)


def test_seeder_contract_hash_is_stable():
    seeder = ProbabilitySeeder()

    first = seeder.contract_hash()
    second = seeder.contract_hash()

    assert first == second
    assert first.startswith("sha256:")
