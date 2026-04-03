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
                except Exception as e:
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
        feature_weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        if evidence_frame is None or len(evidence_frame) != 1:
            raise ValueError("evidence_frame must contain exactly one observation")

        feature_names = list(getattr(evidence_frame, "columns", []))
        x = np.asarray(evidence_frame.iloc[0], dtype=float)
        weights = np.array([float((feature_weights or {}).get(name, 1.0)) for name in feature_names], dtype=float)
        runtime = self._normalize(runtime_priors or self.base_priors)
        if not runtime: runtime = self._normalize(self.base_priors)

        eps = 1e-12
        raw_log_lhs = {}
        for idx, regime_label in enumerate(classifier.classes_):
            regime_key = str(regime_label)
            theta = np.asarray(classifier.theta_[idx], dtype=float)
            var = np.maximum(np.asarray(classifier.var_[idx], dtype=float), eps)
            log_lh = -0.5 * (np.log(2.0 * np.pi * var) + ((x - theta) ** 2) / var)
            # AC-0: Mean Log-LH (Likelihood Shrinkage) to handle redundancy
            raw_log_lhs[regime_key] = float(np.sum(weights * log_lh)) / max(1.0, len(feature_names))

        max_log = max(raw_log_lhs.values())
        raw_evidence_dist = self._normalize({r: np.exp(val - max_log) for r, val in raw_log_lhs.items()})

        # AC-0 v12.8: Global Robust Momentum (Systematic reduction of impact rate)
        m = 0.15
        return {k: (1 - m) * runtime.get(k, 0.0) + m * v for k, v in raw_evidence_dist.items()}

    def reweight_probabilities(self, *, classifier_posteriors: dict[str, float], training_priors: dict[str, float], runtime_priors: dict[str, float] | None = None) -> dict[str, float]:
        runtime = self._normalize(runtime_priors or self.base_priors)
        posterior = self._normalize(classifier_posteriors)
        train = self._normalize(training_priors)
        if not posterior: return runtime
        regimes = sorted(set(runtime) | set(posterior) | set(train))
        eps = 1e-12
        adjusted = {r: posterior.get(r, 0.0) * runtime.get(r, 0.0) / max(train.get(r, 0.0), eps) for r in regimes}
        return self._normalize(adjusted) or runtime

    @staticmethod
    def _normalize(weights: dict[str, float] | None) -> dict[str, float]:
        if not weights: return {}
        sanitized = {str(k): max(0.0, float(v)) for k, v in weights.items()}
        total = float(sum(sanitized.values()))
        if total <= 0: return {k: 1.0 / len(sanitized) for k in sanitized}
        return {k: v / total for k, v in sanitized.items()}
