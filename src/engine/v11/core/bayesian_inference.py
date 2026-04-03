import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

class BayesianInferenceEngine:
    def __init__(self, kde_models: dict[str, Any], base_priors: dict[str, float]):
        self.kde_models = kde_models
        self.base_priors = base_priors
        self.regimes = list(base_priors.keys())

    def infer_posterior(self, evidence_vector: np.ndarray) -> dict[str, float]:
        posteriors = {}
        total_likelihood = 0.0
        X = evidence_vector.reshape(1, -1)
        for regime in self.regimes:
            prior = self.base_priors.get(regime, 0.0)
            if regime in self.kde_models:
                try:
                    log_lh = self.kde_models[regime].score_samples(X)[0]
                    likelihood = np.exp(log_lh)
                except Exception:
                    likelihood = 1e-9
            else:
                likelihood = 1e-9
            posteriors[regime] = likelihood * prior
            total_likelihood += posteriors[regime]
        if total_likelihood > 0:
            for r in self.regimes:
                posteriors[r] /= total_likelihood
        else:
            return dict(zip(self.regimes, self.base_priors.values(), strict=True))
        return posteriors

    def infer_gaussian_nb_posterior(
        self,
        *,
        classifier: Any,
        evidence_frame: Any,
        runtime_priors: dict[str, float],
        weight_registry: dict[str, Any] | None = None,
        tau: float = 0.5,
        m: float = 0.35,
    ) -> tuple[dict[str, float], dict[str, Any]]:
        """
        SRD-v13.4 Calibrated Weighted Bayesian Inference.
        Implements Lineage Normalization, Static Tau, and Level Contributions.
        """
        try:
            if evidence_frame is None or len(evidence_frame) != 1:
                raise ValueError("evidence_frame must contain exactly one observation")

            feature_names = list(getattr(evidence_frame, "columns", []))
            x = np.asarray(evidence_frame.iloc[0], dtype=float)

            # 1. SRD-v13.4: Lineage Normalization
            weights_config = (weight_registry or {}).get("feature_weight_matrix", {})
            fallback_w = float(weights_config.get("DEFAULT_FALLBACK", 1.0))

            root_mapping = {}
            root_counts = {}
            for name in feature_names:
                matched_root = "DEFAULT_FALLBACK"
                longest_match = 0
                for root in weights_config:
                    if root != "DEFAULT_FALLBACK" and name.startswith(root):
                        if len(root) > longest_match:
                            matched_root = root
                            longest_match = len(root)
                root_mapping[name] = matched_root
                root_counts[matched_root] = root_counts.get(matched_root, 0) + 1

            effective_weights = np.array([
                float(weights_config.get(root_mapping[name], fallback_w)) / root_counts[root_mapping[name]]
                for name in feature_names
            ], dtype=float)

            total_weight_sum = np.sum(effective_weights)
            runtime = self._normalize(runtime_priors or self.base_priors)
            eps = 1e-12

            # 2. SRD-v13.4: Weighted Log-Likelihood with Temperature Scaling (Tau)
            raw_log_lhs = {}
            level_contributions = {regime: {} for regime in classifier.classes_}

            # v13.7-FINAL: Asymmetric Tau mapping derived from injected tau.
            base_tau = max(0.01, float(tau))
            acute_tau = base_tau * 0.7

            tau_map = {
                "credit_spread_bps": base_tau,
                "erp_ttm_pct": base_tau,
                "net_liquidity_usd_bn": base_tau,
                "real_yield_10y_pct": base_tau,
                "pmi_momentum": acute_tau,
                "labor_slack": acute_tau,
                "treasury_vol_21d": acute_tau,
                "move_21d": acute_tau,
                "DEFAULT_FALLBACK": base_tau
            }

            for idx, regime_label in enumerate(classifier.classes_):
                regime_key = str(regime_label)
                theta = np.asarray(classifier.theta_[idx], dtype=float)
                var = np.maximum(np.asarray(classifier.var_[idx], dtype=float), eps)

                feature_log_lh = -0.5 * (np.log(2.0 * np.pi * var) + ((x - theta) ** 2) / var)

                scaled_log_lh = np.array([
                    feature_log_lh[f_idx] / tau_map.get(root_mapping[f_name], base_tau)
                    for f_idx, f_name in enumerate(feature_names)
                ])

                raw_log_lhs[regime_key] = float(np.sum(effective_weights * scaled_log_lh))

                for f_idx, f_name in enumerate(feature_names):
                    level_contributions[regime_key][f_name] = float(effective_weights[f_idx] * scaled_log_lh[f_idx])

            # 3. Apply Base Temperature Scaling
            max_log = max(raw_log_lhs.values())
            raw_evidence_dist = self._normalize({
                r: np.exp(val - max_log) for r, val in raw_log_lhs.items()
            })

            # v13.7-REFINED: Momentum下调至 0.35
            posteriors = {k: (1 - m) * runtime.get(k, 0.0) + m * v for k, v in raw_evidence_dist.items()}

            diagnostics = {
                "effective_weights": dict(zip(feature_names, effective_weights.tolist())),
                "total_weight": total_weight_sum,
                "tau_applied": base_tau,
                "m_applied": m,
                "evidence_dist": raw_evidence_dist,
                "level_contributions": level_contributions
            }
            return posteriors, diagnostics

        except Exception as e:
            logger.error("Inference failed: %s", e)
            # CR-1 Fix: Consistent return signature
            return runtime_priors or self.base_priors, {"error": str(e)}

    def reweight_probabilities(self, *, classifier_posteriors: dict[str, float], training_priors: dict[str, float], runtime_priors: dict[str, float] | None = None) -> dict[str, float]:
        runtime = self._normalize(runtime_priors or self.base_priors)
        posterior = self._normalize(classifier_posteriors)
        train = self._normalize(training_priors)
        if not posterior:
            return runtime
        regimes = sorted(set(runtime) | set(posterior) | set(train))
        eps = 1e-12
        adjusted = {r: posterior.get(r, 0.0) * runtime.get(r, 0.0) / max(train.get(r, 0.0), eps) for r in regimes}
        return self._normalize(adjusted) or runtime

    @staticmethod
    def _normalize(weights: dict[str, float] | None) -> dict[str, float]:
        if not weights:
            return {}

        # v13.7-GOLD-FINAL: Numerical Safety Reinforcement
        # Apply eps to prevent total zero collapse and ensure non-negativity
        eps = 1e-15
        sanitized = {str(k): max(0.0, float(v)) for k, v in weights.items()}
        total = float(sum(sanitized.values()))

        if total <= 0:
            # Fallback to uniform distribution instead of NaN
            n = len(sanitized)
            return {k: 1.0 / n for k in sanitized}

        return {k: (v + eps) / (total + (len(sanitized) * eps)) for k, v in sanitized.items()}
