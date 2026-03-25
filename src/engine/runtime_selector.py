"""v7.0 Runtime Selector — deterministic, no backtest, adjustment-cost ranked."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.deployment_controller import DeploymentDecision
from src.engine.risk_controller import RiskDecision
from src.models.candidate import CertifiedCandidate


class NoCompliantCandidatesError(ValueError):
    """Raised when a risk state has candidates but none satisfy runtime hard constraints."""

    def __init__(self, rejected_candidates: list[dict]):
        super().__init__("No compliant candidates available for the requested risk constraints.")
        self.rejected_candidates = tuple(rejected_candidates)


@dataclass(frozen=True)
class RuntimeSelection:
    """Result of the deterministic runtime candidate selection."""
    selected_candidate: CertifiedCandidate
    rejected_candidates: tuple   # sequence of {candidate_id, reason}
    selection_score: float       # lower = better (adjustment cost)


def _effective_exposure(candidate: CertifiedCandidate) -> float:
    """Compute expected effective exposure from candidate weights."""
    return candidate.qqq_pct + 2.0 * candidate.qld_pct


