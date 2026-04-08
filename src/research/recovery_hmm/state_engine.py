"""Asymmetric state-transition helpers for the recovery HMM research track."""

from __future__ import annotations

import math


def recovery_to_midcycle_probability(
    *,
    level_score: float,
    decay_score: float,
    alpha: float = 2.0,
    beta: float = 3.0,
) -> float:
    """Momentum-decay transition rule for RECOVERY -> MID_CYCLE."""
    logits = (alpha * float(level_score)) - (beta * float(decay_score))
    return 1.0 / (1.0 + math.exp(-logits))
