"""v7.0 Runtime Selector — deterministic, no backtest, adjustment-cost ranked."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.deployment_controller import DeploymentDecision
from src.engine.risk_controller import RiskDecision
from src.models import CurrentPortfolioState
from src.models.candidate import CertifiedCandidate


@dataclass(frozen=True)
class RuntimeSelection:
    """Result of the deterministic runtime candidate selection."""
    selected_candidate: CertifiedCandidate
    rejected_candidates: tuple   # sequence of {candidate_id, reason}
    selection_score: float       # lower = better (adjustment cost)


def _effective_exposure(candidate: CertifiedCandidate) -> float:
    """Compute expected effective exposure from candidate weights."""
    return candidate.qqq_pct + 2.0 * candidate.qld_pct


def _portfolio_exposure(portfolio: CurrentPortfolioState) -> float:
    return portfolio.qqq_pct + 2.0 * portfolio.qld_pct


def _adjustment_cost(portfolio: CurrentPortfolioState, candidate: CertifiedCandidate) -> float:
    """
    Compute the total adjustment cost from current portfolio to candidate.

    Lower is better. Penalises QQQ drift, QLD drift, and cash drift equally.
    Turnover bonus: lower turnover candidates preferred when cost is equal.
    """
    qqq_gap = abs(portfolio.qqq_pct - candidate.qqq_pct)
    qld_gap = abs(portfolio.qld_pct - candidate.qld_pct)
    cash_gap = abs(portfolio.current_cash_pct - candidate.cash_pct)
    turnover_penalty = candidate.research_metrics.get("turnover", 0.10) * 0.1
    return qqq_gap + qld_gap + cash_gap + turnover_penalty


def choose_target_candidate(
    portfolio: CurrentPortfolioState,
    risk_decision: RiskDecision,
    deployment_decision: DeploymentDecision,
    candidates: list[CertifiedCandidate],
) -> RuntimeSelection:
    """
    Select the best certified candidate deterministically (SRD §10.3, ADD §3.6).

    Selection priority:
      1. Must respect risk_decision exposure ceiling and cash floor
      2. Minimise adjustment cost from current portfolio
      3. Minimise turnover profile (via cost function)
      4. No randomness — identical inputs → identical output (NFR-1)

    If no candidates pass the ceiling filter, use "least bad" (SRD AC-5 fallback).
    """
    if not candidates:
        raise ValueError("No candidates provided to runtime selector.")

    rejected: list[dict] = []

    # ── Filter: must respect risk ceiling ─────────────────────────────────────
    compliant = []
    for c in candidates:
        exposure = _effective_exposure(c)
        if exposure > risk_decision.target_exposure_ceiling + 1e-9:
            rejected.append({
                "candidate_id": c.candidate_id,
                "reason": "exceeds_exposure_ceiling",
                "exposure": exposure,
                "ceiling": risk_decision.target_exposure_ceiling,
            })
            continue
        if c.cash_pct < risk_decision.target_cash_floor - 1e-9:
            rejected.append({
                "candidate_id": c.candidate_id,
                "reason": "below_cash_floor",
                "cash_pct": c.cash_pct,
                "floor": risk_decision.target_cash_floor,
            })
            continue
        compliant.append(c)

    # ── Fallback: if all filtered out, use least-bad (SRD AC-5) ──────────────
    pool = compliant if compliant else candidates
    if not compliant:
        rejected.append({"candidate_id": "_all_", "reason": "no_compliant_candidates_least_bad_fallback"})

    # ── Rank by adjustment cost (deterministic sort) ──────────────────────────
    ranked = sorted(pool, key=lambda c: _adjustment_cost(portfolio, c))
    best = ranked[0]
    score = _adjustment_cost(portfolio, best)

    # Record rejected (non-selected) from ranked pool
    for c in ranked[1:]:
        rejected.append({
            "candidate_id": c.candidate_id,
            "reason": "higher_adjustment_cost",
            "cost": _adjustment_cost(portfolio, c),
        })

    return RuntimeSelection(
        selected_candidate=best,
        rejected_candidates=tuple(rejected),
        selection_score=score,
    )
