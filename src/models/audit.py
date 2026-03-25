"""v7.0 Decision Audit model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.models.deployment import DeploymentState
from src.models.risk import RiskState


@dataclass(frozen=True)
class DecisionAudit:
    """Full evidence record for a single v7 production decision."""
    market_date: date
    risk_state: RiskState
    deployment_state: DeploymentState
    selected_candidate_id: str | None
    evidence_trace: tuple  # immutable sequence of dicts
    data_quality: dict
    rejected_candidates: tuple  # immutable sequence of dicts
