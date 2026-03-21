import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from src.output.interpreter import AIInterpreter
from src.models import SignalResult, Signal, Tier1Result, Tier2Result, MarketData, AllocationState, SignalDetail

@pytest.fixture
def mock_signal_result():
    t1 = Tier1Result(
        score=85,
        drawdown_52w=SignalDetail("drawdown", 0.1, 20, (0.05, 0.15), True, True),
        ma200_deviation=SignalDetail("ma200", 0.05, 10, (0.03, 0.07), True, False),
        vix=SignalDetail("vix", 18.5, 10, (15, 25), True, False),
        fear_greed=SignalDetail("fg", 35, 20, (20, 40), True, True),
        breadth=SignalDetail("breadth", 0.6, 10, (0.4, 0.7), True, False),
        stress_score=0,
        capitulation_score=0,
        persistence_score=0,
        market_regime="NORMAL",
        descent_velocity="NORMAL"
    )
    
    t2 = Tier2Result(
        adjustment=10,
        put_wall=430.0,
        call_wall=450.0,
        gamma_flip=435.0,
        support_confirmed=True,
        support_broken=False,
        upside_open=True,
        gamma_positive=True,
        gamma_source="yfinance",
        put_wall_distance_pct=0.02,
        call_wall_distance_pct=0.03,
        poc=432.0
    )
    
    return SignalResult(
        date=date(2026, 3, 21),
        price=438.5,
        signal=Signal.STRONG_BUY,
        final_score=85,
        tier1=t1,
        tier2=t2,
        explanation="Test signal",
        allocation_state=AllocationState.FAST_ACCUMULATE,
        daily_tranche_pct=0.5
    )

@pytest.fixture
def mock_market_data():
    return MagicMock(spec=MarketData, credit_spread=35, net_liquidity=6.5, real_yield=1.2)

def test_explain_signal_ollama_success(mock_signal_result, mock_market_data):
    # Ollama succeeds via httpx
    with patch("httpx.Client") as MockClient:
        mock_instance = MockClient.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Ollama Response"}}
        mock_response.raise_for_status.return_value = None
        mock_instance.post.return_value = mock_response
        
        interpreter = AIInterpreter()
        report = interpreter.explain_signal(mock_signal_result, mock_market_data)
        
        assert "Ollama Response" in report
        assert "qwen3.5:0.8b" in report
        assert mock_instance.post.called

def test_explain_signal_ollama_fail(mock_signal_result, mock_market_data):
    with patch("httpx.Client") as MockClient:
        mock_instance = MockClient.return_value.__enter__.return_value
        mock_instance.post.side_effect = Exception("Ollama Connection Refused")
        
        interpreter = AIInterpreter()
        report = interpreter.explain_signal(mock_signal_result, mock_market_data)
        
        assert "暂不可用" in report
        assert "Connection Refused" in report

def test_explain_signal_strips_thinking_tags(mock_signal_result, mock_market_data):
    # Ollama response includes <think> tags
    with patch("httpx.Client") as MockClient:
        mock_instance = MockClient.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "<think>I am analyzing the data...</think>Final expert advice."}}
        mock_response.raise_for_status.return_value = None
        mock_instance.post.return_value = mock_response
        
        interpreter = AIInterpreter()
        report = interpreter.explain_signal(mock_signal_result, mock_market_data)
        
        assert "Final expert advice." in report
        assert "analyzing" not in report
        assert "<think>" not in report
