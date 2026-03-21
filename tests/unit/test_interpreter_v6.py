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

def test_narrative_engine_risk_containment_honesty():
    # Scenario: NEUTRAL regime + PANIC tactical -> RISK_CONTAINMENT
    # Previously this misled users by saying "standard path"
    trace = [
        {
            "step": "structural_regime",
            "decision": "NEUTRAL",
            "reason": "Normal macro",
            "evidence": {"spread": 280.0, "erp": 4.5}
        },
        {
            "step": "tactical_state",
            "decision": "PANIC",
            "reason": "Market screaming",
            "evidence": {"score": 95}
        },
        {
            "step": "allocation_policy",
            "decision": "RISK_CONTAINMENT",
            "reason": "Tactical PANIC in NEUTRAL regime",
            "evidence": {"regime": "NEUTRAL", "tactical": "PANIC"}
        }
    ]
    
    engine = NarrativeEngine()
    narrative = engine.generate(trace)
    
    # Assertions for honesty
    assert "风险控制" in narrative
    assert "保护模式" in narrative
    assert "标准路径" not in narrative # CRITICAL: Should NOT say standard path anymore
    assert "为什么要看这个" in narrative
