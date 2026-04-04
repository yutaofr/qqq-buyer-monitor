"""v7.0 Candidate and Registry models."""

from __future__ import annotations

from dataclasses import dataclass

from src.models.risk import RiskState


@dataclass(frozen=True)
class CertifiedCandidate:
    """An offline-certified QQQ/QLD/Cash allocation candidate."""

    candidate_id: str
    registry_version: str
    allowed_risk_state: RiskState
    qqq_pct: float
    qld_pct: float
    cash_pct: float
    target_effective_exposure: float
    certification_status: str  # "CERTIFIED" | "CONDITIONAL" | "REJECTED"
    research_metrics: dict


@dataclass(frozen=True)
class CandidateRegistry:
    """Versioned collection of offline-certified candidates."""

    registry_version: str
    generated_at: str
    drawdown_budget: float
    candidates: tuple  # immutable sequence of CertifiedCandidate
