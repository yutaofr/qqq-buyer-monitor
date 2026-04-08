from __future__ import annotations

import numpy as np
import pandas as pd

from src.research.recovery_hmm.orthogonalization import fit_transform_rolling_pca


def test_rolling_pca_keeps_components_until_85pct_variance():
    dates = pd.date_range("2020-01-01", periods=600, freq="B")
    base = np.linspace(-2.0, 2.0, len(dates))
    frame = pd.DataFrame(
        {
            "L1_hy_ig_spread": base,
            "L2_curve_10y_2y": base * 0.8 + 0.1,
            "L3_chicago_fci": base * -0.6,
            "V1_spread_compression_velocity": np.sin(np.linspace(0, 12, len(dates))),
            "V2_real_yield_velocity": np.cos(np.linspace(0, 10, len(dates))),
            "V3_orders_inventory_gap": base * 0.2 + np.sin(np.linspace(0, 6, len(dates))),
            "S1_vix_term_ratio": np.linspace(0.8, 1.2, len(dates)),
            "S2_qqq_skew_mean": np.linspace(0.6, 0.3, len(dates)),
        },
        index=dates,
    )

    result = fit_transform_rolling_pca(frame, window=504, variance_threshold=0.85)

    assert result.component_count >= 1
    assert result.explained_variance_ratio_sum >= 0.85
    assert result.transformed.shape[0] == frame.shape[0] - 503
