import json
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.mahalanobis_guard import MahalanobisGuard
from src.engine.v11.core.position_sizer import PositionSizingResult
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.engine.v11.signal.behavioral_guard import BehavioralGuard
from src.engine.v11.signal.deployment_policy import ProbabilisticDeploymentPolicy
from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper
from src.engine.v11.signal.regime_stabilizer import RegimeStabilizer
from src.engine.v11.utils.memory_booster import SovereignMemoryBooster

logger = logging.getLogger(__name__)

class V11Conductor:
    """The Sovereign Orchestrator. No hard-coded logic constants allowed. (AC-0)"""

    def __init__(
        self,
        macro_data_path: str = "data/macro_historical_dump.csv",
        regime_data_path: str = "data/v11_poc_phase1_results.csv",
        audit_path: str = "src/engine/v11/resources/regime_audit.json",
        prior_state_path: str = "data/v11_prior_state.json",
        initial_model: GaussianNB | None = None,
    ):
        # 0. Load Sovereign Calibration (Audit Archive)
        self.audit_path = Path(audit_path)
        if not self.audit_path.exists():
            raise FileNotFoundError(f"CRITICAL: Audit archive missing at {audit_path}")

        with open(self.audit_path, encoding="utf-8") as f:
            self.audit_data = json.load(f)

        self.macro_data_path = macro_data_path
        self.regime_data_path = regime_data_path
        self.base_betas = self.audit_data["base_betas"]
        self.regime_sharpes = self.audit_data["regime_sharpes"]
        self.entropy_threshold = self.audit_data["risk_thresholds"]["entropy_max"]
        self.regimes = list(self.base_betas.keys())
        self.regime_history = pd.read_csv(
            regime_data_path,
            parse_dates=["observation_date"],
        ).set_index("observation_date")

        # v11.5 Internal Controllers
        self.seeder = ProbabilitySeeder()
        self.entropy_ctrl = EntropyController(threshold=self.entropy_threshold)
        self.outlier_guard = MahalanobisGuard()
        self.prior_book = PriorKnowledgeBase(
            storage_path=prior_state_path,
            regimes=self.regimes,
            bootstrap_regimes=self.regime_history["regime"].tolist(),
        )
        execution_state = self.prior_book.get_execution_state()
        self.beta_mapper = InertialBetaMapper(
            initial_beta=float(execution_state["current_beta"]) if "current_beta" in execution_state else None
        )
        self.beta_mapper.evidence = float(execution_state.get("beta_evidence", 0.0) or 0.0)
        self.behavior_guard = BehavioralGuard(
            initial_bucket=str(execution_state.get("current_bucket", "QQQ") or "QQQ"),
            settlement_days=1,
            evidence=float(execution_state.get("bucket_evidence", 0.0) or 0.0),
        )
        self.behavior_guard.cooldown_days_remaining = int(
            execution_state.get("bucket_cooldown_days", 0) or 0
        )
        self.regime_stabilizer = RegimeStabilizer(
            initial_regime=str(execution_state.get("stable_regime"))
            if execution_state.get("stable_regime")
            else None,
            evidence=float(execution_state.get("regime_evidence", 0.0) or 0.0),
        )
        self.deployment_policy = ProbabilisticDeploymentPolicy(
            initial_state=str(execution_state.get("deployment_state", "DEPLOY_BASE") or "DEPLOY_BASE"),
            evidence=float(execution_state.get("deployment_evidence", 0.0) or 0.0),
        )

        # Initial Model Training & Seeder Priming (Epic 1)
        if initial_model is not None:
            self.gnb = initial_model
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
        """Returns deterministic priors from the persistent knowledge base."""
        return self.prior_book.current_priors()

    def daily_run(self, raw_t0_data: pd.DataFrame) -> dict:
        """
        Main execution loop for v11.5 probabilistic inference.
        """
        # 1. Feature Seeding (Epic 1)
        # AC-0: Conductor must see history to calculate Z-scores (v11.20)
        # Load local memory to provide context for the rolling window
        macro_csv = self.macro_data_path
        if os.path.exists(macro_csv):
            hist_df = pd.read_csv(macro_csv, parse_dates=["observation_date"]).set_index("observation_date")
            # Clear duplicate index if it exists in hist_df and t0
            latest_name = raw_t0_data.iloc[-1].name
            t0_dt = pd.to_datetime(latest_name if latest_name is not None else raw_t0_data.index[-1])
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
        runtime_priors, prior_details = self.prior_book.runtime_priors()

        logger.info("Model Inference: Initiating GaussianNB probabilities with current priors...")
        # AC-3: Numerical Resilience (v11.21)
        try:
            probs = self.gnb.predict_proba(latest_vector)
            probs_array = probs[0]
            if np.isnan(probs_array).any():
                logger.warning("Bayesian Inference produced NaNs. Falling back to priors.")
                posteriors = runtime_priors
            else:
                classifier_posteriors = {
                    str(k): float(v) for k, v in zip(self.gnb.classes_, probs_array, strict=True)
                }
                training_priors = {
                    str(k): float(v)
                    for k, v in zip(self.gnb.classes_, getattr(self.gnb, "class_prior_", []), strict=True)
                }
                posteriors = self.inference_engine.reweight_probabilities(
                    classifier_posteriors=classifier_posteriors,
                    training_priors=training_priors,
                    runtime_priors=runtime_priors,
                )
        except Exception as e:
            logger.error("Bayesian Inference crashed: %s. Falling back to priors.", e)
            posteriors = runtime_priors

        # 3. Probabilistic Exposure Mapping (v11.5)
        # AC-0: No constants. Base betas are audit-derived.
        raw_beta_expectation = sum(posteriors.get(regime, 0.0) * self.base_betas.get(regime, 1.0)
                                   for regime in self.base_betas.keys())

        norm_h = self.entropy_ctrl.calculate_normalized_entropy(posteriors)
        regime_decision = self.regime_stabilizer.update(posteriors=posteriors, entropy=norm_h)

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

        # 4. Continuous Beta Surface with cross-run inertia
        final_beta = self.beta_mapper.calculate_inertial_beta(protected_beta, norm_h)

        # 5. Bayesian Kelly Entry (v11.14 -> v11.15)
        # Goal: Optimize for Risk-Adjusted Expectation.
        # Uses Audit-Derived Regime Sharpe Ratios (Win Rate * Odds).
        erp_percentile = self._resolve_erp_percentile(context_df, raw_t0_data)

        # Bayesian Expected Sharpe (Win-Rate * Odds)
        # Parameters derived from self.audit_data (Structural Consistency).
        e_sharpe = sum(posteriors.get(r, 0.0) * s for r, s in self.regime_sharpes.items())

        # CDR = Information Clarity * Positive Expectation * Structural Value
        deployment_readiness = float(
            np.clip((1.0 - norm_h) * max(0.0, e_sharpe) * erp_percentile, 0.0, 1.0)
        )
        deployment_decision = self.deployment_policy.decide(
            posteriors=posteriors,
            entropy=norm_h,
            readiness_score=deployment_readiness,
            value_score=erp_percentile,
        )

        # 6. UI/Main Alignment Data
        latest_raw = raw_t0_data.iloc[-1]
        feature_values = {
            "credit_spread": float(latest_raw.get("credit_spread_bps", 0.0)),
            "erp": float(latest_raw.get("erp_pct", 0.0)),
            "net_liquidity": float(latest_raw.get("net_liquidity_usd_bn", 0.0)),
            "vix": float(latest_raw.get("vix", 0.0)),
            "entropy": norm_h,
            "outlier_stress": 1.0 - outlier_multiplier,
            "tactical_stress_score": int(np.abs(latest_vector).values.sum() * 10),
            "deployment_readiness": deployment_readiness,
        }

        sizing = self._build_sizing_result(
            beta=final_beta,
            raw_beta=raw_beta_expectation,
            entropy=norm_h,
            raw_t0_data=raw_t0_data,
        )
        execution = self.behavior_guard.apply(sizing)
        bucket = execution.target_bucket

        # Data Integrity Label
        quality = 0.0 if any(np.isnan(v) for v in feature_values.values()) else 1.0
        reason = "SENSOR DEGRADATION" if quality < 1.0 else "V11_PROBABILISTIC_OPTIMAL"

        # 6. Legacy Signal Formatting
        resurrection = (regime_decision["stable_regime"] == "RECOVERY")
        observation_date = pd.Timestamp(features.index[-1]).date().isoformat()
        self.prior_book.update_with_posterior(
            observation_date=observation_date,
            posterior=posteriors,
        )
        self.prior_book.update_execution_state(
            current_beta=float(self.beta_mapper.current_beta),
            beta_evidence=float(self.beta_mapper.evidence),
            current_bucket=self.behavior_guard.current_bucket,
            bucket_evidence=float(self.behavior_guard.evidence),
            bucket_cooldown_days=int(self.behavior_guard.cooldown_days_remaining),
            stable_regime=str(regime_decision["stable_regime"]),
            regime_evidence=float(self.regime_stabilizer.evidence),
            deployment_state=str(deployment_decision["deployment_state"]),
            deployment_evidence=float(self.deployment_policy.evidence),
        )

        return {
            "date": features.index[-1],
            "signal": {
                "target_bucket": bucket,
                "reason": execution.reason,
                "lock_active": execution.lock_active,
                "action_required": execution.action_required,
            },
            "priors": runtime_priors,
            "prior_details": prior_details,
            "probabilities": posteriors,
            "raw_regime": regime_decision["raw_regime"],
            "stable_regime": regime_decision["stable_regime"],
            "entropy": norm_h,
            "target_beta": final_beta,
            "raw_target_beta": raw_beta_expectation,
            "deployment_readiness": deployment_readiness,
            "cdr_sharpe": e_sharpe,
            "erp_percentile": erp_percentile,
            "target_allocation": self._calculate_dollars(final_beta),
            "deployment": deployment_decision,
            "feature_values": feature_values,
            "data_quality": quality,
            "resurrection_active": resurrection,
            "quality_audit": {"quality_score": quality, "reason": reason},
            "v11_execution": execution.to_dict(),
        }

    @staticmethod
    def _resolve_erp_percentile(context_df: pd.DataFrame, raw_t0_data: pd.DataFrame) -> float:
        if "erp_pct" in context_df.columns:
            erp_series = pd.to_numeric(context_df["erp_pct"], errors="coerce").dropna()
            if not erp_series.empty:
                return float(erp_series.rank(pct=True).iloc[-1])

        if "erp_pct" in raw_t0_data.columns:
            erp_series = pd.to_numeric(raw_t0_data["erp_pct"], errors="coerce").dropna()
            if not erp_series.empty:
                return float(erp_series.rank(pct=True).iloc[-1])

        return 0.5

    def _build_sizing_result(
        self,
        *,
        beta: float,
        raw_beta: float,
        entropy: float,
        raw_t0_data: pd.DataFrame,
    ) -> PositionSizingResult:
        allocation = self._calculate_dollars(beta)
        latest_raw = raw_t0_data.iloc[-1]
        current_nav = float(latest_raw.get("current_nav", 100_000.0) or 100_000.0)
        reference_capital = float(latest_raw.get("reference_capital", current_nav) or current_nav)
        invested = allocation["qqq_dollars"] + allocation["qld_notional_dollars"]
        qld_share = allocation["qld_notional_dollars"] / invested if invested > 0 else 0.0

        return PositionSizingResult(
            target_beta=round(float(beta), 6),
            raw_target_beta=round(float(raw_beta), 6),
            entropy=round(float(entropy), 6),
            uncertainty_penalty=round(max(0.0, float(raw_beta) - float(beta)), 6),
            reference_capital=round(reference_capital, 6),
            current_nav=round(current_nav, 6),
            risk_budget_dollars=round(reference_capital * float(beta), 6),
            qqq_dollars=round(float(allocation["qqq_dollars"]), 6),
            qld_notional_dollars=round(float(allocation["qld_notional_dollars"]), 6),
            cash_dollars=round(float(allocation["cash_dollars"]), 6),
            qld_share=round(qld_share, 6),
        )

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
