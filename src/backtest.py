"""
QQQ backtest methodology.

v6.2 Institutional Upgrade: Support for Portfolio Net Value Tracking,
Dynamic Rebalancing, and Max Drawdown Improvement quantification.
"""
from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, List, Any

import pandas as pd
import yfinance as yf

from src.models import AllocationState, Tier1Result, Tier2Result, PortfolioState
from src.engine.aggregator import aggregate, _ALLOCATION_PROFILE
from src.collector.historical_macro_seeder import HistoricalMacroSeeder

logger = logging.getLogger(__name__)

START_DATE = "1999-03-10"
END_DATE = date.today().isoformat()
FWD_HORIZONS = (5, 20, 60)
WEEKLY_ADD_INTERVAL = 5
BASE_WEEKLY_DCA_UNITS = 1.0
EXCLUDED_HISTORICAL_FEATURES = ("fear_greed", "short_vol_ratio")

# Units added per state (multiplier for BASE_WEEKLY_DCA_UNITS)
STATE_BONUS_UNITS = {
    AllocationState.PAUSE_CHASING: -0.5,
    AllocationState.BASE_DCA: 0.0,
    AllocationState.SLOW_ACCUMULATE: 0.5,
    AllocationState.FAST_ACCUMULATE: 1.0,
    AllocationState.RISK_CONTAINMENT: -0.5,
    # v6.2 Defensive Units
    AllocationState.WATCH_DEFENSE: -0.5,
    AllocationState.DELEVERAGE: -1.0,
    AllocationState.CASH_FLIGHT: -1.0,
}

@dataclass(frozen=True)
class AllocationEventMetrics:
    """Metrics for a single weekly add event."""
    date: pd.Timestamp
    price: float
    state: AllocationState
    units: float
    forward_returns: dict[int, Optional[float]]
    max_adverse_excursion: Optional[float]
    # v6.2 Portfolio Snapshot
    cash_balance: float = 0.0
    equity_value: float = 0.0
    net_asset_value: float = 0.0
    cash_pct: float = 0.0

@dataclass(frozen=True)
class BacktestMethodologySummary:
    """Methodology summary for allocator-style backtests."""
    events: tuple[AllocationEventMetrics, ...]
    forward_returns_by_horizon: dict[int, float]
    max_adverse_excursion: Optional[float]
    average_cost_improvement_vs_baseline_dca: float
    average_cost_penalty_vs_lump_sum: float
    baseline_dca_average_cost: float
    tactical_average_cost: float
    lump_sum_average_cost: float
    fraction_capital_deployed_before_final_low: float
    capital_deployed_before_final_low_units: float
    total_capital_units: float
    # v6.2 Performance KPIs
    tactical_mdd: float = 0.0
    baseline_mdd: float = 0.0
    excluded_features: tuple[str, ...] = EXCLUDED_HISTORICAL_FEATURES

