"""Data models for QQQ signal monitor (v11 Bayesian Convergence)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

import numpy as np


@dataclass(frozen=True)
class CurrentPortfolioState:
    """Current asset allocation and leverage auditing (Reality)."""
    current_cash_pct: float = 1.0
    qqq_pct: float = 0.0
    qld_pct: float = 0.0
    rolling_drawdown: float | None = None
    leverage_ratio: float = 1.0
    gross_exposure_pct: float = 0.0
    net_exposure_pct: float = 0.0
    core_equity_pct: float = 0.0
    tactical_equity_pct: float = 0.0
    target_cash_pct: float = 0.0

    @staticmethod
    def from_env() -> CurrentPortfolioState:
        """
        Parses CASH_LEVEL, QQQ_LEVEL, QLD_LEVEL from env with normalization.
        """
        def _env_float(name: str, default: float | None = None) -> float | None:
            raw = os.environ.get(name)
            if raw is None:
                return default
            try:
                return float(raw)
            except (ValueError, TypeError):
                return default

        try:
            raw_c = float(os.environ.get("CASH_LEVEL", "0.0"))
            raw_q = float(os.environ.get("QQQ_LEVEL", "0.0"))
            raw_l = float(os.environ.get("QLD_LEVEL", "0.0"))
        except (ValueError, TypeError):
            raw_c, raw_q, raw_l = 0.0, 0.0, 0.0
        raw_drawdown = _env_float("PORTFOLIO_ROLLING_DRAWDOWN", None)

        vals = np.array([max(0.0, raw_c), max(0.0, raw_q), max(0.0, raw_l)])
        s = np.sum(vals)

        if s <= 0 or not np.isfinite(s):
            return CurrentPortfolioState(
                current_cash_pct=1.0,
                qqq_pct=0.0,
                qld_pct=0.0,
                rolling_drawdown=raw_drawdown,
                gross_exposure_pct=0.0
            )

        norm_vals = vals / s
        cash, qqq, qld = norm_vals[0], norm_vals[1], norm_vals[2]
        exposure = qqq + 2.0 * qld

        return CurrentPortfolioState(
            current_cash_pct=float(cash),
            qqq_pct=float(qqq),
            qld_pct=float(qld),
            rolling_drawdown=raw_drawdown,
            gross_exposure_pct=float(exposure),
            net_exposure_pct=float(exposure),
            leverage_ratio=float(exposure) if exposure > 1.0 else 1.0
        )

# Backward Compatibility Alias
PortfolioState = CurrentPortfolioState


@dataclass(frozen=True)
class TargetAllocationState:
    """Ideal asset allocation model (Target)."""
    target_cash_pct: float = 0.10
    target_qqq_pct: float = 0.90
    target_qld_pct: float = 0.0
    target_beta: float = 0.90

    def to_dict(self) -> dict:
        return {
            "target_cash_pct": self.target_cash_pct,
            "target_qqq_pct": self.target_qqq_pct,
            "target_qld_pct": self.target_qld_pct,
            "target_beta": self.target_beta
        }

    @staticmethod
    def from_dict(data: dict) -> TargetAllocationState:
        return TargetAllocationState(
            target_cash_pct=data.get("target_cash_pct", 0.10),
            target_qqq_pct=data.get("target_qqq_pct", 0.90),
            target_qld_pct=data.get("target_qld_pct", 0.0),
            target_beta=data.get("target_beta", 0.90)
        )


@dataclass(frozen=True)
class SignalResult:
    """Final v11 probabilistic signal result."""
    date: date
    price: float
    target_beta: float
    probabilities: dict[str, float]
    entropy: float
    stable_regime: str
    target_allocation: TargetAllocationState
    logic_trace: list[dict]
    explanation: str
    metadata: dict = field(default_factory=dict)
