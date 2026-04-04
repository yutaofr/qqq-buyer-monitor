from src.engine.v11.core.expectation_surface import BETA_CEILING, BETA_FLOOR, clamp_beta


class InertialBetaMapper:
    """
    v13.6-EX Second-Order Kinetic Smoothing.
    Responsibility: Information-Theoretic Path Stabilization.
    Eliminates "Sawtooth" oscillations near physical floors using
    entropy-damped velocity and momentum.
    """

    def __init__(
        self,
        initial_beta: float | None = 1.0,
        initial_evidence: float = 0.0,
        *,
        beta_floor: float = BETA_FLOOR,
        beta_ceiling: float = BETA_CEILING,
    ):
        self.beta_floor = float(beta_floor)
        self.beta_ceiling = float(beta_ceiling)
        self.current_beta = (
            clamp_beta(initial_beta, floor=self.beta_floor, ceiling=self.beta_ceiling)
            if initial_beta is not None
            else None
        )
        self.evidence = initial_evidence
        self.velocity = 0.0  # Path rate of change

    def calculate_inertial_beta(self, target_beta_raw: float, normalized_entropy: float) -> float:
        """
        Updates target beta using a damped kinetic model.
        Threshold is still entropy-derived (Odds-Ratio), but transitions are smooth.
        """
        target_beta = clamp_beta(
            target_beta_raw,
            floor=self.beta_floor,
            ceiling=self.beta_ceiling,
        )

        # 0. Cold Start Priming
        if self.current_beta is None:
            self.current_beta = target_beta
            self.velocity = 0.0
            self.evidence = 0.0
            return self.current_beta

        self.current_beta = clamp_beta(
            self.current_beta,
            floor=self.beta_floor,
            ceiling=self.beta_ceiling,
        )

        # 1. Information-Theoretic Barrier (Odds Ratio)
        h = min(0.999, max(0.001, float(normalized_entropy)))
        threshold = 1.0 + (h / (1.0 - h))

        # 2. Update Kinetic Evidence
        # Delta acts as "Force", Entropy acts as "Friction"
        delta = target_beta - self.current_beta
        friction = 1.0 - h  # Higher entropy -> Higher friction (Lower responsiveness)

        # Acceleration term (Force / Friction)
        self.velocity = (self.velocity * 0.5) + (delta * friction)
        self.evidence += self.velocity

        # 3. Check for Phase Shift
        if abs(self.evidence) > threshold:
            # Shift anchor and decay velocity to prevent overshoot
            self.current_beta = target_beta
            self.evidence = 0.0
            self.velocity *= 0.2  # Momentum braking

        self.current_beta = clamp_beta(
            self.current_beta,
            floor=self.beta_floor,
            ceiling=self.beta_ceiling,
        )
        return self.current_beta
