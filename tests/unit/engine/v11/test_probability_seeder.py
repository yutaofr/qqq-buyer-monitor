import numpy as np
import pandas as pd
import pytest

from src.engine.v11.probability_seeder import ProbabilitySeeder


@pytest.fixture
def sample_macro_df():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2020-01-01", periods=1000, freq="D")
    monthly_block = np.repeat(np.linspace(10.0, 25.0, 34), 30)[: len(dates)]
    df = pd.DataFrame(index=dates)
    df["real_yield_10y_pct"] = 0.01 + np.linspace(0.0, 0.02, len(dates))
    df["treasury_vol_21d"] = 0.004 + np.linspace(0.0, 0.006, len(dates))
    df["breakeven_10y"] = 0.018 + np.sin(np.linspace(0.0, 18.0, len(dates))) * 0.004
    df["core_capex_mm"] = monthly_block
    df["copper_gold_ratio"] = 0.16 + np.linspace(0.0, 0.05, len(dates)) + rng.normal(0.0, 0.001, len(dates))
    df["usdjpy"] = 110.0 + np.linspace(0.0, 25.0, len(dates)) + rng.normal(0.0, 0.3, len(dates))
    df["credit_spread_bps"] = 300.0 + np.linspace(0.0, 180.0, len(dates)) + rng.normal(0.0, 4.0, len(dates))
    df["net_liquidity_usd_bn"] = 4000.0 + np.linspace(0.0, 250.0, len(dates))
    df["erp_ttm_pct"] = 0.035 + np.sin(np.linspace(0.0, 12.0, len(dates))) * 0.004
    df.index.name = "date"
    return df


def test_seeder_factor_generation(sample_macro_df):
    """v12 seeder must emit the locked 10-factor orthogonal observation vector."""
    seeder = ProbabilitySeeder()
    features_df = seeder.generate_features(sample_macro_df)

    expected_cols = [
        "real_yield_structural_z",
        "move_21d",
        "breakeven_accel",
        "core_capex_momentum",
        "copper_gold_roc_126d",
        "usdjpy_roc_126d",
        "spread_21d",
        "liquidity_252d",
        "erp_absolute",
        "spread_absolute",
    ]

    assert list(features_df.columns) == expected_cols
    for col in expected_cols:
        assert col in features_df.columns
        assert not features_df[col].isna().any()
        assert features_df[col].between(-8.0, 8.0).all()

    assert "yield_absolute" not in features_df.columns


def test_seeder_timezone_alignment():
    """Seeder must normalize timestamps to tz-naive midnight."""
    seeder = ProbabilitySeeder()
    df_utc = pd.DataFrame(
        {"erp_ttm_pct": [0.03, 0.031]},
        index=pd.to_datetime(["2020-01-01", "2020-01-02"], utc=True),
    )

    processed = seeder._normalize_index(df_utc)
    assert processed.index.tz is None
    assert processed.index[0].hour == 0


def test_seeder_look_ahead_prevention(sample_macro_df):
    """Rolling/expanding statistics must be causal at the cutoff date."""
    seeder = ProbabilitySeeder()
    limit_date = pd.to_datetime("2020-06-01")
    full_features = seeder.generate_features(sample_macro_df)

    half_macro = sample_macro_df[sample_macro_df.index <= limit_date]
    half_features = seeder.generate_features(half_macro)

    pd.testing.assert_series_equal(
        full_features.loc[limit_date],
        half_features.loc[limit_date],
        check_names=False,
    )


def test_seeder_is_deterministic(sample_macro_df):
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


def test_move_is_orthogonalized_against_spread():
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    spread = pd.Series(np.linspace(-2.0, 3.0, len(dates)), index=dates)
    macro_df = pd.DataFrame(
        {
            "real_yield_10y_pct": 0.01 + np.linspace(0.0, 0.005, len(dates)),
            "treasury_vol_21d": 0.004 + spread.values * 0.0015,
            "breakeven_10y": 0.02 + np.sin(np.linspace(0.0, 10.0, len(dates))) * 0.002,
            "core_capex_mm": np.repeat(np.linspace(10.0, 18.0, 14), 30)[: len(dates)],
            "copper_gold_ratio": 0.18 + np.linspace(0.0, 0.01, len(dates)),
            "usdjpy": 120.0 + np.linspace(0.0, 10.0, len(dates)),
            "credit_spread_bps": 350.0 + spread.values * 20.0,
            "net_liquidity_usd_bn": 4000.0 + np.linspace(0.0, 100.0, len(dates)),
            "erp_ttm_pct": 0.035 + np.linspace(0.0, 0.002, len(dates)),
        },
        index=dates,
    )

    seeder = ProbabilitySeeder()
    features = seeder.generate_features(macro_df)

    assert features["move_21d"].corr(features["spread_21d"]) < 0.95
    assert not features["move_21d"].equals(features["spread_21d"])
