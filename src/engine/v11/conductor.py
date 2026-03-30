"""v11.5 Conductor: The Unified Probabilistic Orchestrator.
Coordinates JIT-model training, multi-horizon feature seeding, and entropy-controlled execution.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.mahalanobis_guard import MahalanobisGuard
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper

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
    # Architect-Approved Optimal Constants
    ENTROPY_THRESHOLD = 0.65

    # Standard v11.5 Base Betas
    BASE_BETAS = {
        "BUST": 0.5,
        "CAPITULATION": 1.05,
        "RECOVERY": 1.1,
        "LATE_CYCLE": 0.8,
        "MID_CYCLE": 1.0
    }

    def __init__(self, macro_data_path: str = "data/macro_historical_dump.csv",
                 regime_data_path: str = "data/v11_poc_phase1_results.csv",
                 initial_model: GaussianNB | None = None):
        self.seeder = ProbabilitySeeder()
        self.entropy_ctrl = EntropyController(threshold=self.ENTROPY_THRESHOLD)
        self.beta_mapper = InertialBetaMapper()
        self.outlier_guard = MahalanobisGuard()

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

    def _initialize_model(self, macro_path: str, regime_path: str) -> GaussianNB:
        """
        JIT-fits the GaussianNB engine on start-up.
        Ensures production models are always aligned with the latest seed data.
        """
        logger.info(f"V11.5 Conductor: JIT-training model from {macro_path}...")

        # Load raw data
        macro_df = pd.read_csv(macro_path, parse_dates=["observation_date"]).set_index("observation_date")
        regime_df = pd.read_csv(regime_path, parse_dates=["observation_date"]).set_index("observation_date")

        # Generate features via unified seeder
        features = self.seeder.generate_features(macro_df)
        df = features.join(regime_df["regime"], how="inner").dropna()

        if df.empty:
            raise ValueError("JIT Training failed: Empty intersection between macro and regime data.")

        # Fit GNB (Architect A/B/C feature suite)
        gnb = GaussianNB()
        feature_cols = [c for c in df.columns if c != "regime"]
        gnb.fit(df[feature_cols], df["regime"])

        # Fit Outlier Guard on 'Stable' regimes (MID_CYCLE, RECOVERY)
        stable_mask = df["regime"].isin(["MID_CYCLE", "RECOVERY"])
        if stable_mask.any():
            self.outlier_guard.fit_baseline(df.loc[stable_mask, feature_cols])

        logger.info(f"V11.5 Conductor: JIT-Model Provenance established. Classes: {gnb.classes_}")
        return gnb

    def _get_base_priors(self) -> dict[str, float]:
        """Returns balanced priors for the regimes."""
        return {
            "MID_CYCLE": 0.80,
            "BUST": 0.05,
            "CAPITULATION": 0.05,
            "RECOVERY": 0.05,
            "LATE_CYCLE": 0.05
        }

    def daily_run(self, raw_t0_data: pd.DataFrame) -> dict:
        """
        Main execution loop for v11.5 probabilistic inference.
        """
        # 1. Feature Seeding (Epic 1)
        # Ensure T-0 data is integrated into the seeder's causal window
        features = self.seeder.generate_features(raw_t0_data)
        latest_vector = features.iloc[-1].values

        # 2. Bayesian Inference (Epic 2)
        # We wrap the GNB predict_proba to match the SRD interface
        probs = self.gnb.predict_proba(latest_vector.reshape(1, -1))
        probs_array = probs[0]
        posteriors = {str(k): float(v) for k, v in zip(self.gnb.classes_, probs_array, strict=True)}

        # 3. Entropy Haircut (Epic 3)
        # Calculate raw expectation from the current posterior distribution
        raw_beta_expectation = sum(posteriors.get(regime, 1.0) * self.BASE_BETAS.get(regime, 1.0) 
                                   for regime in posteriors)
        
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

        # 4. Odds-Ratio CUSUM (v11.10)
        # Turnover is now a function of the Information-Odds Barrier (H / (1-H)).
        # Shift only occurs if the cumulative evidence exceeds the uncertainty-odds.
        final_beta = self.beta_mapper.calculate_inertial_beta(protected_beta, norm_h)
        
        # 5. UI/Main Alignment Data
        latest_raw = raw_t0_data.iloc[-1]
        feature_values = {
            "credit_spread": float(latest_raw.get("credit_spread_bps", 0.0)),
            "erp": float(latest_raw.get("erp_pct", 0.0)),
            "net_liquidity": float(latest_raw.get("net_liquidity_usd_bn", 0.0)),
            "vix": float(latest_raw.get("vix", 0.0)),
            "entropy": norm_h,
            "outlier_stress": 1.0 - outlier_multiplier,
            "tactical_stress_score": int(np.abs(latest_vector).sum() * 10)
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
                "reason": reason
            },
            "probabilities": posteriors,
            "entropy": norm_h,
            "target_beta": final_beta,
            "raw_target_beta": raw_beta_expectation,
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
