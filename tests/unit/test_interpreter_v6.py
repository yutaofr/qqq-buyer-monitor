import pytest
from src.output.interpreter import NarrativeEngine

def test_narrative_engine_summarizes_trace():
    # Mock a logic trace from aggregate engine
    trace = [
        {
            "step": "structural_regime",
            "decision": "RICH_TIGHTENING",
            "reason": "Regime identified as RICH_TIGHTENING",
            "evidence": {"spread": 320.0, "erp": 3.5}
        },
        {
            "step": "tactical_state",
            "decision": "CAPITULATION",
            "reason": "Tactical state identified as CAPITULATION",
            "evidence": {"score": 90}
        },
        {
            "step": "allocation_policy",
            "decision": "SLOW_ACCUMULATE",
            "reason": "Tactical CAPITULATION capped by RICH_TIGHTENING regime",
            "evidence": {"regime": "RICH_TIGHTENING", "tactical": "CAPITULATION"}
        }
    ]
    
    engine = NarrativeEngine()
    narrative = engine.generate(trace)
    
    # Assertions: check for key plain-language sections
    assert "大势背景" in narrative
    assert "群众情绪" in narrative
    assert "决策逻辑" in narrative
    # Check if the explanation includes the 'Why' and the 'How'
    assert "为什么" in narrative
    assert "减速" in narrative or "保守" in narrative # Should reflect RICH_TIGHTENING constraint
