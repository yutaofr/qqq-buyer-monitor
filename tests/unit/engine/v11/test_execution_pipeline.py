import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.execution_pipeline import (
    apply_beta_floor,
    compute_effective_entropy,
    run_execution_pipeline,
)


@pytest.fixture
def snapshot():
    path = Path("tests/fixtures/forensics/snapshot_2026-03-31.json")
    with open(path) as f:
        return json.load(f)


def test_compute_effective_entropy_logic():
    # V14.6 Additive: h + (1.0 - q) * 0.15
    h = 0.4
    q = 0.8
    expected = h + (1.0 - q) * 0.15
    assert compute_effective_entropy(posterior_entropy=h, quality_score=q) == pytest.approx(
        expected
    )


def test_apply_beta_floor_logic():
    # Regular case
    beta, active = apply_beta_floor(pre_floor_beta=0.6, floor=0.5)
    assert beta == 0.6
    assert active is False

    # Floor case
    beta, active = apply_beta_floor(pre_floor_beta=0.4, floor=0.5)
    assert beta == 0.5
    assert active is True

    # Business redline case: crash overlays may not violate the 0.5x floor
    beta, active = apply_beta_floor(pre_floor_beta=0.4, floor=0.5, overlay_state="CRASH")
    assert beta == 0.5
    assert active is True


def test_execution_pipeline_matches_snapshot_floor_and_overlay_order(snapshot):
    # Mocking components
    entropy_ctrl = MagicMock()
    entropy_ctrl.apply_haircut.return_value = 0.7

    posteriors = snapshot["runtime_priors"]
    raw_beta = 0.8
    effective_entropy = 0.5
    overlay = {"beta_overlay_multiplier": 0.9, "overlay_state": "NORMAL"}

    result = run_execution_pipeline(
        raw_beta=raw_beta,
        posterior_entropy=effective_entropy,
        quality_score=1.0,
        posteriors=posteriors,
        entropy_controller=entropy_ctrl,
        overlay=overlay,
        e_sharpe=0.5,
        erp_percentile=0.5,
        high_entropy_streak=5,
    )

    assert result["pre_floor_beta"] == 0.7
    assert result["protected_beta"] == 0.7  # > 0.5
    assert result["is_floor_active"] is False
    assert result["overlay_beta"] == pytest.approx(0.7 * 0.9)


def test_execution_pipeline_updates_high_entropy_streak_correctly():
    # Streak increments if entropy > 0.85
    entropy_ctrl = MagicMock()
    entropy_ctrl.apply_haircut.return_value = 0.5

    # High entropy case
    res1 = run_execution_pipeline(
        raw_beta=0.5,
        posterior_entropy=0.86,
        quality_score=1.0,
        posteriors={"A": 0.5, "B": 0.5},
        entropy_controller=entropy_ctrl,
        overlay={"beta_overlay_multiplier": 1.0},
        e_sharpe=0.5,
        erp_percentile=0.5,
        high_entropy_streak=10,
    )
    assert res1["high_entropy_streak"] == 11

    # Low entropy case
    res2 = run_execution_pipeline(
        raw_beta=0.5,
        posterior_entropy=0.4,
        quality_score=1.0,
        posteriors={"A": 0.5, "B": 0.5},
        entropy_controller=entropy_ctrl,
        overlay={"beta_overlay_multiplier": 1.0},
        e_sharpe=0.5,
        erp_percentile=0.5,
        high_entropy_streak=11,
    )
    assert res2["high_entropy_streak"] == 0


def test_execution_pipeline_reapplies_business_floor_after_negative_overlay():
    entropy_ctrl = MagicMock()
    entropy_ctrl.apply_haircut.return_value = 0.45

    result = run_execution_pipeline(
        raw_beta=0.55,
        posterior_entropy=0.30,
        quality_score=1.0,
        posteriors={"MID_CYCLE": 0.2, "LATE_CYCLE": 0.4, "BUST": 0.4},
        entropy_controller=entropy_ctrl,
        overlay={"beta_overlay_multiplier": 0.5, "overlay_state": "PENALTY"},
        e_sharpe=0.2,
        erp_percentile=0.4,
        high_entropy_streak=0,
    )

    assert result["protected_beta"] == pytest.approx(0.5)
    assert result["overlay_beta"] == pytest.approx(0.5)


def test_entropy_haircut_only_scales_surplus_above_business_floor():
    controller = EntropyController()

    beta = controller.apply_haircut(base_beta=0.8, norm_entropy=1.0, state_count=4)

    assert beta == pytest.approx(0.594717183958671, rel=1e-4)
