import pandas as pd

from src.engine.v11.core.feature_library import FeatureLibraryManager


def test_feature_library_resets_index_after_append(tmp_path):
    manager = FeatureLibraryManager(storage_path=str(tmp_path / "v11_library.csv"))
    manager.df = pd.DataFrame(
        [
            {
                "observation_date": pd.Timestamp("2020-01-01"),
                "credit_spread_bps": 400.0,
                "vix": 15.0,
                "vix3m": 18.0,
                "drawdown_pct": -0.01,
                "breadth_proxy": 0.55,
                "liquidity_roc_pct_4w": 0.02,
            },
            {
                "observation_date": pd.Timestamp("2020-01-02"),
                "credit_spread_bps": 410.0,
                "vix": 16.0,
                "vix3m": 18.5,
                "drawdown_pct": -0.02,
                "breadth_proxy": 0.50,
                "liquidity_roc_pct_4w": 0.01,
            },
        ],
        index=[10, 11],
    )

    manager.update_library(
        pd.Series(
            {
                "observation_date": pd.Timestamp("2020-01-03"),
                "credit_spread_bps": 430.0,
                "vix": 18.0,
                "vix3m": 17.0,
                "drawdown_pct": -0.05,
                "breadth_proxy": 0.40,
                "liquidity_roc_pct_4w": -0.03,
            }
        )
    )

    assert list(manager.df.index) == [0, 1, 2]
