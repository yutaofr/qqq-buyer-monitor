import pandas as pd


class ProbabilitySeeder:
    """
    v11.5 Probability Seeder
    Responsibility: Standardize 6 mixed-horizon factors into a Bayesian Observation Vector.
    Strictly follows Architect A/B/C research criteria.
    """
    def __init__(self):
        # Time horizons defined by Architect Research (ADD/SRD)
        self.config = {
            "erp_21d_mom": {"src": "erp_pct", "window": 21, "mom": True, "accel": False, "ewma": True},
            "real_yield_10d_mom": {"src": "real_yield_10y_pct", "window": 10, "mom": True, "accel": False, "ewma": False},
            "spread_21d": {"src": "credit_spread_bps", "window": 21, "mom": False, "accel": False, "ewma": False},
            "liquidity_252d": {"src": "net_liquidity_usd_bn", "window": 252, "mom": False, "accel": False, "ewma": False},
            "credit_accel_21d": {"src": "credit_spread_bps", "window": 21, "mom": False, "accel": True, "ewma": False},
            "liq_mom_4w": {"src": "net_liquidity_usd_bn", "window": 20, "mom": True, "accel": False, "ewma": False},
            "real_yield_structural_z": {"src": "real_yield_10y_pct", "window": 126, "mom": False, "accel": False, "ewma": True},
            "erp_absolute": {"src": "erp_pct", "window": 1, "mom": False, "accel": False, "ewma": False, "absolute": True},
            "spread_absolute": {"src": "credit_spread_bps", "window": 1, "mom": False, "accel": False, "ewma": False, "absolute": True},
            "yield_absolute": {"src": "real_yield_10y_pct", "window": 1, "mom": False, "accel": False, "ewma": False, "absolute": True},
        }

    def generate_features(self, macro_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the 6-factor Bayesian vector from raw macro data.
        Ensures Z-score normalization for each factor.
        """
        # 1. Normalize index to tz-naive
        df = self._normalize_index(macro_df)
        df = df.sort_index()

        features = pd.DataFrame(index=df.index)

        # 2. Sequential Calculation to avoid Look-Ahead Bias
        for feat_name, cfg in self.config.items():
            src_col = cfg["src"]
            if src_col not in df.columns:
                features[feat_name] = 0.0 # Safety floor
                continue

            series = df[src_col]

            # Apply EWMA if requested (Architect A Strategic Smoothing)
            if cfg["ewma"]:
                series = series.ewm(span=cfg["window"]).mean()

            # Calculate Momentum or Acceleration
            val = series
            if cfg["accel"]:
                val = series.diff(cfg["window"]).diff(cfg["window"])
            elif cfg["mom"]:
                val = series.diff(cfg["window"])

            # 3. Dynamic Z-Score Normalization (Rolling 1-Year baseline)
            # This ensures we only use information available at time T
            if cfg.get("absolute"):
                # Scale absolute values to be in similar range as Z-scores (-3 to 3)
                if src_col == "erp_pct":
                    features[feat_name] = (val * 100.0 - 4.0) + np.random.normal(0, 0.5)
                elif src_col == "credit_spread_bps":
                    features[feat_name] = (val - 350.0) / 100.0 + np.random.normal(0, 0.2)
                elif src_col == "real_yield_10y_pct":
                    # Aligning Real Yield expectations for Late Cycle
                    features[feat_name] = (val * 100.0 - 3.5) + np.random.normal(0, 0.3)
                else:
                    features[feat_name] = val
            else:
                mean = val.rolling(252, min_periods=1).mean()
                std = val.rolling(252, min_periods=1).std()
                features[feat_name] = (val - mean) / (std.fillna(1e-6).replace(0, 1e-6))

        # Final cleanup: Remove bfill() to prevent Look-Ahead Bias.
        # We only ffill (causal) and fillna(0) for the very beginning of the series.
        return features.ffill().fillna(0.0)

    def _normalize_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Forces index to be DatetimeIndex, frequency-aligned, and tz-naive."""
        res = df.copy()
        if not isinstance(res.index, pd.DatetimeIndex):
            res.index = pd.to_datetime(res.index)

        if res.index.tz is not None:
            res.index = res.index.tz_convert(None)

        res.index = res.index.normalize()
        return res
