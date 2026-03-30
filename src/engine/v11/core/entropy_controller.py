import numpy as np
from scipy.stats import entropy


class EntropyController:
    """
    v11.5 Entropy Controller
    Responsibility: Information-theoretic safety valve.
    Scales Target Beta toward 1.0 (Safe Neutral) as posterior uncertainty (Shannon Entropy) increases.
    """
    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold

    def calculate_normalized_entropy(self, probs: dict[str, float]) -> float:
        """
        Calculates normalized Shannon Entropy (0.0 to 1.0).
        0.0 = Absolute certainty (one state handles all).
        1.0 = Absolute chaos (equal probability for all states).
        """
        p_vals = list(probs.values())
        if len(p_vals) < 2:
            return 0.0

        # Calculate raw entropy (base 2)
        h = entropy(p_vals, base=2)

        # Normalize by maximum possible entropy (log2 of number of states)
        max_h = np.log2(len(p_vals))
        return h / max_h if max_h > 0 else 0.0

    def apply_haircut(
        self,
        base_beta: float,
        norm_entropy: float,
        structural_z: float = 0.0,
        outlier_multiplier: float = 1.0
    ) -> float:
        """
        Applies linear haircut to the target beta if entropy exceeds threshold.
        Also applies a Probabilistic Valuation Penalty (v11.6) and an Outlier Resilience Penalty (v11.7).
        """
        # 1. Non-Threshold Valuation Penalty (v11.6)
        valuation_penalty = 1.0
        if structural_z > 0:
            decay = 1.0 - np.exp(-0.2 * structural_z)
            valuation_penalty = 1.0 - (decay * 0.25)

        # 2. Adaptive Outlier Scaling (v11.7)
        # Outlier multiplier is derived from Mahalanobis Distance (D_M).
        target_beta = base_beta * valuation_penalty * outlier_multiplier

        # 3. Entropy Protection
        if norm_entropy <= self.threshold:
            return target_beta

        # Scale 0 to 1 as entropy goes threshold -> 1.0
        haircut_strength = (norm_entropy - self.threshold) / (1.0 - self.threshold)
        haircut_strength = np.clip(haircut_strength, 0.0, 1.0)

        # Weighted average between predicted beta and neutral 1.0
        return target_beta * (1.0 - haircut_strength) + 1.0 * haircut_strength