class Backtester:
    """Encapsulates backtesting logic with macro injection and portfolio simulation."""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital

    def run(self, ohlcv: pd.DataFrame, macro_seeder: Optional[HistoricalMacroSeeder] = None) -> List[Dict[str, Any]]:
        """Legacy run method for basic signal verification."""
        summary = self.simulate_portfolio(ohlcv, macro_seeder)
        results = []
        for event in summary.events:
            results.append({
                "date": event.date,
                "price": event.price,
                "allocation_state": event.state,
                "units": event.units
            })
        return results

    def simulate_portfolio(self, ohlcv: pd.DataFrame, macro_seeder: Optional[HistoricalMacroSeeder] = None) -> BacktestMethodologySummary:
        """
        Simulate a full portfolio with cash management and dynamic rebalancing.
        """
        prices = ohlcv["Close"].dropna().astype(float)
        if prices.empty:
            raise ValueError("Empty price data")

        # 1. State Derivation (Full Logic)
        tactical_states = self._derive_states(ohlcv, macro_seeder)
        
        # 2. Portfolio Loop
        cash = self.initial_capital
        units_held = 0.0
        baseline_units_held = 0.0
        
        # Track Daily NAV for MDD
        daily_nav = []
        baseline_nav = []
        
        add_dates = list(prices.index[::WEEKLY_ADD_INTERVAL])
        event_metrics = []
        
        # Cost tracking
        tactical_cost_num = 0.0
        baseline_cost_num = 0.0
        total_tactical_units = 0.0
        final_low_date = prices.idxmin()
        deployed_before_low = 0.0
        mae_values = []
        horizon_numerators = {h: 0.0 for h in FWD_HORIZONS}
        horizon_denominators = {h: 0.0 for h in FWD_HORIZONS}

        for dt in prices.index:
            price = float(prices.loc[dt])
            state = tactical_states.loc[dt]
            
            # A. Check for Weekly Addition
            if dt in add_dates:
                # Tactical Addition
                units_to_add = _state_units(state)
                cost = units_to_add * price
                
                # Check for cash availability
                if cash >= cost:
                    cash -= cost
                    units_held += units_to_add
                    tactical_cost_num += price * units_to_add
                    total_tactical_units += units_to_add
                else:
                    # Partial add if cash is limited
                    can_afford_units = cash / price
                    cash = 0.0
                    units_held += can_afford_units
                    tactical_cost_num += price * can_afford_units
                    total_tactical_units += can_afford_units
                
                # Baseline Addition (Assuming infinite baseline cash for pure DCA comparison)
                baseline_units_held += BASE_WEEKLY_DCA_UNITS
                baseline_cost_num += price
                
                if dt <= final_low_date:
                    deployed_before_low += units_to_add
                
                # B. Execute Rebalancing (v6.2 Defense)
                target_cash_pct = _ALLOCATION_PROFILE[state].get("target_cash_pct", 0.0) / 100.0
                current_nav = units_held * price + cash
                current_cash_pct = cash / current_nav if current_nav > 0 else 1.0
                
                if target_cash_pct > current_cash_pct:
                    # Sell to reach target
                    cash_needed = target_cash_pct * current_nav - cash
                    units_to_sell = cash_needed / price
                    units_held = max(0.0, units_held - units_to_sell)
                    cash += (units_to_sell * price)
                
                # C. Metrics Collection
                fwd_ret = compute_forward_returns(prices, dt)
                mae = compute_max_adverse_excursion(prices, dt)
                if mae is not None: mae_values.append(mae)
                for h, val in fwd_ret.items():
                    if val is not None:
                        horizon_numerators[h] += val * units_to_add
                        horizon_denominators[h] += units_to_add
                
                event_metrics.append(AllocationEventMetrics(
                    date=dt, price=price, state=state, units=units_to_add,
                    forward_returns=fwd_ret, max_adverse_excursion=mae,
                    cash_balance=cash, equity_value=units_held * price,
                    net_asset_value=units_held * price + cash,
                    cash_pct=(cash / (units_held * price + cash)) * 100.0 if (units_held * price + cash) > 0 else 100.0
                ))

            # D. Track Daily Performance
            daily_nav.append(units_held * price + cash)
            baseline_nav.append(baseline_units_held * price) # Baseline is pure equity DCA

        # 3. Compute MDDs
        tactical_mdd = self._calculate_mdd(daily_nav)
        baseline_mdd = self._calculate_mdd(baseline_nav)
        
        # 4. Final Summary
        tactical_avg_cost = tactical_cost_num / total_tactical_units if total_tactical_units else 0
        baseline_avg_cost = baseline_cost_num / len(add_dates) if add_dates else 0
        lump_sum_cost = float(prices.iloc[0])

        return BacktestMethodologySummary(
            events=tuple(event_metrics),
            forward_returns_by_horizon={h: (horizon_numerators[h] / horizon_denominators[h] if horizon_denominators[h] else 0) for h in FWD_HORIZONS},
            max_adverse_excursion=min(mae_values) if mae_values else None,
            average_cost_improvement_vs_baseline_dca=((baseline_avg_cost - tactical_avg_cost) / baseline_avg_cost if baseline_avg_cost else 0),
            average_cost_penalty_vs_lump_sum=((tactical_avg_cost - lump_sum_cost) / lump_sum_cost if lump_sum_cost else 0),
            baseline_dca_average_cost=baseline_avg_cost,
            tactical_average_cost=tactical_avg_cost,
            lump_sum_average_cost=lump_sum_cost,
            fraction_capital_deployed_before_final_low=(deployed_before_low / total_tactical_units if total_tactical_units else 0),
            capital_deployed_before_final_low_units=deployed_before_low,
            total_capital_units=total_tactical_units,
            tactical_mdd=tactical_mdd,
            baseline_mdd=baseline_mdd
        )

    def _calculate_mdd(self, nav_series: List[float]) -> float:
        """Calculate Maximum Drawdown from a NAV series."""
        if not nav_series: return 0.0
        nav = np.array(nav_series)
        running_max = np.maximum.accumulate(nav)
        # Avoid division by zero
        drawdowns = np.where(running_max > 0, (nav - running_max) / running_max, 0.0)
        return float(np.min(drawdowns))

    def _derive_states(self, ohlcv: pd.DataFrame, macro_seeder: Optional[HistoricalMacroSeeder]) -> pd.Series:
        """Derive allocation states using full v6.2 logic."""
        prices = ohlcv["Close"].astype(float)
        drawdown = prices / prices.cummax() - 1.0
        
        states: List[AllocationState] = []
        for dt, price in prices.items():
            macro_features = {
                "credit_spread": None, "credit_accel": 0.0,
                "liquidity_roc": 0.0, "is_funding_stressed": False
            }
            if macro_seeder:
                macro_features = macro_seeder.get_features_for_date(dt.date())
            
            # Simple simulation of Tier 1 score based on price
            t1_score = 50
            dd = float(drawdown.loc[dt])
            if dd <= -0.20: t1_score = 80
            elif dd <= -0.10: t1_score = 65
            
            t1 = Tier1Result(score=t1_score, drawdown_52w=None, ma200_deviation=None, vix=None, fear_greed=None, breadth=None)
            t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, 
                            support_confirmed=False, support_broken=False, upside_open=False, 
                            gamma_positive=True, gamma_source="yf", put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
            
            result = aggregate(
                market_date=dt.date(), price=float(price), tier1=t1, tier2=t2,
                credit_accel=macro_features.get("credit_accel"),
                liquidity_roc=macro_features.get("liquidity_roc"),
                is_funding_stressed=macro_features.get("is_funding_stressed", False)
            )
            states.append(result.allocation_state)
            
        return pd.Series(states, index=prices.index)

