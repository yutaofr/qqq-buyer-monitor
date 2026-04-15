"""Smoke tests for config loader (Story 1.1 / T1.1.4)."""

from src.liquidity.config import load_config


class TestLoadConfig:
    """Verify bocpd_params.json structure and SRD v1.2 parameter values."""

    def test_returns_dict(self):
        config = load_config()
        assert isinstance(config, dict)

    def test_top_level_keys(self):
        """Must contain all 8 top-level sections."""
        config = load_config()
        expected_keys = {
            "hazard",
            "nig_priors",
            "aema",
            "deadband",
            "hold_period",
            "mapping",
            "execution",
            "macro_hazard",
        }
        assert set(config.keys()) == expected_keys

    def test_aema_alpha_down(self):
        """SRD v1.2: alpha_down = 0.08 (half-life ~8.3 days)."""
        config = load_config()
        assert config["aema"]["alpha_down"] == 0.08

    def test_deadband_delta_up(self):
        """SRD v1.2: delta_up = 0.30 (very wide — suppress false QLD re-entry)."""
        config = load_config()
        assert config["deadband"]["delta_up"] == 0.30

    def test_hold_period(self):
        """SRD v1.2 / 4.5: minimum QLD hold = 63 trading days (~3 months)."""
        config = load_config()
        assert config["hold_period"]["min_qld_hold_days"] == 63

    def test_macro_hazard_floor(self):
        """lambda_floor = 0.002 (one changepoint per 2 years at minimum)."""
        config = load_config()
        assert config["macro_hazard"]["lambda_floor"] == 0.002

    def test_macro_hazard_ceil(self):
        """lambda_ceil = 0.016, ceil * g(0)=6.0 → 0.096 < 1.0 (safety)."""
        config = load_config()
        assert config["macro_hazard"]["lambda_ceil"] == 0.016

    def test_hazard_r_max(self):
        """R_MAX = 504 (2 years, frozen)."""
        config = load_config()
        assert config["hazard"]["R_MAX"] == 504
