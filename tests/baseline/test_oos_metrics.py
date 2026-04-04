import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score
from src.engine.baseline.validation import (
    generate_baseline_target,
    run_ac2_label_permutation_test,
    run_ac2_leakage_detection,
)
from src.engine.baseline.execution import calculate_baseline_oos_series
from src.engine.baseline.sidecar import generate_sidecar_target

def test_ac2_random_convergence():
    """
    Verify that AC-2 label permutation results in AUC near 0.5.
    Uses true walk-forward across synthetic data.
    Increased sample size to avoid TimeSeriesSplit issues.
    """
    rng = np.random.default_rng(42)
    n = 600
    dates = pd.date_range("2010-01-01", periods=n, freq="B")
    X = pd.DataFrame({
        "growth": rng.standard_normal(n),
        "liquidity": rng.standard_normal(n),
        "stress": rng.standard_normal(n)
    }, index=dates)
    
    y = pd.Series(rng.choice([0, 1], size=n), index=dates)
    
    # Run AC-2 with fewer shuffles for speed in tests
    mean_auc = run_ac2_label_permutation_test(X, y, n_shuffles=2)
    
    # Check if within [0.35, 0.65] range
    assert 0.35 <= mean_auc <= 0.65, f"AC-2 failed: Random AUC was {mean_auc:.4f}"

def test_ac2_leakage_detection():
    """
    Verify that leakage detection correctly identifies leaky vs PIT-safe handling.
    """
    results = run_ac2_leakage_detection()
    assert "pit_safe_auc" in results
    assert "leaky_auc" in results
    # With many features, leaky AUC should be significantly higher (often > 0.8) 
    # while PIT-safe remains near 0.5
    assert results["leaky_auc"] > results["pit_safe_auc"] + 0.1
    assert results["leakage_detected"] is True


def test_sidecar_target_invalidates_incomplete_future_windows():
    """
    Verify that the sidecar target does not silently degrade into drawdown-only
    when the future VXN window is incomplete.
    """
    n = 80
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    qqq = pd.Series(np.linspace(100.0, 110.0, n), index=dates)
    vxn = pd.Series(20.0, index=dates)
    vxn.iloc[40:50] = np.nan

    y = generate_sidecar_target(qqq, vxn, horizon=20)

    # Early window is complete and should be valid.
    assert pd.notna(y.iloc[10])

    # This window looks into the missing VXN band and must be invalid.
    assert pd.isna(y.iloc[25])

    # Tail remains invalid because the horizon cannot be fully observed.
    assert pd.isna(y.iloc[-1])


def test_sidecar_target_aligns_price_and_vxn_by_date():
    price_dates = pd.date_range("2020-06-01", periods=30, freq="B")
    vxn_dates = pd.date_range("2020-01-01", periods=180, freq="B")

    qqq = pd.Series(100.0, index=price_dates)
    vxn = pd.Series(20.0, index=vxn_dates)
    vxn.loc[pd.Timestamp("2020-06-10")] = 40.0

    y = generate_sidecar_target(qqq, vxn, horizon=10)

    assert y.loc[pd.Timestamp("2020-06-01")] == 1


def test_baseline_target_aligns_price_and_vix_by_date():
    price_dates = pd.date_range("2020-06-01", periods=30, freq="B")
    vix_dates = pd.date_range("2020-01-01", periods=180, freq="B")

    spy = pd.Series(100.0, index=price_dates)
    vix = pd.Series(15.0, index=vix_dates)
    vix.loc[pd.Timestamp("2020-06-10")] = 35.0

    y = generate_baseline_target(spy, vix, horizon=10)

    assert y.loc[pd.Timestamp("2020-06-01")] == 1


def test_sidecar_validity_tracking():
    """
    Verify that calculate_baseline_oos_series correctly tracks ^VXN availability.
    Provides full feature set to satisfy composite calculation.
    """
    rng = np.random.default_rng(42)
    n = 800
    dates = pd.date_range("2010-01-01", periods=n, freq="B")
    # Provide all columns needed by calculate_composites
    data = pd.DataFrame({
        "IPMAN": rng.standard_normal(n),
        "growth_margin": rng.standard_normal(n),
        "M2REAL": rng.standard_normal(n),
        "T10Y2Y": rng.standard_normal(n),
        "BAMLH0A0HYM2": rng.standard_normal(n),
        "VIXCLS": rng.standard_normal(n),
        "^VXN": rng.standard_normal(n)
    }, index=dates)
    
    # Inject missing ^VXN at the end
    data.loc[dates[-50:], "^VXN"] = np.nan
    
    target_spy = pd.Series(rng.choice([0, 1], size=n), index=dates)
    target_qqq = pd.Series(rng.choice([0, 1], size=n), index=dates)
    
    # Start OOS after enough training data
    oos_start = dates[600].strftime("%Y-%m-%d")
    results = calculate_baseline_oos_series(data, target_spy, target_qqq, start_date=oos_start)
    
    # First part of OOS should be valid
    valid_mask = results.index < dates[-50]
    invalid_mask = (results.index >= dates[-50]) & (results.index < dates[-1]) # Avoid last point which might be ffilled if I'm not careful, but execution.py now returns NaN
    
    assert results.loc[valid_mask, "sidecar_valid"].all()
    # In my execution.py update:
    # res.loc[current_dt, "sidecar_prob"] = np.nan
    # res.loc[current_dt, "sidecar_valid"] = False
    
    # Check that sidecar_valid is False for invalid mask
    assert not results.loc[invalid_mask, "sidecar_valid"].any()
    assert results.loc[invalid_mask, "sidecar_prob"].isna().all()