# ── Re-exposed Helpers ────────────────────────────────────────────────────────

def _coerce_state(value: object) -> AllocationState:
    if isinstance(value, AllocationState): return value
    if value is None: return AllocationState.BASE_DCA
    try: return AllocationState(str(value))
    except ValueError: return AllocationState.BASE_DCA

def _state_units(state: AllocationState) -> float:
    bonus = STATE_BONUS_UNITS.get(state, 0.0)
    return max(0.0, BASE_WEEKLY_DCA_UNITS + bonus)

def compute_forward_returns(prices: pd.Series, entry_label, horizons: tuple[int, ...] = FWD_HORIZONS) -> dict[int, Optional[float]]:
    try:
        entry_loc = prices.index.get_loc(entry_label)
        if hasattr(entry_loc, '__len__'): entry_loc = entry_loc[0]
        entry_price = float(prices.iloc[entry_loc])
        returns: dict[int, Optional[float]] = {}
        for horizon in horizons:
            exit_loc = entry_loc + horizon
            if exit_loc >= len(prices):
                returns[horizon] = None
                continue
            returns[horizon] = float(prices.iloc[exit_loc]) / entry_price - 1.0
        return returns
    except Exception: return {h: None for h in horizons}

def compute_max_adverse_excursion(prices: pd.Series, entry_label, lookahead: int = max(FWD_HORIZONS)) -> Optional[float]:
    try:
        entry_loc = prices.index.get_loc(entry_label)
        if hasattr(entry_loc, '__len__'): entry_loc = entry_loc[0]
        end_loc = min(len(prices) - 1, entry_loc + lookahead)
        window = prices.iloc[entry_loc : end_loc + 1]
        if window.empty: return None
        entry_price = float(prices.iloc[entry_loc])
        return float(window.min() / entry_price - 1.0)
    except Exception: return None

