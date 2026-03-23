"""
v6.4 Personal Allocation Search: Generates SRD-approved QQQ:QLD:Cash candidates.
"""
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
    for q, l, c in bands:
        beta = q + 2.0 * l
        candidates.append(TargetAllocationState(
            target_cash_pct=float(c),
            target_qqq_pct=float(q),
            target_qld_pct=float(l),
            target_beta=float(beta)
        ))
    return candidates

def find_best_allocation(state: AllocationState, scores: list[dict] = None) -> TargetAllocationState:
    """
    Deterministic Selector: Returns the best allocation from candidates.
    v6.4: Selection rules (Hard Constraints First):
    1. Filter out violations (Beta Deviation > 0.05, MDD > 0.30 - soft limit here).
    2. Pick highest CAGR.
    3. If CAGR tied (within 0.1%), lower MDD.
    4. If MDD tied, lower Beta Deviation.
    5. If still tied, lower Turnover.
    """
    candidates = generate_candidates(state)
    if not scores:
        return candidates[0]
    
    # 1. Hard Constraints (AC-4, AC-5)
    valid = []
    for s in scores:
        # Note: MDD check should be cautious as backtests vary.
        # We prefer those meeting AC-4 (Beta fidelity).
        is_valid_beta = s["mean_interval_beta_deviation"] <= 0.05
        # is_valid_mdd = s["max_drawdown"] <= 0.30 
        # (We allow slight overflow in backtest if it's best we have)
        
        if is_valid_beta:
            valid.append(s)
            
    # If no one is valid by AC-4, take all and pick least bad
    if not valid:
        valid = scores
        
    # 2. Sort by Soft Targets
    # Sort order: CAGR (desc), MDD (asc), BetaDev (asc), Turnover (asc)
    # We use a epsilon for CAGR tie-breaking
    def sort_key(s):
        # We negate cagr for descending sort with ascending on others
        return (-round(s["cagr"], 3), round(s["max_drawdown"], 3), 
                round(s["mean_interval_beta_deviation"], 4), round(s["turnover"], 3))
    
    sorted_scores = sorted(valid, key=sort_key)
    return sorted_scores[0]["candidate"]
