"""v7.0 Research Certifier — offline candidate certification pipeline."""
from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from src.models.candidate import CandidateRegistry, CertifiedCandidate
from src.models.risk import RiskState

# Required research metrics fields (SRD AC-8)
REQUIRED_METRICS = {
    "max_drawdown",
    "cagr",
    "ulcer_index",
    "expected_shortfall",
    "mean_interval_beta_deviation",
    "turnover",
    "defense_coverage",
    "nav_integrity",
}

# Hard constraint: MDD must be below drawdown budget to earn CERTIFIED (SRD AC-5)
_MDD_HARD_LIMIT = 0.30

# Acceptable edge-case: MDD within tolerance above budget → CONDITIONAL
_MDD_CONDITIONAL_LIMIT = 0.35
_BETA_DEVIATION_CERTIFIED_LIMIT = 0.05
_BETA_DEVIATION_CONDITIONAL_LIMIT = 0.10


def _compute_metrics(
    price_history: pd.DataFrame,
    macro_history: pd.DataFrame | None,
    qqq_pct: float,
    qld_pct: float,
    cash_pct: float,
) -> dict[str, float]:
    """
    Compute research metrics for a candidate over the provided price history.

    price_history must have columns: ['qqq_ret', 'qld_ret'] with daily returns.
    macro_history may provide benchmark_ret and nav_integrity audit inputs.
    Returns a dict of all REQUIRED_METRICS.
    """
    if price_history is None or price_history.empty:
        return {m: float("nan") for m in REQUIRED_METRICS}

    qqq_ret = price_history.get("qqq_ret", pd.Series(dtype=float))
    qld_ret = price_history.get("qld_ret", pd.Series(dtype=float))
    cash_ret = pd.Series(0.0, index=qqq_ret.index)

    portfolio_ret = qqq_pct * qqq_ret + qld_pct * qld_ret + cash_pct * cash_ret
    cum_ret = (1 + portfolio_ret).cumprod()

    # Max Drawdown
    rolling_max = cum_ret.cummax()
    drawdown = (cum_ret - rolling_max) / rolling_max
    max_drawdown = abs(float(drawdown.min()))

    # CAGR
    n_years = len(cum_ret) / 252.0
    cagr = float(cum_ret.iloc[-1] ** (1 / n_years) - 1) if n_years > 0 else 0.0

    # Ulcer Index (RMS of drawdown)
    ulcer_index = float((drawdown ** 2).mean() ** 0.5) * 100

    # Expected Shortfall (CVaR at 5%)
    tail = portfolio_ret[portfolio_ret <= portfolio_ret.quantile(0.05)]
    expected_shortfall = abs(float(tail.mean())) if not tail.empty else 0.0

    # Turnover proxy (mean absolute daily change in effective exposure)
    effective_exposure = qqq_pct + 2.0 * qld_pct
    turnover = abs(effective_exposure - (qqq_pct + qld_pct)) * 0.01  # simplified proxy

    benchmark_ret = pd.Series(dtype=float)
    if macro_history is not None and not macro_history.empty:
        for col in ("benchmark_ret", "spy_ret"):
            if col in macro_history:
                benchmark_ret = macro_history[col].dropna()
                if not benchmark_ret.empty:
                    break
    if benchmark_ret.empty:
        benchmark_ret = price_history.get("qqq_ret", pd.Series(dtype=float)).dropna()

    # Beta fidelity
    if benchmark_ret.std() > 0:
        aligned_portfolio = portfolio_ret.reindex(benchmark_ret.index).dropna()
        aligned_benchmark = benchmark_ret.reindex(aligned_portfolio.index).dropna()
        if len(aligned_portfolio) > 1 and len(aligned_benchmark) > 1 and aligned_benchmark.std() > 0:
            beta = aligned_portfolio.corr(aligned_benchmark) * (aligned_portfolio.std() / aligned_benchmark.std())
        else:
            beta = 0.0
    else:
        beta = 0.0
    mean_interval_beta_deviation = abs(beta - effective_exposure)

    # Defense coverage: fraction of months where drawdown < 20%
    monthly_dd = drawdown.resample("ME").min() if hasattr(drawdown.index, "freq") else drawdown
    defense_coverage = float((monthly_dd > -0.20).mean())

    # NAV integrity: prefer an external audit input when available.
    nav_integrity = 1.0
    if macro_history is not None and not macro_history.empty and "nav_integrity" in macro_history:
        nav_series = macro_history["nav_integrity"].dropna()
        if not nav_series.empty:
            nav_integrity = float(nav_series.iloc[-1])

    return {
        "max_drawdown": max_drawdown,
        "cagr": cagr,
        "ulcer_index": ulcer_index,
        "expected_shortfall": expected_shortfall,
        "mean_interval_beta_deviation": mean_interval_beta_deviation,
        "turnover": turnover,
        "defense_coverage": defense_coverage,
        "nav_integrity": nav_integrity,
    }


