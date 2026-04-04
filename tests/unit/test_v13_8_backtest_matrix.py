from __future__ import annotations

import pytest
import pandas as pd
import scripts.run_v13_backtest_matrix as matrix_script

def test_judge_acceptance_passes_on_perfect_parity():
    baseline = {
        "mode": "DISABLED",
        "left_tail_mean_beta": 0.5,
        "penalty_days": 10.0,
        "reward_days": 5.0,
    }
    current = {
        "mode": "FULL",
        "max_raw_target_beta_delta_vs_disabled": 0.0,
        "left_tail_mean_beta": 0.45, # Defensive: lower is better
        "penalty_days": 15.0,
        "reward_days": 5.0, # Defensive asymmetry: rewards <= penalties
    }
    
    # This should pass
    passed, reason = matrix_script.judge_acceptance(current, baseline)
    assert passed is True
    assert reason == "PASS"

def test_judge_acceptance_fails_on_canonical_drift():
    baseline = {"mode": "DISABLED", "left_tail_mean_beta": 0.5, "penalty_days": 10.0, "reward_days": 5.0}
    current = {
        "mode": "FULL",
        "max_raw_target_beta_delta_vs_disabled": 0.001, # Drift!
        "left_tail_mean_beta": 0.45,
        "penalty_days": 15.0,
        "reward_days": 5.0,
    }
    
    passed, reason = matrix_script.judge_acceptance(current, baseline)
    assert passed is False
    assert "Canonical Drift" in reason

def test_judge_acceptance_fails_on_aggressive_left_tail():
    baseline = {"mode": "DISABLED", "left_tail_mean_beta": 0.5, "penalty_days": 10.0, "reward_days": 5.0}
    current = {
        "mode": "FULL",
        "max_raw_target_beta_delta_vs_disabled": 0.0,
        "left_tail_mean_beta": 0.55, # Aggressive: higher is bad in left tail
        "penalty_days": 15.0,
        "reward_days": 5.0,
    }
    
    passed, reason = matrix_script.judge_acceptance(current, baseline)
    assert passed is False
    assert "Defensive Violation" in reason

def test_judge_acceptance_fails_on_optimism_bias():
    baseline = {"mode": "DISABLED", "left_tail_mean_beta": 0.5, "penalty_days": 10.0, "reward_days": 5.0}
    current = {
        "mode": "FULL",
        "max_raw_target_beta_delta_vs_disabled": 0.0,
        "left_tail_mean_beta": 0.45,
        "penalty_days": 10.0,
        "reward_days": 11.0, # Optimism: more rewards than penalties
    }
    
    passed, reason = matrix_script.judge_acceptance(current, baseline)
    assert passed is False
    assert "Optimism Bias" in reason
