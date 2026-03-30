import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

class BayesianInferenceEngine:
    """
    v11.5 Bayesian Inference Engine
    Responsibility: Discrete Regime inference from multi-factor evidence.
    Strictly follows Architect B (GaussianNB/KDE) and Architect C (Derivative Momentum) criteria.
    NO hard-coded thresholds or if-else logic.
    """
    def __init__(self, kde_models: dict[str, Any], base_priors: dict[str, float]):
        self.kde_models = kde_models
        self.base_priors = base_priors
        self.regimes = list(base_priors.keys())

    def infer_posterior(self, evidence_vector: np.ndarray) -> dict[str, float]:
        """
        Calculates the 5-way posterior regime probability.
        Uses P(Regime | Evidence) = P(Evidence | Regime) * P(Regime) / P(Evidence)
        """
        posteriors = {}
        total_likelihood = 0.0

        # Evidence vector must be reshaped for sklearn-like models
        X = evidence_vector.reshape(1, -1)

        for regime in self.regimes:
            prior = self.base_priors.get(regime, 0.0)

            # 1. Calculate Likelihood P(Evidence | Regime)
            if regime in self.kde_models:
                # Expecting sklearn.neighbors.KernelDensity or similar
                try:
                    log_lh = self.kde_models[regime].score_samples(X)[0]
                    likelihood = np.exp(log_lh)
                except Exception as e:
                    logger.warning(f"Likelihood calculation failed for {regime}: {e}")
                    likelihood = 1e-9 # Penalty for out-of-distribution
            else:
                likelihood = 1e-9 # Penalty for unknown states

            # 2. Multiply by Prior: P(R) * P(E|R)
            posteriors[regime] = likelihood * prior
            total_likelihood += posteriors[regime]

        # 3. Final Posterior Normalization: P(R|E)
        if total_likelihood > 0:
            for r in self.regimes:
                posteriors[r] /= total_likelihood
        else:
            # Absolute Data-Blackout / Multi-Factor Paradox
            logger.error("Evidence vector resulted in ZERO total likelihood. Reverting to base priors.")
            return dict(zip(self.regimes, self.base_priors.values(), strict=True))

        return posteriors

    def reweight_probabilities(
        self,
        *,
        classifier_posteriors: dict[str, float],
        training_priors: dict[str, float],
        runtime_priors: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """
        Reweights a classifier posterior onto runtime priors.

        If the classifier was trained with prior p_train(y), then:
        p(y | x; runtime) ∝ p(y | x; train) * p_runtime(y) / p_train(y)
        """
        runtime = self._normalize(runtime_priors or self.base_priors)
        posterior = self._normalize(classifier_posteriors)
        train = self._normalize(training_priors)
        if not posterior:
            return runtime

        regimes = sorted(set(runtime) | set(posterior) | set(train))
        eps = 1e-12
        adjusted = {}
        for regime in regimes:
            model_prob = posterior.get(regime, 0.0)
            runtime_prob = runtime.get(regime, 0.0)
            train_prob = max(train.get(regime, 0.0), eps)
            adjusted[regime] = model_prob * runtime_prob / train_prob

        normalized = self._normalize(adjusted)
        return normalized or runtime

    @staticmethod
    def _normalize(weights: dict[str, float] | None) -> dict[str, float]:
        if not weights:
            return {}

        sanitized = {}
        for key, value in weights.items():
            numeric = float(value)
            if np.isnan(numeric) or np.isinf(numeric):
                numeric = 0.0
            sanitized[str(key)] = max(0.0, numeric)

        total = float(sum(sanitized.values()))
        if total <= 0:
            n = max(1, len(sanitized))
            return {key: 1.0 / n for key in sanitized}
        return {key: value / total for key, value in sanitized.items()}
