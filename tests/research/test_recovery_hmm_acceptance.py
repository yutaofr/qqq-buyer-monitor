from __future__ import annotations

import numpy as np
import pandas as pd

from src.research.recovery_hmm.audit import run_shadow_audit
from src.research.recovery_hmm.variants import WORLDVIEW_OPTIMIZATION_VARIANTS


def _acceptance_frame() -> pd.DataFrame:
    dates = pd.date_range("2021-01-01", "2024-12-31", freq="B")
    frame = pd.DataFrame(index=dates)
    stressed_2022 = (dates >= "2022-01-03") & (dates <= "2022-03-31")
    recovery_2023 = (dates >= "2023-01-03") & (dates <= "2023-02-28")

    frame["hy_ig_spread"] = np.where(stressed_2022, 9.0, np.where(recovery_2023, 1.2, 4.2))
    frame["curve_10y_2y"] = np.where(stressed_2022, -0.9, np.where(recovery_2023, 1.0, 0.1))
    frame["chicago_fci"] = np.where(stressed_2022, 1.4, np.where(recovery_2023, -0.8, 0.15))
    frame["real_yield_10y"] = np.where(stressed_2022, 2.6, np.where(recovery_2023, 0.4, 1.5))
    frame["ism_new_orders"] = np.where(stressed_2022, 40.0, np.where(recovery_2023, 63.0, 49.0))
    frame["ism_inventories"] = np.where(stressed_2022, 60.0, np.where(recovery_2023, 43.0, 52.0))
    frame["vix_3m_1m_ratio"] = np.where(stressed_2022, 0.62, np.where(recovery_2023, 1.35, 0.98))
    frame["qqq_skew_20d_mean"] = np.where(stressed_2022, 1.05, np.where(recovery_2023, 0.28, 0.58))
    return frame


def test_shadow_acceptance_hits_2022_defensive_floor_and_2023_recovery_reacceleration(tmp_path):
    summary = run_shadow_audit(
        training_end="2021-12-31",
        evaluation_start="2022-01-01",
        evaluation_end="2024-12-31",
        artifact_dir=tmp_path,
        raw_frame=_acceptance_frame(),
    )

    assert summary["acceptance"]["q1_2022_below_or_equal_0_5"] is True
    assert summary["acceptance"]["q1_2023_above_or_equal_0_85"] is True


def test_shadow_audit_writes_readout_ready_summary(tmp_path):
    summary = run_shadow_audit(
        training_end="2021-12-31",
        evaluation_start="2022-01-01",
        evaluation_end="2024-12-31",
        artifact_dir=tmp_path,
        raw_frame=_acceptance_frame(),
    )

    assert "decision_gate" in summary


def test_shadow_audit_records_variant_metadata(tmp_path):
    summary = run_shadow_audit(
        training_end="2021-12-31",
        evaluation_start="2022-01-01",
        evaluation_end="2024-12-31",
        artifact_dir=tmp_path,
        raw_frame=_acceptance_frame(),
        variant=WORLDVIEW_OPTIMIZATION_VARIANTS[0],
    )

    assert summary["variant"]["name"] == "stress_hardened"
