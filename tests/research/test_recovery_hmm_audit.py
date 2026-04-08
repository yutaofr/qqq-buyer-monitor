from __future__ import annotations

import numpy as np
import pandas as pd

from src.research.recovery_hmm.audit import _domain_scores, run_shadow_audit


def _sample_raw_frame() -> pd.DataFrame:
    dates = pd.date_range("2021-01-01", "2024-12-31", freq="B")
    frame = pd.DataFrame(index=dates)
    stressed_2022 = (dates >= "2022-01-03") & (dates <= "2022-03-31")
    recovery_2023 = (dates >= "2023-01-03") & (dates <= "2023-02-28")

    frame["hy_ig_spread"] = np.where(stressed_2022, 8.0, np.where(recovery_2023, 2.0, 4.0))
    frame["curve_10y_2y"] = np.where(stressed_2022, -0.5, np.where(recovery_2023, 0.8, 0.1))
    frame["chicago_fci"] = np.where(stressed_2022, 1.2, np.where(recovery_2023, -0.6, 0.1))
    frame["real_yield_10y"] = np.where(stressed_2022, 2.4, np.where(recovery_2023, 0.8, 1.4))
    frame["ism_new_orders"] = np.where(stressed_2022, 42.0, np.where(recovery_2023, 60.0, 50.0))
    frame["ism_inventories"] = np.where(stressed_2022, 58.0, np.where(recovery_2023, 45.0, 51.0))
    frame["vix_3m_1m_ratio"] = np.where(stressed_2022, 0.7, np.where(recovery_2023, 1.2, 0.95))
    frame["qqq_skew_20d_mean"] = np.where(stressed_2022, 0.95, np.where(recovery_2023, 0.35, 0.55))
    return frame


def test_shadow_audit_respects_training_cutoff_and_oos_window(tmp_path):
    summary = run_shadow_audit(
        training_end="2021-12-31",
        evaluation_start="2022-01-01",
        evaluation_end="2024-12-31",
        artifact_dir=tmp_path,
        raw_frame=_sample_raw_frame(),
    )

    assert summary["training_end"] == "2021-12-31"
    assert summary["evaluation_start"] == "2022-01-01"
    assert summary["evaluation_end"] == "2024-12-31"


def test_domain_scores_sharpen_recovery_when_velocity_turns_positive_under_bad_levels():
    row = pd.Series(
        {
            "L1_hy_ig_spread": 4.1,
            "L2_curve_10y_2y": -0.8,
            "L3_chicago_fci": -0.31,
            "V1_spread_compression_velocity": 0.4,
            "V2_real_yield_velocity": -0.2,
            "V3_orders_inventory_gap": -1.0,
            "S1_vix_term_ratio": 1.11,
            "S2_qqq_skew_mean": 0.45,
        }
    )

    probabilities = _domain_scores(row)

    assert probabilities["RECOVERY"] > 0.7
    assert probabilities["RECOVERY"] > probabilities["BUST"]
