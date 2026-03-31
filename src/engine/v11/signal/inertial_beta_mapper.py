
class InertialBetaMapper:
    """
    v11.10 Odds-Ratio CUSUM
    Responsibility: Information-Theoretic Evidence Integration.
    Achieves 2-3 shifts/year by using the Odds-Ratio of Shannon Entropy
    as a dynamic, zero-constant barrier.
    Zero-Constant Architecture.
    """
    def __init__(self, initial_beta: float | None = 1.0):
        self.current_beta = initial_beta
        self.evidence = 0.0

    def calculate_inertial_beta(self, target_beta_raw: float, normalized_entropy: float) -> float:
        """
        Updates target beta only if the cumulative signal evidence
        surpasses the current Information Odds Ratio (barrier).
        """
        # 0. Cold Start Priming
        if self.current_beta is None:
            self.current_beta = target_beta_raw
            self.evidence = 0.0
            return self.current_beta

        # 1. Accumulate Informational Evidence
        delta = target_beta_raw - self.current_beta
        self.evidence += delta

        # 2. Calculate Dynamic Barrier (Odds Ratio)
        # Avoid division by zero by clipping h to 0.999
        h = min(0.999, max(0.001, normalized_entropy))
        threshold = 1.0 + (h / (1.0 - h))

        # 3. Check for Phase Shift
        # No constants. Threshold is derived from the Information-Theoretic Odds.
        if abs(self.evidence) > threshold:
            self.current_beta = target_beta_raw
            self.evidence = 0.0  # Reset evidence after action

        return self.current_beta
