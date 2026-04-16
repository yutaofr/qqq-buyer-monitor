"""Tests for Asymmetric EMA (AEMA) filter (Story 4.1).

SRD v1.2 Section 4.2:
  s_t = alpha_up   * p_cp + (1 - alpha_up)   * s_{t-1}  if p_cp > s_{t-1}
  s_t = alpha_down * p_cp + (1 - alpha_down) * s_{t-1}  if p_cp <= s_{t-1}

alpha_up=0.50   → fast risk elevation (half-life ≈ 1 step)
alpha_down=0.08 → slow decay (half-life ≈ 8.3 steps)
"""

import numpy as np
import pytest

from src.liquidity.control.aema import run_aema_series, update_aema


class TestUpdateAEMA:
    """Unit tests for single-step AEMA update."""

    def test_rising_uses_alpha_up(self):
        """p_cp > s_prev → new_s = alpha_up * p_cp + (1 - alpha_up) * s_prev."""
        s_prev = 0.10
        p_cp = 0.50
        alpha_up = 0.50
        alpha_down = 0.08
        result = update_aema(s_prev, p_cp, alpha_up, alpha_down)
        expected = alpha_up * p_cp + (1 - alpha_up) * s_prev
        np.testing.assert_allclose(result, expected, atol=1e-12)

    def test_falling_uses_alpha_down(self):
        """p_cp < s_prev → new_s = alpha_down * p_cp + (1 - alpha_down) * s_prev."""
        s_prev = 0.60
        p_cp = 0.10
        alpha_up = 0.50
        alpha_down = 0.08
        result = update_aema(s_prev, p_cp, alpha_up, alpha_down)
        expected = alpha_down * p_cp + (1 - alpha_down) * s_prev
        np.testing.assert_allclose(result, expected, atol=1e-12)

    def test_equal_uses_alpha_down(self):
        """p_cp == s_prev → falling branch (no change)."""
        s_prev = 0.30
        result = update_aema(s_prev, 0.30, alpha_up=0.50, alpha_down=0.08)
        expected = 0.08 * 0.30 + 0.92 * 0.30
        np.testing.assert_allclose(result, expected, atol=1e-12)

    def test_output_bounded_01(self):
        """AEMA must stay in [0, 1] for input in [0, 1]."""
        for p in [0.0, 0.001, 0.5, 0.999, 1.0]:
            for s in [0.0, 0.3, 1.0]:
                r = update_aema(s, p, 0.50, 0.08)
                assert 0.0 <= r <= 1.0, f"Out of [0,1]: update_aema({s}, {p}) = {r}"

    def test_fast_rise_slow_fall(self):
        """Spike then calm: stress rises quickly, decays slowly."""
        s = 0.01
        # One large spike
        s = update_aema(s, 0.80, alpha_up=0.50, alpha_down=0.08)
        s_after_spike = s
        # Five calm steps
        for _ in range(5):
            s = update_aema(s, 0.01, alpha_up=0.50, alpha_down=0.08)
        # Should still be well above initial level (slow decay)
        assert s > 0.20, (
            f"Stress decayed too fast: s={s:.4f} after 5 calm steps from {s_after_spike:.4f}"
        )

    def test_default_params_analytic(self):
        """Exact analytic check with SRD params: alpha_up=0.50, alpha_down=0.08."""
        s = update_aema(0.0, 1.0, alpha_up=0.50, alpha_down=0.08)
        np.testing.assert_allclose(s, 0.50, atol=1e-12)  # 0.5*1 + 0.5*0 = 0.5


