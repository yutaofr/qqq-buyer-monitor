"""AI interpretation of QQQ signals using Gemini and local Ollama fallback."""
from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

from google import genai
from openai import OpenAI
from dotenv import load_dotenv

from src.output.prompts import EXPERT_INTERPRETER_PROMPT

if TYPE_CHECKING:
    from src.models import MarketData, SignalResult

logger = logging.getLogger(__name__)


class AIInterpreter:
    """High-availability interpreter using Gemini (Cloud) and Ollama (Local)."""

    def __init__(self, gemini_client: Any | None = None, ollama_client: Any | None = None) -> None:
        """Initialize both Cloud and Local LLM clients."""
        load_dotenv()
        self.gemini_client = gemini_client
        self.ollama_client = ollama_client
        
        # 1. Config Gemini
        self.gemini_model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_client and gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=gemini_api_key)
                logger.info("Gemini Cloud client initialized.")
            except Exception as exc:
                logger.error("Failed to init Gemini client: %s", exc)

        # 2. Config Ollama (OpenAI compatible)
        # In Docker, use host.docker.internal to reach the host's Ollama service
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434/v1")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen3.5:latest")
        
        if not self.ollama_client:
            try:
                # We use a dummy api_key as Ollama doesn't require one by default
                self.ollama_client = OpenAI(base_url=self.ollama_host, api_key="ollama")
                logger.info("Ollama Local client configured at %s", self.ollama_host)
            except Exception as exc:
                logger.error("Failed to init Ollama client: %s", exc)

    def explain_signal(self, result: SignalResult, market_data: MarketData) -> str:
        """
        Generate interpretation with Gemini -> Ollama fallback.
        """
        summary = self._prepare_summary(result, market_data)
        user_prompt = f"请解读以下量化交易信号：\n{summary}"

        # --- Attempt 1: Gemini (Cloud) ---
        if self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=[EXPERT_INTERPRETER_PROMPT, user_prompt]
                )
                if response and response.text:
                    cleaned = self._clean_response(response.text)
                    return f"{cleaned}\n\n*(解读由 Gemini 提供)*"
            except Exception as exc:
                logger.warning("Gemini Cloud failed, attempting Ollama fallback: %s", exc)

        # --- Attempt 2: Ollama (Local) ---
        if self.ollama_client:
            try:
                response = self.ollama_client.chat.completions.create(
                    model=self.ollama_model,
                    messages=[
                        {"role": "system", "content": EXPERT_INTERPRETER_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    timeout=10.0 # Don't hang CLI forever
                )
                if response.choices and response.choices[0].message.content:
                    cleaned = self._clean_response(response.choices[0].message.content)
                    return f"{cleaned}\n\n*(解读由本地模型 {self.ollama_model} 提供)*"
            except Exception as exc:
                logger.error("Ollama Local fallback also failed: %s", exc)

        return "⚠️  AI 解读服务暂不可用 (Gemini 配额用尽且本地 Ollama 未响应)。"

    def _clean_response(self, text: str) -> str:
        """Strip <think>...</think> tags and other LLM artifacts."""
        # Remove thinking tags and their content
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
