"""
v6.4 Personal Allocation Search: Generates SRD-approved QQQ:QLD:Cash candidates.
"""
from __future__ import annotations

from src.models.candidate import CertifiedCandidate
from src.models import AllocationState, TargetAllocationState

# SRD-defined Candidate Matrix (QQQ, QLD, Cash)
# Each entry is (QQQ%, QLD%, Cash%)
_SRD_BANDS = {
    AllocationState.FAST_ACCUMULATE: [(0.4, 0.4, 0.2), (0.4, 0.3, 0.3)],
    AllocationState.BASE_DCA:        [(0.5, 0.2, 0.3), (0.6, 0.1, 0.3), (0.7, 0.1, 0.2)],
    AllocationState.SLOW_ACCUMULATE: [(0.6, 0.0, 0.4), (0.7, 0.1, 0.2)],
    AllocationState.WATCH_DEFENSE:   [(0.7, 0.0, 0.3)],
    AllocationState.DELEVERAGE:      [(0.6, 0.0, 0.4)],
    AllocationState.CASH_FLIGHT:     [(0.7, 0.0, 0.3), (0.6, 0.0, 0.4)],
    # Fallback/Legacy states
    AllocationState.PAUSE_CHASING:   [(0.8, 0.0, 0.2)],
    AllocationState.RISK_CONTAINMENT:[(0.7, 0.0, 0.3)],
}

def generate_candidates(state: AllocationState) -> list[TargetAllocationState]:
    """Generates TargetAllocationState candidates based on SRD-defined bands."""
    bands = _SRD_BANDS.get(state, _SRD_BANDS[AllocationState.BASE_DCA])
    candidates = []
    for qqq, qld, cash in bands:
        beta = qqq + 2.0 * qld
        candidates.append(TargetAllocationState(
            target_cash_pct=cash,
            target_qqq_pct=qqq,
            target_qld_pct=qld,
            target_beta=float(beta)
        ))
    return candidates

def find_best_allocation(state: AllocationState, scores: list[dict] = None) -> TargetAllocationState:
    """
    Deterministic Selector: Returns the best allocation from candidates.
    v6.4: Selection rules (Hard Constraints First):
    1. Filter out violations (Beta Deviation > 0.05, MDD > 0.30).
    2. Pick highest CAGR.
    3. If CAGR tied (within 0.1%), lower MDD.
    4. If MDD tied, lower Beta Deviation.
    5. If still tied, lower Turnover.
    
    AC-5 Hard Gate: If no candidate meets the 30% MDD budget, it MUST return
    a safe fallback (100% Cash).
    """
    candidates = generate_candidates(state)

    # State-level safest option (lowest beta)
    state_safest = sorted(candidates, key=lambda c: c.target_beta)[0]

    # Global Safe Fallback: 100% Cash (Target Beta = 0.0)
    # This is the ultimate "Reject" path for AC-5 violations.
    global_safe_fallback = TargetAllocationState(target_cash_pct=1.0, target_qqq_pct=0.0, target_qld_pct=0.0, target_beta=0.0)

    # AC-5 Strictness: If search was active but found no safe data, return global fallback.
    if scores == []:
        return global_safe_fallback

    # If no scores provided (live path without history or legacy call),
    # return the first candidate as default (v6.3 behavior).
    if scores is None:
        return candidates[0]

    # 1. Hard Constraints (AC-4, AC-5)
    valid = []
    for s in scores:
        # AC-4: Beta Fidelity (mean deviation <= 0.05)
        is_valid_beta = s["mean_interval_beta_deviation"] <= 0.05
        # AC-5: 30% Drawdown Budget (Strict Hard Threshold)
        is_valid_mdd = s["max_drawdown"] <= 0.30

        if is_valid_beta and is_valid_mdd:
            valid.append(s)

    # If no candidate meets AC-5, verify if state_safest at least passes.
    # If even the safest candidate for this state fails, force GLOBAL_SAFE_FALLBACK.
    if not valid:
        safest_score = next((s for s in scores if s["candidate"] == state_safest), None)
        if safest_score and safest_score["max_drawdown"] > 0.30:
            return global_safe_fallback
        return state_safest

    # 2. Sort by Soft Targets
    # Sort order: CAGR (desc), MDD (asc), BetaDev (asc), Turnover (asc)
    # We use a epsilon for CAGR tie-breaking
    def sort_key(s):
        # We negate cagr for descending sort with ascending on others
        return (-round(s["cagr"], 3), round(s["max_drawdown"], 3),
                round(s["mean_interval_beta_deviation"], 4), round(s["turnover"], 3))

    sorted_scores = sorted(valid, key=sort_key)
    return sorted_scores[0]["candidate"]


def find_best_allocation_v8(
    max_beta_ceiling: float,
    max_drawdown_budget: float = 0.30,
    candidates: list[CertifiedCandidate] | None = None,
) -> CertifiedCandidate | None:
    """v8.0: select from certified candidates using pure mathematical constraints."""
    if not candidates:
        return None

    valid = [
        candidate for candidate in candidates
        if 0.50 <= candidate.target_effective_exposure <= max_beta_ceiling
        and candidate.research_metrics.get("max_drawdown", 1.0) <= max_drawdown_budget
    ]
    if not valid:
        return None

    def sort_key(candidate: CertifiedCandidate) -> tuple[float, float, float]:
        metrics = candidate.research_metrics
        return (
            -float(metrics.get("cagr", 0.0)),
            float(metrics.get("max_drawdown", 1.0)),
            float(metrics.get("mean_interval_beta_deviation", 1.0)),
        )

    return sorted(valid, key=sort_key)[0]
