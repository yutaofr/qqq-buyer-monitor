import logging

logger = logging.getLogger(__name__)

class HysteresisBetaMapper:
    """
    v11.5 Hysteresis Beta Mapper
    Responsibility: Dictatorial Execution Engine.
    Converts posterior probabilities into a discrete Target Beta while minimizing transactional noise.
    Ensures T+1 Retail Settlement alignment.
    """
    def __init__(self, base_betas: dict[str, float], delta_threshold: float = 0.08, initial_beta: float = 1.0):
        self.base_betas = base_betas
        self.delta_threshold = delta_threshold
        self.current_beta = initial_beta
        self.cooldown_remaining = 0

    def tick_cooldown(self):
        """Reduces cooldown days remaining."""
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1

    def calculate_expectation(self, probabilities: dict[str, float]) -> float:
        """
        Calculates the weighted average target beta from probabilistic distribution.
        Formula: E[Beta] = sum( P(Regime_i) * Base_Beta_i )
        """
        expectation = 0.0
        for regime, p in probabilities.items():
            base = self.base_betas.get(regime, 1.0) # Default to Neutral
            expectation += p * base
        return round(expectation, 4)

    def apply_hysteresis(self, target_beta: float) -> float:
        """
        Applies Delta Deadband and Settlement Locks.
        Only returns a new beta if the change is significant and system is not locked.
        """
        # 1. Settlement Lock Protection
        if self.cooldown_remaining > 0:
            return self.current_beta

        # 2. Delta Deadband Check
        # Only trigger re-balance if the difference is substantial (> delta_threshold)
        beta_diff = abs(target_beta - self.current_beta)
        if beta_diff < self.delta_threshold:
            return self.current_beta

        # 3. Action Required: Update state and trigger cooldown
        if target_beta != self.current_beta:
            self.current_beta = target_beta
            self.cooldown_remaining = 1 # Lock for T+1
            logger.info(f"Beta Shift Triggered: {self.current_beta:.2f}, delta_diff: {beta_diff:.4f}")

        return self.current_beta
