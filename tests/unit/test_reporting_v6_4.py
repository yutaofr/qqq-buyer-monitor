import pytest
from src.output.cli import print_signal
from src.output.report import to_json
from src.models import (
    SignalResult, Signal, Tier1Result, Tier2Result, AllocationState,
    CurrentPortfolioState, TargetAllocationState, SignalDetail
)
from datetime import date
from src.models.deployment import DeploymentState
from src.models.risk import RiskState

@pytest.fixture
def mock_result():
    t1 = Tier1Result(
        score=50,
        drawdown_52w=SignalDetail("dd", 0, 0, (0,0), False, False),
        ma200_deviation=SignalDetail("ma", 0, 0, (0,0), False, False),
        vix=SignalDetail("vix", 0, 0, (0,0), False, False),
        fear_greed=SignalDetail("fg", 0, 0, (0,0), False, False),
        breadth=SignalDetail("br", 0, 0, (0,0), False, False),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "yf", 0, 0)
    
    return SignalResult(
        date=date(2026, 3, 23),
        price=400.0,
        signal=Signal.TRIGGERED,
        final_score=60,
        tier1=t1,
        tier2=t2,
        explanation="Test explanation",
        current_portfolio=CurrentPortfolioState(0.2, 0.4, 0.4),
        target_allocation=TargetAllocationState(0.1, 0.8, 0.1, 1.0),
        effective_exposure=1.2,
        logic_trace=[{"step": "search", "decision": "442 selected", "reason": "Best CAGR"}]
    )

def test_cli_output_contains_v6_4_fields(mock_result, capsys):
    """CLI should print reality and ideal allocation."""
    print_signal(mock_result, use_color=False)
    captured = capsys.readouterr()
    assert "Reality:" in captured.out
    assert "Ideal:" in captured.out
    assert "Cash=20.0%" in captured.out
    assert "Beta=1.00x" in captured.out

def test_report_json_contains_v6_4_fields(mock_result):
    """JSON report should contain strategic allocation fields."""
    report = to_json(mock_result)
    assert '"target_allocation"' in report
    assert '"current_portfolio"' in report
    assert '"effective_exposure"' in report
    assert '"interval_beta_audit"' in report


def test_cli_output_reflects_v7_runtime_when_available(mock_result, capsys):
    mock_result.risk_state = RiskState.RISK_NEUTRAL
    mock_result.deployment_state = DeploymentState.DEPLOY_BASE
    mock_result.selected_candidate_id = "neutral-base-001"
    mock_result.registry_version = "2026-03-24-v7.0-r1"
    mock_result.rebalance_action = {
        "should_rebalance": True,
        "reason": "risk_state_changed",
        "target_qqq_pct": 0.70,
        "target_qld_pct": 0.10,
        "target_cash_pct": 0.20,
    }
    mock_result.deployment_action = {
        "deploy_cash_amount": 1000.0,
        "deploy_mode": "FAST",
        "reason": "available_new_cash=500.00;dca_multiplier=2.0",
    }

    print_signal(mock_result, use_color=False)
    captured = capsys.readouterr()
    assert "QQQ BUY-SIGNAL MONITOR (v7.0)" in captured.out
    assert "资产配置风险管理" in captured.out
    assert "增量资金买入时机决策" in captured.out
    assert "风险状态=RISK_NEUTRAL" in captured.out
    assert "目标Beta: 1.00x" in captured.out
    assert "mode=FAST" in captured.out


def test_cli_output_hides_default_portfolio_fallback(capsys):
    t1 = Tier1Result(
        score=50,
        drawdown_52w=SignalDetail("dd", 0, 0, (0,0), False, False),
        ma200_deviation=SignalDetail("ma", 0, 0, (0,0), False, False),
        vix=SignalDetail("vix", 0, 0, (0,0), False, False),
        fear_greed=SignalDetail("fg", 0, 0, (0,0), False, False),
        breadth=SignalDetail("br", 0, 0, (0,0), False, False),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "yf", 0, 0)
    result = SignalResult(
        date=date(2026, 3, 25),
        price=583.98,
        signal=Signal.WATCH,
        final_score=50,
        tier1=t1,
        tier2=t2,
        explanation="Test explanation",
    )

    print_signal(result, use_color=False)
    captured = capsys.readouterr()
    assert "Reality:" not in captured.out
    assert "Ideal:" not in captured.out
