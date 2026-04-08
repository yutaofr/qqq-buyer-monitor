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
from src.engine.v11.core.expectation_surface import (
    allocate_reference_path,
    compute_beta_expectation,
)
from src.engine.v11.core.mahalanobis_guard import MahalanobisGuard
from src.engine.v11.core.model_validation import validate_feature_contract, validate_gaussian_nb
from src.engine.v11.core.position_sizer import PositionSizingResult
from src.engine.v11.core.price_topology import (
    align_posteriors_with_recovery_process,
    anchor_beta_with_topology,
    blend_posteriors_with_topology,
    infer_price_topology_state,
    price_topology_payload,
    topology_likelihood_penalties,
)
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.engine.v11.signal.behavioral_guard import BehavioralGuard
from src.engine.v11.signal.deployment_policy import ProbabilisticDeploymentPolicy
from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper
from src.engine.v11.signal.regime_stabilizer import RegimeStabilizer
from src.engine.v11.signal.resonance_detector import ResonanceDetector
from src.engine.v13.execution_overlay import ExecutionOverlayEngine
from src.regime_dynamics import compute_probability_dynamics
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
        price_history_path: str = "data/qqq_history_cache.csv",
        initial_model: GaussianNB | None = None,
        overlay_mode: str | None = None,
        training_cutoff: str | datetime | None = None,
        allow_prior_bootstrap_drift: bool = False,
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
        self.training_cutoff = pd.to_datetime(training_cutoff) if training_cutoff is not None else None
        self.price_history_path = str(price_history_path)
        self.price_history = self._load_price_history(price_history_path)
        self.allow_prior_bootstrap_drift = bool(allow_prior_bootstrap_drift)
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
            self.audit_data.get("model_hyperparameters", {}).get("gaussian_nb_var_smoothing", 0.1)
        )
        self.posterior_mode = str(
            self.audit_data.get("model_hyperparameters", {}).get(
                "posterior_mode", "runtime_reweight"
            )
        )
        self.price_topology_contract = dict(self.audit_data.get("price_topology_contract", {}))
        self.regimes = list(self.base_betas.keys())
        self._validate_canonical_inputs()
        self.regime_history = pd.read_csv(
            self.regime_data_path,
            parse_dates=["observation_date"],
        ).set_index("observation_date")
        self.regime_history["regime"] = self.regime_history["regime"].apply(
            canonicalize_regime_name
        )
        regime_training_view = self.regime_history
        if self.training_cutoff is not None:
            regime_training_view = regime_training_view[regime_training_view.index < self.training_cutoff]
        self.model_regimes = self._resolve_effective_model_regimes(regime_training_view)
        if not self.model_regimes:
            raise ValueError(
                "No effective regime classes remain after aligning regime DNA with the canonical macro calendar."
            )
        self._validate_regime_coverage()

        # v12.0 Internal Controllers
        expected_feature_contract = self.audit_data.get("feature_contract", {})
        self.seeder = ProbabilitySeeder(
            selected_features=expected_feature_contract.get("feature_names")
        )
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

        constraints_path = Path(__file__).parent / "resources" / "logical_constraints.json"
        if constraints_path.exists():
            with open(constraints_path) as f:
                self.logical_constraints = json.load(f)
            logger.info("Bayesian Logical Constraints established.")
        else:
            self.logical_constraints = None
            logger.warning("Logical Constraints NOT found at %s.", constraints_path)

        self.entropy_ctrl = EntropyController()
        self.mahalanobis_guard = MahalanobisGuard()

        bootstrap_history = self.regime_history
        if self.training_cutoff is not None:
            bootstrap_history = bootstrap_history[bootstrap_history.index < self.training_cutoff]
        bootstrap_regimes = bootstrap_history["regime"].tolist()

        self.prior_book = PriorKnowledgeBase(
            storage_path=prior_state_path,
            regimes=self.regimes,
            bootstrap_regimes=bootstrap_regimes,
            allow_bootstrap_fingerprint_drift=self.allow_prior_bootstrap_drift,
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
        self.resonance_detector = ResonanceDetector()

        # Initial Model Training & Seeder Priming (Epic 1)
        if initial_model is not None:
            self.gnb = initial_model
            # For cold start with initial model, we still need a baseline featureset for the guard.
            # We use the full history available to avoid breaking the guard.
            initial_features = self.seeder.generate_features(self.regime_history.dropna())
            self.mahalanobis_guard.fit_baseline(initial_features)
            self._validate_model(self.gnb)
        else:
            self.gnb, training_features = self._initialize_model(
                macro_data_path, regime_data_path, training_cutoff=training_cutoff
            )
            # Fit Mahalanobis Guard on EXACT matched features used for model training (v14.4)
            self.mahalanobis_guard.fit_baseline(training_features)

        self.inference_engine = BayesianInferenceEngine(
            base_priors=self._get_base_priors(),
            kde_models={r: None for r in self.gnb.classes_}
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

    @staticmethod
    def _load_price_history(price_history_path: str) -> pd.DataFrame:
        path = Path(price_history_path)
        if not path.exists():
            return pd.DataFrame()

        price_df = pd.read_csv(path, index_col=0)
        index = pd.to_datetime(price_df.index, errors="coerce", utc=True)
        index = index.tz_convert(None)
        price_df.index = index.normalize()
        price_df = price_df[price_df.index.notna()]
        if "Close" in price_df.columns:
            price_df["Close"] = pd.to_numeric(price_df["Close"], errors="coerce")
        if "Volume" in price_df.columns:
            price_df["Volume"] = pd.to_numeric(price_df["Volume"], errors="coerce")
        return price_df.sort_index()

    def _augment_context_with_price_history(self, context_df: pd.DataFrame) -> pd.DataFrame:
        if context_df.empty or self.price_history.empty:
            return context_df

        frame = context_df.copy()
        if not isinstance(frame.index, pd.DatetimeIndex):
            frame.index = pd.to_datetime(frame.index, errors="coerce")
        index = pd.to_datetime(frame.index, errors="coerce")
        if getattr(index, "tz", None) is not None:
            index = index.tz_convert(None)
        frame.index = index.normalize()
        frame = frame[frame.index.notna()]
        if frame.empty:
            return context_df

        history = self.price_history.reindex(frame.index, method="ffill")
        if "Close" in history.columns:
            existing_close = (
                pd.to_numeric(frame["qqq_close"], errors="coerce")
                if "qqq_close" in frame.columns
                else pd.Series(index=frame.index, dtype=float)
            )
            frame["qqq_close"] = existing_close.combine_first(history["Close"])
            source_close = frame.get("source_qqq_close")
            if source_close is None:
                frame["source_qqq_close"] = "direct:yfinance:cached"
            else:
                frame["source_qqq_close"] = source_close.where(
                    source_close.notna(), "direct:yfinance:cached"
                )
            quality_close = (
                pd.to_numeric(frame["qqq_close_quality_score"], errors="coerce")
                if "qqq_close_quality_score" in frame.columns
                else pd.Series(index=frame.index, dtype=float)
            )
            frame["qqq_close_quality_score"] = quality_close.fillna(1.0)

        if "Volume" in history.columns:
            existing_volume = (
                pd.to_numeric(frame["qqq_volume"], errors="coerce")
                if "qqq_volume" in frame.columns
                else pd.Series(index=frame.index, dtype=float)
            )
            frame["qqq_volume"] = existing_volume.combine_first(history["Volume"])
            source_volume = frame.get("source_qqq_volume")
            if source_volume is None:
                frame["source_qqq_volume"] = "direct:yfinance:cached"
            else:
                frame["source_qqq_volume"] = source_volume.where(
                    source_volume.notna(), "direct:yfinance:cached"
                )
            quality_volume = (
                pd.to_numeric(frame["qqq_volume_quality_score"], errors="coerce")
                if "qqq_volume_quality_score" in frame.columns
                else pd.Series(index=frame.index, dtype=float)
            )
            frame["qqq_volume_quality_score"] = quality_volume.fillna(1.0)

        return frame

    def _validate_regime_coverage(self) -> None:
        missing_betas = sorted(set(self.model_regimes) - set(self.base_betas))
        missing_sharpes = sorted(set(self.model_regimes) - set(self.regime_sharpes))
        if missing_betas or missing_sharpes:
            raise ValueError(
                "Audit calibration is incomplete for the supplied regime DNA: "
                f"missing base_betas={missing_betas}, missing regime_sharpes={missing_sharpes}."
            )

    def _resolve_effective_model_regimes(self, regime_training_view: pd.DataFrame) -> list[str]:
        macro_index = pd.read_csv(
            self.macro_data_path,
            usecols=["observation_date"],
            parse_dates=["observation_date"],
        )["observation_date"]
        macro_index = pd.DatetimeIndex(macro_index)
        if getattr(macro_index, "tz", None) is not None:
            macro_index = macro_index.tz_convert(None)
        macro_index = macro_index.normalize()

        effective_view = regime_training_view.copy()
        index = pd.DatetimeIndex(effective_view.index)
        if getattr(index, "tz", None) is not None:
            index = index.tz_convert(None)
        effective_view.index = index.normalize()
        effective_view = effective_view[effective_view.index.isin(macro_index)]
        return sorted(effective_view["regime"].dropna().astype(str).unique())

    def _validate_feature_contract(self) -> dict[str, object]:
        expected_contract = self.audit_data.get("feature_contract", {})
        return validate_feature_contract(
            expected_hash=expected_contract.get("seeder_config_hash"),
            actual_hash=self.seeder.contract_hash(),
            expected_features=expected_contract.get("feature_names"),
            actual_features=self.seeder.feature_names(),
        )

    def _initialize_model(
        self,
        macro_data_path: str,
        regime_data_path: str,
        training_cutoff: str | datetime | None = None,
    ) -> GaussianNB:
        """JIT training of the Bayesian regime inference model with canonical DNA."""

        # 1. Load Seeding Datasets
        macro_df = pd.read_csv(macro_data_path, index_col="observation_date", parse_dates=True)
        regime_df = pd.read_csv(regime_data_path, parse_dates=["observation_date"]).set_index(
            "observation_date"
        )
        regime_df["regime"] = regime_df["regime"].apply(canonicalize_regime_name)

        # Apply training cutoff for PIT integrity (v14 forensic fix)
        if training_cutoff:
            cutoff_dt = pd.to_datetime(training_cutoff)
            macro_df = macro_df[macro_df.index < cutoff_dt]
            regime_df = regime_df[regime_df.index < cutoff_dt]
            logger.info(f"V12.0 Conductor: JIT Model training constrained to < {cutoff_dt}")

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
        # FIT AND DIAGNOSE (Forensic Audit 13.9)
        gnb.fit(df[feature_cols], df["regime"])

        # Log class means to detect "Identity Lock"
        for i, label in enumerate(gnb.classes_):
             logger.info(f"FORENSIC GNB [{label}]: mean[spread_21d]={gnb.theta_[i][feature_cols.index('spread_21d')]:.4f}, var={gnb.var_[i][feature_cols.index('spread_21d')]:.6f}")

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
        return gnb, df[feature_cols]

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

    def daily_run(self, raw_t0_data: pd.DataFrame, baseline_result: dict | None = None) -> dict:
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
        context_df = self._augment_context_with_price_history(context_df)

        features = self.seeder.generate_features(context_df)
        diagnostics = self.seeder.latest_diagnostics()

        # 2. Bayesian Inference (Epic 2)
        # Inference only on the last point
        latest_vector = features.iloc[-1:]
        topology_state = infer_price_topology_state(
            context_df,
            posterior_blend_weight=float(
                self.price_topology_contract.get("posterior_blend_weight", 0.25)
            ),
            beta_anchor_weight=float(self.price_topology_contract.get("beta_anchor_weight", 0.35)),
            confidence_margin=float(self.price_topology_contract.get("confidence_margin", 0.25)),
        )

        # v14.2 Duration Hardening: Pass macro_values for Inertia/Mid-Cycle Anchor
        active_registry = self.v13_4_registry
        f_vals_for_prior = latest_vector.iloc[0].to_dict()

        # v14.5: Inject inertia matrix from registry
        f_vals_for_prior["dynamic_beta_inertia_matrix"] = active_registry.get(
            "dynamic_beta_inertia_matrix", {}
        )

        runtime_priors, prior_details = self.prior_book.runtime_priors(
            macro_values=f_vals_for_prior
        )
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

            if self.high_entropy_streak >= 42:
                # v14.4 FIX: RESET DEADLOCK. If we have been blind for >42 days, we must probe for signal.
                logger.warning("ULTIMA PERSISTENCE LIMIT REACHED (42d). Resetting high-entropy streak to restore sensors.")
                self.high_entropy_streak = 0

            if self.high_entropy_streak >= 21:
                logger.warning(
                    f"ULTIMA CIRCUIT BREAKER ACTIVE: Streak={self.high_entropy_streak}. Dampening non-core sensors."
                )
                import copy
                active_registry = copy.deepcopy(self.v13_4_registry)
                matrix = active_registry.get("feature_weight_matrix", {})
                core_fields = set(active_registry.get("core_fields", ["spread_21d", "spread_absolute", "real_yield_structural_z"]))

                for k in list(matrix.keys()):
                    is_core = any(k.startswith(cf) or cf.startswith(k) for cf in core_fields)
                    if not is_core and k != "DEFAULT_FALLBACK":
                        # v14.4 FIX: Softened from 0.0 to 0.1 to prevent evidence blackout (Uniform Deadlock)
                        matrix[k] = 0.1
            elif self.high_entropy_streak >= 5:
                logger.warning(
                    f"PARANOID_MODE ACTIVE: High entropy streak={self.high_entropy_streak}. Damping secondary factors."
                )
                import copy
                active_registry = copy.deepcopy(self.v13_4_registry)
                matrix = active_registry.get("feature_weight_matrix", {})
                core_fields = set(active_registry.get("core_fields", ["spread_21d", "spread_absolute", "real_yield_structural_z"]))
                for k in matrix:
                    if k not in core_fields:
                        matrix[k] = float(matrix[k]) * 0.7

            # SRD-v14.3: QQQ Structural Cycle Alignment
            # We use the standardized features from the seeder to drive Physical Gating.
            f_values = latest_vector.iloc[0].to_dict()
            regime_penalties = topology_likelihood_penalties(
                topology_state,
                floor=float(self.price_topology_contract.get("likelihood_penalty_floor", 0.03)),
                exponent=float(
                    self.price_topology_contract.get("likelihood_penalty_exponent", 0.75)
                ),
            )

            # v14.4 BAYESIAN OVERDRIVE: Out-of-distribution detection
            # Capture extreme market states (Crash/Bubble) and increase model responsiveness.
            ood_threshold = float(active_registry.get("mahalanobis_ood_threshold", 4.0))
            is_overdrive = self.mahalanobis_guard.is_outlier(
                latest_vector.iloc[0].values, threshold=ood_threshold
            )
            tau_factor = float(active_registry.get("overdrive_tau_factor", 0.5))

            # v13.7-FINAL: Extract tau from registry (CR-1)
            registry_tau = float(active_registry.get("inference_tau", 0.5))

            posteriors, bayesian_diagnostics = self.inference_engine.infer_gaussian_nb_posterior(
                classifier=self.gnb,
                evidence_frame=latest_vector,
                runtime_priors=active_priors,
                weight_registry=active_registry,
                feature_quality_weights=feature_weights,
                feature_values=f_values,
                tau=registry_tau,
                is_overdrive=is_overdrive,
                tau_factor=tau_factor,
                logical_constraints=self.logical_constraints,
                regime_penalties=regime_penalties,
            )
            if any(np.isnan(list(posteriors.values()))):
                logger.warning("Bayesian Inference produced NaNs. Falling back to priors.")
                posteriors = active_priors
                bayesian_diagnostics = {"level_contributions": {}}
        except Exception as e:
            logger.error("Bayesian Inference Pipeline crashed: %s. Falling back to priors.", e)
            posteriors = runtime_priors
            bayesian_diagnostics = {"level_contributions": {}}

        posteriors = blend_posteriors_with_topology(posteriors, topology_state)
        posteriors = align_posteriors_with_recovery_process(posteriors, topology_state)
        posteriors = {r: float(posteriors.get(r, 0.0)) for r in ACTIVE_REGIME_ORDER}
        posterior_entropy = self.entropy_ctrl.calculate_normalized_entropy(posteriors)

        # 3. Execution Pipeline (v13.8 Unified)
        # Goal: Decouple risk-haircut, floor/overlay logic, and deployment readiness.
        # Parameters derived from self.audit_data (Structural Consistency).
        e_sharpe = sum(posteriors.get(r, 0.0) * s for r, s in self.regime_sharpes.items())
        erp_percentile = self._resolve_erp_percentile(context_df, raw_t0_data)

        # Use canonical sorting for probabilities to prevent index shift hallucinations
        prior_execution_state = self.prior_book.get_execution_state()
        previous_effective_entropy = pd.to_numeric(
            pd.Series([prior_execution_state.get("effective_entropy")]),
            errors="coerce",
        ).iloc[0]
        previous_effective_entropy = (
            None if pd.isna(previous_effective_entropy) else float(previous_effective_entropy)
        )
        previous_posterior_for_state = self.prior_book.last_posterior
        probability_dynamics = compute_probability_dynamics(
            posteriors,
            previous=previous_posterior_for_state,
            previous_previous=prior_execution_state.get("previous_posterior"),
        )

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
        regime_decision = self.regime_stabilizer.update(
            posteriors=posteriors,
            entropy=norm_h,
            release_hint={
                "topology_regime": topology_state.regime,
                "topology_confidence": topology_state.confidence,
                "recovery_impulse": topology_state.recovery_impulse,
                "damage_memory": topology_state.damage_memory,
                "bust_pressure": topology_state.bust_pressure,
                "bearish_divergence": topology_state.bearish_divergence,
                "transition_intensity": topology_state.transition_intensity,
                "repair_persistence": topology_state.repair_persistence,
            },
        )

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
        final_beta = anchor_beta_with_topology(final_beta, topology_state)

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
            "price_topology_confidence": float(topology_state.confidence),
            "price_topology_expected_beta": float(topology_state.expected_beta),
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
        reentry_signal = max(
            float(overlay.get("positive_score", 0.0) or 0.0),
            float(topology_state.confidence if topology_state.regime == "RECOVERY" else 0.0),
        )
        execution = self.behavior_guard.apply(sizing, reentry_signal=reentry_signal)
        bucket = execution.target_bucket

        quality = float(quality_audit["quality_score"])

        # 7. QLD Resonance Detector (v14.5)
        # Extract inputs for triple-resonance
        tractor_prob = 0.0
        sidecar_prob = 0.0
        if baseline_result:
            tractor_prob = float(baseline_result.get("tractor", {}).get("prob", 0.0))
            sidecar_prob = float(baseline_result.get("sidecar", {}).get("prob", 0.0))
        risk_context = {
            "tractor_prev": float(baseline_result.get("tractor", {}).get("prev_prob", tractor_prob))
            if baseline_result
            else tractor_prob,
            "sidecar_prev": float(baseline_result.get("sidecar", {}).get("prev_prob", sidecar_prob))
            if baseline_result
            else sidecar_prob,
        }

        resonance_result = self.resonance_detector.evaluate(
            posteriors=posteriors,
            dynamics=probability_dynamics,
            effective_entropy=norm_h,
            high_entropy_streak=self.high_entropy_streak,
            tractor_prob=tractor_prob,
            sidecar_prob=sidecar_prob,
            previous_effective_entropy=previous_effective_entropy,
            risk_context=risk_context,
        )

        forensic_snapshot_path = self._write_runtime_snapshot(
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
                "resonance_action": resonance_result["action"],
                "resonance_confidence": resonance_result["confidence"],
                "resonance_reason": resonance_result["reason"],
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
                "resonance": resonance_result,
            },
            "priors": runtime_priors,
            "prior_details": prior_details,
            "probabilities": posteriors,
            "probability_dynamics": probability_dynamics,
            "price_topology": price_topology_payload(topology_state),
            "regime_stabilizer": dict(regime_decision),
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
            "target_allocation": self._calculate_dollars(
                final_beta,
                preferred_bucket=bucket,
            ),
            "deployment": deployment_decision,
            "feature_values": feature_values,
            "data_quality": quality,
            "resurrection_active": resurrection,
            "quality_audit": quality_audit,
            "v11_execution": execution.to_dict(),
            "v13_4_diagnostics": quality_audit.get("v13_4_diagnostics", {}),
            "forensic_snapshot_path": forensic_snapshot_path,
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
            previous_posterior=previous_posterior_for_state,
            effective_entropy=float(norm_h),
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
    ) -> str | None:
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
            return str(snapshot_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write v11 runtime snapshot: %s", exc)
            return None

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
        latest_raw = raw_t0_data.iloc[-1]
        current_nav = float(latest_raw.get("current_nav", 100_000.0) or 100_000.0)
        reference_capital = float(latest_raw.get("reference_capital", current_nav) or current_nav)
        allocation = allocate_reference_path(
            beta,
            bucket=self.behavior_guard.current_bucket,
            reference_capital=reference_capital,
        )
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

    def _calculate_dollars(self, beta: float, *, preferred_bucket: str = "QQQ") -> dict:
        """Lightweight dollar mapping for main.py and user-facing reference paths."""
        return allocate_reference_path(
            beta,
            bucket=preferred_bucket,
            reference_capital=100_000.0,
        )
