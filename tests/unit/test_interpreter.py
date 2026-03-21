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

def test_explain_signal_gemini_success(mock_signal_result, mock_market_data):
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.return_value.text = "Gemini Response"
    
    interpreter = AIInterpreter(gemini_client=mock_gemini)
    report = interpreter.explain_signal(mock_signal_result, mock_market_data)
    
    assert "Gemini Response" in report
    assert "Gemini" in report
    assert mock_gemini.models.generate_content.called

def test_explain_signal_fallback_to_ollama(mock_signal_result, mock_market_data):
    # Gemini fails
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.side_effect = Exception("Quota Exceeded")
    
    # Ollama succeeds
    mock_ollama = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Ollama Response"
    mock_ollama.chat.completions.create.return_value.choices = [mock_choice]
    
    interpreter = AIInterpreter(gemini_client=mock_gemini, ollama_client=mock_ollama)
    report = interpreter.explain_signal(mock_signal_result, mock_market_data)
    
    assert "Ollama Response" in report
    assert "qwen3.5:latest" in report # Default model
    assert mock_gemini.models.generate_content.called
    assert mock_ollama.chat.completions.create.called

def test_explain_signal_all_fail(mock_signal_result, mock_market_data):
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.side_effect = Exception("Gemini Down")
    
    mock_ollama = MagicMock()
    mock_ollama.chat.completions.create.side_effect = Exception("Ollama Down")
    
    interpreter = AIInterpreter(gemini_client=mock_gemini, ollama_client=mock_ollama)
    report = interpreter.explain_signal(mock_signal_result, mock_market_data)
    
    assert "暂不可用" in report

def test_explain_signal_strips_thinking_tags(mock_signal_result, mock_market_data):
    mock_gemini = MagicMock()
    # Response includes <think> tags which should be removed
    mock_gemini.models.generate_content.return_value.text = "<think>Thinking hard...</think>Final recommendation."
    
    interpreter = AIInterpreter(gemini_client=mock_gemini)
    report = interpreter.explain_signal(mock_signal_result, mock_market_data)
    
    assert "Final recommendation." in report
    assert "Thinking hard..." not in report
    assert "<think>" not in report

def test_explain_signal_ollama_strips_thinking_tags(mock_signal_result, mock_market_data):
    # Gemini fails
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.side_effect = Exception("Fail")
    
    # Ollama response includes <think> tags
    mock_ollama = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "<think>Ollama is thinking...</think>Local recommendation."
    mock_ollama.chat.completions.create.return_value.choices = [mock_choice]
    
    interpreter = AIInterpreter(gemini_client=mock_gemini, ollama_client=mock_ollama)
    report = interpreter.explain_signal(mock_signal_result, mock_market_data)
    
    assert "Local recommendation." in report
    assert "Ollama is thinking..." not in report
