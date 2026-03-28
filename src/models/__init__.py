"""Data models for QQQ signal monitor."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

import numpy as np
import pandas as pd

from src.models.audit import DecisionAudit as DecisionAudit
from src.models.candidate import CandidateRegistry as CandidateRegistry
from src.models.candidate import CertifiedCandidate as CertifiedCandidate
from src.models.deployment import DeploymentState

# v7.0 state models (imported here for re-export convenience)
from src.models.risk import RiskState


class Signal(StrEnum):
    STRONG_BUY = "STRONG_BUY"
    TRIGGERED = "TRIGGERED"
    WATCH = "WATCH"
    GREEDY = "GREEDY"
    NO_SIGNAL = "NO_SIGNAL"


class AllocationState(StrEnum):
    PAUSE_CHASING = "PAUSE_CHASING"
    BASE_DCA = "BASE_DCA"
    SLOW_ACCUMULATE = "SLOW_ACCUMULATE"
    FAST_ACCUMULATE = "FAST_ACCUMULATE"
    RISK_CONTAINMENT = "RISK_CONTAINMENT"
    # v6.2 Defensive States
    WATCH_DEFENSE = "WATCH_DEFENSE"
    DELEVERAGE = "DELEVERAGE"
    CASH_FLIGHT = "CASH_FLIGHT"


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
    # Legacy target field (deprecated in favor of TargetAllocationState)
    target_cash_pct: float = 0.0

    @staticmethod
    def from_env() -> CurrentPortfolioState:
        """
        v6.3.8 Defensive Input Protocol:
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

        # Legality Clipping (max(0, v))
        vals = np.array([max(0.0, raw_c), max(0.0, raw_q), max(0.0, raw_l)])
        s = np.sum(vals)

        # Safe Fallback (AC-1)
        if s <= 0 or not np.isfinite(s):
            return CurrentPortfolioState(
                current_cash_pct=1.0,
                qqq_pct=0.0,
                qld_pct=0.0,
                rolling_drawdown=raw_drawdown,
                gross_exposure_pct=0.0
            )

        # Normalization
        norm_vals = vals / s
        cash, qqq, qld = norm_vals[0], norm_vals[1], norm_vals[2]

        # Effective Exposure = QQQ% + 2 * QLD%
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
class OptionsOverlay:
    """Soft overlay derived from options structure."""

    can_reduce_tranche: bool = False
    cannot_upgrade_structural_state: bool = True
    tranche_multiplier: float = 1.0
    confidence: str = "medium"
    delay_days: int = 0


@dataclass
class MarketData:
    """Raw market data collected from all data sources."""

    date: date
    price: float  # QQQ closing price
    ma200: float  # 200-day moving average
    high_52w: float  # 52-week high
    vix: float  # VIX closing level
    fear_greed: int  # CNN Fear & Greed index (0-100)
    adv_dec_ratio: float  # NYSE Advance/Decline ratio
    pct_above_50d: float  # Fraction of NYSE stocks above 50-day MA (0-1)
    ndx_concentration: float = 0.0  # Spread between QQQ and QQEW 50d dev
    # v5.0 Performance & Flow
    days_since_52w_high: int | None = None
    short_vol_ratio: float | None = None # FINRA Institutional Proxy
    # v3.0 Macro & Fundamentals
    credit_spread: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    real_yield: float | None = None
    fcf_yield: float | None = None
    earnings_revisions_breadth: float | None = None
    pe_source: str = "yfinance"
    options_df: pd.DataFrame | None = field(default=None, repr=False)
    # v2.0 Divergence historical data (prices, vix, breadth)
    history_window: pd.DataFrame | None = field(default=None, repr=False)

    # v4.0 Adaptive Z-Scores
    vix_zscore: float = 0.0
    drawdown_zscore: float = 0.0

    # v4.0 Phase 2 Macro Gravity
    net_liquidity: float | None = None
    liquidity_roc: float | None = None
    move_index: float | None = None

    # v4.0 Phase 3: Volatility & Sentiment Extremes
    ohlcv_history: pd.DataFrame | None = field(default=None, repr=False)
    sector_rotation: float | None = None


@dataclass
class SignalDetail:
    """Single Tier-1 signal breakdown."""

    name: str
    value: float
    points: int  # 0, 10, or 20
    thresholds: tuple  # (low_threshold, high_threshold)
    triggered_half: bool
    triggered_full: bool