def _certify_status(metrics: dict[str, float], drawdown_budget: float = 0.30) -> str:
    """Assign CERTIFIED / CONDITIONAL / REJECTED based on hard constraints (SRD §9.4)."""
    mdd = metrics.get("max_drawdown", 1.0)
    nav = metrics.get("nav_integrity", 0.0)
    beta_dev = metrics.get("mean_interval_beta_deviation", float("inf"))
    beta_dev = float(beta_dev) if beta_dev is not None else float("inf")
    if not math.isfinite(beta_dev):
        beta_dev = float("inf")

    if mdd <= drawdown_budget and nav >= 0.99 and beta_dev <= _BETA_DEVIATION_CERTIFIED_LIMIT:
        return "CERTIFIED"
    if mdd <= _MDD_CONDITIONAL_LIMIT and nav >= 0.95 and beta_dev <= _BETA_DEVIATION_CONDITIONAL_LIMIT:
        return "CONDITIONAL"
    return "REJECTED"


def certify_candidates(
    price_history: pd.DataFrame | None,
    macro_history: pd.DataFrame | None,
    candidate_space: list[dict[str, Any]],
    drawdown_budget: float = 0.30,
    registry_version: str | None = None,
) -> CandidateRegistry:
    """
    Offline certify candidate configurations and produce a versioned registry.

    Args:
        price_history: DataFrame with daily returns (columns: qqq_ret, qld_ret).
        macro_history: DataFrame with macro features (currently unused in skeleton).
        candidate_space: List of dicts with keys: candidate_id, allowed_risk_state,
                         qqq_pct, qld_pct, cash_pct.
        drawdown_budget: Maximum allowed portfolio MDD.
        registry_version: Optional explicit version; auto-generated if None.

    Returns:
        CandidateRegistry with certified candidates.
    """
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    version = registry_version or f"v7-research-{ts}"

    certified: list[CertifiedCandidate] = []

    for space in candidate_space:
        candidate_id = space["candidate_id"]
        risk_state = RiskState(space["allowed_risk_state"])
        qqq = float(space["qqq_pct"])
        qld = float(space["qld_pct"])
        cash = float(space["cash_pct"])

        metrics = _compute_metrics(price_history, macro_history, qqq, qld, cash)
        status = _certify_status(metrics, drawdown_budget)

        candidate = CertifiedCandidate(
            candidate_id=candidate_id,
            registry_version=version,
            allowed_risk_state=risk_state,
            qqq_pct=qqq,
            qld_pct=qld,
            cash_pct=cash,
            target_effective_exposure=qqq + 2.0 * qld,
            certification_status=status,
            research_metrics=metrics,
        )
        certified.append(candidate)

    return CandidateRegistry(
        registry_version=version,
        generated_at=ts,
        drawdown_budget=drawdown_budget,
        candidates=tuple(certified),
    )


def export_registry_json(registry: CandidateRegistry, path: str) -> None:
    """Serialise a CandidateRegistry to JSON file for use by the runtime."""
    data = {
        "registry_version": registry.registry_version,
        "generated_at": registry.generated_at,
        "drawdown_budget": registry.drawdown_budget,
        "candidates": [
            {
                "candidate_id": c.candidate_id,
                "registry_version": c.registry_version,
                "allowed_risk_state": c.allowed_risk_state.value,
                "qqq_pct": c.qqq_pct,
                "qld_pct": c.qld_pct,
                "cash_pct": c.cash_pct,
                "target_effective_exposure": c.target_effective_exposure,
                "certification_status": c.certification_status,
                "research_metrics": c.research_metrics,
            }
            for c in registry.candidates
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
