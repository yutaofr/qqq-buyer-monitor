import hashlib
import json

import pandas as pd

_CLIP_RANGE = (-8.0, 8.0)


class ProbabilitySeeder:
    """
    v12 Probability Seeder
    Responsibility: Standardize the locked 10-factor orthogonal observation vector
    used by the GaussianNB regime engine.
    """

    def __init__(self):
        self.config = {
            "real_yield_structural_z": {
                "src": "real_yield_10y_pct",
                "ewma_span": 126,
                "z_method": "expanding",
                "min_periods": 63,
            },
            "move_21d": {
                "src": "treasury_vol_21d",
                "z_method": "expanding",
                "min_periods": 63,
                "orthogonalize_against": "spread_21d",
            },
            "breakeven_accel": {
                "src": "breakeven_10y",
                "diff": (21, 21),
                "z_method": "rolling",
                "z_window": 252,
                "min_periods": 42,
            },
            "core_capex_momentum": {
                "src": "core_capex_mm",
                "z_method": "expanding",
                "min_periods": 6,
            },
            "copper_gold_roc_126d": {
                "src": "copper_gold_ratio",
                "diff": (126,),
                "z_method": "rolling",
                "z_window": 252,
                "min_periods": 126,
            },
            "usdjpy_roc_126d": {
                "src": "usdjpy",
                "diff": (126,),
                "z_method": "rolling",
                "z_window": 252,
                "min_periods": 126,
            },
            "spread_21d": {
                "src": "credit_spread_bps",
                "z_method": "rolling",
                "z_window": 252,
                "min_periods": 21,
            },
            "liquidity_252d": {
                "src": "net_liquidity_usd_bn",
                "z_method": "rolling",
                "z_window": 252,
                "min_periods": 63,
            },
            "erp_absolute": {
                "src": "erp_ttm_pct",
                "z_method": "expanding",
                "min_periods": 63,
            },
            "spread_absolute": {
                "src": "credit_spread_bps",
                "z_method": "expanding",
                "min_periods": 63,
            },
        }
        self.diagnostics_: pd.DataFrame = pd.DataFrame()

    def contract_hash(self) -> str:
        canonical = json.dumps(self.config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def feature_names(self) -> list[str]:
        return list(self.config.keys())

    def generate_features(self, macro_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the 10-factor Bayesian vector from raw macro data using
        a single deterministic code path for live and backtest.
        """
        df = self._normalize_index(macro_df).sort_index()
        features = pd.DataFrame(index=df.index)

        for feature_name, cfg in self.config.items():
            src_col = str(cfg["src"])
            if src_col not in df.columns:
                features[feature_name] = 0.0
                continue

            series = pd.to_numeric(df[src_col], errors="coerce")
            transformed = self._transform_series(series, cfg)
            features[feature_name] = self._compute_z(
                transformed,
                method=str(cfg["z_method"]),
                window=cfg.get("z_window"),
                min_periods=int(cfg["min_periods"]),
            )

        features = features.ffill().fillna(0.0)
        features = self._orthogonalize_move(features)
        return features.clip(*_CLIP_RANGE)

    def _transform_series(self, series: pd.Series, cfg: dict[str, object]) -> pd.Series:
        val = series.copy()

        ewma_span = cfg.get("ewma_span")
        if ewma_span is not None:
            val = val.ewm(span=int(ewma_span), adjust=False).mean()

        for periods in tuple(cfg.get("diff", ())):
            val = val.diff(int(periods))

        return val

    def _compute_z(
        self,
        series: pd.Series,
        *,
        method: str,
        window: int | None,
        min_periods: int,
    ) -> pd.Series:
        if method == "expanding":
            mean = series.expanding(min_periods=min_periods).mean()
            std = series.expanding(min_periods=max(min_periods, 2)).std()
        elif method == "rolling":
            if window is None:
                raise ValueError("rolling z-score requires a window")
            mean = series.rolling(int(window), min_periods=min_periods).mean()
            std = series.rolling(int(window), min_periods=max(min_periods, 2)).std()
        else:
            raise ValueError(f"Unknown z-score method: {method}")

        std_safe = std.fillna(1e-6).replace(0, 1e-6)
        z = (series - mean) / std_safe
        return z.clip(*_CLIP_RANGE)

    def _orthogonalize_move(self, features: pd.DataFrame) -> pd.DataFrame:
        if "move_21d" not in features.columns or "spread_21d" not in features.columns:
            self.diagnostics_ = pd.DataFrame(index=features.index)
            return features

        out = features.copy()
        move_z = out["move_21d"].copy()
        spread_z = out["spread_21d"].copy()

        cov = move_z.expanding(min_periods=63).cov(spread_z)
        var = spread_z.expanding(min_periods=63).var()
        beta = (cov / var.replace(0, pd.NA)).fillna(0.0)
        residual = (move_z - beta * spread_z).clip(*_CLIP_RANGE)
        corr_21d = move_z.rolling(21, min_periods=5).corr(spread_z).fillna(0.0)

        out["move_21d"] = residual
        self.diagnostics_ = pd.DataFrame(
            {
                "move_21d_raw_z": move_z,
                "move_21d_orth_z": residual,
                "move_spread_beta": beta,
                "move_spread_corr_21d": corr_21d,
            },
            index=features.index,
        )
        return out

    def latest_diagnostics(self) -> pd.DataFrame:
        return self.diagnostics_.copy()

    def _normalize_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Force index to DatetimeIndex, frequency-aligned, and tz-naive."""
        res = df.copy()
        if not isinstance(res.index, pd.DatetimeIndex):
            try:
                res.index = pd.to_datetime(res.index, format="mixed")
            except (TypeError, ValueError):
                res.index = pd.to_datetime(res.index)

        if res.index.tz is not None:
            res.index = res.index.tz_convert(None)

        res.index = res.index.normalize()
        return res
