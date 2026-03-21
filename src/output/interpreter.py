"""
AI Narrative Interpreter: Translates technical logic traces into 
plain-language investment rationales for non-professional investors.
"""
from __future__ import annotations

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
            sections.append(f"1️⃣ 【大势背景】: {self.regime_map.get(regime_node['decision'], '中性环境')}")
            sections.append(f"   - 为什么要看这个？因为‘季节’决定了操作的容错率。在干旱季节（RICH），即使短期有反弹也容易‘渴死’。")
            
        # 2. Sentiment Context
        tactical_node = next((n for n in trace if n["step"] == "tactical_state"), None)
        if tactical_node:
            sections.append(f"2️⃣ 【群众情绪】: {self.tactical_map.get(tactical_node['decision'], '情绪平稳')}")
            sections.append(f"   - 为什么要看这个？逆向思维。别人极度害怕时，往往是风险释放最充分、筹码最便宜的时候。")

        # 3. Decision Logic (The White-box part)
        allocation_node = next((n for n in trace if n["step"] == "allocation_policy"), None)
        if allocation_node:
            sections.append(f"🎯 【决策逻辑：为什么是这样定案的？】")
            reason = allocation_node.get("reason", "综合判定")
            # Translate common architectural constraints into plain language
            if "capped" in reason or "降级" in reason or "forces" in reason:
                sections.append(f"   - 系统判定：虽然短期情绪有买入机会，但受限于第一步的【宏观压制】，我们必须‘减速慢行’。")
                sections.append(f"   - 理由：在大趋势不利时，即便群众恐慌，也要防止‘接飞刀’，所以选择小幅试探而非全力进攻。")
            else:
                sections.append(f"   - 系统判定：目前的宏观与情绪共振良好，按照标准路径执行策略。")
            
            sections.append(f"   - 详细路径：{reason}")

        # 4. Final Verification
        sections.append("────────────────────────────────────────────────────────────────")
        return "\n".join(sections)

    def print_narrative(self, trace: list[dict]):
        """Helper to print to console with styling."""
        output = self.generate(trace)
        print("\n💡 [AI 投资解释器 - 深度逻辑拆解]")
        print(output)
