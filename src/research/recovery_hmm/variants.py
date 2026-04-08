"""Variant catalog for worldview-consistent recovery HMM optimization research."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RecoveryHmmVariant:
    name: str
    description: str
    transition_alpha: float = 2.0
    transition_beta: float = 3.0
    softmax_temperature: float = 0.4
    orthogonal_temperature_strength: float = 0.0
    orthogonal_entropy_relief: float = 0.0
    entropy_threshold: float = 0.65
    entropy_slope: float = 2.5
    entropy_floor: float = 0.3
    fdas_z_threshold: float = 2.5
    fdas_min_breaches: int = 3
    fdas_multiplier: float = 0.15
    preserve_production_floor: bool = True
    production_floor: float = 0.5
    decay_spread_velocity_weight: float = 1.0
    decay_real_yield_relief_weight: float = 1.0
    decay_orders_weight: float = 1.0
    level_curve_weight: float = 1.0
    level_fci_penalty_weight: float = 1.0
    level_spread_penalty_weight: float = 1.0
    level_term_support_weight: float = 1.0
    recovery_decay_weight: float = 1.8
    recovery_term_support_weight: float = 1.0
    recovery_skew_relief_weight: float = 1.0
    mid_transition_weight: float = 2.5
    mid_curve_support_weight: float = 1.0
    mid_orders_support_weight: float = 1.0
    late_spread_weight: float = 1.0
    late_skew_weight: float = 1.0
    late_term_inversion_weight: float = 1.0
    bust_spread_weight: float = 1.0
    bust_fci_weight: float = 1.0
    bust_term_inversion_weight: float = 1.0
    bust_skew_weight: float = 1.0
    bust_curve_inversion_weight: float = 0.0
    bust_spread_widening_weight: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


LOCKED_CANDIDATE_VARIANT = RecoveryHmmVariant(
    name="locked_candidate",
    description="Current accepted shadow candidate used as the control reference.",
)


WORLDVIEW_OPTIMIZATION_VARIANTS = (
    RecoveryHmmVariant(
        name="stress_hardened",
        description="Earlier BUST/LATE recognition to reduce late-cycle complacency under spread and curve stress.",
        softmax_temperature=0.35,
        entropy_threshold=0.63,
        entropy_slope=2.8,
        late_spread_weight=1.15,
        bust_spread_weight=1.25,
        bust_fci_weight=1.15,
        bust_curve_inversion_weight=0.85,
        bust_spread_widening_weight=0.75,
    ),
    RecoveryHmmVariant(
        name="recovery_accelerated",
        description="Faster recovery release once stress compresses and orthogonal clarity returns.",
        transition_alpha=2.35,
        transition_beta=2.35,
        softmax_temperature=0.38,
        orthogonal_entropy_relief=0.22,
        entropy_threshold=0.68,
        entropy_slope=2.0,
        recovery_decay_weight=2.1,
        recovery_term_support_weight=1.15,
        mid_transition_weight=2.9,
        mid_orders_support_weight=1.15,
    ),
    RecoveryHmmVariant(
        name="orthogonal_consensus",
        description="Use PCA consensus to sharpen posterior conviction and reduce false ambiguity in clear regimes.",
        softmax_temperature=0.42,
        orthogonal_temperature_strength=0.45,
        orthogonal_entropy_relief=0.18,
    ),
    RecoveryHmmVariant(
        name="barbell_balance",
        description="Combine harder front-end defense with faster back-end recovery release.",
        transition_alpha=2.2,
        transition_beta=2.5,
        softmax_temperature=0.36,
        orthogonal_temperature_strength=0.22,
        orthogonal_entropy_relief=0.20,
        entropy_threshold=0.66,
        entropy_slope=2.25,
        late_spread_weight=1.1,
        bust_spread_weight=1.15,
        bust_fci_weight=1.1,
        bust_curve_inversion_weight=0.55,
        bust_spread_widening_weight=0.55,
        recovery_decay_weight=1.95,
        mid_transition_weight=2.7,
    ),
    RecoveryHmmVariant(
        name="fdas_guardrail",
        description="Strengthen distribution-level crisis isolation while keeping the state engine mostly unchanged.",
        fdas_z_threshold=2.25,
        fdas_min_breaches=2,
    ),
)


def get_variant_by_name(name: str) -> RecoveryHmmVariant:
    if name == LOCKED_CANDIDATE_VARIANT.name:
        return LOCKED_CANDIDATE_VARIANT
    for variant in WORLDVIEW_OPTIMIZATION_VARIANTS:
        if variant.name == name:
            return variant
    raise KeyError(f"Unknown recovery HMM variant: {name}")
