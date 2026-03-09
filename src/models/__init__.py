"""Data models for QQQ signal monitor."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

import pandas as pd


class Signal(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    TRIGGERED = "TRIGGERED"
    WATCH = "WATCH"
    NO_SIGNAL = "NO_SIGNAL"


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
    # v3.0 Macro & Fundamentals
    credit_spread: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    us10y: Optional[float] = None
    fcf_yield: Optional[float] = None
    earnings_revisions_breadth: Optional[float] = None
    options_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    # options_df columns: strike, expiration, option_type ('call'/'put'),
    #   openInterest, impliedVolatility, gamma, gamma_source ('yfinance'/'bs')
    
    # v2.0 Divergence historical data (prices, vix, breadth)
    history_window: Optional[pd.DataFrame] = field(default=None, repr=False)


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
    
    # v3.0 Valuation & FCF
    valuation_bonus: int = 0
    fcf_bonus: int = 0
    
    # v2.0 Divergence additions
    divergence_bonus: int = 0
    divergence_flags: dict = field(default_factory=dict)


@dataclass
class Tier2Result:
    """Result from Tier-2 options wall engine."""

    adjustment: int  # -40 to +30
    put_wall: Optional[float]  # strike price
    call_wall: Optional[float]  # strike price
    gamma_flip: Optional[float]  # price level
    # Flags
    support_confirmed: bool
    support_broken: bool
    upside_open: bool
    gamma_positive: bool
    gamma_source: str  # 'yfinance' or 'bs' (Black-Scholes)
    # Distance metrics (pct from current price)
    put_wall_distance_pct: Optional[float]
    call_wall_distance_pct: Optional[float]


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
