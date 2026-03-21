"""AI interpretation of QQQ signals using Gemini."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from google import genai
from dotenv import load_dotenv

from src.output.prompts import EXPERT_INTERPRETER_PROMPT

if TYPE_CHECKING:
    from src.models import MarketData, SignalResult

logger = logging.getLogger(__name__)


class GeminiInterpreter:
    """Expert interpreter using Gemini Pro to explain market signals."""

    def __init__(self, client: Any | None = None) -> None:
        """
        Initialize the interpreter.
        
        Args:
            client: Optional client instance to inject (useful for testing).
        """
        load_dotenv()
        self.client = client
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
        
        if self.client:
            self.enabled = True
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. AI interpretation will be disabled.")
            self.enabled = False
            return

        try:
            self.client = genai.Client(api_key=api_key)
            self.enabled = True
            logger.info("GeminiInterpreter initialized with model: %s", self.model_name)
        except Exception as exc:
            logger.error("Failed to initialize Gemini: %s", exc)
            self.enabled = False

    def explain_signal(self, result: SignalResult, market_data: MarketData) -> str:
        """Generate a Chinese explanation for the given signal and market state."""
        if not self.enabled:
            return "AI interpretation is disabled (check API key)."

        # Prepare a structured summary for the LLM
        signal_summary = self._prepare_summary(result, market_data)
        user_prompt = f"请解读以下量化交易信号：\n{signal_summary}"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    EXPERT_INTERPRETER_PROMPT,
                    user_prompt
                ]
            )
            return response.text
        except Exception as exc:
            logger.error("Gemini generation failed: %s", exc)
            return f"生成解读时发生错误: {exc}"

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
