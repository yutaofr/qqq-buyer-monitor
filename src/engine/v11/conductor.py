import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.data_quality import (
    assess_data_quality,
    feature_reliability_weights,
)
from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.execution_pipeline import run_execution_pipeline
from src.engine.v11.core.expectation_surface import compute_beta_expectation
from src.engine.v11.core.model_validation import validate_feature_contract, validate_gaussian_nb
from src.engine.v11.core.position_sizer import PositionSizingResult
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.engine.v11.signal.behavioral_guard import BehavioralGuard
from src.engine.v11.signal.deployment_policy import ProbabilisticDeploymentPolicy
from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper
from src.engine.v11.signal.regime_stabilizer import RegimeStabilizer
from src.engine.v13.execution_overlay import ExecutionOverlayEngine
from src.regime_topology import (
    ACTIVE_REGIME_ORDER,
    canonicalize_regime_name,
    canonicalize_regime_sequence,
    merge_regime_weights,
)

logger = logging.getLogger(__name__)


def _v12_quality_field_specs() -> dict[str, tuple[str, str, str | None]]:
    return {
        "credit_spread": ("credit_spread_bps", "source_credit_spread", None),
        "net_liquidity": ("net_liquidity_usd_bn", "source_net_liquidity", None),
        "real_yield": ("real_yield_10y_pct", "source_real_yield", None),
        "treasury_vol": ("treasury_vol_21d", "source_treasury_vol", None),
        "copper_gold": ("copper_gold_ratio", "source_copper_gold", None),
        "breakeven": ("breakeven_10y", "source_breakeven", None),
        "core_capex": ("core_capex_mm", "source_core_capex", None),
        "usdjpy": ("usdjpy", "source_usdjpy", None),
        "erp_ttm": ("erp_ttm_pct", "source_erp_ttm", None),
    }


