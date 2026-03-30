import pandas as pd


class ProbabilitySeeder:
    """
    v11.5 Probability Seeder
    Responsibility: Standardize 6 mixed-horizon factors into a Bayesian Observation Vector.
    Strictly follows Architect A/B/C research criteria.
    """
    def __init__(self):
        # Production-curated feature set:
        # keep only factors that improved regime discrimination in the current audit corpus.
        self.config = {
            "spread_21d": {"src": "credit_spread_bps", "window": 21, "mom": False, "accel": False, "ewma": False},
            "liquidity_252d": {"src": "net_liquidity_usd_bn", "window": 252, "mom": False, "accel": False, "ewma": False},
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
                features[feat_name] = self._scale_absolute_feature(src_col, val)
            else:
                mean = val.rolling(252, min_periods=1).mean()
                std = val.rolling(252, min_periods=1).std()
                features[feat_name] = (val - mean) / (std.fillna(1e-6).replace(0, 1e-6))

        # Final cleanup: Remove bfill() to prevent Look-Ahead Bias.
        # We only ffill (causal) and fillna(0) for the very beginning of the series.
        return features.ffill().fillna(0.0)

    def _scale_absolute_feature(self, src_col: str, val: pd.Series) -> pd.Series:
        """
        Deterministically maps level features into a roughly z-score-like space.
        Random perturbations are forbidden because they destroy prior stability.
        """
        numeric = pd.to_numeric(val, errors="coerce")
        if src_col == "erp_pct":
            scaled = (numeric * 100.0 - 4.0) / 2.0
        elif src_col == "credit_spread_bps":
            scaled = (numeric - 350.0) / 100.0
        elif src_col == "real_yield_10y_pct":
            scaled = (numeric * 100.0 - 3.5) / 2.0
        else:
            scaled = numeric

        return scaled.clip(-8.0, 8.0)

    def _normalize_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Forces index to be DatetimeIndex, frequency-aligned, and tz-naive."""
        res = df.copy()
        if not isinstance(res.index, pd.DatetimeIndex):
            res.index = pd.to_datetime(res.index)

        if res.index.tz is not None:
            res.index = res.index.tz_convert(None)

        res.index = res.index.normalize()
        return res
