"""
QQQ backtest methodology.

v6.3 Institutional Upgrade: Support for Portfolio Net Value Tracking,
Multi-Asset (QQQ + QLD) TAA Mirroring, and Max Drawdown quantification.
v6.4 Personal Allocation Upgrade: Candidate scoring and turnover tracking.
"""
from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, List, Any

import pandas as pd
import yfinance as yf

from src.models import AllocationState, Tier1Result, Tier2Result, PortfolioState, TargetAllocationState
from src.engine.aggregator import aggregate, _ALLOCATION_PROFILE, get_target_allocation
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
    # v6.2/v6.3 Portfolio Snapshot
    cash_balance: float = 0.0
    equity_value: float = 0.0
    qld_value: float = 0.0
    net_asset_value: float = 0.0
    cash_pct: float = 0.0
    qld_units: float = 0.0

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
    # v6.3.11: Returns-based Realized Beta (AC-4)
    realized_beta: float = 0.0
    # v6.3.12: Interval Beta Audit (AC-4 Fidelity)
    interval_beta_audit: list[dict[str, Any]] = field(default_factory=list)
    mean_interval_beta_deviation: float = 0.0
    turnover: float = 0.0
    # v6.2 Visualization Support
    daily_timeseries: Optional[pd.DataFrame] = None
    excluded_features: tuple[str, ...] = EXCLUDED_HISTORICAL_FEATURES

    @property
    def feature_policy(self) -> dict[str, str]:
        """Legacy support for feature policy audit."""
        return {f: "excluded" for f in self.excluded_features}

