from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StressComponentScore:
    kind: str
    value: float
    subcomponents: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CombinedStressScore:
    raw_score: float
    linear_score: float
    terms: dict[str, float]
    transformed_inputs: dict[str, float]
