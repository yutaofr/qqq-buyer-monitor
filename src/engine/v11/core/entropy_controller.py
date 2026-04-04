import numpy as np
from scipy.stats import entropy

from src.engine.v11.core.expectation_surface import BETA_FLOOR, clamp_beta


class EntropyController:
    """
    v12.0 Entropy Controller
    Responsibility: Information-theoretic safety valve.
    Scales Target Beta toward 1.0 (Safe Neutral) as posterior uncertainty (Shannon Entropy) increases.
    """

    def __init__(self, threshold: float | None = None):
        # Retained for backwards compatibility only. Risk pricing is now threshold-free.
        self.threshold = threshold

    def calculate_normalized_entropy(self, probs: dict[str, float]) -> float:
        """
        Calculates normalized Shannon Entropy (0.0 to 1.0).
        0.0 = Absolute certainty (one state handles all).
        1.0 = Absolute chaos (equal probability for all states).
        """
        p_vals = [max(0.0, float(value)) for value in probs.values()]
        if len(p_vals) < 2:
            return 0.0

        total = float(sum(p_vals))
        if total <= 0.0:
            return 1.0
        p_vals = [value / total for value in p_vals]

        # Calculate raw entropy (base 2)
        h = entropy(p_vals, base=2)

        # Normalize by maximum possible entropy (log2 of number of states)
        max_h = np.log2(len(p_vals))
        return h / max_h if max_h > 0 else 0.0

    def apply_haircut(
        self,
        base_beta: float,
        norm_entropy: float,
        *,
        state_count: int | None = None,
        floor: float = BETA_FLOOR,
    ) -> float:
        """
        Applies a threshold-free probabilistic haircut derived from Shannon entropy.

        The multiplier is the inverse effective state count with damped non-linear squaring:
        confidence = exp(-0.6 * (H_norm * log(states))^2)  # v13.5-GOLD Damping

        This preserves determinism, removes arbitrary thresholds, and ensures
        rational de-risking in high-conflict states (H > 0.7).
        """
        h_norm = float(np.clip(norm_entropy, 0.0, 1.0))
        states = max(2, int(state_count or 2))

        # SRD-v13.5-GOLD: Damped Gaussian Confidence Mapping (k=0.6)
        # Rationalized by ML Expert to prevent "Suicidal De-risking".
        base_h = h_norm * np.log(states)
        confidence = float(np.exp(-0.6 * (base_h**2)))

        anchored_beta = clamp_beta(float(base_beta), floor=floor)
        surplus = max(0.0, anchored_beta - float(floor))
        return float(floor) + (surplus * confidence)