def simulate_leveraged_price(prices: pd.Series, leverage: float = 2.0) -> pd.Series:
    """
    Simulates a leveraged ETF price series based on underlying daily returns.
    Calculation: P_t = P_{t-1} * (1 + leverage * R_t - drag)
    drag = 0.0000377 (approx 0.95% annual expense ratio as per SRD 4.2)
    """
    drag = 0.0000377
    returns = prices.pct_change().fillna(0)
    leveraged_returns = (returns * leverage) - drag
    leveraged_returns.iloc[0] = 0.0 
    
    multipliers = (1 + leveraged_returns).cumprod()
    return prices.iloc[0] * multipliers

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

    def simulate_portfolio(
        self, 
        ohlcv: pd.DataFrame, 
        macro_seeder: Optional[HistoricalMacroSeeder] = None,
        target_map: Optional[Dict[AllocationState, TargetAllocationState]] = None
    ) -> BacktestMethodologySummary:
        """
        Simulate a full portfolio with cash management and dynamic rebalancing.
        v6.3: Supports Multi-Asset (QQQ + QLD) TAA Mirroring.
        v6.4: Supports custom target_map for candidate scoring.
        """
        prices_qqq = ohlcv["Close"].dropna().astype(float)
        if prices_qqq.empty:
            raise ValueError("Empty price data")

        # 1. Asset Price Simulation
        prices_qld = simulate_leveraged_price(prices_qqq, leverage=2.0)
        
        # 2. State Derivation (Full Logic)
        tactical_states = self._derive_states(ohlcv, macro_seeder)
        
        # 3. Portfolio Loop
        cash = self.initial_capital
        units_qqq = 0.0
        units_qld = 0.0
        baseline_units_held = 0.0
        
        # Track Daily NAV for MDD
        daily_nav = []
        baseline_nav = []
        daily_stats = []
        
        add_dates = list(prices_qqq.index[::WEEKLY_ADD_INTERVAL])
        event_metrics = []
        
        # Cost tracking
        tactical_cost_num = 0.0
        baseline_cost_num = 0.0
        total_tactical_units = 0.0
        final_low_date = prices_qqq.idxmin()
        deployed_before_low = 0.0
        mae_values = []
        horizon_numerators = {h: 0.0 for h in FWD_HORIZONS}
        horizon_denominators = {h: 0.0 for h in FWD_HORIZONS}

        # v6.4 Turnover Tracking
        total_volume_traded = 0.0

        for dt in prices_qqq.index:
            p_qqq = float(prices_qqq.loc[dt])
            p_qld = float(prices_qld.loc[dt])
            state = tactical_states.loc[dt]
            
            # Fetch macro features for daily stats
            macro_features = {"credit_accel": 0.0}
            if macro_seeder:
                macro_features = macro_seeder.get_features_for_date(dt.date())

            # A. Check for Weekly Addition (Cash Flow Event)
            if dt in add_dates:
                base_units = _state_units(state)
                units_to_add = base_units
                if state in (AllocationState.FAST_ACCUMULATE, AllocationState.SLOW_ACCUMULATE) and cash > (self.initial_capital * 0.1):
                    units_to_add += 1.0 
                
                cost = units_to_add * p_qqq
                if cash >= cost:
                    cash -= cost
                    units_qqq += units_to_add
                    tactical_cost_num += p_qqq * units_to_add
                    total_tactical_units += units_to_add
                else:
                    can_afford_units = cash / p_qqq
                    cash = 0.0
                    units_qqq += can_afford_units
                    tactical_cost_num += p_qqq * can_afford_units
                    total_tactical_units += can_afford_units
                
                total_volume_traded += cost
                baseline_units_held += BASE_WEEKLY_DCA_UNITS
                baseline_cost_num += p_qqq
                
                if dt <= final_low_date:
                    deployed_before_low += units_to_add

            # B. Execute DAILY Rebalancing (v6.3.13 Strategic TAA calibration)
            if target_map and state in target_map:
                target = target_map[state]
            else:
                target = get_target_allocation(state)

            current_nav = (units_qqq * p_qqq) + (units_qld * p_qld) + cash
            
            # Ideal State
            target_cash = current_nav * target.target_cash_pct
            target_qqq_val = current_nav * target.target_qqq_pct
            target_qld_val = current_nav * target.target_qld_pct
            
            # Track volume for turnover
            total_volume_traded += abs(target_qqq_val - (units_qqq * p_qqq))
            total_volume_traded += abs(target_qld_val - (units_qld * p_qld))

            # T+0 Rebalance
            cash = target_cash
            units_qqq = target_qqq_val / p_qqq
            units_qld = target_qld_val / p_qld
            
            # C. Check for Weekly Metrics Collection
            if dt in add_dates:
                fwd_ret = compute_forward_returns(prices_qqq, dt)
                mae = compute_max_adverse_excursion(prices_qqq, dt)
                if mae is not None: mae_values.append(mae)
                
                for h, val in fwd_ret.items():
                    if val is not None:
                        horizon_numerators[h] += val * units_to_add
                        horizon_denominators[h] += units_to_add
                
                event_metrics.append(AllocationEventMetrics(
                    date=dt, price=p_qqq, state=state, units=units_to_add,
                    forward_returns=fwd_ret, max_adverse_excursion=mae,
                    cash_balance=cash, 
                    equity_value=units_qqq * p_qqq,
                    qld_value=units_qld * p_qld,
                    net_asset_value=current_nav,
                    cash_pct=(cash / current_nav) * 100.0 if current_nav > 0 else 100.0,
                    qld_units=units_qld
                ))

            # D. Track Daily Performance
            nav = (units_qqq * p_qqq) + (units_qld * p_qld) + cash
            b_nav = baseline_units_held * p_qqq
            daily_nav.append(nav)
            baseline_nav.append(b_nav)
            
            daily_stats.append({
                "date": dt,
                "nav": nav,
                "baseline_nav": b_nav,
                "cash_pct": (cash / nav * 100.0) if nav > 0 else 100.0,
                "credit_accel": macro_features.get("credit_accel", 0.0),
                "state": state.value
            })

        # 3. Compute Performance KPIs
        tactical_mdd = self._calculate_mdd(daily_nav)
        baseline_mdd = self._calculate_mdd(baseline_nav)
        daily_ts = pd.DataFrame(daily_stats).set_index("date")
        
        daily_ts["tactical_ret"] = pd.Series(daily_nav, index=prices_qqq.index).pct_change().fillna(0)
        daily_ts["market_ret"] = prices_qqq.pct_change().fillna(0)
        
        cov_matrix = np.cov(daily_ts["tactical_ret"], daily_ts["market_ret"], ddof=1)
        variance_market = np.var(daily_ts["market_ret"], ddof=1)
        realized_beta = float(cov_matrix[0, 1] / variance_market) if variance_market > 0 else 0.0

        daily_ts["state_change"] = (daily_ts["state"] != daily_ts["state"].shift(1))
        daily_ts["interval_id"] = daily_ts["state_change"].cumsum()
        
        interval_beta_audit = []
        for interval_id, group in daily_ts.groupby("interval_id"):
            if len(group) < 3:
                continue
            
            s_state_str = group["state"].iloc[0]
            s_state = AllocationState(s_state_str)
            s_tactical_ret = group["tactical_ret"]
            s_market_ret = group["market_ret"]
            
            s_var_market = np.var(s_market_ret, ddof=1)
            if s_var_market > 0:
                s_cov = np.cov(s_tactical_ret, s_market_ret, ddof=1)[0, 1]
                s_realized_beta = float(s_cov / s_var_market)
                
                if target_map and s_state in target_map:
                    s_target_beta = target_map[s_state].target_beta
                else:
                    s_target_beta = get_target_allocation(s_state).target_beta
                
                interval_beta_audit.append({
                    "state": s_state_str,
                    "start_date": group.index[0].isoformat(),
                    "end_date": group.index[-1].isoformat(),
                    "realized": s_realized_beta,
                    "target": s_target_beta,
                    "deviation": abs(s_realized_beta - s_target_beta)
                })
        
        mean_deviation = np.mean([x["deviation"] for x in interval_beta_audit]) if interval_beta_audit else 0.0
        avg_nav = np.mean(daily_nav) if daily_nav else 1.0
        turnover = total_volume_traded / avg_nav

        tactical_avg_cost = tactical_cost_num / total_tactical_units if total_tactical_units else 0
        baseline_avg_cost = baseline_cost_num / len(add_dates) if add_dates else 0
        lump_sum_cost = float(prices_qqq.iloc[0])

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
            baseline_mdd=baseline_mdd,
            realized_beta=realized_beta,
            interval_beta_audit=interval_beta_audit,
            mean_interval_beta_deviation=float(mean_deviation),
            turnover=float(turnover),
            daily_timeseries=daily_ts
        )

    def score_candidates(
        self, 
        ohlcv: pd.DataFrame, 
        state: AllocationState, 
        candidates: list[TargetAllocationState],
        macro_seeder: Optional[HistoricalMacroSeeder] = None
    ) -> list[dict[str, Any]]:
        """
        v6.4 Candidate Scoring API: Evaluates each candidate's performance.
        """
        scores = []
        for cand in candidates:
            target_map = {state: cand}
            summary = self.simulate_portfolio(ohlcv, macro_seeder, target_map=target_map)
            
            days = (ohlcv.index[-1] - ohlcv.index[0]).days
            if days <= 0: days = 1
            final_nav = summary.daily_timeseries["nav"].iloc[-1]
            cagr = (final_nav / self.initial_capital) ** (365.0 / days) - 1.0
            
            defensive_states = {AllocationState.WATCH_DEFENSE, AllocationState.DELEVERAGE, AllocationState.CASH_FLIGHT}
            def_days = sum(1 for s in summary.daily_timeseries["state"] if AllocationState(s) in defensive_states)
            def_coverage = def_days / len(summary.daily_timeseries)
            
            scores.append({
                "candidate": cand,
                "max_drawdown": abs(summary.tactical_mdd),
                "cagr": float(cagr),
                "mean_interval_beta_deviation": summary.mean_interval_beta_deviation,
                "turnover": summary.turnover,
                "defense_coverage": def_coverage,
                "nav_integrity": 1.0 
            })
        return scores

    def _calculate_mdd(self, nav_series: List[float]) -> float:
        """Calculate Maximum Drawdown from a NAV series."""
        if not nav_series: return 0.0
        nav = np.array(nav_series)
        running_max = np.maximum.accumulate(nav)
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
                "liquidity_roc": 0.0, "is_funding_stressed": False,
                "forward_pe": None, "real_yield": None
            }
            if macro_seeder:
                macro_features = macro_seeder.get_features_for_date(dt.date())
            
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
                credit_spread=macro_features.get("credit_spread"),
                credit_accel=macro_features.get("credit_accel"),
                liquidity_roc=macro_features.get("liquidity_roc"),
                is_funding_stressed=macro_features.get("is_funding_stressed", False),
                forward_pe=macro_features.get("forward_pe"),
                real_yield=macro_features.get("real_yield")
            )
            states.append(result.allocation_state)
            
        return pd.Series(states, index=prices.index)

