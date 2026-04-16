"""Tests for FPR validation anchors (P0-4, Story 3.3/5.3).

SRD 7.5: Treasury Fails + SOFR Volume as independent stress labels.
SRD 7.4 acceptance criterion: FPR < 3% in historical calm periods.

Architecture guard: validation.py MUST NOT import signal/ or engine/.
"""

import ast
import inspect

import numpy as np
import pandas as pd
import pytest

from src.liquidity.backtest.validation import compute_fpr, label_stress_periods


class TestLabelStressPeriods:
    """Stress label generation from independent anchors."""

    @pytest.fixture()
    def sample_data(self):
        """100 days of synthetic data with a 10-day stress period."""
        n = 100
        idx = pd.bdate_range("2020-01-02", periods=n)
        # Calm baseline
        fails = pd.Series(np.ones(n) * 100, index=idx)
        sofr  = pd.Series(np.ones(n) * 500e9, index=idx)
        # Stress spike days 80-89
        fails.iloc[80:90] = 500   # well above 90th pct
        sofr.iloc[80:90]  = 2e12  # well above 95th pct
        return fails, sofr

    def test_output_has_required_columns(self, sample_data):
        fails, sofr = sample_data
        df = label_stress_periods(fails, sofr)
        for col in ["treas_fails_elevated", "sofr_vol_spike", "is_stress_period"]:
            assert col in df.columns

    def test_stress_period_detected(self, sample_data):
        fails, sofr = sample_data
        df = label_stress_periods(fails, sofr)
        # At least some stress days should be flagged
        assert df["is_stress_period"].sum() > 0

    def test_calm_period_not_flagged(self, sample_data):
        """First 50 calm days should have few or no stress flags."""
        fails, sofr = sample_data
        df = label_stress_periods(fails, sofr)
        # First 50 days are all identical (100) — no expanding pct exceedance
        calm_flags = df["is_stress_period"].iloc[:50].sum()
        # Allow for very few false positives from expanding window edge effects
        assert calm_flags < 5, f"Too many false flags in calm period: {calm_flags}"

    def test_boolean_output(self, sample_data):
        fails, sofr = sample_data
        df = label_stress_periods(fails, sofr)
        assert df["is_stress_period"].dtype == bool

    def test_constant_series_no_stress(self):
        """Perfectly constant series → no value can exceed its own expanding quantile."""
        n = 200
        idx = pd.bdate_range("2020-01-02", periods=n)
        const = pd.Series(np.ones(n) * 42.0, index=idx)
        df = label_stress_periods(const, const)
        # Constant series: no value exceeds expanding quantile (value == quantile, not >)
        assert df["is_stress_period"].sum() == 0


class TestComputeFPR:
    """FPR computation against independent labels."""

    def test_zero_fpr_on_perfect_system(self):
        """p_cp always low in calm, high in stress → FPR = 0."""
        idx = pd.bdate_range("2020-01-02", periods=100)
        p_cp = pd.Series(np.full(100, 0.01), index=idx)
        p_cp.iloc[80:90] = 0.70  # high only during stress

        labels = pd.DataFrame({
            "treas_fails_elevated": [False] * 80 + [True] * 10 + [False] * 10,
            "sofr_vol_spike":       [False] * 80 + [True] * 10 + [False] * 10,
            "is_stress_period":     [False] * 80 + [True] * 10 + [False] * 10,
        }, index=idx)

        result = compute_fpr(p_cp, labels, threshold=0.30)
        assert result["fpr"] == 0.0
        assert result["false_alarms"] == 0
        assert result["calm_days"] == 90
        assert result["stress_days"] == 10

    def test_full_fpr_on_noisy_system(self):
        """p_cp always high → FPR = 1.0 (all calm days raise alarm)."""
        idx = pd.bdate_range("2020-01-02", periods=100)
        p_cp = pd.Series(np.full(100, 0.90), index=idx)

        labels = pd.DataFrame({
            "treas_fails_elevated": [False] * 100,
            "sofr_vol_spike":       [False] * 100,
            "is_stress_period":     [False] * 100,
        }, index=idx)

        result = compute_fpr(p_cp, labels, threshold=0.30)
        assert result["fpr"] == 1.0
        assert result["false_alarms"] == 100
        assert result["calm_days"] == 100

    def test_detection_rate_perfect(self):
        """All stress days have p_cp > threshold → detection_rate = 1.0."""
        idx = pd.bdate_range("2020-01-02", periods=50)
        p_cp = pd.Series(np.full(50, 0.01), index=idx)
        p_cp.iloc[40:50] = 0.50  # 10 stress days with high p_cp

        labels = pd.DataFrame({
            "treas_fails_elevated": [False] * 40 + [True] * 10,
            "sofr_vol_spike":       [False] * 40 + [True] * 10,
            "is_stress_period":     [False] * 40 + [True] * 10,
        }, index=idx)

        result = compute_fpr(p_cp, labels, threshold=0.30)
        assert result["detection_rate"] == 1.0
        assert result["true_alarms"] == 10

    def test_result_keys_complete(self):
        """All required keys present in output."""
        idx = pd.bdate_range("2020-01-02", periods=10)
        result = compute_fpr(
            pd.Series(np.zeros(10), index=idx),
            pd.DataFrame({"is_stress_period": [False] * 10,
                          "treas_fails_elevated": [False] * 10,
                          "sofr_vol_spike": [False] * 10}, index=idx),
        )
        required = {"fpr", "calm_days", "false_alarms",
                    "stress_days", "true_alarms", "detection_rate"}
        assert required == set(result.keys())


class TestModuleIsolation:
    """Architecture guard: validation.py must not import from signal/ or engine/."""

    def test_no_signal_imports(self):
        """validation.py does not import anything from src.liquidity.signal."""
        import src.liquidity.backtest.validation as mod
        source = inspect.getsource(mod)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "signal" not in node.module, (
                        f"Forbidden import: {node.module}"
                    )
                    assert "engine" not in node.module, (
                        f"Forbidden import: {node.module}"
                    )
