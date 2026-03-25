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
    mock_result.tier0_regime = "NEUTRAL"
    mock_result.risk_state = RiskState.RISK_NEUTRAL
    mock_result.deployment_state = DeploymentState.DEPLOY_BASE
    mock_result.selected_candidate_id = "neutral-base-001"
    mock_result.registry_version = "2026-03-25-v8.0-r1"
    mock_result.target_beta = 1.00
    mock_result.should_adjust = True
    mock_result.rebalance_action = {
        "should_adjust": True,
        "reason": "risk_state_changed",
    }
    mock_result.deployment_action = {
        "deploy_mode": "FAST",
        "reason": "capitulation_fast",
    }

    print_signal(mock_result, use_color=False)
    captured = capsys.readouterr()
    assert "QQQ BUY-SIGNAL MONITOR (v8.0)" in captured.out
    assert "风险评估与目标 Beta" in captured.out
    assert "增量入场节奏推荐" in captured.out
    assert "Tier-0=NEUTRAL" in captured.out
    assert "target_beta=1.00x" in captured.out
    assert "mode=FAST" in captured.out
    assert "amount=" not in captured.out


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