class TestRunAEMASeries:
    """Vectorised series version of AEMA update."""

    def test_output_length_matches_input(self):
        import pandas as pd
        p_series = pd.Series([0.01, 0.50, 0.10, 0.05, 0.02])
        out = run_aema_series(p_series, s0=0.0, alpha_up=0.50, alpha_down=0.08)
        assert len(out) == len(p_series)

    def test_monotone_rising_stays_high(self):
        """Monotone p_cp=0.8 → s_t converges to 0.8 from below (alpha_up=0.5).
        After 10 steps from s0=0: s ≈ 0.8*(1 - 0.5^10) ≈ 0.799.
        """
        import pandas as pd
        p = pd.Series([0.8] * 10)
        s = run_aema_series(p, s0=0.0, alpha_up=0.50, alpha_down=0.08)
        expected = 0.8 * (1 - 0.5 ** 10)
        np.testing.assert_allclose(s.iloc[-1], expected, atol=1e-6)
        assert s.iloc[-1] > 0.79

    def test_zero_input_decays_from_initial(self):
        """p_cp=0 always → exponential decay from s0."""
        import pandas as pd
        p = pd.Series([0.0] * 20)
        s = run_aema_series(p, s0=0.50, alpha_up=0.50, alpha_down=0.08)
        # s decays by (1 - 0.08)^20 ≈ 0.19 factor
        expected_approx = 0.50 * (1 - 0.08) ** 20
        np.testing.assert_allclose(s.iloc[-1], expected_approx, atol=1e-8)

    def test_first_element_correct(self):
        """First output element = update_aema(s0, p[0])."""
        import pandas as pd
        p = pd.Series([0.30])
        s = run_aema_series(p, s0=0.10, alpha_up=0.50, alpha_down=0.08)
        expected = update_aema(0.10, 0.30, 0.50, 0.08)
        np.testing.assert_allclose(s.iloc[0], expected, atol=1e-12)


class TestCircuitBreakerBypass:
    """SRD 4.1: p_cp > circuit_breaker → bypass AEMA entirely."""

    def test_above_threshold_returns_raw(self):
        """p_cp=0.85 > CB=0.70 → output = 0.85 exactly (no smoothing)."""
        s = update_aema(0.10, 0.85, alpha_up=0.50, alpha_down=0.08,
                        circuit_breaker=0.70)
        np.testing.assert_allclose(s, 0.85, atol=1e-12)

    def test_below_threshold_uses_ema(self):
        """p_cp=0.60 < CB=0.70 → normal EMA (not bypass)."""
        s = update_aema(0.10, 0.60, alpha_up=0.50, alpha_down=0.08,
                        circuit_breaker=0.70)
        expected = 0.50 * 0.60 + 0.50 * 0.10  # alpha_up branch
        np.testing.assert_allclose(s, expected, atol=1e-12)

    def test_state_updated_to_crisis_level(self):
        """After bypass, next calm step decays from crisis value (Option A).

        Step 1: p_cp=0.85 > CB=0.70 → s=0.85 (bypass)
        Step 2: p_cp=0.01 < CB=0.70 → s = 0.08*0.01 + 0.92*0.85 = 0.7828
        The system remembers the crisis.
        """
        s = update_aema(0.10, 0.85, 0.50, 0.08, circuit_breaker=0.70)
        assert s == pytest.approx(0.85)

        s_next = update_aema(s, 0.01, 0.50, 0.08, circuit_breaker=0.70)
        expected = 0.08 * 0.01 + 0.92 * 0.85  # alpha_down from crisis level
        np.testing.assert_allclose(s_next, expected, atol=1e-12)
        assert s_next > 0.78, "State must decay slowly from crisis peak"

    def test_exactly_at_threshold_not_bypassed(self):
        """p_cp=0.70 == CB=0.70 → normal EMA (bypass is strictly >)."""
        s = update_aema(0.30, 0.70, 0.50, 0.08, circuit_breaker=0.70)
        expected = 0.50 * 0.70 + 0.50 * 0.30
        np.testing.assert_allclose(s, expected, atol=1e-12)

    def test_series_with_circuit_breaker(self):
        """Verify bypass in series mode."""
        import pandas as pd
        p = pd.Series([0.01, 0.01, 0.85, 0.01])
        s = run_aema_series(p, s0=0.0, alpha_up=0.50, alpha_down=0.08,
                            circuit_breaker=0.70)
        # Step 3 (index 2): p=0.85 > 0.70 → bypass, s=0.85
        np.testing.assert_allclose(s.iloc[2], 0.85, atol=1e-12)
        # Step 4 (index 3): p=0.01, slow decay from 0.85
        assert s.iloc[3] > 0.78

