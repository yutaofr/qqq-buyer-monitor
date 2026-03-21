"""AI interpretation of QQQ signals using local Ollama."""
from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

import httpx
from dotenv import load_dotenv

from src.output.prompts import EXPERT_INTERPRETER_PROMPT

if TYPE_CHECKING:
    from src.models import MarketData, SignalResult

logger = logging.getLogger(__name__)


class AIInterpreter:
    """Expert interpreter using local Ollama to explain market signals."""

    def __init__(self) -> None:
        """Initialize local Ollama configuration."""
        load_dotenv()
        
        # In Docker, use host.docker.internal to reach the host's Ollama service
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen3.5:0.8b")
        logger.info("AIInterpreter (Local Only) configured with model: %s", self.ollama_model)

    def explain_signal(self, result: SignalResult, market_data: MarketData) -> str:
        """
        Generate interpretation using local Ollama API.
        """
        summary = self._prepare_summary(result, market_data)
        user_prompt = f"请解读以下量化交易信号：\n{summary}"

        try:
            # Reconstruct the host for the direct API
            base_url = self.ollama_host.rstrip("/")
            payload = {
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": EXPERT_INTERPRETER_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            # High timeout for local inference on potential 9B+ models or non-GPU hardware
            with httpx.Client(timeout=90.0) as client:
                resp = client.post(f"{base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if content:
                    cleaned = self._clean_response(content)
                    return f"{cleaned}\n\n*(解读由本地模型 {self.ollama_model} 提供)*"
        except Exception as exc:
            logger.error("Ollama Local inference failed: %s", exc)
            return (
                f"⚠️  AI 解读服务暂不可用 (本地 Ollama 响应失败: {exc})。\n"
                f"💡 提示: 请检查宿主机 Ollama 是否已运行并监听 0.0.0.0 (参考 README 常见网络问题)。"
            )

        return "⚠️  AI 解读服务未返回有效内容。"

    def _clean_response(self, text: str) -> str:
        """Strip <think>...</think> tags and other LLM artifacts."""
        # Remove thinking tags and their content (non-greedy match, dotall for multi-line)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return text.strip()

    def _prepare_summary(self, result: SignalResult, market_data: MarketData) -> dict[str, Any]:
        """Extract key metrics into a flat structure for the LLM."""
        return {
            "date": str(result.date),
            "final_signal": result.signal.value,
            "final_score": result.final_score,
            "tier1_breakdown": result.tier1.to_dict(),
            "tier2_breakdown": result.tier2.to_dict(),
            "macro_context": {
                "credit_spread": market_data.credit_spread,
                "net_liquidity": market_data.net_liquidity,
                "real_yield": market_data.real_yield,
            },
            "allocation": {
                "state": result.allocation_state.value,
                "tranche_pct": result.daily_tranche_pct,
            }
        }
