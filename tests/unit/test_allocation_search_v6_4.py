import pytest
from src.engine.allocation_search import generate_candidates, find_best_allocation
from src.models import AllocationState, TargetAllocationState

def test_generate_candidates_srd_bounds():
    """AC-6: Candidates must stay within SRD-defined bands."""
    
    # FAST_ACCUMULATE: 442 or 433
    fast = generate_candidates(AllocationState.FAST_ACCUMULATE)
    assert len(fast) == 2
    ratios = {(c.target_qqq_pct, c.target_qld_pct, c.target_cash_pct) for c in fast}
    assert (0.4, 0.4, 0.2) in ratios
    assert (0.4, 0.3, 0.3) in ratios

    # BASE_DCA: 523, 613, 712
    base = generate_candidates(AllocationState.BASE_DCA)
    assert len(base) == 3
    ratios = {(c.target_qqq_pct, c.target_qld_pct, c.target_cash_pct) for c in base}
    assert (0.5, 0.2, 0.3) in ratios
    assert (0.6, 0.1, 0.3) in ratios
    assert (0.7, 0.1, 0.2) in ratios

    # SLOW_ACCUMULATE: 604 or 712
    slow = generate_candidates(AllocationState.SLOW_ACCUMULATE)
    assert len(slow) == 2
    ratios = {(c.target_qqq_pct, c.target_qld_pct, c.target_cash_pct) for c in slow}
    assert (0.6, 0.0, 0.4) in ratios
    assert (0.7, 0.1, 0.2) in ratios

def test_defensive_states_no_qld():
    """AC-2: Defensive states never emit nonzero QLD."""
    for state in [AllocationState.WATCH_DEFENSE, AllocationState.DELEVERAGE, AllocationState.CASH_FLIGHT]:
        candidates = generate_candidates(state)
        for c in candidates:
            assert c.target_qld_pct == 0.0

def test_find_best_allocation_fallback():
    """AC-5: Search returns 100% cash (Beta 0.0) when scores are explicitly empty (failed search)."""
    # Empty list means search was active but found no safe candidates
    best = find_best_allocation(AllocationState.BASE_DCA, [])
    assert isinstance(best, TargetAllocationState)
    assert best.target_cash_pct == 1.0
    assert best.target_beta == 0.0

    # None means no search performed (legacy/live fallback) - returns default band
    best_default = find_best_allocation(AllocationState.BASE_DCA, None)
    assert best_default.target_cash_pct in [0.3, 0.2]
