import pytest
import json
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock
from src.engine.v11.core.execution_pipeline import (
    compute_effective_entropy,
    compute_pre_floor_beta,
    apply_beta_floor,
    compute_overlay_beta,
    compute_deployment_readiness,
    run_execution_pipeline
)

@pytest.fixture
def snapshot():
    path = Path("tests/fixtures/forensics/snapshot_2026-03-31.json")
    with open(path) as f:
        return json.load(f)

def test_compute_effective_entropy_logic():
    # 1.0 - ((1.0 - h) * q)
    h = 0.4
    q = 0.8
    expected = 1.0 - ((1.0 - h) * q)
    assert compute_effective_entropy(posterior_entropy=h, quality_score=q) == pytest.approx(expected)

def test_apply_beta_floor_logic():
    # Regular case
    beta, active = apply_beta_floor(pre_floor_beta=0.6, floor=0.5)
    assert beta == 0.6
    assert active is False
    
    # Floor case
    beta, active = apply_beta_floor(pre_floor_beta=0.4, floor=0.5)
    assert beta == 0.5
    assert active is True
    
    # Crash case
    beta, active = apply_beta_floor(pre_floor_beta=0.4, floor=0.0, overlay_state="CRASH")
    assert beta == 0.4 # max(0.0, 0.4)
    assert active is False

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
        high_entropy_streak=5
    )
    
    assert result["pre_floor_beta"] == 0.7
    assert result["protected_beta"] == 0.7 # > 0.5
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
        high_entropy_streak=10
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
        high_entropy_streak=11
    )
    assert res2["high_entropy_streak"] == 0
