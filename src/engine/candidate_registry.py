"""v7.0 Candidate Registry — load and filter offline-certified candidates."""
from __future__ import annotations

import json
from pathlib import Path

from src.models.candidate import CandidateRegistry, CertifiedCandidate
from src.models.risk import RiskState


def load_registry(path: str) -> CandidateRegistry:
    """
    Load a versioned CandidateRegistry from a JSON file.

    Raises FileNotFoundError if the file does not exist.
    Does NOT fall back to runtime search on missing file (SRD AC-3, ADD §5.3).
    """
    registry_path = Path(path)
    if not registry_path.exists():
        raise FileNotFoundError(
            f"Candidate registry not found at '{path}'. "
            "v7.0 does not fall back to live minimum-backtest search. "
            "Please run the research certifier to generate a registry."
        )

    with registry_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    candidates = tuple(
        CertifiedCandidate(
            candidate_id=c["candidate_id"],
            registry_version=c["registry_version"],
            allowed_risk_state=RiskState(c["allowed_risk_state"]),
            qqq_pct=float(c["qqq_pct"]),
            qld_pct=float(c["qld_pct"]),
            cash_pct=float(c["cash_pct"]),
            target_effective_exposure=float(c["target_effective_exposure"]),
            certification_status=c["certification_status"],
            research_metrics=dict(c.get("research_metrics", {})),
        )
        for c in data.get("candidates", [])
    )

    return CandidateRegistry(
        registry_version=data["registry_version"],
        generated_at=data["generated_at"],
        drawdown_budget=float(data.get("drawdown_budget", 0.30)),
        candidates=candidates,
    )


def select_runtime_candidates(
    registry: CandidateRegistry,
    risk_state: RiskState,
    allow_conditional: bool = False,
) -> list[CertifiedCandidate]:
    """
    Filter to candidates valid for the current risk state.

    Default: only CERTIFIED. CONDITIONAL requires explicit opt-in (SRD §9.4).
    """
    allowed_statuses = {"CERTIFIED"}
    if allow_conditional:
        allowed_statuses.add("CONDITIONAL")

    return [
        c for c in registry.candidates
        if c.allowed_risk_state == risk_state
        and c.certification_status in allowed_statuses
    ]
