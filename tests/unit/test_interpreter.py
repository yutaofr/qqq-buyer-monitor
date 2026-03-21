import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from src.output.interpreter import GeminiInterpreter
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

def test_explain_signal_calls_gemini_correctly(mock_signal_result, mock_market_data):
    mock_response = MagicMock()
    mock_response.text = "这是一份模拟的专家解读报告。"
    
    with patch("google.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.models.generate_content.return_value = mock_response
        
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
            interpreter = GeminiInterpreter()
            report = interpreter.explain_signal(mock_signal_result, mock_market_data)
            
            assert report == "这是一份模拟的专家解读报告。"
            assert instance.models.generate_content.called

def test_interpreter_supports_client_injection():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = "Injected Response"
    
    # This tests the injection logic
    interpreter = GeminiInterpreter(client=mock_client)
    assert interpreter.enabled is True
    
    result = interpreter.explain_signal(MagicMock(), MagicMock())
    assert result == "Injected Response"
    assert mock_client.models.generate_content.called

def test_interpreter_disabled_without_api_key():
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True):
        interpreter = GeminiInterpreter()
        assert interpreter.enabled is False
        
        # 即使调用 explain_signal 也不应报错，而是返回降级提示
        result = interpreter.explain_signal(MagicMock(), MagicMock())
        assert "disabled" in result.lower()
