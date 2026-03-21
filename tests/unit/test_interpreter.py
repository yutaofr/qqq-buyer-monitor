import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from src.output.interpreter import GeminiInterpreter
from src.models import SignalResult, Signal, Tier1Result, Tier2Result, MarketData, AllocationState

@pytest.fixture
def mock_signal_result():
    t1 = MagicMock(spec=Tier1Result)
    t1.score = 85
    t1.vix = MagicMock(value=18.5)
    t1.fear_greed = MagicMock(value=35)
    t1.ma200_deviation = MagicMock(value=0.05)
    t1.market_regime = "NORMAL"
    t1.descent_velocity = "NORMAL"
    
    t2 = MagicMock(spec=Tier2Result)
    t2.adjustment = 10
    t2.put_wall = 430.0
    t2.gamma_flip = 435.0
    t2.support_broken = False
    t2.gamma_positive = True
    
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
    
    with patch("google.generativeai.GenerativeModel") as MockModel:
        instance = MockModel.return_value
        instance.generate_content.return_value = mock_response
        
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
            interpreter = GeminiInterpreter()
            report = interpreter.explain_signal(mock_signal_result, mock_market_data)
            
            assert report == "这是一份模拟的专家解读报告。"
            assert instance.generate_content.called

def test_interpreter_supports_model_injection():
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "Injected Response"
    
    # 这将测试注入逻辑
    interpreter = GeminiInterpreter(model=mock_model)
    assert interpreter.enabled is True
    
    result = interpreter.explain_signal(MagicMock(), MagicMock())
    assert result == "Injected Response"
    assert mock_model.generate_content.called

def test_interpreter_disabled_without_api_key():
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True):
        interpreter = GeminiInterpreter()
        assert interpreter.enabled is False
        
        # 即使调用 explain_signal 也不应报错，而是返回降级提示
        result = interpreter.explain_signal(MagicMock(), MagicMock())
        assert "disabled" in result.lower()
