import pandas as pd
import pytest

from src.research.data_contracts import (
    summarize_regime_state_support,
    validate_regime_state_support,
)
from src.research.v12_diagnostics import (
    DEFAULT_CRISIS_WINDOWS,
    build_v12_diagnostic_report,
)


@pytest.fixture
def label_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": pd.to_datetime(
                [
                    "2018-10-01",
                    "2018-10-02",
                    "2020-03-02",
                    "2020-03-03",
                    "2022-01-03",
                    "2022-01-04",
                ]
            ),
            "regime": [
                "LATE_CYCLE",
                "BUST",
                "BUST",
                "RECOVERY",
                "MID_CYCLE",
                "LATE_CYCLE",
            ],
        }
    )


@pytest.fixture
def audit_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2018-10-01",
                    "2018-10-02",
                    "2020-03-02",
                    "2020-03-03",
                    "2022-01-03",
                    "2022-01-04",
                ]
            ),
            "actual_regime": [
                "LATE_CYCLE",
                "BUST",
                "BUST",
                "RECOVERY",
                "MID_CYCLE",
                "LATE_CYCLE",
            ],
            "predicted_regime": [
                "LATE_CYCLE",
                "BUST",
                "LATE_CYCLE",
                "RECOVERY",
                "MID_CYCLE",
                "MID_CYCLE",
            ],
            "raw_regime": [
                "LATE_CYCLE",
                "BUST",
                "LATE_CYCLE",
                "RECOVERY",
                "MID_CYCLE",
                "LATE_CYCLE",
            ],
            "stable_regime": [
                "LATE_CYCLE",
                "BUST",
                "BUST",
                "RECOVERY",
                "MID_CYCLE",
                "MID_CYCLE",
            ],
            "target_beta": [0.8, 0.5, 0.55, 0.9, 1.0, 0.85],
            "raw_target_beta": [0.9, 0.65, 0.7, 0.95, 1.0, 0.9],
            "entropy": [0.30, 0.25, 0.20, 0.18, 0.22, 0.28],
            "brier": [0.20, 0.15, 0.35, 0.18, 0.12, 0.31],
            "lock_active": [False, False, False, True, False, False],
            "close": [100.0, 97.0, 90.0, 95.0, 110.0, 108.0],
            "prob_BUST": [0.20, 0.62, 0.45, 0.05, 0.08, 0.18],
            "prob_CAPITULATION": [0.0] * 6,
            "prob_RECOVERY": [0.05, 0.03, 0.08, 0.72, 0.05, 0.04],
            "prob_LATE_CYCLE": [0.60, 0.28, 0.42, 0.10, 0.15, 0.39],
            "prob_MID_CYCLE": [0.15, 0.07, 0.05, 0.13, 0.72, 0.39],
        }
    )


@pytest.fixture
def feature_diag_frame() -> pd.DataFrame:
    dates = pd.to_datetime(
        [
            "2018-10-01",
            "2018-10-02",
            "2020-03-02",
            "2020-03-03",
            "2022-01-03",
            "2022-01-04",
        ]
    )
    return pd.DataFrame(
        {
            "move_21d_raw_z": [1.0, 1.2, 2.2, 2.0, 0.8, 0.7],
            "move_21d_orth_z": [0.9, 1.1, 1.6, 1.5, 0.7, 0.6],
            "move_spread_beta": [0.15, 0.16, 0.14, 0.13, 0.17, 0.16],
            "move_spread_corr_21d": [0.5, 0.55, 0.62, 0.58, 0.35, 0.33],
        },
        index=dates,
    )


def test_validate_regime_state_support_rejects_unsupported_audit_regimes(label_frame):
    with pytest.raises(ValueError, match="CAPITULATION"):
        validate_regime_state_support(
            label_frame,
            audit_regimes=["BUST", "CAPITULATION", "RECOVERY", "LATE_CYCLE", "MID_CYCLE"],
        )


def test_summarize_regime_state_support_reports_unsupported_regime(label_frame):
    report = summarize_regime_state_support(
        label_frame,
        audit_regimes=["BUST", "CAPITULATION", "RECOVERY", "LATE_CYCLE", "MID_CYCLE"],
    )

    assert report["label_regimes"] == ["BUST", "LATE_CYCLE", "MID_CYCLE", "RECOVERY"]
    assert report["unsupported_audit_regimes"] == ["CAPITULATION"]
    assert report["supported_regimes"] == ["BUST", "LATE_CYCLE", "MID_CYCLE", "RECOVERY"]


def test_build_v12_diagnostic_report_includes_protocol_sections(
    audit_frame,
    label_frame,
    feature_diag_frame,
):
    report = build_v12_diagnostic_report(
        audit_frame,
        label_frame=label_frame,
        audit_regimes=["BUST", "CAPITULATION", "RECOVERY", "LATE_CYCLE", "MID_CYCLE"],
        feature_diag_frame=feature_diag_frame,
    )

    assert report["summary"]["compared_points"] == len(audit_frame)
    assert report["summary"]["top1_accuracy"] == pytest.approx(4 / 6)
    assert report["state_support"]["unsupported_audit_regimes"] == ["CAPITULATION"]
    assert "2018Q4" in report["crisis_windows"]
    assert "2020_COVID" in report["crisis_windows"]
    assert "2022_H1" in report["crisis_windows"]
    assert report["critical_regime_performance"]["raw_critical_recall"] == pytest.approx(1.0)
    assert report["critical_regime_performance"]["stable_critical_recall"] == pytest.approx(0.75)
    assert "overall" in report["beta_comparison"]
    assert "2020_COVID" in report["beta_comparison"]["windows"]
    assert "overall" in report["entropy"]
    assert "2020_COVID" in report["feature_diagnostics"]["windows"]
    assert report["feature_diagnostics"]["windows"]["2020_COVID"]["mean_move_spread_beta"] == pytest.approx(0.135)


def test_default_crisis_windows_cover_required_protocol_periods():
    assert tuple(DEFAULT_CRISIS_WINDOWS) == ("2018Q4", "2020_COVID", "2022_H1")
