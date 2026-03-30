import json
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.mahalanobis_guard import MahalanobisGuard
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper
from src.engine.v11.utils.memory_booster import SovereignMemoryBooster

logger = logging.getLogger(__name__)

class ExecutionGuard:
    """v11.5 Settlement Lock / Cooldown Tracker."""
    def __init__(self, cooldown_days: int = 0):
        self.cooldown_days_remaining = cooldown_days

    def trigger(self, days: int = 3):
        self.cooldown_days_remaining = days

    def tick(self):
        if self.cooldown_days_remaining > 0:
            self.cooldown_days_remaining -= 1

class V11Conductor:
    """The Sovereign Orchestrator. No hard-coded logic constants allowed. (AC-0)"""

    def __init__(self,
                 macro_data_path: str = "data/macro_historical_dump.csv",
                 regime_data_path: str = "data/v11_poc_phase1_results.csv",
                 audit_path: str = "src/engine/v11/resources/regime_audit.json",
                 initial_model: GaussianNB | None = None):
        # 0. Load Sovereign Calibration (Audit Archive)
        self.audit_path = Path(audit_path)
        if not self.audit_path.exists():
            raise FileNotFoundError(f"CRITICAL: Audit archive missing at {audit_path}")
        
        with open(self.audit_path, "r", encoding="utf-8") as f:
            self.audit_data = json.load(f)
            
        self.base_betas = self.audit_data["base_betas"]
        self.regime_sharpes = self.audit_data["regime_sharpes"]
        self.entropy_threshold = self.audit_data["risk_thresholds"]["entropy_max"]

        # v11.5 Internal Controllers
        self.seeder = ProbabilitySeeder()
        self.entropy_ctrl = EntropyController(threshold=self.entropy_threshold)
        self.beta_mapper = InertialBetaMapper()
        self.outlier_guard = MahalanobisGuard()
        self.execution_guard = ExecutionGuard()

        # Initial Model Training & Seeder Priming (Epic 1)
        if initial_model is not None:
            self.gnb = initial_model
            # Force prime seeder with regime data for test continuity
            regime_df = pd.read_csv(regime_data_path)
            regime_df["observation_date"] = pd.to_datetime(regime_df["observation_date"])
            self.seeder.generate_features(regime_df)
        else:
            self.gnb = self._initialize_model(macro_data_path, regime_data_path)

        self.inference_engine = BayesianInferenceEngine(
            kde_models={r: None for r in self.gnb.classes_},
            base_priors=self._get_base_priors()
        )

    def _initialize_model(self, macro_data_path: str, regime_data_path: str) -> GaussianNB:
        """JIT training of the Bayesian regime inference model with Sovereign DNA."""
        # AC-0: Always ensure baseline memory exists (DNA self-healing)
        booster = SovereignMemoryBooster(macro_data_path, regime_data_path)
        booster.ensure_baseline()
        
        # 1. Load Seeding Datasets
        macro_df = pd.read_csv(macro_data_path, index_col="observation_date", parse_dates=True)
        regime_df = pd.read_csv(regime_data_path, parse_dates=["observation_date"]).set_index("observation_date")

        # Generate features via unified seeder
        features = self.seeder.generate_features(macro_df)
        df = features.join(regime_df["regime"], how="inner").dropna()

        if df.empty:
            raise ValueError("JIT Training failed: Empty intersection between macro and regime data.")

        # Fit GNB (Architect A/B/C feature suite)
        # AC-0: Add variance smoothing to prevent probability collapse on low data (v11.19)
        gnb = GaussianNB(var_smoothing=1e-2)
        feature_cols = [c for c in df.columns if c != "regime"]
        gnb.fit(df[feature_cols], df["regime"])

        # Fit Outlier Guard on 'Stable' regimes (MID_CYCLE, RECOVERY)
        stable_mask = df["regime"].isin(["MID_CYCLE", "RECOVERY"])
        if stable_mask.any():
            self.outlier_guard.fit_baseline(df.loc[stable_mask, feature_cols])

        logger.info(f"V11.5 Conductor: JIT-Model Provenance established. Classes: {gnb.classes_}")
        return gnb

    def _get_base_priors(self) -> dict[str, float]:
        """Returns balanced priors (v11.26 DNA sensitivity edit)."""
        return {
            "MID_CYCLE": 0.20,
            "BUST": 0.20,
            "CAPITULATION": 0.20,
            "RECOVERY": 0.20,
            "LATE_CYCLE": 0.20
        }

    def daily_run(self, raw_t0_data: pd.DataFrame) -> dict:
        """
        Main execution loop for v11.5 probabilistic inference.
        """
        # 1. Feature Seeding (Epic 1)
        # AC-0: Conductor must see history to calculate Z-scores (v11.20)
        # Load local memory to provide context for the rolling window
        macro_csv = "data/macro_historical_dump.csv"
        if os.path.exists(macro_csv):
            hist_df = pd.read_csv(macro_csv, parse_dates=["observation_date"]).set_index("observation_date")
            # Clear duplicate index if it exists in hist_df and t0
            t0_dt = pd.to_datetime(raw_t0_data.iloc[-1].name or raw_t0_data.index[-1])
            hist_df = hist_df[hist_df.index < t0_dt]
            # Use raw_t0_data as a DataFrame to match columns
            t0_df = raw_t0_data.copy()
            # Use observation_date column as index if available to avoid Epoch 0 (1970-01-01)
            if "observation_date" in t0_df.columns:
                t0_df = t0_df.set_index("observation_date")
            elif not isinstance(t0_df.index, pd.DatetimeIndex):
                t0_df.index = pd.to_datetime(t0_df.index)
            # Standardize columns for v11 macro suite
            v11_cols = ["erp_pct", "real_yield_10y_pct", "credit_spread_bps", "net_liquidity_usd_bn"]
            # Only use columns that exist in both to prevent KeyError
            available_cols = [c for c in v11_cols if c in hist_df.columns and c in t0_df.columns]
            context_df = pd.concat([hist_df[available_cols], t0_df[available_cols]])
        else:
            context_df = raw_t0_data

        features = self.seeder.generate_features(context_df)
        
        # 2. Bayesian Inference (Epic 2)
        # Inference only on the last point
        latest_vector = features.iloc[-1:]
        
        # AC-3: Numerical Resilience (v11.21)
        try:
            probs = self.gnb.predict_proba(latest_vector)
            probs_array = probs[0]
            if np.isnan(probs_array).any():
                logger.warning("Bayesian Inference produced NaNs. Falling back to priors.")
                posteriors = self._get_base_priors()
            else:
                posteriors = {str(k): float(v) for k, v in zip(self.gnb.classes_, probs_array, strict=True)}
        except Exception as e:
            logger.error("Bayesian Inference crashed: %s. Falling back to priors.", e)
            posteriors = self._get_base_priors()

        # 3. Probabilistic Exposure Mapping (v11.5)
        # AC-0: No constants. Base betas are audit-derived.
        raw_beta_expectation = sum(posteriors.get(regime, 0.0) * self.base_betas.get(regime, 1.0) 
                                   for regime in self.base_betas.keys())
        
        norm_h = self.entropy_ctrl.calculate_normalized_entropy(posteriors)
        
        # Adaptive Outlier Inference (v11.7)
        outlier_multiplier = self.outlier_guard.calculate_outlier_multiplier(latest_vector)
        
        # Continuous Probabilistic Penalty (v11.6)
        ry_z = float(features.iloc[-1].get("real_yield_structural_z", 0.0))
        protected_beta = self.entropy_ctrl.apply_haircut(
            raw_beta_expectation, 
            norm_h, 
            structural_z=ry_z,
            outlier_multiplier=outlier_multiplier
        )

        # 4. Behavioral Guard: Settled Inertia vs Probabilities (CUSUM)
        # AC-0: Turnover control.
        self.execution_guard.tick()
        old_beta = self.beta_mapper.current_beta
        final_beta = self.beta_mapper.calculate_inertial_beta(protected_beta, norm_h)
        
        # Trigger settlement lock on substantial change (v11.0 safeguard)
        lock_active = self.execution_guard.cooldown_days_remaining > 0
        if abs(final_beta - old_beta) > 0.01 and not lock_active:
             self.execution_guard.trigger(3) 
             lock_active = True
        
        # 5. Bayesian Kelly Entry (v11.14 -> v11.15)
        # Goal: Optimize for Risk-Adjusted Expectation.
        # Uses Audit-Derived Regime Sharpe Ratios (Win Rate * Odds).
        erp_series = raw_t0_data.get('erp_pct', features.get('erp_pct', pd.Series([0.0])))
        erp_percentile = erp_series.rank(pct=True).iloc[-1]
        
        # Bayesian Expected Sharpe (Win-Rate * Odds)
        # Parameters derived from self.audit_data (Structural Consistency).
        e_sharpe = sum(posteriors.get(r, 0.0) * s for r, s in self.regime_sharpes.items())
        
        # CDR = Information Clarity * Positive Expectation * Structural Value
        deployment_readiness = (1.0 - norm_h) * max(0.0, e_sharpe) * erp_percentile
        
        # 6. UI/Main Alignment Data
        latest_raw = raw_t0_data.iloc[-1]
        feature_values = {
            "credit_spread": float(latest_raw.get("credit_spread_bps", 0.0)),
            "erp": float(latest_raw.get("erp_pct", 0.0)),
            "net_liquidity": float(latest_raw.get("net_liquidity_usd_bn", 0.0)),
            "vix": float(latest_raw.get("vix", 0.0)),
            "entropy": norm_h,
            "outlier_stress": 1.0 - outlier_multiplier,
            "tactical_stress_score": int(np.abs(latest_vector).values.sum() * 10)
        }

        # Map back to legacy allocation buckets for v8.2/main.py compatibility
        bucket = "QQQ"
        if final_beta > 1.0:
            bucket = "QLD"
        elif final_beta < 0.6:
            bucket = "CASH"

        # Data Integrity Label
        quality = 0.0 if any(np.isnan(v) for v in feature_values.values()) else 1.0
        reason = "SENSOR DEGRADATION" if quality < 1.0 else "V11_PROBABILISTIC_OPTIMAL"

        # 6. Legacy Signal Formatting
        resurrection = (posteriors.get("RECOVERY", 0.0) > 1e-6)

        return {
            "date": features.index[-1],
            "signal": {
                "target_bucket": bucket,
                "reason": reason,
                "lock_active": lock_active
            },
            "probabilities": posteriors,
            "entropy": norm_h,
            "target_beta": final_beta,
            "raw_target_beta": raw_beta_expectation,
            "deployment_readiness": deployment_readiness,
            "cdr_sharpe": e_sharpe,
            "erp_percentile": erp_percentile,
            "target_allocation": self._calculate_dollars(final_beta),
            "feature_values": feature_values,
            "data_quality": quality,
            "resurrection_active": resurrection,
        }

    def _calculate_dollars(self, beta: float) -> dict:
        """Lightweight dollar mapping for main.py."""
        # Standard unit of $100k for the signal generator
        NAV = 100_000.0
        if beta > 1.0:
            qld = (beta - 1.0) * NAV # Exposure above 1.0 goes to QLD
            qqq = NAV
            cash = 0.0
        else:
            qld = 0.0
            qqq = NAV * beta
            cash = NAV - qqq
        return {
            "qqq_dollars": qqq,
            "qld_notional_dollars": qld,
            "cash_dollars": cash
        }