class V11Conductor:
    """The Sovereign Orchestrator. No hard-coded logic constants allowed. (AC-0)"""

    def __init__(
        self,
        macro_data_path: str = "data/macro_historical_dump.csv",
        regime_data_path: str = "data/v11_poc_phase1_results.csv",
        audit_path: str = "src/engine/v11/resources/regime_audit.json",
        prior_state_path: str = "data/v13_6_ex_hydrated_prior.json",
        snapshot_dir: str = "artifacts/v12_runtime_snapshots",
        initial_model: GaussianNB | None = None,
        overlay_mode: str | None = None,
    ):
        # 0. Load Sovereign Calibration (Audit Archive)
        self.audit_path = Path(audit_path)
        if not self.audit_path.exists():
            raise FileNotFoundError(f"CRITICAL: Audit archive missing at {audit_path}")

        with open(self.audit_path, encoding="utf-8") as f:
            self.audit_data = json.load(f)

        self.macro_data_path = str(macro_data_path)
        self.regime_data_path = str(regime_data_path)
        self.snapshot_dir = Path(snapshot_dir)
        canonical_audit_regimes = canonicalize_regime_sequence(
            self.audit_data.get("base_betas", {}).keys(),
            include_all=False,
        )
        self.base_betas = merge_regime_weights(
            self.audit_data["base_betas"],
            regimes=canonical_audit_regimes,
            include_zeros=True,
        )
        self.regime_sharpes = merge_regime_weights(
            self.audit_data["regime_sharpes"],
            regimes=canonical_audit_regimes,
            include_zeros=True,
        )
        self.gaussian_nb_var_smoothing = float(
            self.audit_data.get("model_hyperparameters", {}).get("gaussian_nb_var_smoothing", 1e-2)
        )
        self.posterior_mode = str(
            self.audit_data.get("model_hyperparameters", {}).get(
                "posterior_mode", "runtime_reweight"
            )
        )
        self.regimes = list(self.base_betas.keys())
        self._validate_canonical_inputs()
        self.regime_history = pd.read_csv(
            self.regime_data_path,
            parse_dates=["observation_date"],
        ).set_index("observation_date")
        self.regime_history["regime"] = self.regime_history["regime"].apply(
            canonicalize_regime_name
        )
        self.model_regimes = sorted(self.regime_history["regime"].dropna().astype(str).unique())
        self._validate_regime_coverage()

        # v12.0 Internal Controllers
        self.seeder = ProbabilitySeeder()
        self.feature_contract = self._validate_feature_contract()

        # SRD-v13.4: Load Weight Registry and Quality Transfer Function
        registry_path = Path(__file__).parent / "resources" / "v13_4_weights_registry.json"
        if registry_path.exists():
            with open(registry_path) as f:
                self.v13_4_registry = json.load(f)
            logger.info("V13.4 Weight Registry established.")
        else:
            self.v13_4_registry = {}
            logger.warning("V13.4 Weight Registry NOT found at %s. Using defaults.", registry_path)

        self.entropy_ctrl = EntropyController()
        self.prior_book = PriorKnowledgeBase(
            storage_path=prior_state_path,
            regimes=self.regimes,
            bootstrap_regimes=self.regime_history["regime"].tolist(),
        )

        # v13.5-GOLD+: Initial Regime Synchronization
        # Force stabilizer to align with hydrated priors on cold start to prevent "Locked Stale Regime".
        execution_state = self.prior_book.get_execution_state()
        hydrated_regime = None
        if self.prior_book.counts:
            # Select the most frequent regime from hydrated counts as the anchor
            hydrated_regime = max(self.prior_book.counts, key=self.prior_book.counts.get)
            logger.info(
                f"GOLD+: Cold-start synchronizing regime to {hydrated_regime} from hydrated priors."
            )

        self.regime_stabilizer = RegimeStabilizer(
            initial_regime=hydrated_regime or str(execution_state.get("stable_regime")),
            evidence=float(execution_state.get("bucket_evidence", 0.0) or 0.0),
        )
        execution_state = self.prior_book.get_execution_state()
        self.beta_mapper = InertialBetaMapper(
            initial_beta=float(execution_state["current_beta"])
            if "current_beta" in execution_state
            else None,
            initial_evidence=float(execution_state.get("beta_evidence", 0.0) or 0.0),
        )
        self.behavior_guard = BehavioralGuard(
            initial_bucket=str(execution_state.get("current_bucket", "QQQ") or "QQQ"),
            settlement_days=1,
            evidence=float(execution_state.get("bucket_evidence", 0.0) or 0.0),
        )
        self.behavior_guard.cooldown_days_remaining = int(
            execution_state.get("bucket_cooldown_days", 0) or 0
        )
        self.overlay_engine = ExecutionOverlayEngine()
        self.overlay_mode = overlay_mode
        self.high_entropy_streak = int(execution_state.get("high_entropy_streak", 0) or 0)
        self.deployment_policy = ProbabilisticDeploymentPolicy(
            initial_state=str(
                execution_state.get("deployment_state", "DEPLOY_BASE") or "DEPLOY_BASE"
            ),
            evidence=float(execution_state.get("deployment_evidence", 0.0) or 0.0),
        )

        # Initial Model Training & Seeder Priming (Epic 1)
        if initial_model is not None:
            self.gnb = initial_model
            self._validate_model(self.gnb)
        else:
            self.gnb = self._initialize_model(macro_data_path, regime_data_path)

        self.inference_engine = BayesianInferenceEngine(
            kde_models={r: None for r in self.gnb.classes_}, base_priors=self._get_base_priors()
        )

    def _validate_canonical_inputs(self) -> None:
        macro_path = Path(self.macro_data_path)
        regime_path = Path(self.regime_data_path)

        if not macro_path.exists():
            raise FileNotFoundError(
                f"Canonical macro DNA missing at {macro_path}. Production cold start requires checked-in DNA, not synthetic bootstrap."
            )
        if not regime_path.exists():
            raise FileNotFoundError(
                f"Canonical regime DNA missing at {regime_path}. Production cold start requires checked-in DNA, not synthetic bootstrap."
            )

    def _validate_regime_coverage(self) -> None:
        missing_betas = sorted(set(self.model_regimes) - set(self.base_betas))
        missing_sharpes = sorted(set(self.model_regimes) - set(self.regime_sharpes))
        if missing_betas or missing_sharpes:
            raise ValueError(
                "Audit calibration is incomplete for the supplied regime DNA: "
                f"missing base_betas={missing_betas}, missing regime_sharpes={missing_sharpes}."
            )

    def _validate_feature_contract(self) -> dict[str, object]:
        expected_contract = self.audit_data.get("feature_contract", {})
        return validate_feature_contract(
            expected_hash=expected_contract.get("seeder_config_hash"),
            actual_hash=self.seeder.contract_hash(),
            expected_features=expected_contract.get("feature_names"),
            actual_features=self.seeder.feature_names(),
        )

    def _initialize_model(self, macro_data_path: str, regime_data_path: str) -> GaussianNB:
        """JIT training of the Bayesian regime inference model with canonical DNA."""

        # 1. Load Seeding Datasets
        macro_df = pd.read_csv(macro_data_path, index_col="observation_date", parse_dates=True)
        regime_df = pd.read_csv(regime_data_path, parse_dates=["observation_date"]).set_index(
            "observation_date"
        )

        # Generate features via unified seeder
        features = self.seeder.generate_features(macro_df)
        df = features.join(regime_df["regime"], how="inner").dropna()

        if df.empty:
            raise ValueError(
                "JIT Training failed: Empty intersection between macro and regime data."
            )

        # Fit GNB (Architect A/B/C feature suite)
        # AC-0: Add variance smoothing to prevent probability collapse on low data (v11.19)
        gnb = GaussianNB(var_smoothing=self.gaussian_nb_var_smoothing)
        feature_cols = [c for c in df.columns if c != "regime"]
        gnb.fit(df[feature_cols], df["regime"])
        summary = self._validate_model(gnb, feature_count=len(feature_cols))

        logger.info(
            "V12.0 Conductor: JIT-Model Provenance established. "
            "Classes=%s features=%s theta=[%.4f, %.4f] var=[%.6f, %.6f]",
            summary["classes"],
            summary["feature_count"],
            summary["theta_min"],
            summary["theta_max"],
            summary["var_min"],
            summary["var_max"],
        )
        return gnb

    def _validate_model(
        self, gnb: GaussianNB, *, feature_count: int | None = None
    ) -> dict[str, object]:
        return validate_gaussian_nb(
            gnb,
            expected_classes=self.model_regimes,
            feature_count=feature_count or len(self.seeder.config),
        )

    def _get_base_priors(self) -> dict[str, float]:
        """Returns deterministic priors from the persistent knowledge base."""
        return self.prior_book.current_priors()

    def daily_run(self, raw_t0_data: pd.DataFrame) -> dict:
        """
        Main execution loop for v12.0 probabilistic inference.
        """
        # 1. Feature Seeding (Epic 1)
        # AC-0: Conductor must see history to calculate Z-scores (v11.20)
        # Load local memory to provide context for the rolling window
        macro_csv = self.macro_data_path
        previous_raw = None
        if os.path.exists(macro_csv):
            hist_df = pd.read_csv(macro_csv, parse_dates=["observation_date"]).set_index(
                "observation_date"
            )
            # Use raw_t0_data as a DataFrame to match columns
            t0_df = raw_t0_data.copy()
            # Use observation_date column as index if available to avoid Epoch 0 (1970-01-01)
            if "observation_date" in t0_df.columns:
                t0_df = t0_df.set_index("observation_date")
            elif not isinstance(t0_df.index, pd.DatetimeIndex):
                t0_df.index = pd.to_datetime(t0_df.index)

            # Clear duplicate index if it exists in hist_df and t0
            t0_dt = pd.to_datetime(t0_df.index[-1])
            hist_df = hist_df[hist_df.index < t0_dt]
            if not hist_df.empty:
                previous_raw = hist_df.iloc[-1]

            context_df = pd.concat([hist_df, t0_df], sort=False)
        else:
            context_df = raw_t0_data

        features = self.seeder.generate_features(context_df)
        diagnostics = self.seeder.latest_diagnostics()

        # 2. Bayesian Inference (Epic 2)
        # Inference only on the last point
        latest_vector = features.iloc[-1:]
        runtime_priors, prior_details = self.prior_book.runtime_priors()
        latest_raw = raw_t0_data.iloc[-1]
        quality_audit = assess_data_quality(
            latest_raw,
            previous_raw=previous_raw,
            registry=self.v13_4_registry,
            field_specs=_v12_quality_field_specs(),
        )
        feature_weights = feature_reliability_weights(
            latest_vector=latest_vector,
            latest_raw=latest_raw,
            field_quality={
                str(name): float(payload.get("quality", 1.0))
                for name, payload in dict(quality_audit.get("fields", {})).items()
            },
            seeder_config=self.seeder.config,
        )

        logger.info("Model Inference: Initiating GaussianNB probabilities with current priors...")
        # AC-3: Numerical Resilience (v11.21) + v13.6-EX Precision
        try:
            class_priors = list(getattr(self.gnb, "class_prior_", []))
            if len(class_priors) != len(self.gnb.classes_):
                class_priors = [1.0 / len(self.gnb.classes_)] * len(self.gnb.classes_)
            training_priors = {
                str(label): float(probability)
                for label, probability in zip(self.gnb.classes_, class_priors, strict=True)
            }
            if self.posterior_mode == "classifier_only":
                active_priors = training_priors
            elif self.posterior_mode == "runtime_reweight":
                active_priors = runtime_priors
            else:
                active_priors = runtime_priors  # Default to runtime

            # v13.6-EX / v13.7-ULTIMA: Adaptive Paranoid Adjustment
            active_registry = self.v13_4_registry
            if self.high_entropy_streak >= 21:
                logger.warning(
                    f"ULTIMA CIRCUIT BREAKER: Streak={self.high_entropy_streak}. Cutting all non-core sensors."
                )
                # v13.7-ULTIMA: Mandatory Cut (Weight=0) for everything except Level 1
                import copy

                active_registry = copy.deepcopy(self.v13_4_registry)
                matrix = active_registry.get("feature_weight_matrix", {})
                core_fields = set(
                    active_registry.get("core_fields", ["credit_spread_bps", "spread_"])
                )
                for k in matrix:
                    if k not in core_fields:
                        matrix[k] = 0.0  # Extreme surgical cut
            elif self.high_entropy_streak >= 5:
                logger.warning(
                    f"PARANOID_MODE ACTIVE: High entropy streak={self.high_entropy_streak}. Damping secondary factors."
                )
                import copy

                active_registry = copy.deepcopy(self.v13_4_registry)
                matrix = active_registry.get("feature_weight_matrix", {})
                core_fields = set(
                    active_registry.get("core_fields", ["credit_spread_bps", "spread_"])
                )
                for k in matrix:
                    if k not in core_fields:
                        matrix[k] = float(matrix[k]) * 0.7

            # SRD-v13.5-PRO: Asymmetric Weighted Inference
            # v13.7-FINAL: Extract tau and m from registry (CR-1 & CR-4)
            registry_tau = float(active_registry.get("inference_tau", 0.5))
            registry_m = float(active_registry.get("inference_momentum_m", 0.35))

            posteriors, bayesian_diagnostics = self.inference_engine.infer_gaussian_nb_posterior(
                classifier=self.gnb,
                evidence_frame=latest_vector,
                runtime_priors=active_priors,
                weight_registry=active_registry,
                feature_quality_weights=feature_weights,  # Task 6: External quality signals
                tau=registry_tau,
                m=registry_m,
            )
            if any(np.isnan(list(posteriors.values()))):
                logger.warning("Bayesian Inference produced NaNs. Falling back to priors.")
                posteriors = active_priors
                bayesian_diagnostics = {"level_contributions": {}}
        except Exception as e:
            logger.error("Bayesian Inference Pipeline crashed: %s. Falling back to priors.", e)
            posteriors = runtime_priors
            bayesian_diagnostics = {"level_contributions": {}}

        posterior_entropy = self.entropy_ctrl.calculate_normalized_entropy(posteriors)

        # 3. Execution Pipeline (v13.8 Unified)
        # Goal: Decouple risk-haircut, floor/overlay logic, and deployment readiness.
        # Parameters derived from self.audit_data (Structural Consistency).
        e_sharpe = sum(posteriors.get(r, 0.0) * s for r, s in self.regime_sharpes.items())
        erp_percentile = self._resolve_erp_percentile(context_df, raw_t0_data)

        # Use canonical sorting for probabilities to prevent index shift hallucinations
        posteriors = {r: float(posteriors[r]) for r in ACTIVE_REGIME_ORDER if r in posteriors}

        raw_beta_expectation = compute_beta_expectation(posteriors, self.base_betas)

        # SRD-v13.4: Evaluate Overlay BEFORE Pipeline to support Conditional Floor
        overlay = self.overlay_engine.evaluate(context_df.reset_index(), mode=self.overlay_mode)

        pipeline_result = run_execution_pipeline(
            raw_beta=raw_beta_expectation,
            posterior_entropy=posterior_entropy,
            quality_score=float(quality_audit["quality_score"]),
            posteriors=posteriors,
            entropy_controller=self.entropy_ctrl,
            overlay=overlay,
            e_sharpe=e_sharpe,
            erp_percentile=erp_percentile,
            high_entropy_streak=self.high_entropy_streak,
        )

        norm_h = pipeline_result["effective_entropy"]
        pre_floor_beta = pipeline_result["pre_floor_beta"]
        protected_beta = pipeline_result["protected_beta"]
        is_floor_active = pipeline_result["is_floor_active"]
        overlay_beta = pipeline_result["overlay_beta"]
        deployment_readiness = pipeline_result["deployment_readiness"]
        overlay_deployment_readiness = pipeline_result["overlay_deployment_readiness"]
        self.high_entropy_streak = pipeline_result["high_entropy_streak"]

        quality_audit["posterior_entropy"] = posterior_entropy
        quality_audit["effective_entropy"] = norm_h
        quality_audit["entropy_penalty"] = max(0.0, norm_h - posterior_entropy)

        # v13.7-FINAL: Inject quality details for trace (CR-2)
        quality_audit["q_core_val"] = quality_audit.get("q_core", 1.0)
        quality_audit["q_support_val"] = quality_audit.get("q_support", 1.0)
        quality_audit["v13_4_diagnostics"] = bayesian_diagnostics

        # 3. Probabilistic Exposure Mapping (v13.5-GOLD)
        # SRD-v13.5-GOLD: Precision Stabilizer Update
        regime_decision = self.regime_stabilizer.update(posteriors=posteriors, entropy=norm_h)

        # Expert Audit: Log level contributions to resolve conflict (H=0.87)
        top_regime = regime_decision["raw_regime"]
        if norm_h > 0.8:
            contribs = bayesian_diagnostics.get("level_contributions", {}).get(top_regime, {})
            sorted_contribs = sorted(contribs.items(), key=lambda x: x[1])
            logger.info(
                f"High Entropy Conflict Audit (Top Regime={top_regime}): Lowest Contribs: {sorted_contribs[:3]}"
            )

        # 4. Continuous Beta Surface with cross-run inertia (SRD: Floor is input to smoothing)
        final_beta = self.beta_mapper.calculate_inertial_beta(overlay_beta, norm_h)

        # 5. Bayesian Kelly Entry (v11.14 -> v11.15)
        # CDR = Information Clarity * Positive Expectation * Structural Value
        deployment_decision = self.deployment_policy.decide(
            posteriors=posteriors,
            entropy=norm_h,
            readiness_score=overlay_deployment_readiness,
            value_score=erp_percentile,
        )

        deployment_decision = {
            **deployment_decision,
            "base_readiness_score": deployment_readiness,
            "overlay_readiness_score": overlay_deployment_readiness,
            "overlay_multiplier": float(overlay["deployment_overlay_multiplier"]),
        }

        # 6. UI/Main Alignment Data
        def _safe_float(value: object, default: float = 0.0) -> float:
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(numeric) or not np.isfinite(float(numeric)):
                return float(default)
            return float(numeric)

        feature_values = {
            "credit_spread": _safe_float(latest_raw.get("credit_spread_bps")),
            "real_yield": _safe_float(latest_raw.get("real_yield_10y_pct")),
            "net_liquidity": _safe_float(latest_raw.get("net_liquidity_usd_bn")),
            "treasury_vol": _safe_float(latest_raw.get("treasury_vol_21d")),
            "copper_gold": _safe_float(latest_raw.get("copper_gold_ratio")),
            "breakeven": _safe_float(latest_raw.get("breakeven_10y")),
            "core_capex": _safe_float(latest_raw.get("core_capex_mm")),
            "usdjpy": _safe_float(latest_raw.get("usdjpy")),
            "erp_ttm": _safe_float(latest_raw.get("erp_ttm_pct")),
            "entropy": norm_h,
            "deployment_readiness": deployment_readiness,
        }
        if not diagnostics.empty:
            latest_diag = diagnostics.iloc[-1]
            feature_values.update(
                {
                    "move_21d_raw_z": _safe_float(latest_diag.get("move_21d_raw_z")),
                    "move_21d_orth_z": _safe_float(latest_diag.get("move_21d_orth_z")),
                    "move_spread_beta": _safe_float(latest_diag.get("move_spread_beta")),
                    "move_spread_corr_21d": _safe_float(latest_diag.get("move_spread_corr_21d")),
                }
            )

        sizing = self._build_sizing_result(
            beta=final_beta,
            raw_beta=raw_beta_expectation,
            entropy=norm_h,
            raw_t0_data=raw_t0_data,
        )
        execution = self.behavior_guard.apply(sizing)
        bucket = execution.target_bucket

        quality = float(quality_audit["quality_score"])
        self._write_runtime_snapshot(
            raw_t0_data=raw_t0_data,
            latest_vector=latest_vector,
            runtime_priors=runtime_priors,
            prior_details=prior_details,
            quality_audit=quality_audit,
            feature_weights=feature_weights,
            execution_overlay=overlay,
            final_execution={
                "protected_beta_pre_overlay": round(float(protected_beta), 6),
                "overlay_beta": round(float(overlay_beta), 6),
                "raw_target_beta": round(float(raw_beta_expectation), 6),
                "beta_expectation": round(float(raw_beta_expectation), 6),
                "deployment_state_pre_overlay": "derived_from_readiness",
                "deployment_state_post_overlay": str(deployment_decision["deployment_state"]),
                "behavioral_guard_input_beta": round(float(final_beta), 6),
                "behavioral_guard_output_bucket": bucket,
                "final_target_beta": round(float(final_beta), 6),
            },
        )

        # 6. UI/Main Alignment Data (v13.6-EX)
        resurrection = regime_decision["stable_regime"] == "RECOVERY"
        observation_date = pd.Timestamp(features.index[-1]).date().isoformat()
        self.prior_book.update_with_posterior(
            observation_date=observation_date,
            posterior=posteriors,
        )

        # Update High Entropy Streak for PARANOID_MODE (v13.6-EX)
        if norm_h > 0.85:
            self.high_entropy_streak += 1
        else:
            self.high_entropy_streak = 0

        # Build final unified result dictionary
        runtime_result = {
            "date": features.index[-1],
            "signal": {
                "target_bucket": bucket,
                "reason": execution.reason,
                "lock_active": execution.lock_active,
                "action_required": execution.action_required,
                "is_floor_active": is_floor_active,
                "hydration_anchor": self.prior_book.execution_state.get(
                    "hydration_anchor", "2018-01-01"
                ),
                "high_entropy_streak": self.high_entropy_streak,
            },
            "priors": runtime_priors,
            "prior_details": prior_details,
            "probabilities": posteriors,
            "raw_regime": regime_decision["raw_regime"],
            "stable_regime": regime_decision["stable_regime"],
            "entropy": norm_h,
            "protected_beta": protected_beta,
            "raw_target_beta_pre_floor": pre_floor_beta,
            "is_floor_active": is_floor_active,
            "overlay_beta": overlay_beta,
            "overlay": overlay,
            "target_beta": final_beta,
            "raw_target_beta": raw_beta_expectation,
            "beta_expectation": raw_beta_expectation,
            "deployment_readiness": deployment_readiness,
            "deployment_readiness_overlay": overlay_deployment_readiness,
            "cdr_sharpe": e_sharpe,
            "erp_percentile": erp_percentile,
            "target_allocation": self._calculate_dollars(final_beta),
            "deployment": deployment_decision,
            "feature_values": feature_values,
            "data_quality": quality,
            "resurrection_active": resurrection,
            "quality_audit": quality_audit,
            "v11_execution": execution.to_dict(),
            "v13_4_diagnostics": quality_audit.get("v13_4_diagnostics", {}),
        }

        # Save Persistent Execution State
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
            high_entropy_streak=self.high_entropy_streak,
            hydration_anchor=runtime_result.get("signal", {}).get("hydration_anchor", "2018-01-01"),
        )

        return runtime_result

    def _write_runtime_snapshot(
        self,
        *,
        raw_t0_data: pd.DataFrame,
        latest_vector: pd.DataFrame,
        runtime_priors: dict[str, float],
        prior_details: dict[str, object],
        quality_audit: dict[str, object],
        feature_weights: dict[str, float],
        execution_overlay: dict[str, object],
        final_execution: dict[str, object],
    ) -> None:
        try:
            serialized_row = self._serialize_frame(raw_t0_data)
            observation_date = str(serialized_row[0].get("observation_date", "unknown"))
            payload = {
                "snapshot_version": "v13_runtime_snapshot.v1",
                "captured_at_utc": datetime.now(UTC).isoformat(),
                "observation_date": observation_date,
                "macro_data_path": self.macro_data_path,
                "regime_data_path": self.regime_data_path,
                "audit_path": str(self.audit_path),
                "overlay_audit_path": str(self.overlay_engine.audit_path),
                "feature_contract": self.feature_contract,
                "runtime_priors": runtime_priors,
                "prior_details": prior_details,
                "quality_audit": quality_audit,
                "feature_weights": feature_weights,
                "raw_t0_data": serialized_row,
                "feature_vector": self._serialize_frame(latest_vector),
                "gaussian_nb": {
                    "classes": [str(value) for value in getattr(self.gnb, "classes_", [])],
                    "theta": np.asarray(getattr(self.gnb, "theta_", [])).tolist(),
                    "var": np.asarray(getattr(self.gnb, "var_", [])).tolist(),
                    "class_prior": np.asarray(getattr(self.gnb, "class_prior_", [])).tolist(),
                },
                "execution_overlay": execution_overlay,
                "final_execution": final_execution,
            }

            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = self.snapshot_dir / f"snapshot_{observation_date}.json"
            snapshot_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write v11 runtime snapshot: %s", exc)

    @staticmethod
    def _serialize_frame(frame: pd.DataFrame) -> list[dict[str, object]]:
        serializable = frame.copy()
        if "observation_date" not in serializable.columns:
            index_name = serializable.index.name or "observation_date"
            serializable = serializable.reset_index().rename(
                columns={index_name: "observation_date"}
            )

        for column in serializable.columns:
            if pd.api.types.is_datetime64_any_dtype(serializable[column]):
                serializable[column] = pd.to_datetime(serializable[column]).dt.strftime("%Y-%m-%d")

        serializable = serializable.replace({np.nan: None})
        return [
            {
                str(key): (value.item() if hasattr(value, "item") else value)
                for key, value in row.items()
            }
            for row in serializable.to_dict(orient="records")
        ]

    @staticmethod
    def _resolve_erp_percentile(context_df: pd.DataFrame, raw_t0_data: pd.DataFrame) -> float:
        if "erp_ttm_pct" in context_df.columns:
            erp_series = pd.to_numeric(context_df["erp_ttm_pct"], errors="coerce").dropna()
            if not erp_series.empty:
                return float(erp_series.rank(pct=True).iloc[-1])

        if "erp_ttm_pct" in raw_t0_data.columns:
            erp_series = pd.to_numeric(raw_t0_data["erp_ttm_pct"], errors="coerce").dropna()
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
            qld = (beta - 1.0) * NAV  # Exposure above 1.0 goes to QLD
            qqq = NAV
            cash = 0.0
        else:
            qld = 0.0
            qqq = NAV * beta
            cash = NAV - qqq
        return {"qqq_dollars": qqq, "qld_notional_dollars": qld, "cash_dollars": cash}
