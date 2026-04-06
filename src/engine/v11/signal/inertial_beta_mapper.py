import numpy as np

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
        Updates target beta using an asymmetric kinetic model.
        De-risking is intentionally faster than re-risking when entropy is high,
        which prevents the system from getting stranded at mediocre beta plateaus.
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

        h = min(0.999, max(0.001, float(normalized_entropy)))
        delta = target_beta - self.current_beta
        deleveraging = delta < 0.0

        response = (0.65 + (0.25 * h)) if deleveraging else (0.20 + (0.20 * (1.0 - h)))
        damping = 0.25 if deleveraging else 0.55
        max_step = 0.18 if deleveraging else 0.12

        self.velocity = (self.velocity * damping) + (delta * response)
        step = float(np.clip(self.velocity, -max_step, max_step))
        self.current_beta = clamp_beta(
            self.current_beta + step,
            floor=self.beta_floor,
            ceiling=self.beta_ceiling,
        )
        self.evidence = (self.evidence * 0.35) + step

        self.current_beta = clamp_beta(
            self.current_beta,
            floor=self.beta_floor,
            ceiling=self.beta_ceiling,
        )
        return self.current_beta
