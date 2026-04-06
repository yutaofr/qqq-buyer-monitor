import hashlib
import json

import pandas as pd

_DEFAULT_CLIP_RANGE = (-8.0, 8.0)


class ProbabilitySeeder:
    """
    v12 Probability Seeder
    Responsibility: Standardize the configured orthogonal observation vector
    used by the GaussianNB regime engine.
    """

    def __init__(
        self,
        *,
        config_overrides: dict[str, dict[str, object]] | None = None,
        clip_range: tuple[float, float] = _DEFAULT_CLIP_RANGE,
        orthogonalization_mode: str = "residualize",
        orthogonalization_strength: float = 1.0,
        selected_features: list[str] | tuple[str, ...] | None = None,
    ):
        self.clip_range = (float(clip_range[0]), float(clip_range[1]))
        self.orthogonalization_mode = str(orthogonalization_mode)
        self.orthogonalization_strength = float(orthogonalization_strength)
        self.config = self._merge_config(self._default_config(), config_overrides or {})
        self.selected_features = list(selected_features) if selected_features is not None else None
        self._contract_payload = {
            "config": self.config,
            "clip_range": self.clip_range,
            "orthogonalization_mode": self.orthogonalization_mode,
            "orthogonalization_strength": self.orthogonalization_strength,
            "selected_features": self.selected_features,
        }
        self._validate_runtime_contract()
        self.diagnostics_: pd.DataFrame = pd.DataFrame()

    @staticmethod
    def _default_config() -> dict[str, dict[str, object]]:
        return {
            "real_yield_structural_z": {
                "src": "real_yield_10y_pct",
                "ewma_span": 21,  # Responsive to Fed pivots (1-month)
                "z_method": "rolling",
                "z_window": 1260,  # 5-year structural anchor
                "min_periods": 63,
            },
            "move_21d": {
                "src": "treasury_vol_21d",
                "z_method": "rolling",
                "z_window": 1260,  # 5-year structural anchor
                "min_periods": 63,
                "orthogonalize_against": "spread_21d",
            },
            "breakeven_accel": {
                "src": "breakeven_10y",
                "diff": (21, 21),
                "z_method": "expanding",
                "min_periods": 42,
            },
            "core_capex_momentum": {
                "src": "core_capex_mm",
                "ewma_span": 3,
                "z_method": "expanding",
                "min_periods": 6,
            },
            "copper_gold_roc_126d": {
                "src": "copper_gold_ratio",
                "diff": (126,),
                "z_method": "rolling",
                "z_window": 756,  # 3-year medium-term sensitive
                "min_periods": 126,
            },
            "usdjpy_roc_126d": {
                "src": "usdjpy",
                "diff": (126,),
                "z_method": "rolling",
                "z_window": 756,
                "min_periods": 126,
            },
            "spread_21d": {
                "src": "credit_spread_bps",
                "z_method": "rolling",
                "z_window": 1260,  # 5-year structural anchor
                "min_periods": 21,
            },
            "liquidity_252d": {
                "src": "net_liquidity_usd_bn",
                "z_method": "expanding",
                "min_periods": 63,
            },
            "erp_absolute": {
                "src": "erp_ttm_pct",
                "z_method": "expanding",
                "min_periods": 63,
            },
            "spread_absolute": {
                "src": "credit_spread_bps",
                "z_method": "rolling",
                "z_window": 1260,
                "min_periods": 63,
            },
            "pmi_momentum": {
                "src": "pmi_proxy_manemp",
                "ewma_span": 21,
                "diff": (21, 21),
                "z_method": "rolling",
                "z_window": 756,
                "min_periods": 63,
            },
            "labor_slack": {
                "src": "job_openings",
                "ewma_span": 21,
                "z_method": "rolling",
                "z_window": 756,
                "min_periods": 63,
            },
            "qqq_ma_ratio": {
                "src": "qqq_close",
                "z_method": "rolling",
                "z_window": 1260,
                "min_periods": 252,
            },
            "qqq_pv_divergence_z": {
                "src": "qqq_close",
                "z_method": "rolling",
                "z_window": 1260,
                "min_periods": 126,
            },
            "credit_acceleration": {
                "src": "credit_spread_bps",
                "diff": (21, 21),
                "z_method": "rolling",
                "z_window": 756,
                "min_periods": 63,
            },
            "liquidity_velocity": {
                "src": "liquidity_roc_pct_4w",
                "z_method": "rolling",
                "z_window": 252,
                "min_periods": 21,
            },
        }

    @staticmethod
    def _merge_config(
        base: dict[str, dict[str, object]],
        overrides: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        merged = {name: dict(cfg) for name, cfg in base.items()}
        for feature_name, feature_overrides in overrides.items():
            if feature_name not in merged:
                raise ValueError(f"Unknown seeder feature override: {feature_name}")
            merged[feature_name].update(dict(feature_overrides))
        return merged

    def _validate_runtime_contract(self) -> None:
        if self.orthogonalization_mode not in {"residualize", "none"}:
            raise ValueError("orthogonalization_mode must be `residualize` or `none`")
        if self.clip_range[0] >= self.clip_range[1]:
            raise ValueError("clip_range must be increasing")
        self.orthogonalization_strength = float(min(1.0, max(0.0, self.orthogonalization_strength)))
        if self.selected_features is not None:
            unknown = [name for name in self.selected_features if name not in self.config]
            if unknown:
                raise ValueError(f"Unknown selected_features: {unknown}")
            if len(dict.fromkeys(self.selected_features)) != len(self.selected_features):
                raise ValueError("selected_features must be unique")

        # v14 Forensic Hardening: Validate Z-method integrity
        for name, cfg in self.config.items():
            method = cfg.get("z_method")
            if method == "rolling" and cfg.get("z_window") is None:
                raise ValueError(f"Feature '{name}' configured as 'rolling' but missing 'z_window'.")
            if method not in {"rolling", "expanding"}:
                raise ValueError(f"Feature '{name}' has unknown z_method: {method}")

    def contract_hash(self) -> str:
        canonical = json.dumps(
            self._contract_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def feature_names(self) -> list[str]:
        if self.selected_features is not None:
            return list(self.selected_features)
        return list(self.config.keys())

    def generate_features(self, macro_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the configured Bayesian factor vector from raw macro data using
        a single deterministic code path for live and backtest.
        """
        df = self._normalize_index(macro_df).sort_index()
        features = pd.DataFrame(index=df.index)

        for feature_name in self.feature_names():
            cfg = self.config[feature_name]
            src_col = str(cfg["src"])
            if src_col not in df.columns:
                features[feature_name] = 0.0
                continue

            series = pd.to_numeric(df[src_col], errors="coerce")

            # Specialized Feature Logic (v14.3 Cycle Alignment)
            if feature_name == "qqq_ma_ratio":
                sma50 = series.rolling(50, min_periods=10).mean()
                sma200 = series.rolling(200, min_periods=50).mean()
                val = (sma50 / sma200.replace(0, pd.NA)).fillna(1.0) - 1.0
            elif feature_name == "qqq_pv_divergence_z":
                # Price ROC vs Volume ROC Correlation
                # Negative correlation = Price up while Volume down (Top Divergence)
                # or Price down while Volume up (Bottom Divergence/Capitulation)
                p_roc = series.pct_change(21)
                v_col = "qqq_volume" if "qqq_volume" in df.columns else src_col
                v_roc = pd.to_numeric(df[v_col], errors="coerce").pct_change(21)
                val = p_roc.rolling(21, min_periods=10).corr(v_roc).fillna(0.0)
            else:
                val = self._transform_series(series, cfg)

            features[feature_name] = self._compute_z(
                val,
                method=str(cfg["z_method"]),
                window=cfg.get("z_window"),
                min_periods=int(cfg["min_periods"]),
            )

        features = features.ffill().fillna(0.0)
        # AC-0: Store all raw Z-scores in diagnostics for TailRiskRadar visibility (v14 forensic fix)
        self.diagnostics_ = features.copy()
        features = self._orthogonalize_move(features)
        return features.clip(*self.clip_range)

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
        return z.clip(*self.clip_range)

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
        residual = move_z.copy()
        if self.orthogonalization_mode == "residualize":
            residual = (move_z - (self.orthogonalization_strength * beta * spread_z)).clip(
                *self.clip_range
            )
        corr_21d = move_z.rolling(21, min_periods=5).corr(spread_z).fillna(0.0)

        out["move_21d"] = residual
        # v14 forensic fix: JOIN with existing diagnostics instead of overwriting
        ortho_diag = pd.DataFrame(
            {
                "move_21d_raw_z": move_z,
                "move_21d_orth_z": residual,
                "move_spread_beta": beta,
                "move_spread_corr_21d": corr_21d,
            },
            index=features.index,
        )
        self.diagnostics_ = self.diagnostics_.join(ortho_diag, how="left")
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
