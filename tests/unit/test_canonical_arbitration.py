from __future__ import annotations

from datetime import date

from src.engine.canonical_arbitration import apply_v16_topology_arbitration
from src.models import SignalResult, TargetAllocationState


def _bayesian_result(*, target_beta: float = 0.59, bust: float = 0.29) -> SignalResult:
    return SignalResult(
        date=date(2026, 4, 16),
        price=637.40,
        target_beta=target_beta,
        probabilities={
            "LATE_CYCLE": 0.65,
            "BUST": bust,
            "RECOVERY": 0.03,
            "MID_CYCLE": 0.03,
        },
        priors={},
        entropy=0.597,
        stable_regime="LATE_CYCLE",
        target_allocation=TargetAllocationState(
            target_cash_pct=0.41,
            target_qqq_pct=0.59,
            target_qld_pct=0.0,
            target_beta=target_beta,
        ),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="bayesian base",
        metadata={"execution_bucket": "QQQ"},
    )


def test_v16_topology_can_become_official_when_price_process_is_safe():
    result = apply_v16_topology_arbitration(
        _bayesian_result(bust=0.407),
        {
            "last_timestamp": "2026-04-15 00:00:00",
            "latest_log": {
                "state": "active",
                "qld": 0.599,
                "qqq": 0.401,
                "cash": 0.0,
                "weight": 0.599,
                "p_cp": 0.0041,
                "s_t": 0.007,
                "vol_guard_cap": 2.0,
                "momentum_lockout": False,
                "circuit_breaker": False,
                "l_final": 1.599,
            },
            "latest_row": {"QQQ_price": 637.40, "QQQ_sma200": 596.59},
        },
    )

    assert result.target_beta == 1.599
    assert result.target_allocation.target_qld_pct == 0.599
    assert result.target_allocation.target_qqq_pct == 0.401
    assert result.target_allocation.target_cash_pct == 0.0
    assert result.metadata["canonical_decision"]["source"] == "v16_topology"
    assert result.metadata["execution_bucket"] == "QLD"


def test_bayesian_bust_must_dominate_before_it_blocks_safe_v16_topology():
    result = apply_v16_topology_arbitration(
        _bayesian_result(bust=0.56),
        {
            "last_timestamp": "2026-04-15 00:00:00",
            "latest_log": {
                "state": "active",
                "qld": 0.599,
                "qqq": 0.401,
                "cash": 0.0,
                "weight": 0.599,
                "p_cp": 0.0041,
                "s_t": 0.007,
                "vol_guard_cap": 2.0,
                "momentum_lockout": False,
                "circuit_breaker": False,
                "l_final": 1.599,
            },
            "latest_row": {"QQQ_price": 637.40, "QQQ_sma200": 596.59},
        },
    )

    assert result.metadata["canonical_decision"]["source"] == "bayesian_base"
    assert result.target_allocation.target_qld_pct == 0.0


def test_v16_hard_risk_veto_removes_qld_even_when_bayesian_is_bullish():
    result = apply_v16_topology_arbitration(
        _bayesian_result(target_beta=1.1, bust=0.05),
        {
            "last_timestamp": "2026-04-15 00:00:00",
            "latest_log": {
                "state": "active",
                "qld": 0.40,
                "qqq": 0.60,
                "cash": 0.0,
                "weight": 0.40,
                "p_cp": 0.82,
                "s_t": 0.91,
                "vol_guard_cap": 0.8,
                "momentum_lockout": False,
                "circuit_breaker": True,
                "l_final": 1.4,
            },
            "latest_row": {"QQQ_price": 510.0, "QQQ_sma200": 596.59},
        },
    )

    assert result.target_beta == 0.5
    assert result.target_allocation.target_qld_pct == 0.0
    assert result.target_allocation.target_qqq_pct == 0.5
    assert result.target_allocation.target_cash_pct == 0.5
    assert result.metadata["canonical_decision"]["source"] == "v16_hard_veto"
    assert result.metadata["execution_bucket"] == "QQQ"
