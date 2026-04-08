from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.recovery_hmm.feature_space import build_feature_space


@pytest.fixture
def sample_macro_frame() -> pd.DataFrame:
    dates = pd.date_range("2021-01-01", periods=40, freq="B")
    return pd.DataFrame(
        {
            "hy_ig_spread": np.linspace(4.5, 2.0, len(dates)),
            "curve_10y_2y": np.linspace(-0.2, 1.1, len(dates)),
            "chicago_fci": np.linspace(0.8, -0.3, len(dates)),
            "real_yield_10y": np.linspace(1.8, 0.9, len(dates)),
            "ism_new_orders": np.linspace(45.0, 58.0, len(dates)),
            "ism_inventories": np.linspace(53.0, 47.0, len(dates)),
            "vix_3m_1m_ratio": np.linspace(0.9, 1.3, len(dates)),
            "qqq_skew_20d_mean": np.linspace(0.7, 0.4, len(dates)),
        },
        index=dates,
    )


def test_feature_space_emits_locked_domain_columns(sample_macro_frame):
    frame = build_feature_space(sample_macro_frame)

    expected = {
        "L1_hy_ig_spread",
        "L2_curve_10y_2y",
        "L3_chicago_fci",
        "V1_spread_compression_velocity",
        "V2_real_yield_velocity",
        "V3_orders_inventory_gap",
        "S1_vix_term_ratio",
        "S2_qqq_skew_mean",
    }
    assert expected.issubset(frame.columns)


def test_feature_space_fails_closed_on_missing_required_columns(sample_macro_frame):
    broken = sample_macro_frame.drop(columns=["qqq_skew_20d_mean"])

    with pytest.raises(ValueError, match="Missing required recovery HMM columns"):
        build_feature_space(broken)
