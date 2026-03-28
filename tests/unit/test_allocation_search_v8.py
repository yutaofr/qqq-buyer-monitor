"""TDD: v8 allocation search — pure mathematical ceiling selection."""
from __future__ import annotations

import inspect

from src.models.candidate import CertifiedCandidate
from src.models.risk import RiskState


def _candidate(
    candidate_id: str,
    exposure: float,
    *,
    cagr: float,
    mdd: float,
    qld: float | None = None,
    expected_shortfall: float | None = None,
    ulcer_index: float | None = None,
    turnover: float | None = None,
) -> CertifiedCandidate:
    qld = max(0.0, exposure - 0.5) if qld is None else qld
    qqq = exposure - 2.0 * qld
    cash = 1.0 - qqq - qld
    return CertifiedCandidate(
        candidate_id=candidate_id,
        registry_version="v8-test-r1",
        allowed_risk_state=RiskState.RISK_REDUCED,
        qqq_pct=qqq,
        qld_pct=qld,
        cash_pct=cash,
        target_effective_exposure=exposure,
        certification_status="CERTIFIED",
        research_metrics={
            "cagr": cagr,
            "max_drawdown": mdd,
            "expected_shortfall": mdd if expected_shortfall is None else expected_shortfall,
            "ulcer_index": mdd if ulcer_index is None else ulcer_index,
            "mean_interval_beta_deviation": 0.01,
            "turnover": 0.01 if turnover is None else turnover,
        },
    )


def test_allocation_search_filters_by_beta_ceiling():
    from src.engine.allocation_search import find_best_allocation_v8

    candidates = [
        _candidate("exp-090", 0.90, cagr=0.14, mdd=0.22),
        _candidate("exp-050", 0.50, cagr=0.10, mdd=0.16),
        _candidate("exp-030", 0.30, cagr=0.08, mdd=0.10),
    ]
    best = find_best_allocation_v8(max_beta_ceiling=0.50, qld_share_ceiling=0.0, candidates=candidates)
    assert best is not None
    assert best.target_effective_exposure <= 0.50


def test_allocation_search_returns_none_when_nothing_fits_ceiling():
    from src.engine.allocation_search import find_best_allocation_v8

    candidates = [
        _candidate("exp-090", 0.90, cagr=0.14, mdd=0.22),
        _candidate("exp-070", 0.70, cagr=0.12, mdd=0.18),
    ]
    assert find_best_allocation_v8(max_beta_ceiling=0.30, qld_share_ceiling=0.0, candidates=candidates) is None


def test_allocation_search_keeps_floor_beta_candidate_when_capped():
    from src.engine.allocation_search import find_best_allocation_v8

    candidates = [
        _candidate("exp-030", 0.30, cagr=0.08, mdd=0.10),
        _candidate("exp-050", 0.50, cagr=0.10, mdd=0.16),
    ]
    best = find_best_allocation_v8(max_beta_ceiling=0.50, qld_share_ceiling=0.0, candidates=candidates)
    assert best is not None
    assert best.candidate_id == "exp-050"


def test_allocation_search_prefers_higher_cagr_after_constraints():
    from src.engine.allocation_search import find_best_allocation_v8

    candidates = [
        _candidate("higher-cagr", 0.50, cagr=0.12, mdd=0.20),
        _candidate("lower-cagr", 0.50, cagr=0.10, mdd=0.10),
    ]
    best = find_best_allocation_v8(max_beta_ceiling=0.50, qld_share_ceiling=0.0, candidates=candidates)
    assert best is not None
    assert best.candidate_id == "higher-cagr"


def test_allocation_search_breaks_cagr_ties_with_tail_risk_metrics():
    from src.engine.allocation_search import find_best_allocation_v8

    candidates = [
        _candidate(
            "lower-tail-risk",
            1.20,
            qld=0.25,
            cagr=0.18,
            mdd=0.29,
            expected_shortfall=0.24,
            ulcer_index=13.0,
            turnover=0.10,
        ),
        _candidate(
            "lower-mdd-but-worse-tail",
            1.20,
            qld=0.20,
            cagr=0.18,
            mdd=0.28,
            expected_shortfall=0.27,
            ulcer_index=15.0,
            turnover=0.16,
        ),
    ]
    best = find_best_allocation_v8(max_beta_ceiling=1.20, qld_share_ceiling=0.25, candidates=candidates)

    assert best is not None
    assert best.candidate_id == "lower-tail-risk"


def test_allocation_search_filters_by_qld_share_ceiling():
    from src.engine.allocation_search import find_best_allocation_v8

    candidates = [
        _candidate("reduced-safe-qld", 0.80, qld=0.10, cagr=0.08, mdd=0.16),
        _candidate("reduced-over-qld", 0.80, qld=0.20, cagr=0.14, mdd=0.12),
    ]
    best = find_best_allocation_v8(
        max_beta_ceiling=0.80,
        qld_share_ceiling=0.10,
        candidates=candidates,
    )

    assert best is not None
    assert best.candidate_id == "reduced-safe-qld"


def test_allocation_search_signature_has_no_allocation_state_parameter():
    from src.engine.allocation_search import find_best_allocation_v8

    signature = inspect.signature(find_best_allocation_v8)
    assert "state" not in signature.parameters
    assert "allocation_state" not in signature.parameters


def test_allocation_search_uses_global_beta_floor_fallback_when_scoped_candidates_fail():
    from src.engine.allocation_search import select_candidate_with_floor_fallback_v8

    scoped = [
        _candidate("exp-090", 0.90, cagr=0.14, mdd=0.22),
        _candidate("exp-070", 0.70, cagr=0.12, mdd=0.18),
    ]
    registry = scoped + [
        _candidate("floor-050", 0.50, cagr=0.05, mdd=0.10),
    ]

    selected, used_fallback = select_candidate_with_floor_fallback_v8(
        scoped_candidates=scoped,
        registry_candidates=registry,
        max_beta_ceiling=0.50,
        qld_share_ceiling=0.0,
        max_drawdown_budget=0.30,
    )

    assert used_fallback is True
    assert selected is not None
    assert selected.candidate_id == "floor-050"


def test_allocation_search_floor_fallback_rejects_qld_above_ceiling():
    from src.engine.allocation_search import select_candidate_with_floor_fallback_v8

    registry = [
        _candidate("floor-050-qld", 0.50, qld=0.05, cagr=0.08, mdd=0.10),
    ]

    selected, used_fallback = select_candidate_with_floor_fallback_v8(
        scoped_candidates=[],
        registry_candidates=registry,
        max_beta_ceiling=0.50,
        qld_share_ceiling=0.0,
        max_drawdown_budget=0.30,
    )

    assert used_fallback is False
    assert selected is None
