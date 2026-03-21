"""AI interpretation of QQQ signals using Gemini."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

import google.generativeai as genai
from dotenv import load_dotenv

from src.output.prompts import EXPERT_INTERPRETER_PROMPT

if TYPE_CHECKING:
    from src.models import MarketData, SignalResult

logger = logging.getLogger(__name__)


class GeminiInterpreter:
    """Expert interpreter using Gemini Pro to explain market signals."""

    def __init__(self, model: Any | None = None) -> None:
        """
        Initialize the interpreter.
        
        Args:
            model: Optional model instance to inject (useful for testing).
        """
        load_dotenv()
        self.model = model
        
        if self.model:
            self.enabled = True
            return

        api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.5-flash")
        
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. AI interpretation will be disabled.")
            self.enabled = False
            return

        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
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
            response = self.model.generate_content([
                EXPERT_INTERPRETER_PROMPT,
                user_prompt
            ])
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
            "tier1_breakdown": {
                "score": result.tier1.score,
                "vix": result.tier1.vix.value if hasattr(result.tier1.vix, 'value') else result.tier1.vix,
                "fear_greed": result.tier1.fear_greed.value if hasattr(result.tier1.fear_greed, 'value') else result.tier1.fear_greed,
                "ma200_deviation": result.tier1.ma200_deviation.value if hasattr(result.tier1.ma200_deviation, 'value') else result.tier1.ma200_deviation,
                "market_regime": result.tier1.market_regime,
                "descent_velocity": result.tier1.descent_velocity,
            },
            "tier2_breakdown": {
                "adjustment": result.tier2.adjustment,
                "put_wall": result.tier2.put_wall,
                "gamma_flip": result.tier2.gamma_flip,
                "support_broken": result.tier2.support_broken,
                "gamma_positive": result.tier2.gamma_positive,
            },
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
