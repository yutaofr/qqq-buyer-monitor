from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PriceDamageConfig:
    damage_center: float = 0.58
    bust_center: float = 0.55
    transition_center: float = 0.62
    damage_weight: float = 0.38
    bust_weight: float = 0.34
    transition_weight: float = 0.18
    bearish_divergence_weight: float = 0.10


@dataclass(frozen=True)
class MarketStressConfig:
    vol_feature_names: tuple[str, ...] = ("move_21d",)
    spread_feature_names: tuple[str, ...] = ("spread_21d", "credit_acceleration")
    breadth_feature_names: tuple[str, ...] = ("qqq_pv_divergence_z",)
    correlation_feature_names: tuple[str, ...] = ("move_spread_corr_21d",)
    breadth_internal_names: tuple[str, ...] = ("adv_dec_ratio", "breadth_proxy")
    breadth_quality_names: tuple[str, ...] = ("breadth_quality_score",)
    term_structure_names: tuple[str, ...] = ("vix_3m_1m_ratio", "term_structure_stress")
    beta_instability_names: tuple[str, ...] = ("move_spread_beta",)
    z_center: float = 1.15
    z_scale: float = 1.10


@dataclass(frozen=True)
class MacroAnomalyConfig:
    threshold: float = 3.75
    width: float = 1.25
    cap_distance: float = 8.0


@dataclass(frozen=True)
class PersistenceConfig:
    half_life_days: float = 8.0
    stressed_half_life_days: float = 16.0
    activation_threshold: float = 0.45
    release_threshold: float = 0.30
    max_daily_release: float = 0.18
    occupancy_window: int = 21


@dataclass(frozen=True)
class StressCombinerConfig:
    transform: str = "identity"
    coefficients: dict[str, float] = field(
        default_factory=lambda: {
            "intercept": -3.15,
            "S_price": 1.15,
            "S_market": 1.05,
            "S_macro_anom": 0.55,
            "S_persist": 0.85,
            "interaction_price_market": 1.35,
            "interaction_price_macro": 0.75,
            "interaction_market_macro": 0.65,
        }
    )


@dataclass(frozen=True)
class StressPosteriorConfig:
    mode: str = "component_logistic"
    calibrator_method: str = "platt"
    price: PriceDamageConfig = field(default_factory=PriceDamageConfig)
    market: MarketStressConfig = field(default_factory=MarketStressConfig)
    macro: MacroAnomalyConfig = field(default_factory=MacroAnomalyConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    combiner: StressCombinerConfig = field(default_factory=StressCombinerConfig)
