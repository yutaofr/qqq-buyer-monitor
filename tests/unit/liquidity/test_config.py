"""Smoke tests for config loader (Story 1.1 / T1.1.4)."""

from src.liquidity.config import load_config


class TestLoadConfig:
    """Verify bocpd_params.json structure and SRD v1.2 parameter values."""

    def test_returns_dict(self):
        config = load_config()
        assert isinstance(config, dict)

    def test_top_level_keys(self):
        """Must contain all 14 top-level sections."""
        config = load_config()
        expected_keys = {
            "hazard",
            "nig_priors",
            "aema",
            "deadband",
            "hold_period",
            "mapping",
            "execution",
            "price_loader",
            "ed_signal",
            "proxy_universe",
            "macro_hazard",
            "overdrive",
            "forgetting",
            "regime_vol_guard",
            "regime_severity",
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

    def test_forgetting_lambda_default(self):
        """SRD v1.3: lambda=0.995 → kappa_∞=200, keeps Student-t thick-tailed."""
        config = load_config()
        assert config["forgetting"]["lambda"] == 0.995

    def test_ed_signal_filters(self):
        """ED must use the production min coverage / min names filter."""
        config = load_config()
        assert config["ed_signal"]["min_coverage"] == 0.9
        assert config["ed_signal"]["min_names"] == 20

    def test_proxy_universe_defaults(self):
        """Proxy universe defaults must remain stable for reproducibility."""
        config = load_config()
        assert config["proxy_universe"]["top_n"] == 50
        assert config["proxy_universe"]["min_listing_days"] == 63
        assert config["proxy_universe"]["liquidity_lookback"] == 60

    def test_price_loader_retry_defaults(self):
        """Chunk/retry defaults should be config-driven and reproducible."""
        config = load_config()
        assert config["price_loader"]["chunk_size"] == 5
        assert config["price_loader"]["max_retries"] == 3
        assert config["price_loader"]["base_delay_seconds"] == 1.0
        assert config["price_loader"]["jitter_seconds"] == 0.25

    def test_regime_vol_guard_release_alpha(self):
        """Vol guard should release stale stress faster without changing the stress cap."""
        config = load_config()
        guard = config["regime_vol_guard"]
        assert guard["quantile"] == 0.95
        assert guard["stress_max_leverage"] == 0.50
        assert guard["floor_alpha_down"] == 0.12

    def test_regime_severity_defaults(self):
        """Regime severity is configured but disabled by default for baseline parity."""
        config = load_config()
        assert config["regime_severity"]["enabled"] is False
        assert config["regime_severity"]["aggregation"] == "posterior_mixture_variance"
        assert config["regime_severity"]["combine"] == "max"
        assert config["regime_severity"]["alpha_up"] == 0.25
        assert config["regime_severity"]["alpha_down"] == 0.03
        assert config["regime_severity"]["floor_method"] == "prior_predictive_null"
        assert config["regime_severity"]["floor_quantile"] == 0.90
        assert config["regime_severity"]["floor_mc_paths"] == 200
        assert config["regime_severity"]["floor_mc_steps"] == 756
        assert config["regime_severity"]["floor_warmup"] == 252
        assert config["regime_severity"]["floor_seed"] == 1337
        assert config["regime_severity"]["ceil_method"] == "variance_inflation_scenario"
        assert config["regime_severity"]["ceil_multipliers"] == {
            "ed_accel": 2.0,
            "spread_anomaly": 4.0,
            "fisher_rho": 2.0,
        }
        assert config["regime_severity"]["dimension_caps"] == {
            "ed_accel": 1.0986122886681098,
            "spread_anomaly": 1.3862943611198906,
            "fisher_rho": 1.0986122886681098,
        }
        assert config["regime_severity"]["resonance_method"] == "participation_ratio"
        assert config["regime_severity"]["resonance_gamma"] == 1.0
        assert config["regime_severity"]["threshold_resource"] == "regime_severity_thresholds.json"
        assert config["regime_severity"]["weights"] == {
            "ed_accel": 0.35,
            "spread_anomaly": 0.45,
            "fisher_rho": 0.20,
        }
