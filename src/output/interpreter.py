"""
Narrative engine to generate human-readable explanations and decision logic traces.
"""
from __future__ import annotations

import logging
import re
from typing import Any, List, Dict
from src.models import AllocationState

logger = logging.getLogger(__name__)

class NarrativeEngine:
    """Generates narrative interpretation of signal logic."""

    def __init__(self) -> None:
        self.defensive_mapping = {
            "抄底": "流动性保护下的防御性观望",
            "黄金坑": "估值修复的不确定区间",
            "回撤买入": "风险敞口收缩",
            "绝佳机会": "防御性窗口",
            "积极": "谨慎",
            "加仓": "存量调整",
        }

    def print_narrative(self, logic_trace: List[Dict[str, Any]]) -> None:
        """Prints a human-readable interpretation of the decision process."""
        print("\n--- 决策逻辑深度解读 (Narrative) ---")
        for step in logic_trace:
            name = step.get("step", "Unknown")
            decision = step.get("decision", "N/A")
            reason = step.get("reason", "")
            print(f"[{name:18s}] -> {decision:18s} | {reason}")

    def print_decision_tree(self, logic_trace: List[Dict[str, Any]]) -> None:
        """Prints the logic flow as a symbolic tree."""
        print("\n--- 逻辑决策链 (Decision Tree) ---")
        indent = ""
        for i, step in enumerate(logic_trace):
            prefix = "└── " if i == len(logic_trace) - 1 else "├── "
            decision = step.get("decision", "")
            print(f"{indent}{prefix}{decision}")
            indent += "    "

    def apply_defensive_filter(self, text: str, state: AllocationState) -> str:
        """
        v6.2 Narrative Guardrail: Filters out bullish vocabulary in defensive states.
        """
        if state not in (
            AllocationState.WATCH_DEFENSE, 
            AllocationState.DELEVERAGE, 
            AllocationState.CASH_FLIGHT
        ):
            return text
            
        filtered_text = text
        for bullish, defensive in self.defensive_mapping.items():
            # Use regex to replace while maintaining some sentence flow
            filtered_text = re.sub(bullish, defensive, filtered_text)
            
        if filtered_text != text:
            logger.info("Narrative Guardrail active: filtered bullish biased vocabulary.")
            
        return filtered_text

    def format_explanation(self, explanation: str, state: AllocationState) -> str:
        """Entry point for formatting the final explanation with guardrails."""
        return self.apply_defensive_filter(explanation, state)
