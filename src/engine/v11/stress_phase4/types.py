from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Phase4Stage1Output:
    normal: float
    ordinary_correction: float
    transition_onset: float
    structural_stress_onset: float
    recovery_healing: float
    ambiguity: float
    transition_intensity: float
    confidence: float
    attribution: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Phase4Stage2Output:
    non_crisis_anomaly: float
    elevated_structural_stress: float
    systemic_crisis: float
    severity_score: float
    confidence: float
    attribution: dict[str, float] = field(default_factory=dict)
