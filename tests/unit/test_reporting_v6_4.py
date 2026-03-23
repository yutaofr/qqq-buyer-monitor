import pytest
from src.output.cli import print_signal
from src.output.report import to_json
from src.models import (
    SignalResult, Signal, Tier1Result, Tier2Result, AllocationState,
    CurrentPortfolioState, TargetAllocationState, SignalDetail
)
from datetime import date

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
