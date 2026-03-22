import pytest
from src.output.interpreter import NarrativeEngine
from src.models import AllocationState

def test_defensive_vocabulary_filter():
    """验证解释器在防御状态下过滤看多措辞"""
    interpreter = NarrativeEngine()
    
    # 模拟一个带有看多措辞的原始解释（这种解释可能由旧逻辑产生）
    raw_explanation = "当前处于黄金坑，是绝佳的抄底机会，建议积极回撤买入。"
    
    # 在 CASH_FLIGHT 状态下运行过滤
    safe_text = interpreter.apply_defensive_filter(
        raw_explanation, 
        AllocationState.CASH_FLIGHT
    )
    
    # 预期看多措辞被替换
    assert "抄底" not in safe_text
    assert "黄金坑" not in safe_text
    assert "流动性保护" in safe_text # 预期替换词
    assert "防御" in safe_text

def test_normal_vocabulary_no_filter():
    """验证解释器在正常状态下不进行强制过滤"""
    interpreter = NarrativeEngine()
    raw_explanation = "当前处于黄金坑，建议回撤买入。"
    
    # 在 FAST_ACCUMULATE 状态下不应强力过滤（除非逻辑认定真的贪婪）
    text = interpreter.apply_defensive_filter(
        raw_explanation, 
        AllocationState.FAST_ACCUMULATE
    )
    assert "黄金坑" in text