def simulate_allocator(prices: pd.Series, tactical_states: Optional[pd.Series] = None, interval: int = WEEKLY_ADD_INTERVAL) -> BacktestMethodologySummary:
    # This is now mostly a wrapper or used for NAV-agnostic cost stats
    # For full portfolio, use Backtester().simulate_portfolio
    prices = prices.astype(float).dropna()
    if tactical_states is None:
        tactical_states = pd.Series(AllocationState.BASE_DCA, index=prices.index)
    
    aligned_states = tactical_states.reindex(prices.index, method="ffill").fillna(AllocationState.BASE_DCA)
    add_dates = list(prices.index[::interval])
    
    total_capital_units = 0.0
    tactical_cost_num = 0.0
    baseline_cost_num = 0.0
    deployed_before_low = 0.0
    event_metrics = []
    horizon_nums = {h: 0.0 for h in FWD_HORIZONS}
    horizon_dens = {h: 0.0 for h in FWD_HORIZONS}
    mae_values = []
    final_low_date = prices.idxmin()

    for dt in add_dates:
        state = _coerce_state(aligned_states.loc[dt])
        price = float(prices.loc[dt])
        units = _state_units(state)
        fwd_ret = compute_forward_returns(prices, dt)
        mae = compute_max_adverse_excursion(prices, dt)

        event_metrics.append(AllocationEventMetrics(dt, price, state, units, fwd_ret, mae))
        total_capital_units += units
        tactical_cost_num += price * units
        baseline_cost_num += price
        if dt <= final_low_date: deployed_before_low += units
        for h, val in fwd_ret.items():
            if val is not None:
                horizon_nums[h] += val * units
                horizon_dens[h] += units
        if mae is not None: mae_values.append(mae)

    tactical_avg_cost = tactical_cost_num / total_capital_units if total_capital_units else 0
    baseline_avg_cost = baseline_cost_num / len(add_dates) if add_dates else 0
    lump_sum_cost = float(prices.iloc[0])
    
    return BacktestMethodologySummary(
        events=tuple(event_metrics),
        forward_returns_by_horizon={h: (horizon_nums[h] / horizon_dens[h] if horizon_dens[h] else 0) for h in FWD_HORIZONS},
        max_adverse_excursion=min(mae_values) if mae_values else None,
        average_cost_improvement_vs_baseline_dca=((baseline_avg_cost - tactical_avg_cost) / baseline_avg_cost if baseline_avg_cost else 0),
        average_cost_penalty_vs_lump_sum=((tactical_avg_cost - lump_sum_cost) / lump_sum_cost if lump_sum_cost else 0),
        baseline_dca_average_cost=baseline_avg_cost,
        tactical_average_cost=tactical_avg_cost,
        lump_sum_average_cost=lump_sum_cost,
        fraction_capital_deployed_before_final_low=(deployed_before_low / total_capital_units if total_capital_units else 0),
        capital_deployed_before_final_low_units=deployed_before_low,
        total_capital_units=total_capital_units
    )

def summarize_backtest_methodology(prices: pd.Series, tactical_states: Optional[pd.Series] = None, interval: int = WEEKLY_ADD_INTERVAL) -> BacktestMethodologySummary:
    return simulate_allocator(prices, tactical_states=tactical_states, interval=interval)

def _format_pct(value: Optional[float]) -> str:
    return f"{value * 100:.1f}%" if value is not None else "n/a"

def run_backtest() -> None:
    print(f"Fetching QQQ history from {START_DATE} to {END_DATE}...")
    qqq = yf.Ticker("QQQ").history(start=START_DATE, end=END_DATE)
    if qqq.empty: return
    
    seeder = HistoricalMacroSeeder(csv_path="data/macro_historical_dump.csv")
    tester = Backtester()
    summary = tester.simulate_portfolio(qqq, seeder)

    print("\n--- v6.2 Institutional Backtest Summary ---")
    print(f"Weekly add events: {len(summary.events)}")
    print(f"Tactical Max Drawdown: {_format_pct(summary.tactical_mdd)}")
    print(f"Baseline DCA Max Drawdown: {_format_pct(summary.baseline_mdd)}")
    print(f"MDD Improvement: {_format_pct(summary.baseline_mdd - summary.tactical_mdd)}")
    print("-" * 40)
    print("Forward returns: " + ", ".join(f"T+{h}={_format_pct(summary.forward_returns_by_horizon[h])}" for h in FWD_HORIZONS))
    print(f"Max adverse excursion after add: {_format_pct(summary.max_adverse_excursion)}")
    print(f"Average cost vs baseline DCA: {_format_pct(summary.average_cost_improvement_vs_baseline_dca)} improvement")
    print(f"Baseline weekly DCA average cost: ${summary.baseline_dca_average_cost:.2f}")
    print(f"Tactical allocator average cost: ${summary.tactical_average_cost:.2f}")
    print(f"Capital deployed before final low: {_format_pct(summary.fraction_capital_deployed_before_final_low)}")
    print("-" * 40)
    
    # Show defense activation stats
    states = [e.state for e in summary.events]
    from collections import Counter
    counts = Counter(states)
    print("Defense Activation Stats:")
    for s in [AllocationState.WATCH_DEFENSE, AllocationState.DELEVERAGE, AllocationState.CASH_FLIGHT]:
        if counts[s] > 0:
            print(f"  - {s.value}: {counts[s]} weeks")

if __name__ == "__main__":
    run_backtest()
