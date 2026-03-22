"""
AI Narrative Interpreter: Translates technical logic traces into 
plain-language investment rationales for non-professional investors.
"""
from __future__ import annotations
from src.models import AllocationState

class NarrativeEngine:
    """Consumes logic traces and generates plain-language explanations."""

    def __init__(self):
        self.regime_map = {
            "CRISIS": "【流动性危机】目前处于极端风险窗口，钱非常贵且市场流动性枯竭。在这种‘暴风雪’天气下，保住本金是第一优先级。",
            "RICH_TIGHTENING": "【干旱季节】目前股票估值偏贵，且信用环境在收紧。这意味着市场缺乏‘便宜钱’，上涨阻力大，底色应以保守为主。",
            "TRANSITION_STRESS": "【多云转阴】宏观环境开始出现压力信号，虽然没到危机程度，但已经不是‘晴天’了，需要提高警惕。",
            "EUPHORIC": "【盛夏骄阳】目前估值极具性价比且流动性充裕，是理想的进攻窗口。",
            "NEUTRAL": "【春秋温和】宏观环境处于平衡状态，没有明显的极端利好或利空。"
        }
        
        self.tactical_map = {
            "PANIC": "市场正在‘尖叫’。大众情绪已经失控，恐慌性抛售（Panic）正在发生。这通常是捡漏好机会的前兆。",
            "CAPITULATION": "市场出现‘投降式’抛售。虽然还没到完全崩溃，但大家已经开始绝望，带血的筹码正在被扔出。",
            "PERSISTENT_STRESS": "市场正处于‘阴跌’或持续压力中。没有爆发性恐慌，但寒意刺骨，需要耐心等待底部的出现。",
            "STRESS": "体感温度降低。市场开始感到不安，波动率上升，属于正常的风险释放过程。",
            "CALM": "体感舒适。市场情绪平稳，大家都在正常交易，没有明显的恐慌迹象。"
        }

    def generate(self, trace: list[dict]) -> str:
        """Process the trace and assemble the narrative."""
        sections = []
        
        # 1. Macro Context
        regime_node = next((n for n in trace if n["step"] == "structural_regime"), None)
        if regime_node:
            regime = regime_node['decision']
            sections.append(f"1️⃣ 【大势背景】: {self.regime_map.get(regime, '中性环境')}")
            
            if regime == "RICH_TIGHTENING":
                sections.append(f"   - 为什么要看这个？因为‘季节’决定了操作的容错率。在干旱季节，即便短期有反弹也容易‘渴死’。")
            elif regime == "CRISIS":
                sections.append(f"   - 为什么要看这个？在危机模式下，传统的估值支撑往往会失效，‘活下去’比‘赚多少’更重要。")
            else:
                sections.append(f"   - 为什么要看这个？宏观环境决定了市场的‘底色’，影响我们投入资金的整体信心。")
            
        # 2. Sentiment Context
        tactical_node = next((n for n in trace if n["step"] == "tactical_state"), None)
        if tactical_node:
            sections.append(f"2️⃣ 【群众情绪】: {self.tactical_map.get(tactical_node['decision'], '情绪平稳')}")
            sections.append(f"   - 为什么要看这个？逆向思维。别人极度害怕时，往往是风险释放最充分、筹码最便宜的时候。")

        # 3. Decision Logic (The White-box part)
        allocation_node = next((n for n in trace if n["step"] == "allocation_policy"), None)
        if allocation_node:
            sections.append(f"🎯 【决策逻辑：为什么是这样定案的？】")
            
            decision = allocation_node['decision']
            reason = allocation_node.get("reason", "")
            
            # Use explicit decision-state branching instead of string heuristics
            if decision == AllocationState.RISK_CONTAINMENT.value:
                sections.append(f"   - 系统判定：触发【风险控制】模式。当前防御高于一切。")
                sections.append(f"   - 理由：由于市场出现极端恐慌或宏观崩溃信号，系统强制进入保护模式以防止本金受损。")
            elif decision == AllocationState.PAUSE_CHASING.value:
                sections.append(f"   - 系统判定：进入【暂停追高】模式。")
                sections.append(f"   - 理由：市场估值已进入过热区间，缺乏安全边际，此时不宜继续加仓。")
            elif decision == AllocationState.SLOW_ACCUMULATE.value:
                if "capped" in reason or "降级" in reason or "forces" in reason:
                    sections.append(f"   - 系统判定：虽有买入信号，但受【宏观环境压制】，必须‘减速慢行’。")
                    sections.append(f"   - 理由：在大趋势不利时，需防止‘接飞刀’，故选择小幅试探。")
                else:
                    sections.append(f"   - 系统判定：进入【小幅试探】模式。")
                    sections.append(f"   - 理由：市场开始释放机会，但尚未达到全力进攻的条件，保持耐心分批入场。")
            elif decision == AllocationState.FAST_ACCUMULATE.value:
                sections.append(f"   - 系统判定：开启【快速加仓】模式！")
                sections.append(f"   - 理由：宏观气候与战术情绪产生共振，市场正处于高性价比的‘黄金坑’。")
            else:
                sections.append(f"   - 系统判定：目前的宏观与情绪处于平衡态，执行【标准定投】策略。")
            
            sections.append(f"   - 详细路径：{reason}")

        # 4. Final Verification
        sections.append("────────────────────────────────────────────────────────────────")
        return "\n".join(sections)

    def print_decision_tree(self, trace: list[dict]):
        """Prints a visual tree of the decision execution path."""
        print("\n🌳 [AI 决策树执行路径 - 逻辑追踪]")
        
        for i, node in enumerate(trace):
            is_last = (i == len(trace) - 1)
            marker = "└──" if is_last else "├──"
            
            step_name = node["step"].replace("_", " ").upper()
            decision = node["decision"]
            reason = node.get("reason", "N/A")
            
            # Print the main node
            print(f"{marker} [{step_name}] ──▶ {decision}")
            
            # Print the evidence/reason sub-node
            indent = "    " if is_last else "│   "
            # Clean up reason for visual clarity
            clean_reason = reason.replace("Regime identified as ", "").replace("Tactical state identified as ", "")
            print(f"{indent}└── 理由: {clean_reason}")
            
        print("────────────────────────────────────────────────────────────────")

    def print_narrative(self, trace: list[dict]):
        """Helper to print to console with styling."""
        output = self.generate(trace)
        print("\n💡 [AI 投资解释器 - 深度逻辑拆解]")
        print(output)
