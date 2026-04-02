import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.model_validation import validate_feature_contract, validate_gaussian_nb
from src.engine.v11.core.position_sizer import PositionSizingResult
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.engine.v11.signal.behavioral_guard import BehavioralGuard
from src.engine.v11.signal.deployment_policy import ProbabilisticDeploymentPolicy
from src.engine.v11.signal.inertial_beta_mapper import InertialBetaMapper
from src.engine.v11.signal.regime_stabilizer import RegimeStabilizer
from src.regime_topology import canonicalize_regime_sequence, merge_regime_weights

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
        prior_state_path: str = "data/v11_prior_state.json",
        snapshot_dir: str = "artifacts/v12_runtime_snapshots",
        initial_model: GaussianNB | None = None,
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
            self.audit_data.get("model_hyperparameters", {}).get("posterior_mode", "runtime_reweight")
        )
        self.regimes = list(self.base_betas.keys())
        self._validate_canonical_inputs()
        self.regime_history = pd.read_csv(
            self.regime_data_path,
            parse_dates=["observation_date"],
        ).set_index("observation_date")
        self.model_regimes = sorted(self.regime_history["regime"].astype(str).unique())
        self._validate_regime_coverage()

        # v11.5 Internal Controllers
        self.seeder = ProbabilitySeeder()
        self.feature_contract = self._validate_feature_contract()
        self.entropy_ctrl = EntropyController()
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
            self._validate_model(self.gnb)
        else:
            self.gnb = self._initialize_model(macro_data_path, regime_data_path)

        self.inference_engine = BayesianInferenceEngine(
            kde_models={r: None for r in self.gnb.classes_},
            base_priors=self._get_base_priors()
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
        regime_df = pd.read_csv(regime_data_path, parse_dates=["observation_date"]).set_index("observation_date")

        # Generate features via unified seeder
        features = self.seeder.generate_features(macro_df)
        df = features.join(regime_df["regime"], how="inner").dropna()

        if df.empty:
            raise ValueError("JIT Training failed: Empty intersection between macro and regime data.")

        # Fit GNB (Architect A/B/C feature suite)
        # AC-0: Add variance smoothing to prevent probability collapse on low data (v11.19)
        gnb = GaussianNB(var_smoothing=self.gaussian_nb_var_smoothing)
        feature_cols = [c for c in df.columns if c != "regime"]
        gnb.fit(df[feature_cols], df["regime"])
        summary = self._validate_model(gnb, feature_count=len(feature_cols))

        logger.info(
            "V11.5 Conductor: JIT-Model Provenance established. "
            "Classes=%s features=%s theta=[%.4f, %.4f] var=[%.6f, %.6f]",
            summary["classes"],
            summary["feature_count"],
            summary["theta_min"],
            summary["theta_max"],
            summary["var_min"],
            summary["var_max"],
        )
        return gnb

    def _validate_model(self, gnb: GaussianNB, *, feature_count: int | None = None) -> dict[str, object]:
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
        Main execution loop for v11.5 probabilistic inference.
        """
        # 1. Feature Seeding (Epic 1)
        # AC-0: Conductor must see history to calculate Z-scores (v11.20)
        # Load local memory to provide context for the rolling window
        macro_csv = self.macro_data_path
        previous_raw = None
        if os.path.exists(macro_csv):
            hist_df = pd.read_csv(macro_csv, parse_dates=["observation_date"]).set_index("observation_date")
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
        quality_audit = self._assess_data_quality(latest_raw, previous_raw=previous_raw)
        feature_weights = self._feature_reliability_weights(
            latest_vector=latest_vector,
            latest_raw=latest_raw,
            quality_audit=quality_audit,
        )
        self._write_runtime_snapshot(
            raw_t0_data=raw_t0_data,
            latest_vector=latest_vector,
            runtime_priors=runtime_priors,
            prior_details=prior_details,
            quality_audit=quality_audit,
            feature_weights=feature_weights,
        )

        logger.info("Model Inference: Initiating GaussianNB probabilities with current priors...")
        # AC-3: Numerical Resilience (v11.21)
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
                raise ValueError(f"Unknown posterior_mode: {self.posterior_mode}")
            posteriors = self.inference_engine.infer_gaussian_nb_posterior(
                classifier=self.gnb,
                evidence_frame=latest_vector,
                runtime_priors=active_priors,
                feature_weights=feature_weights,
            )
            if any(np.isnan(list(posteriors.values()))):
                logger.warning("Bayesian Inference produced NaNs after attenuation. Falling back to priors.")
                posteriors = runtime_priors
        except Exception as e:
            logger.error("Bayesian Inference crashed: %s. Falling back to priors.", e)
            posteriors = runtime_priors

        posterior_entropy = self.entropy_ctrl.calculate_normalized_entropy(posteriors)
        norm_h = self._apply_data_quality_penalty(
            posterior_entropy=posterior_entropy,
            quality_score=float(quality_audit["quality_score"]),
        )
        quality_audit["posterior_entropy"] = posterior_entropy
        quality_audit["effective_entropy"] = norm_h
        quality_audit["entropy_penalty"] = max(0.0, norm_h - posterior_entropy)

        # 3. Probabilistic Exposure Mapping (v11.5)
        # AC-0: No constants. Base betas are audit-derived.
        raw_beta_expectation = sum(posteriors.get(regime, 0.0) * self.base_betas.get(regime, 1.0)
                                   for regime in self.base_betas.keys())

        regime_decision = self.regime_stabilizer.update(posteriors=posteriors, entropy=norm_h)

        protected_beta = self.entropy_ctrl.apply_haircut(
            raw_beta_expectation,
            norm_h,
            state_count=len(posteriors),
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
            "quality_audit": quality_audit,
            "v11_execution": execution.to_dict(),
        }

    @staticmethod
    def _apply_data_quality_penalty(*, posterior_entropy: float, quality_score: float) -> float:
        h = float(np.clip(posterior_entropy, 0.0, 1.0))
        q = float(np.clip(quality_score, 0.0, 1.0))
        return 1.0 - ((1.0 - h) * q)

    def _assess_data_quality(
        self,
        latest_raw: pd.Series,
        *,
        previous_raw: pd.Series | None = None,
    ) -> dict[str, object]:
        field_specs = _v12_quality_field_specs()

        fields: dict[str, dict[str, object]] = {}
        degraded_present = False
        missing_present = False
        quality_values: list[float] = []

        for field_name, (value_key, source_key, quality_key) in field_specs.items():
            raw_value = latest_raw.get(value_key)
            numeric_value = pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0]
            available = bool(pd.notna(numeric_value) and np.isfinite(float(numeric_value)))
            source = self._normalize_source_marker(latest_raw.get(source_key)) if source_key else "direct"
            degraded = source.startswith(
                ("proxy:", "fallback:", "synthetic:", "default:", "unavailable:", "missing:")
            )
            explicit_quality = latest_raw.get(quality_key) if quality_key else None
            explicit_quality_numeric = pd.to_numeric(pd.Series([explicit_quality]), errors="coerce").iloc[0]
            if pd.notna(explicit_quality_numeric):
                field_quality = float(np.clip(float(explicit_quality_numeric), 0.0, 1.0))
            else:
                field_quality = 1.0 if available and not degraded else 0.0
            degraded_present = degraded_present or degraded
            missing_present = missing_present or not available
            quality_values.append(field_quality)
            fields[field_name] = {
                "available": available,
                "source": source,
                "degraded": degraded,
                "quality": field_quality,
            }

        if quality_values:
            denom = sum(1.0 / max(float(value), 0.01) for value in quality_values)
            quality_score = float(len(quality_values) / denom)
        else:
            quality_score = 1.0
        source_switch = self._detect_source_switch(latest_raw, previous_raw=previous_raw)
        if degraded_present:
            reason = "DEGRADED_SOURCE"
        elif missing_present:
            reason = "SENSOR_DEGRADATION"
        elif source_switch["detected"]:
            reason = "SOURCE_SWITCH"
        else:
            reason = "V11_PROBABILISTIC_OPTIMAL"

        return {
            "quality_score": quality_score,
            "reason": reason,
            "fields": fields,
            "source_switch": source_switch,
        }

    @staticmethod
    def _normalize_source_marker(raw_source: object) -> str:
        if raw_source is None or pd.isna(raw_source):
            return "missing:provenance"

        source = str(raw_source).strip()
        if not source or source.lower() in {"nan", "none", "null"}:
            return "missing:provenance"
        return source

    @classmethod
    def _detect_source_switch(
        cls,
        latest_raw: pd.Series,
        *,
        previous_raw: pd.Series | None = None,
    ) -> dict[str, object]:
        if previous_raw is None:
            return {
                "detected": False,
                "changed_fields": [],
                "previous_build_version": None,
                "current_build_version": str(latest_raw.get("build_version", "")) or None,
            }

        source_fields = {field: source_key for field, (_, source_key, _) in _v12_quality_field_specs().items()}

        changed_fields: list[str] = []
        for field_name, source_key in source_fields.items():
            previous_source = cls._normalize_source_marker(previous_raw.get(source_key))
            current_source = cls._normalize_source_marker(latest_raw.get(source_key))
            if previous_source and current_source and previous_source != current_source:
                changed_fields.append(field_name)

        previous_build_version = str(previous_raw.get("build_version", "") or "")
        current_build_version = str(latest_raw.get("build_version", "") or "")
        if previous_build_version and current_build_version and previous_build_version != current_build_version:
            changed_fields.append("build_version")

        return {
            "detected": bool(changed_fields),
            "changed_fields": sorted(set(changed_fields)),
            "previous_build_version": previous_build_version or None,
            "current_build_version": current_build_version or None,
        }

    def _feature_reliability_weights(
        self,
        *,
        latest_vector: pd.DataFrame,
        latest_raw: pd.Series,
        quality_audit: dict[str, object],
    ) -> dict[str, float]:
        field_quality = {
            str(name): float(payload.get("quality", 1.0))
            for name, payload in dict(quality_audit.get("fields", {})).items()
        }

        source_to_field = {
            "credit_spread_bps": "credit_spread",
            "net_liquidity_usd_bn": "net_liquidity",
            "real_yield_10y_pct": "real_yield",
            "treasury_vol_21d": "treasury_vol",
            "copper_gold_ratio": "copper_gold",
            "breakeven_10y": "breakeven",
            "core_capex_mm": "core_capex",
            "usdjpy": "usdjpy",
            "erp_ttm_pct": "erp_ttm",
        }

        weights: dict[str, float] = {}
        for feature_name in latest_vector.columns:
            src = self.seeder.config.get(feature_name, {}).get("src")
            raw_value = latest_raw.get(src)
            numeric_value = pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0]
            if pd.isna(numeric_value) or not np.isfinite(float(numeric_value)):
                weights[str(feature_name)] = 0.0
                continue

            field_name = source_to_field.get(str(src))
            weights[str(feature_name)] = float(np.clip(field_quality.get(field_name, 1.0), 0.0, 1.0))

        return weights

    def _write_runtime_snapshot(
        self,
        *,
        raw_t0_data: pd.DataFrame,
        latest_vector: pd.DataFrame,
        runtime_priors: dict[str, float],
        prior_details: dict[str, object],
        quality_audit: dict[str, object],
        feature_weights: dict[str, float],
    ) -> None:
        try:
            serialized_row = self._serialize_frame(raw_t0_data)
            observation_date = str(serialized_row[0].get("observation_date", "unknown"))
            payload = {
                "snapshot_version": "v12_runtime_snapshot.v1",
                "captured_at_utc": datetime.now(UTC).isoformat(),
                "observation_date": observation_date,
                "macro_data_path": self.macro_data_path,
                "regime_data_path": self.regime_data_path,
                "audit_path": str(self.audit_path),
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
            }

            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = self.snapshot_dir / f"snapshot_{observation_date}.json"
            snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write v11 runtime snapshot: %s", exc)

    @staticmethod
    def _serialize_frame(frame: pd.DataFrame) -> list[dict[str, object]]:
        serializable = frame.copy()
        if "observation_date" not in serializable.columns:
            index_name = serializable.index.name or "observation_date"
            serializable = serializable.reset_index().rename(columns={index_name: "observation_date"})

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