@dataclass
class Tier1Result:
    """Result from Tier-1 engine."""

    score: int  # 0-100
    drawdown_52w: SignalDetail
    ma200_deviation: SignalDetail
    vix: SignalDetail
    fear_greed: SignalDetail
    breadth: SignalDetail

    # Additive tactical buckets derived from the five core signals.
    stress_score: int = 0
    capitulation_score: int = 0
    persistence_score: int = 0

    # v3.0 Valuation & FCF
    valuation_bonus: int = 0
    fcf_bonus: int = 0
    short_flow_bonus: int = 0
    trailing_pe: float | None = None
    forward_pe: float | None = None
    fcf_yield: float | None = None
    real_yield: float | None = None
    pe_source: str = "yfinance"

    # NDX Internal Breadth
    ndx_concentration: float = 0.0
    concentration_penalty: int = 0

    # v2.0 Divergence additions
    divergence_bonus: int = 0
    divergence_flags: dict = field(default_factory=dict)

    # v4.0 Z-Scores
    vix_zscore: float = 0.0
    drawdown_zscore: float = 0.0

    # v4.0 Phase 2 Macro Gravity
    net_liquidity: float | None = None
    liquidity_roc: float | None = None
    move_index: float | None = None
    market_regime: str = "NORMAL"
    sector_rotation: float | None = None
    # v5.0 Analytics
    descent_velocity: str | None = None # "PANIC", "GRIND", "NORMAL"
    short_vol_rank: float | None = None


@dataclass
class Tier2Result:
    """Result from Tier-2 options wall engine."""

    adjustment: int  # -40 to +30
    put_wall: float | None  # strike price
    call_wall: float | None  # strike price
    gamma_flip: float | None  # price level
    # Flags
    support_confirmed: bool
    support_broken: bool
    upside_open: bool
    gamma_positive: bool
    gamma_source: str  # 'yfinance' or 'bs' (Black-Scholes)
    # Distance metrics (pct from current price)
    put_wall_distance_pct: float | None
    call_wall_distance_pct: float | None
    next_put_wall: float | None = None
    next_put_wall_distance_pct: float | None = None
    overlay: OptionsOverlay = field(default_factory=OptionsOverlay)
    poc: float | None = None  # v6.0 Volume POC price level


@dataclass
class SignalResult:
    """Final aggregated signal result."""

    date: date
    price: float
    signal: Signal
    final_score: int
    tier1: Tier1Result
    tier2: Tier2Result
    explanation: str
    pe_source: str = "yfinance"

    # 2026-03 v3.0 logic extensions
    erp: float | None = None

    # 2026-03 allocation-oriented output surface
    allocation_state: AllocationState = AllocationState.BASE_DCA
    daily_tranche_pct: float = 0.25
    max_total_add_pct: float = 1.0
    cooldown_days: int = 0
    required_persistence_days: int = 1
    confidence: str = "medium"
    data_quality: dict = field(default_factory=dict)
    logic_trace: list[dict] = field(default_factory=list)  # v6.1 Decision evidence chain

    # v6.3 Strategic Architecture (Ideal Target)
    target_allocation: TargetAllocationState = field(default_factory=TargetAllocationState)
    interval_beta_audit: list[dict] = field(default_factory=list)

    # v7.0 Dual-Controller fields (all optional for backward compatibility)
    risk_state: RiskState | None = None
    deployment_state: DeploymentState | None = None
    selected_candidate_id: str | None = None
    registry_version: str | None = None
    tier0_regime: str | None = None
    tier0_applied: bool = False
    raw_target_beta: float | None = None
    target_beta: float | None = None
    target_exposure_ceiling: float | None = None
    target_cash_floor: float | None = None
    qld_share_ceiling: float | None = None
    assumed_beta_before: float | None = None
    assumed_beta_after: float | None = None
    friction_blockers: list[str] = field(default_factory=list)
    estimated_turnover: float | None = None
    estimated_cost_drag: float | None = None
    should_adjust: bool | None = None
    rebalance_action: dict = field(default_factory=dict)
    deployment_action: dict = field(default_factory=dict)
    candidate_selection_audit: list[dict] = field(default_factory=list)

    # Runtime Evidence Tracing
    risk_reasons: list[dict] = field(default_factory=list)
    deployment_reasons: list[dict] = field(default_factory=list)
    feature_values: dict = field(default_factory=dict)

    # Deprecated fields (kept for db migration bridge)

    @property
    def target_cash_pct(self) -> float:
        return self.target_allocation.target_cash_pct