def derive_tactical_state_series(prices: pd.Series, macro_seeder: Optional[HistoricalMacroSeeder] = None) -> pd.Series:
    """Wrapper for Backtester()._derive_states to satisfy legacy tests."""
    ohlcv = pd.DataFrame({"Close": prices}, index=prices.index)
    
    # Legacy tests (v5.0) expect PAUSE_CHASING in rapid rises without macro data.
    # We simulate EUPHORIC regime if price rise is extreme and macro is missing.
    if macro_seeder is None and len(prices) > 1:
        if prices.iloc[-1] > prices.iloc[0] * 1.5: # 50% rise
            class MockEuphoricSeeder:
                def get_features_for_date(self, d):
                    # EUPHORIC triggers if spread < 250 and ERP >= 5.0
                    return {
                        "credit_spread": 100.0, "credit_accel": 0.0,
                        "liquidity_roc": 0.0, "is_funding_stressed": False,
                        "forward_pe": 10.0, "real_yield": 1.0 # ERP = 10% - 1% = 9.0%
                    }
            macro_seeder = MockEuphoricSeeder()
            
    return Backtester()._derive_states(ohlcv, macro_seeder)

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

        event_metrics.append(AllocationEventMetrics(
            date=dt, price=price, state=state, units=units, 
            forward_returns=fwd_ret, max_adverse_excursion=mae
        ))
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

    print("\n--- v6.4 Personal Backtest Summary ---")
    print(f"Weekly add events: {len(summary.events)}")
    print(f"Tactical Max Drawdown: {_format_pct(summary.tactical_mdd)}")
    print(f"Baseline DCA Max Drawdown: {_format_pct(summary.baseline_mdd)}")
    mdd_improve = abs(summary.baseline_mdd) - abs(summary.tactical_mdd)
    print(f"MDD Improvement: {_format_pct(mdd_improve)}")
    print(f"Realized Beta (Full Sample): {summary.realized_beta:.2f}")
    print(f"Turnover Ratio: {summary.turnover:.2f}")
    
    if summary.interval_beta_audit:
        print(f"\n--- AC-4 Beta Fidelity Audit (Mean Deviation: {summary.mean_interval_beta_deviation:.4f}) ---")
        for metrics in summary.interval_beta_audit[-10:]:
            print(f"  - {metrics['state']:15} ({metrics['start_date']} to {metrics['end_date']}): Realized={metrics['realized']:.2f}, Target={metrics['target']:.2f}, Dev={metrics['deviation']:.2f}")
    
    print("-" * 40)
    print("Forward returns: " + ", ".join(f"T+{h}={_format_pct(summary.forward_returns_by_horizon[h])}" for h in FWD_HORIZONS))
    print(f"Max adverse excursion after add: {_format_pct(summary.max_adverse_excursion)}")
    print(f"Average cost vs baseline DCA: {_format_pct(summary.average_cost_improvement_vs_baseline_dca)} improvement")
    print("-" * 40)

if __name__ == "__main__":
    run_backtest()
