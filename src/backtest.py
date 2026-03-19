"""
QQQ backtest methodology.

This module treats the backtest as an allocator simulation, not a signal
labeler. It uses observable price history only, reports forward returns and
drawdown pain, and explicitly excludes synthetic fear/greed and fabricated
short-volume features from the backtest methodology.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from src.models import AllocationState

START_DATE = "1999-03-10"
END_DATE = date.today().isoformat()
FWD_HORIZONS = (5, 20, 60)
WEEKLY_ADD_INTERVAL = 5
BASE_WEEKLY_DCA_UNITS = 1.0
EXCLUDED_HISTORICAL_FEATURES = ("fear_greed", "short_vol_ratio")

STATE_BONUS_UNITS = {
    AllocationState.PAUSE_CHASING: -0.5,
    AllocationState.BASE_DCA: 0.0,
    AllocationState.SLOW_ACCUMULATE: 0.5,
    AllocationState.FAST_ACCUMULATE: 1.0,
    AllocationState.RISK_CONTAINMENT: -0.5,
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
    excluded_features: tuple[str, ...] = EXCLUDED_HISTORICAL_FEATURES
    feature_policy: dict[str, str] = field(
        default_factory=lambda: {
            "fear_greed": "excluded: unavailable historically, not synthesized",
            "short_vol_ratio": "excluded: fabricated in old methodology, not used",
        }
    )


def _coerce_state(value: object) -> AllocationState:
    if isinstance(value, AllocationState):
        return value
    if value is None:
        return AllocationState.BASE_DCA
    try:
        return AllocationState(str(value))
    except ValueError:
        return AllocationState.BASE_DCA


def _state_units(state: AllocationState) -> float:
    return max(0.0, BASE_WEEKLY_DCA_UNITS + STATE_BONUS_UNITS[state])


def compute_forward_returns(
    prices: pd.Series,
    entry_label,
    horizons: tuple[int, ...] = FWD_HORIZONS,
) -> dict[int, Optional[float]]:
    """Return forward price returns from a specific entry point."""

    if entry_label not in prices.index:
        raise KeyError(f"Entry label {entry_label!r} is not present in the price series")

    entry_loc = prices.index.get_loc(entry_label)
    if isinstance(entry_loc, slice):
        entry_loc = entry_loc.start

    entry_price = float(prices.iloc[entry_loc])
    returns: dict[int, Optional[float]] = {}

    for horizon in horizons:
        exit_loc = entry_loc + horizon
        if exit_loc >= len(prices):
            returns[horizon] = None
            continue
        exit_price = float(prices.iloc[exit_loc])
        returns[horizon] = exit_price / entry_price - 1.0

    return returns


def compute_max_adverse_excursion(
    prices: pd.Series,
    entry_label,
    lookahead: int = max(FWD_HORIZONS),
) -> Optional[float]:
    """Return worst drawdown from the entry price during the lookahead window."""

    if entry_label not in prices.index:
        raise KeyError(f"Entry label {entry_label!r} is not present in the price series")

    entry_loc = prices.index.get_loc(entry_label)
    if isinstance(entry_loc, slice):
        entry_loc = entry_loc.start

    end_loc = min(len(prices) - 1, entry_loc + lookahead)
    window = prices.iloc[entry_loc : end_loc + 1]
    if window.empty:
        return None

    entry_price = float(prices.iloc[entry_loc])
    return float(window.min() / entry_price - 1.0)


def _align_state_series(
    prices: pd.Series,
    tactical_states: Optional[pd.Series],
) -> pd.Series:
    if tactical_states is None or tactical_states.empty:
        return pd.Series(AllocationState.BASE_DCA, index=prices.index)

    aligned = tactical_states.copy()
    aligned.index = pd.to_datetime(aligned.index)
    aligned = aligned.sort_index().reindex(prices.index, method="ffill")
    if aligned.isna().any():
        aligned = aligned.fillna(AllocationState.BASE_DCA)

    return pd.Series([_coerce_state(value) for value in aligned], index=prices.index)


def derive_tactical_state_series(prices: pd.Series) -> pd.Series:
    """Derive a deterministic tactical state series from observable price action."""

    prices = prices.astype(float)
    if prices.empty:
        return pd.Series(dtype=object)

    drawdown = prices / prices.cummax() - 1.0
    ma50 = prices.rolling(50, min_periods=20).mean()
    prior_high_20 = prices.shift(1).rolling(20, min_periods=5).max()

    states: list[AllocationState] = []
    for i, price in enumerate(prices):
        dd = float(drawdown.iloc[i])
        momentum_5 = 0.0
        if i >= 5:
            momentum_5 = float(price / float(prices.iloc[i - 5]) - 1.0)

        dist_to_20d_high = 0.0
        if not pd.isna(prior_high_20.iloc[i]):
            dist_to_20d_high = float(price / float(prior_high_20.iloc[i]) - 1.0)

        below_ma50 = not pd.isna(ma50.iloc[i]) and float(price) < float(ma50.iloc[i])

        if dd <= -0.25:
            state = AllocationState.RISK_CONTAINMENT
        elif dd <= -0.12 and momentum_5 < -0.03:
            state = AllocationState.FAST_ACCUMULATE
        elif dd <= -0.05 or below_ma50:
            state = AllocationState.SLOW_ACCUMULATE
        elif dist_to_20d_high > 0.08:
            state = AllocationState.PAUSE_CHASING
        else:
            state = AllocationState.BASE_DCA

        states.append(state)

    return pd.Series(states, index=prices.index)


def simulate_allocator(
    prices: pd.Series,
    tactical_states: Optional[pd.Series] = None,
    interval: int = WEEKLY_ADD_INTERVAL,
) -> BacktestMethodologySummary:
    """Simulate weekly DCA plus tactical state-driven speed-ups or slow-downs."""

    prices = prices.astype(float).dropna()
    if prices.empty:
        raise ValueError("Price series cannot be empty")

    aligned_states = _align_state_series(prices, tactical_states)
    add_dates = list(prices.index[::interval])
    if not add_dates:
        add_dates = [prices.index[0]]

    total_capital_units = 0.0
    tactical_cost_numerator = 0.0
    baseline_cost_numerator = 0.0
    capital_deployed_before_final_low = 0.0
    event_metrics: list[AllocationEventMetrics] = []
    horizon_return_numerators: dict[int, float] = {horizon: 0.0 for horizon in FWD_HORIZONS}
    horizon_return_denominators: dict[int, float] = {horizon: 0.0 for horizon in FWD_HORIZONS}
    mae_values: list[float] = []

    final_low_date = prices.idxmin()

    for dt in add_dates:
        state = _coerce_state(aligned_states.loc[dt])
        price = float(prices.loc[dt])
        units = _state_units(state)

        forward_returns = compute_forward_returns(prices, dt)
        max_adverse_excursion = compute_max_adverse_excursion(prices, dt)

        event_metrics.append(
            AllocationEventMetrics(
                date=dt,
                price=price,
                state=state,
                units=units,
                forward_returns=forward_returns,
                max_adverse_excursion=max_adverse_excursion,
            )
        )

        total_capital_units += units
        tactical_cost_numerator += price * units
        baseline_cost_numerator += price

        if dt <= final_low_date:
            capital_deployed_before_final_low += units

        for horizon, value in forward_returns.items():
            if value is not None:
                horizon_return_numerators[horizon] += value * units
                horizon_return_denominators[horizon] += units

        if max_adverse_excursion is not None:
            mae_values.append(max_adverse_excursion)

    tactical_average_cost = tactical_cost_numerator / total_capital_units
    baseline_dca_average_cost = baseline_cost_numerator / len(add_dates)
    lump_sum_average_cost = float(prices.iloc[add_dates.index(add_dates[0])])

    average_cost_improvement_vs_baseline_dca = (
        (baseline_dca_average_cost - tactical_average_cost) / baseline_dca_average_cost
        if baseline_dca_average_cost
        else 0.0
    )
    average_cost_penalty_vs_lump_sum = (
        (tactical_average_cost - lump_sum_average_cost) / lump_sum_average_cost
        if lump_sum_average_cost
        else 0.0
    )

    forward_returns_by_horizon = {
        horizon: (
            horizon_return_numerators[horizon] / horizon_return_denominators[horizon]
            if horizon_return_denominators[horizon]
            else 0.0
        )
        for horizon in FWD_HORIZONS
    }
    max_adverse_excursion = min(mae_values) if mae_values else None
    fraction_capital_deployed_before_final_low = (
        capital_deployed_before_final_low / total_capital_units if total_capital_units else 0.0
    )

    return BacktestMethodologySummary(
        events=tuple(event_metrics),
        forward_returns_by_horizon=forward_returns_by_horizon,
        max_adverse_excursion=max_adverse_excursion,
        average_cost_improvement_vs_baseline_dca=average_cost_improvement_vs_baseline_dca,
        average_cost_penalty_vs_lump_sum=average_cost_penalty_vs_lump_sum,
        baseline_dca_average_cost=baseline_dca_average_cost,
        tactical_average_cost=tactical_average_cost,
        lump_sum_average_cost=lump_sum_average_cost,
        fraction_capital_deployed_before_final_low=fraction_capital_deployed_before_final_low,
        capital_deployed_before_final_low_units=capital_deployed_before_final_low,
        total_capital_units=total_capital_units,
    )


def summarize_backtest_methodology(
    prices: pd.Series,
    tactical_states: Optional[pd.Series] = None,
    interval: int = WEEKLY_ADD_INTERVAL,
) -> BacktestMethodologySummary:
    """Public summary helper used by tests and the CLI entry point."""

    return simulate_allocator(prices, tactical_states=tactical_states, interval=interval)


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def run_backtest() -> None:
    print(f"Fetching QQQ history from {START_DATE} to {END_DATE}...")

    qqq = yf.Ticker("QQQ").history(start=START_DATE, end=END_DATE)
    if qqq.empty:
        print("Failed to fetch QQQ historical data.")
        return

    prices = qqq["Close"].dropna().astype(float)
    tactical_states = derive_tactical_state_series(prices)
    summary = summarize_backtest_methodology(prices, tactical_states=tactical_states)

    print("\n--- Backtest Methodology Summary ---")
    print(f"Weekly add events: {len(summary.events)}")
    print(
        "Forward returns: "
        + ", ".join(
            f"T+{h}={_format_pct(summary.forward_returns_by_horizon[h])}"
            for h in FWD_HORIZONS
        )
    )
    print(f"Max adverse excursion after add: {_format_pct(summary.max_adverse_excursion)}")
    print(
        "Average cost vs baseline DCA: "
        f"{_format_pct(summary.average_cost_improvement_vs_baseline_dca)} improvement"
    )
    print(
        "Average cost vs lump-sum: "
        f"{_format_pct(summary.average_cost_penalty_vs_lump_sum)} penalty"
    )
    print(f"Baseline weekly DCA average cost: ${summary.baseline_dca_average_cost:.2f}")
    print(f"Tactical allocator average cost: ${summary.tactical_average_cost:.2f}")
    print(f"Lump-sum average cost: ${summary.lump_sum_average_cost:.2f}")
    print(
        "Capital deployed before final low: "
        f"{_format_pct(summary.fraction_capital_deployed_before_final_low)}"
    )
    print("Excluded historical features: " + ", ".join(summary.excluded_features))


if __name__ == "__main__":
    run_backtest()
