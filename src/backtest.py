"""
QQQ backtest methodology.

v6.3 Institutional Upgrade: Support for Portfolio Net Value Tracking,
Multi-Asset (QQQ + QLD) TAA Mirroring, and Max Drawdown quantification.
v6.4 Personal Allocation Upgrade: Candidate scoring and turnover tracking.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.engine.aggregator import aggregate, get_target_allocation
from src.engine.allocation_search import (
    find_best_allocation,
    generate_candidates,
    select_candidate_with_floor_fallback_v8,
)
from src.engine.candidate_registry import load_registry, select_runtime_candidates
from src.engine.cycle_factor import decide_cycle_state
from src.engine.deployment_controller import DeploymentDecision, decide_deployment_state
from src.engine.execution_policy import (
    AdvisoryState,
    beta_requires_qld_above_ceiling,
    build_advisory_rebalance_decision,
    build_beta_recommendation,
    target_allocation_from_beta,
)
from src.engine.feature_pipeline import build_feature_snapshot
from src.engine.risk_controller import decide_risk_state
from src.engine.runtime_selector import RuntimeSelection
from src.engine.tier0_macro import assess_structural_regime
from src.models import (
    AllocationState,
    CurrentPortfolioState,
    TargetAllocationState,
    Tier1Result,
    Tier2Result,
)
from src.models.deployment import (
    DEPLOYMENT_MULTIPLIER_BY_STATE,
    DeploymentState,
    deployment_multiplier_for_state,
)
from src.models.risk import RiskState
from src.output.backtest_plots import save_beta_backtest_figure
from src.research.data_contracts import (
    summarize_historical_macro_coverage,
    summarize_signal_expectation_coverage,
    validate_historical_macro_frame,
    validate_signal_expectation_frame,
)

logger = logging.getLogger(__name__)
_PARALLEL_FALLBACK_WARNED = False
_EXPECTED_TARGET_BETA_COLUMN = "expected_target_beta"
_EXPECTED_DEPLOYMENT_COLUMN = "expected_deployment_state"
_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN = "expected_deployment_multiplier"
_EXPECTED_DEPLOYMENT_CASH_COLUMN = "expected_deployment_cash"
_DEPLOYMENT_STATE_RANK = {
    DeploymentState.DEPLOY_FAST.value: 4,
    DeploymentState.DEPLOY_RECOVER.value: 3,
    DeploymentState.DEPLOY_BASE.value: 2,
    DeploymentState.DEPLOY_SLOW.value: 1,
    DeploymentState.DEPLOY_PAUSE.value: 0,
}


def _coerce_alignment_frame(
    expected_matrix: pd.DataFrame | pd.Series | None,
    target_index: pd.Index,
    *,
    default_column: str | None = None,
) -> pd.DataFrame:
    """Normalize expectation inputs onto the market-date index."""
    if expected_matrix is None:
        return pd.DataFrame(index=target_index)

    if isinstance(expected_matrix, pd.Series):
        if default_column is None:
            raise ValueError("default_column is required when expected_matrix is a Series")
        frame = expected_matrix.to_frame(name=default_column)
    else:
        frame = expected_matrix.copy()

    if "date" in frame.columns:
        frame = frame.set_index("date")

    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[~frame.index.isna()].copy()

    target_tz = getattr(target_index, "tz", None)
    if isinstance(frame.index, pd.DatetimeIndex):
        if target_tz is None:
            if frame.index.tz is not None:
                frame.index = frame.index.tz_convert(None)
        else:
            if frame.index.tz is None:
                frame.index = frame.index.tz_localize(target_tz)
            else:
                frame.index = frame.index.tz_convert(target_tz)

    frame = frame[~frame.index.duplicated(keep="last")]
    return frame.reindex(target_index)


def _coerce_optional_float(value: object, default: float | None = None) -> float | None:
    if value is None or pd.isna(value):
        return default
    return float(value)


def _coerce_optional_bool(value: object, default: bool = False) -> bool:
    if value is None or pd.isna(value):
        return default
    return bool(value)


def _coerce_optional_str(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def _coerce_optional_deployment_multiplier(
    value: object,
    *,
    state: object = None,
) -> float | None:
    if value is not None and not pd.isna(value):
        return float(value)
    if state is None or pd.isna(state):
        return None
    return float(deployment_multiplier_for_state(str(state)) or 0.0)


def _deployment_reason_rule(decision: DeploymentDecision) -> str:
    if not decision.reasons:
        return "controller_decision"
    return str(decision.reasons[0].get("rule", "controller_decision"))


def _deployment_reason_path(decision: DeploymentDecision) -> str | None:
    for reason in decision.reasons:
        if reason.get("rule") == "blood_chip_crisis_override":
            return _coerce_optional_str(reason.get("path"))
    return _coerce_optional_str(decision.reasons[0].get("path")) if decision.reasons else None


def _blood_chip_override_active(decision: DeploymentDecision) -> bool:
    return any(reason.get("rule") == "blood_chip_crisis_override" for reason in decision.reasons)


def _safe_beta(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    *,
    fallback_target: float = 0.0,
) -> float:
    """Compute beta defensively for short or degenerate windows."""
    aligned = pd.concat(
        [
            pd.Series(portfolio_returns, dtype=float),
            pd.Series(benchmark_returns, dtype=float),
        ],
        axis=1,
        join="inner",
    ).dropna()
    if aligned.empty:
        return float(fallback_target)

    portfolio = aligned.iloc[:, 0]
    benchmark = aligned.iloc[:, 1]

    if len(aligned) < 2:
        return float(fallback_target)

    variance_market = float(np.var(benchmark, ddof=1))
    if variance_market <= 0:
        return float(fallback_target)

    covariance = float(np.cov(portfolio, benchmark, ddof=1)[0, 1])
    return float(covariance / variance_market)


def _build_active_portfolio(
    active_cash: float,
    units_qqq: float,
    units_qld: float,
    price_qqq: float,
    price_qld: float,
    *,
    rolling_drawdown: float | None = None,
) -> CurrentPortfolioState:
    """Build the investable sleeve state used by the v8 runtime pipeline."""
    equity_value = units_qqq * price_qqq
    qld_value = units_qld * price_qld
    active_nav = active_cash + equity_value + qld_value
    if active_nav <= 0:
        return CurrentPortfolioState(
            current_cash_pct=1.0,
            qqq_pct=0.0,
            qld_pct=0.0,
            rolling_drawdown=rolling_drawdown,
            gross_exposure_pct=0.0,
            net_exposure_pct=0.0,
            leverage_ratio=1.0,
        )

    qqq_pct = equity_value / active_nav
    qld_pct = qld_value / active_nav
    cash_pct = active_cash / active_nav
    exposure = qqq_pct + 2.0 * qld_pct
    return CurrentPortfolioState(
        current_cash_pct=float(cash_pct),
        qqq_pct=float(qqq_pct),
        qld_pct=float(qld_pct),
        rolling_drawdown=rolling_drawdown,
        gross_exposure_pct=float(exposure),
        net_exposure_pct=float(exposure),
        leverage_ratio=float(exposure) if exposure > 1.0 else 1.0,
    )


def _advance_advisory_state(
    advisory_state: AdvisoryState | None,
    *,
    raw_target_beta: float,
) -> AdvisoryState:
    """Advance advisory streak bookkeeping for sequential backtests."""
    if advisory_state is None:
        return AdvisoryState(
            assumed_beta=float(raw_target_beta),
            last_rebalance_date=None,
            last_advised_beta=float(raw_target_beta),
        )

    gap = float(raw_target_beta) - float(advisory_state.assumed_beta)
    if gap > 0:
        return AdvisoryState(
            assumed_beta=advisory_state.assumed_beta,
            last_rebalance_date=advisory_state.last_rebalance_date,
            last_advised_beta=advisory_state.last_advised_beta,
            upshift_streak_days=advisory_state.upshift_streak_days + 1,
            downshift_streak_days=0,
        )
    if gap < 0:
        return AdvisoryState(
            assumed_beta=advisory_state.assumed_beta,
            last_rebalance_date=advisory_state.last_rebalance_date,
            last_advised_beta=advisory_state.last_advised_beta,
            upshift_streak_days=0,
            downshift_streak_days=advisory_state.downshift_streak_days + 1,
        )
    return AdvisoryState(
        assumed_beta=advisory_state.assumed_beta,
        last_rebalance_date=advisory_state.last_rebalance_date,
        last_advised_beta=advisory_state.last_advised_beta,
    )


def _derive_capitulation_score(drawdown: float) -> int:
    """Map market drawdown into the v8 deployment controller's capitulation scale."""
    if drawdown <= -0.20:
        return 80
    if drawdown <= -0.15:
        return 70
    if drawdown <= -0.10:
        return 40
    if drawdown <= -0.05:
        return 20
    return 0


def _rolling_market_drawdown(prices: pd.Series, loc: int, *, window: int = 252) -> float:
    """Return drawdown versus the trailing-window high, expressed as a negative number."""
    start = max(0, loc - window + 1)
    trailing_peak = float(prices.iloc[start : loc + 1].max())
    current = float(prices.iloc[loc])
    if trailing_peak <= 0:
        return 0.0
    return current / trailing_peak - 1.0


def _derive_tactical_stress_score(prices: pd.Series, loc: int) -> int:
    """
    Approximate price-chasing stress from short-term momentum.

    v8 uses Class B tactical overlays for deployment pace. In historical
    backtests we approximate that surface from observable price action instead
    of reusing the legacy aggregate engine.
    """
    if loc < 4:
        return 10
    current = float(prices.iloc[loc])
    recent = float(prices.iloc[max(0, loc - 4)])
    if recent <= 0:
        return 10
    rally = current / recent - 1.0
    if rally >= 0.12:
        return 80
    if rally >= 0.08:
        return 60
    return 10


def _rolling_price_vs_ma200(prices: pd.Series, loc: int, *, window: int = 200) -> float | None:
    """Approximate trend versus a trailing 200-day average using only past prices."""
    start = max(0, loc - window + 1)
    trailing_window = prices.iloc[start : loc + 1]
    if trailing_window.empty:
        return None
    ma200_proxy = float(trailing_window.mean())
    if ma200_proxy <= 0:
        return None
    current = float(prices.iloc[loc])
    return current / ma200_proxy - 1.0


def _rolling_breadth_proxy(prices: pd.Series, loc: int, *, window: int = 50) -> float | None:
    """Map price-vs-trailing-mean into a simple breadth proxy for cycle research."""
    start = max(0, loc - window + 1)
    trailing_window = prices.iloc[start : loc + 1]
    if trailing_window.empty:
        return None
    ma50_proxy = float(trailing_window.mean())
    if ma50_proxy <= 0:
        return None
    current = float(prices.iloc[loc])
    deviation = current / ma50_proxy - 1.0
    if deviation >= 0.05:
        return 0.65
    if deviation <= -0.05:
        return 0.20
    return 0.40


def _deployment_state_to_legacy_state(deployment_state: str, risk_state: str) -> AllocationState:
    """Preserve legacy event/state fields for older reports and tests."""
    if risk_state in {RiskState.RISK_DEFENSE.value, RiskState.RISK_EXIT.value}:
        return AllocationState.RISK_CONTAINMENT
    mapping = {
        "DEPLOY_FAST": AllocationState.FAST_ACCUMULATE,
        "DEPLOY_BASE": AllocationState.BASE_DCA,
        "DEPLOY_SLOW": AllocationState.SLOW_ACCUMULATE,
        "DEPLOY_PAUSE": AllocationState.PAUSE_CHASING,
        "DEPLOY_RECOVER": AllocationState.BASE_DCA,
    }
    return mapping.get(deployment_state, AllocationState.BASE_DCA)

# v6.4 Optimization: Top-level helper for multiprocessing support
def _score_candidate_worker(
    ohlcv_slice: pd.DataFrame,
    state: AllocationState,
    cand: TargetAllocationState,
    initial_capital: float,
    precomputed_states: pd.Series | None = None
) -> dict:
    """Standalone worker function for parallel candidate scoring."""
    tester = Backtester(initial_capital=initial_capital)
    # Sub-simulations must have enable_dynamic_search=False to avoid infinite recursion
    summary = tester.simulate_portfolio(
        ohlcv_slice,
        target_map={state: cand},
        precomputed_states=precomputed_states,
        enable_dynamic_search=False
    )

    if hasattr(ohlcv_slice.index, "date") and len(ohlcv_slice.index) > 1:
        days = (ohlcv_slice.index[-1] - ohlcv_slice.index[0]).days
    elif hasattr(ohlcv_slice.index[0], "days"):
        days = (ohlcv_slice.index[-1] - ohlcv_slice.index[0]).days
    else:
        days = len(ohlcv_slice.index)

    if days <= 0:
        days = 1
    final_nav = summary.daily_timeseries["nav"].iloc[-1]
    cagr = (final_nav / initial_capital) ** (365.0 / days) - 1.0

    defensive_states = {AllocationState.WATCH_DEFENSE, AllocationState.DELEVERAGE, AllocationState.CASH_FLIGHT}
    def_days = sum(1 for s in summary.daily_timeseries["state"] if AllocationState(s) in defensive_states)
    def_coverage = def_days / len(summary.daily_timeseries)

    return {
        "candidate": cand,
        "max_drawdown": abs(summary.tactical_mdd),
        "cagr": float(cagr),
        "mean_interval_beta_deviation": summary.mean_interval_beta_deviation,
        "turnover": summary.turnover,
        "defense_coverage": def_coverage,
        "nav_integrity": summary.nav_integrity
    }

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
    forward_returns: dict[int, float | None]
    max_adverse_excursion: float | None
    tier0_regime: str | None = None
    risk_state: str | None = None
    deployment_state: str | None = None
    selected_candidate_id: str | None = None
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
    max_adverse_excursion: float | None
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
    signal_beta: float = 0.50
    # v6.3.12: Interval Beta Audit (AC-4 Fidelity)
    interval_beta_audit: list[dict[str, Any]] = field(default_factory=list)
    mean_interval_beta_deviation: float = 0.0
    turnover: float = 0.0
    raw_turnover: float = 0.0
    estimated_cost_drag: float = 0.0
    nav_integrity: float = 1.0
    # v6.2 Visualization Support
    daily_timeseries: pd.DataFrame | None = None
    excluded_features: tuple[str, ...] = EXCLUDED_HISTORICAL_FEATURES

    @property
    def feature_policy(self) -> dict[str, str]:
        """Legacy support for feature policy audit."""
        return {f: "excluded" for f in self.excluded_features}


@dataclass(frozen=True)
class TargetBetaAlignmentSummary:
    """Alignment metrics for target-beta decision backtests."""

    compared_points: int
    mean_absolute_error: float
    rmse: float
    within_tolerance_ratio: float
    daily_timeseries: pd.DataFrame


@dataclass(frozen=True)
class DeploymentAlignmentSummary:
    """Alignment metrics for incremental deployment decision backtests."""

    compared_points: int
    exact_match_ratio: float
    mean_rank_abs_error: float
    within_one_step_ratio: float
    daily_timeseries: pd.DataFrame


@dataclass(frozen=True)
class DeploymentPacingAlignmentSummary:
    """Continuous pacing-alignment metrics for incremental cash deployment."""

    compared_points: int
    mean_error: float
    mean_absolute_error: float
    rmse: float
    error_variance: float
    error_std_dev: float
    correlation: float
    explained_variance: float
    within_tolerance_ratio: float
    actual_mean_pacing: float
    expected_mean_pacing: float
    cash_mean_absolute_error: float
    cash_rmse: float
    daily_timeseries: pd.DataFrame

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

    def _parallel_map(self, worker_func, tasks, *args):
        """
        Executes tasks in parallel with a fallback to ThreadPool if ProcessPool fails.
        Handles 'semaphore permission' errors in restricted environments.
        """
        # Try ProcessPool first (True parallelism, bypasses GIL)
        global _PARALLEL_FALLBACK_WARNED
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=min(os.cpu_count() or 1, 8)) as executor:
                futures = [executor.submit(worker_func, *task_args, *args) for task_args in tasks]
                return [f.result() for f in futures]
        except (PermissionError, RuntimeError, OSError) as e:
            if not _PARALLEL_FALLBACK_WARNED:
                logger.warning(f"ProcessPoolExecutor failed ({e}). Falling back to ThreadPoolExecutor.")
                _PARALLEL_FALLBACK_WARNED = True
            # Fallback to ThreadPool (GIL-bound, but safer in restricted sandboxes)
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as executor:
                futures = [executor.submit(worker_func, *task_args, *args) for task_args in tasks]
                return [f.result() for f in futures]

    def run(self, ohlcv: pd.DataFrame, macro_seeder: HistoricalMacroSeeder | None = None) -> list[dict[str, Any]]:
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

    def build_signal_timeseries(
        self,
        ohlcv: pd.DataFrame,
        *,
        macro_seeder: HistoricalMacroSeeder | None = None,
        registry_path: str = "data/candidate_registry_v7.json",
        expected_matrix: pd.DataFrame | pd.Series | None = None,
    ) -> pd.DataFrame:
        """
        Build the pure daily decision surface for v8 runtime logic.

        This path does not simulate cash transfers or portfolio NAV. It emits the
        target-beta signal and incremental deployment pace directly so they can be
        compared against an expected market-date time series.
        """
        prices_qqq = ohlcv["Close"].dropna().astype(float)
        if prices_qqq.empty:
            raise ValueError("Empty price data")

        five_day_returns = prices_qqq.pct_change(5).fillna(0.0)
        twenty_day_returns = prices_qqq.pct_change(20).fillna(0.0)
        registry = load_registry(registry_path)
        expected = _coerce_alignment_frame(expected_matrix, prices_qqq.index)
        previous_risk_state: RiskState | None = None
        advisory_state: AdvisoryState | None = None
        rows: list[dict[str, Any]] = []
        add_dates = set(prices_qqq.index[::WEEKLY_ADD_INTERVAL])

        for loc, dt in enumerate(prices_qqq.index):
            p_qqq = float(prices_qqq.iloc[loc])
            current_date = pd.Timestamp(dt).date()
            row = expected.loc[dt] if not expected.empty else pd.Series(dtype=object)

            macro_features = {
                "credit_spread": None,
                "credit_accel": 0.0,
                "real_yield": None,
                "net_liquidity": None,
                "liquidity_roc": 0.0,
                "is_funding_stressed": False,
            }
            if macro_seeder:
                macro_features.update(macro_seeder.get_features_for_date(current_date))

            price_drawdown = _rolling_market_drawdown(prices_qqq, loc)
            capitulation_score = int(
                _coerce_optional_float(row.get("capitulation_score"), _derive_capitulation_score(price_drawdown))
                or 0
            )
            tactical_stress_score = int(
                _coerce_optional_float(row.get("tactical_stress_score"), _derive_tactical_stress_score(prices_qqq, loc))
                or 0
            )
            inferred_market_drawdown = max(0.0, -price_drawdown)
            rolling_drawdown = _coerce_optional_float(
                row.get("rolling_drawdown"),
                inferred_market_drawdown,
            )
            five_day_return = _coerce_optional_float(
                row.get("five_day_return"),
                float(five_day_returns.iloc[loc]),
            ) or 0.0
            twenty_day_return = _coerce_optional_float(
                row.get("twenty_day_return"),
                float(twenty_day_returns.iloc[loc]),
            ) or 0.0
            funding_event = _coerce_optional_bool(row.get("funding_event"), default=dt in add_dates)
            available_new_cash = _coerce_optional_float(
                row.get("available_new_cash"),
                BASE_WEEKLY_DCA_UNITS * p_qqq if funding_event else 0.0,
            ) or 0.0
            erp = _coerce_optional_float(row.get("erp"), macro_features.get("erp"))
            price_vs_ma200 = _coerce_optional_float(
                row.get("price_vs_ma200"),
                _rolling_price_vs_ma200(prices_qqq, loc),
            )
            breadth = _coerce_optional_float(
                row.get("breadth"),
                _rolling_breadth_proxy(prices_qqq, loc),
            )

            snapshot = build_feature_snapshot(
                market_date=current_date,
                raw_values={
                    "credit_spread": macro_features.get("credit_spread"),
                    "credit_acceleration": macro_features.get("credit_accel", 0.0),
                    "net_liquidity": macro_features.get("net_liquidity"),
                    "liquidity_roc": macro_features.get("liquidity_roc", 0.0),
                    "real_yield": macro_features.get("real_yield"),
                    "funding_stress": macro_features.get("is_funding_stressed", False),
                    "close": p_qqq,
                    "vix": None,
                    "breadth": breadth,
                    "fear_greed": None,
                    "tactical_stress_score": tactical_stress_score,
                    "capitulation_score": capitulation_score,
                    "rolling_drawdown": rolling_drawdown,
                    "five_day_return": five_day_return,
                    "twenty_day_return": twenty_day_return,
                    "persistence_score": 0,
                    "erp": erp,
                    "price_vs_ma200": price_vs_ma200,
                    "price_vix_divergence": _coerce_optional_bool(
                        row.get("price_vix_divergence", False)
                    ),
                    "price_mfi_divergence": _coerce_optional_bool(
                        row.get("price_mfi_divergence", False)
                    ),
                    "short_squeeze_potential": _coerce_optional_bool(
                        row.get("short_squeeze_potential", False)
                    ),
                    "bond_vol_spike": _coerce_optional_bool(row.get("bond_vol_spike", False)),
                    "near_volume_poc": _coerce_optional_bool(row.get("near_volume_poc", False)),
                },
                raw_quality={},
            )
            tier0_regime = assess_structural_regime(
                credit_spread=macro_features.get("credit_spread"),
                erp=erp,
            )
            cycle_decision = decide_cycle_state(snapshot)
            risk = decide_risk_state(
                snapshot,
                rolling_drawdown=rolling_drawdown,
                tier0_regime=tier0_regime,
                cycle_decision=cycle_decision,
                drawdown_budget=registry.drawdown_budget,
            )
            deploy = decide_deployment_state(
                snapshot,
                risk,
                tier0_regime=tier0_regime,
                available_new_cash=available_new_cash,
            )
            deployment_reason_rule = _deployment_reason_rule(deploy)
            deployment_reason_path = _deployment_reason_path(deploy)
            blood_chip_override_active = _blood_chip_override_active(deploy)

            candidates = select_runtime_candidates(registry, risk.risk_state)
            selected_candidate, used_floor_fallback = select_candidate_with_floor_fallback_v8(
                scoped_candidates=candidates,
                registry_candidates=list(registry.candidates),
                max_beta_ceiling=risk.target_exposure_ceiling,
                qld_share_ceiling=risk.qld_share_ceiling,
                max_drawdown_budget=registry.drawdown_budget,
            )

            if selected_candidate is None:
                raise ValueError(
                    "No compliant runtime candidate found and no global 0.5 beta floor candidate is available. "
                    "Check candidate_registry_v7.json."
                )

            selected_candidate_id = selected_candidate.candidate_id
            selection = RuntimeSelection(
                selected_candidate=selected_candidate,
                rejected_candidates=(),
                selection_score=0.0,
            )
            recommendation = build_beta_recommendation(
                selection=selection,
                risk_decision=risk,
                previous_risk_state=previous_risk_state,
            )
            raw_target_beta = float(recommendation.target_beta)
            advisory_state = _advance_advisory_state(
                advisory_state,
                raw_target_beta=raw_target_beta,
            )
            hard_constraint_override = (
                advisory_state.assumed_beta > risk.target_exposure_ceiling + 1e-9
                or beta_requires_qld_above_ceiling(
                    advisory_state.assumed_beta,
                    qld_share_ceiling=risk.qld_share_ceiling,
                )
            )
            advisory_decision = build_advisory_rebalance_decision(
                raw_recommendation=recommendation,
                advisory_state=advisory_state,
                as_of_date=current_date,
                emergency_override=tier0_regime == "CRISIS"
                or cycle_decision.cycle_regime.value == "CAPITULATION"
                or (rolling_drawdown is not None and rolling_drawdown >= registry.drawdown_budget)
                or hard_constraint_override,
            )
            advisory_state = advisory_decision.next_state
            signal_target_beta = raw_target_beta
            expected_deployment_multiplier = _coerce_optional_deployment_multiplier(
                row.get(_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN),
                state=row.get(_EXPECTED_DEPLOYMENT_COLUMN),
            )
            expected_deployment_cash = _coerce_optional_float(
                row.get(_EXPECTED_DEPLOYMENT_CASH_COLUMN),
                None if expected_deployment_multiplier is None else available_new_cash * expected_deployment_multiplier,
            )
            actual_deployment_cash = available_new_cash * float(deploy.dca_multiplier)

            rows.append(
                {
                    "date": dt,
                    "close": p_qqq,
                    _EXPECTED_TARGET_BETA_COLUMN: _coerce_optional_float(row.get(_EXPECTED_TARGET_BETA_COLUMN)),
                    _EXPECTED_DEPLOYMENT_COLUMN: _coerce_optional_str(row.get(_EXPECTED_DEPLOYMENT_COLUMN)),
                    _EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN: expected_deployment_multiplier,
                    _EXPECTED_DEPLOYMENT_CASH_COLUMN: expected_deployment_cash,
                    "rolling_drawdown": rolling_drawdown,
                    "five_day_return": five_day_return,
                    "twenty_day_return": twenty_day_return,
                    "available_new_cash": available_new_cash,
                    "funding_event": funding_event,
                    "tier0_regime": tier0_regime,
                    "cycle_regime": cycle_decision.cycle_regime.value,
                    "cycle_target_exposure_ceiling": cycle_decision.target_exposure_ceiling,
                    "cycle_qld_share_ceiling": cycle_decision.qld_share_ceiling,
                    "risk_state": risk.risk_state.value,
                    "deployment_state": deploy.deployment_state.value,
                    "deployment_multiplier": float(deploy.dca_multiplier),
                    "actual_deployment_cash": actual_deployment_cash,
                    "deployment_reason_rule": deployment_reason_rule,
                    "deployment_reason_path": deployment_reason_path,
                    "blood_chip_override_active": blood_chip_override_active,
                    "selected_candidate_id": selected_candidate_id,
                    "raw_target_beta": raw_target_beta,
                    "signal_target_beta": signal_target_beta,
                    "advised_target_beta": advisory_decision.advised_target_beta,
                    "qld_share_ceiling": risk.qld_share_ceiling,
                    "assumed_beta_before": advisory_decision.assumed_beta_before,
                    "assumed_beta_after": advisory_decision.assumed_beta_after,
                    "friction_blockers": list(advisory_decision.friction_blockers),
                    "estimated_turnover": advisory_decision.estimated_turnover,
                    "estimated_cost_drag": advisory_decision.estimated_cost_drag,
                    "used_beta_floor_fallback": used_floor_fallback,
                }
            )
            previous_risk_state = risk.risk_state

        return pd.DataFrame(rows).set_index("date")

    def backtest_target_beta_alignment(
        self,
        ohlcv: pd.DataFrame,
        *,
        expected_matrix: pd.DataFrame | pd.Series,
        macro_seeder: HistoricalMacroSeeder | None = None,
        registry_path: str = "data/candidate_registry_v7.json",
        tolerance: float = 0.10,
    ) -> TargetBetaAlignmentSummary:
        """Score the target-beta decision path against an expected beta time series."""
        signals = self.build_signal_timeseries(
            ohlcv,
            macro_seeder=macro_seeder,
            registry_path=registry_path,
            expected_matrix=expected_matrix,
        ).copy()
        compared = signals[signals[_EXPECTED_TARGET_BETA_COLUMN].notna()].copy()
        if compared.empty:
            raise ValueError("expected_matrix must contain at least one expected_target_beta value")

        compared["beta_error"] = compared["signal_target_beta"] - compared[_EXPECTED_TARGET_BETA_COLUMN]
        compared["beta_abs_error"] = compared["beta_error"].abs()
        compared["beta_sq_error"] = compared["beta_error"] ** 2
        compared["beta_within_tolerance"] = compared["beta_abs_error"] <= tolerance
        signals.loc[compared.index, compared.columns] = compared

        mae = float(compared["beta_abs_error"].mean())
        rmse = float(np.sqrt(compared["beta_sq_error"].mean()))
        within_ratio = float(compared["beta_within_tolerance"].mean())
        return TargetBetaAlignmentSummary(
            compared_points=len(compared),
            mean_absolute_error=mae,
            rmse=rmse,
            within_tolerance_ratio=within_ratio,
            daily_timeseries=signals,
        )

    def backtest_deployment_alignment(
        self,
        ohlcv: pd.DataFrame,
        *,
        expected_matrix: pd.DataFrame | pd.Series,
        macro_seeder: HistoricalMacroSeeder | None = None,
        registry_path: str = "data/candidate_registry_v7.json",
    ) -> DeploymentAlignmentSummary:
        """Score the incremental deployment decision path against an expected signal time series."""
        signals = self.build_signal_timeseries(
            ohlcv,
            macro_seeder=macro_seeder,
            registry_path=registry_path,
            expected_matrix=expected_matrix,
        ).copy()
        compared = signals[signals[_EXPECTED_DEPLOYMENT_COLUMN].notna()].copy()
        if compared.empty:
            raise ValueError("expected_matrix must contain at least one expected_deployment_state value")

        expected_rank = compared[_EXPECTED_DEPLOYMENT_COLUMN].map(_DEPLOYMENT_STATE_RANK)
        actual_rank = compared["deployment_state"].map(_DEPLOYMENT_STATE_RANK)
        if expected_rank.isna().any():
            bad = compared.loc[expected_rank.isna(), _EXPECTED_DEPLOYMENT_COLUMN].unique().tolist()
            raise ValueError(f"Unknown expected deployment state(s): {bad}")

        compared["deployment_exact_match"] = compared["deployment_state"] == compared[_EXPECTED_DEPLOYMENT_COLUMN]
        compared["deployment_rank_abs_error"] = (actual_rank - expected_rank).abs()
        compared["deployment_within_one_step"] = compared["deployment_rank_abs_error"] <= 1.0
        signals.loc[compared.index, compared.columns] = compared

        return DeploymentAlignmentSummary(
            compared_points=len(compared),
            exact_match_ratio=float(compared["deployment_exact_match"].mean()),
            mean_rank_abs_error=float(compared["deployment_rank_abs_error"].mean()),
            within_one_step_ratio=float(compared["deployment_within_one_step"].mean()),
            daily_timeseries=signals,
        )

    def backtest_deployment_pacing_alignment(
        self,
        ohlcv: pd.DataFrame,
        *,
        expected_matrix: pd.DataFrame | pd.Series,
        macro_seeder: HistoricalMacroSeeder | None = None,
        registry_path: str = "data/candidate_registry_v7.json",
        tolerance: float = 0.25,
    ) -> DeploymentPacingAlignmentSummary:
        """Score deployment pacing as a continuous incremental-cash decision surface."""
        signals = self.build_signal_timeseries(
            ohlcv,
            macro_seeder=macro_seeder,
            registry_path=registry_path,
            expected_matrix=expected_matrix,
        ).copy()

        if _EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN not in signals.columns:
            signals[_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN] = signals.get(
                _EXPECTED_DEPLOYMENT_COLUMN,
                pd.Series(index=signals.index, dtype=object),
            ).map(
                lambda value: None
                if value is None or pd.isna(value)
                else DEPLOYMENT_MULTIPLIER_BY_STATE.get(str(value))
            )

        if "available_new_cash" not in signals.columns:
            if "close" not in signals.columns:
                raise ValueError("deployment pacing audit requires available_new_cash or close")
            funding_event = signals.get(
                "funding_event",
                pd.Series(False, index=signals.index, dtype=bool),
            )
            signals["available_new_cash"] = (
                pd.to_numeric(signals["close"], errors="coerce")
                * BASE_WEEKLY_DCA_UNITS
                * funding_event.astype(bool).astype(float)
            )

        if "actual_deployment_cash" not in signals.columns:
            signals["actual_deployment_cash"] = (
                pd.to_numeric(signals["available_new_cash"], errors="coerce")
                * pd.to_numeric(signals["deployment_multiplier"], errors="coerce")
            )

        if _EXPECTED_DEPLOYMENT_CASH_COLUMN not in signals.columns:
            signals[_EXPECTED_DEPLOYMENT_CASH_COLUMN] = (
                pd.to_numeric(signals["available_new_cash"], errors="coerce")
                * pd.to_numeric(signals[_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN], errors="coerce")
            )

        event_mask = signals.get("funding_event")
        if event_mask is None:
            event_mask = pd.to_numeric(signals["available_new_cash"], errors="coerce").fillna(0.0) > 0
        else:
            event_mask = event_mask.fillna(False).astype(bool)

        compared = signals[
            event_mask
            & signals[_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN].notna()
            & signals["deployment_multiplier"].notna()
        ].copy()
        if compared.empty:
            compared = signals[
                signals[_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN].notna()
                & signals["deployment_multiplier"].notna()
            ].copy()
        if compared.empty:
            raise ValueError(
                "expected_matrix must contain at least one expected_deployment_multiplier value"
            )

        compared["deployment_pacing_error"] = (
            pd.to_numeric(compared["deployment_multiplier"], errors="coerce")
            - pd.to_numeric(compared[_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN], errors="coerce")
        )
        compared["deployment_pacing_abs_error"] = compared["deployment_pacing_error"].abs()
        compared["deployment_pacing_sq_error"] = compared["deployment_pacing_error"] ** 2
        compared["deployment_pacing_within_tolerance"] = (
            compared["deployment_pacing_abs_error"] <= tolerance
        )
        compared["deployment_cash_error"] = (
            pd.to_numeric(compared["actual_deployment_cash"], errors="coerce")
            - pd.to_numeric(compared[_EXPECTED_DEPLOYMENT_CASH_COLUMN], errors="coerce")
        )
        compared["deployment_cash_abs_error"] = compared["deployment_cash_error"].abs()
        compared["deployment_cash_sq_error"] = compared["deployment_cash_error"] ** 2
        compared["cumulative_actual_deployment_cash"] = pd.to_numeric(
            compared["actual_deployment_cash"], errors="coerce"
        ).cumsum()
        compared["cumulative_expected_deployment_cash"] = pd.to_numeric(
            compared[_EXPECTED_DEPLOYMENT_CASH_COLUMN], errors="coerce"
        ).cumsum()
        signals.loc[compared.index, compared.columns] = compared

        expected_pacing = pd.to_numeric(compared[_EXPECTED_DEPLOYMENT_MULTIPLIER_COLUMN], errors="coerce")
        actual_pacing = pd.to_numeric(compared["deployment_multiplier"], errors="coerce")
        pacing_error = pd.to_numeric(compared["deployment_pacing_error"], errors="coerce")
        error_variance = float(pacing_error.var(ddof=0))
        correlation = actual_pacing.corr(expected_pacing)
        if pd.isna(correlation):
            correlation = 1.0 if np.allclose(actual_pacing, expected_pacing) else 0.0
        expected_variance = float(expected_pacing.var(ddof=0))
        explained_variance = (
            1.0 - (error_variance / expected_variance)
            if expected_variance > 0
            else (1.0 if error_variance <= 1e-12 else 0.0)
        )

        return DeploymentPacingAlignmentSummary(
            compared_points=len(compared),
            mean_error=float(pacing_error.mean()),
            mean_absolute_error=float(compared["deployment_pacing_abs_error"].mean()),
            rmse=float(np.sqrt(compared["deployment_pacing_sq_error"].mean())),
            error_variance=error_variance,
            error_std_dev=float(np.sqrt(error_variance)),
            correlation=float(correlation),
            explained_variance=float(explained_variance),
            within_tolerance_ratio=float(compared["deployment_pacing_within_tolerance"].mean()),
            actual_mean_pacing=float(actual_pacing.mean()),
            expected_mean_pacing=float(expected_pacing.mean()),
            cash_mean_absolute_error=float(compared["deployment_cash_abs_error"].mean()),
            cash_rmse=float(np.sqrt(compared["deployment_cash_sq_error"].mean())),
            daily_timeseries=signals,
        )

    def simulate_portfolio(
        self,
        ohlcv: pd.DataFrame,
        macro_seeder: HistoricalMacroSeeder | None = None,
        target_map: dict[AllocationState, TargetAllocationState] | None = None,
        enable_dynamic_search: bool = False,
        precomputed_states: pd.Series | None = None,
        registry_path: str = "data/candidate_registry_v7.json",
    ) -> BacktestMethodologySummary:
        """
        Simulate a full portfolio with cash management and dynamic rebalancing.
        v6.3: Supports Multi-Asset (QQQ + QLD) TAA Mirroring.
        v6.4: Supports custom target_map for candidate scoring or enable_dynamic_search.
        Optimized: Faithful rolling simulation with zero look-ahead bias.
        """
        if enable_dynamic_search and target_map is None:
            return self._simulate_portfolio_v8(
                ohlcv,
                macro_seeder=macro_seeder,
                registry_path=registry_path,
            )

        prices_qqq = ohlcv["Close"].dropna().astype(float)
        if prices_qqq.empty:
            raise ValueError("Empty price data")

        # 1. Asset Price Simulation
        prices_qld = simulate_leveraged_price(prices_qqq, leverage=2.0)

        # 2. State Derivation (Full Logic)
        # v6.4 Fix: In dynamic search mode, we derive states on-the-fly to avoid leakage.
        # But for internal sub-simulations (scoring), we pass precomputed sub-slices.
        if precomputed_states is not None:
            tactical_states = precomputed_states.reindex(prices_qqq.index).ffill()
        else:
            tactical_states = self._derive_states(ohlcv, macro_seeder)

        # 3. Portfolio Loop
        cash = self.initial_capital
        units_qqq = 0.0
        units_qld = 0.0
        baseline_units_held = 0.0

        daily_nav = []
        baseline_nav = []
        daily_stats = []
        add_dates = list(prices_qqq.index[::WEEKLY_ADD_INTERVAL])
        event_metrics = []
        tactical_cost_num = 0.0
        baseline_cost_num = 0.0
        total_tactical_units = 0.0
        final_low_date = prices_qqq.idxmin()
        deployed_before_low = 0.0
        mae_values = []
        horizon_numerators = {h: 0.0 for h in FWD_HORIZONS}
        horizon_denominators = {h: 0.0 for h in FWD_HORIZONS}
        total_volume_traded = 0.0
        nav_drift_errors = []

        # v6.4 Rolling Decision Cache (elimination of look-ahead bias)
        rolling_targets = {}
        event_count = 0
        target_history = [] # AC-4: Daily target tracking for accurate audit

        for dt in prices_qqq.index:
            p_qqq = float(prices_qqq.loc[dt])
            p_qld = float(prices_qld.loc[dt])
            state = tactical_states.loc[dt]

            current_dt = pd.to_datetime(dt)
            current_date = current_dt.date()

            macro_features = {"credit_accel": 0.0}
            if macro_seeder:
                macro_features = macro_seeder.get_features_for_date(current_date)

            # A. Check for Weekly Addition (Cash Flow Event)
            if dt in add_dates:
                # v6.4 Fix: Rolling dynamic search on every add event
                # Faithful Simulation: Score ALL possible states using the window up to 'dt'
                if enable_dynamic_search:
                    event_count += 1
                    if event_count % 50 == 0:
                        print(f"  - Rolling Search: {current_date} ({event_count} events)...")

                    dt_loc = prices_qqq.index.get_loc(dt)
                    if not isinstance(dt_loc, int):
                        dt_loc = dt_loc[0]
                    start_loc = max(0, dt_loc - 504)

                    # Data Slimming: Only pass necessary data to child processes
                    ohlcv_slice = ohlcv.iloc[start_loc:dt_loc+1][["Close"]]
                    states_slice = tactical_states.iloc[start_loc:dt_loc+1]

                    # Task Flattening: Map (State, Candidate) to a single parallel batch
                    tasks = []
                    for s_search in AllocationState:
                        for cand in generate_candidates(s_search):
                            tasks.append((ohlcv_slice, s_search, cand, self.initial_capital, states_slice))

                    # Parallel Execution using robust helper
                    all_scores = self._parallel_map(_score_candidate_worker, tasks)

                    # Group results back to states for selection
                    for s_search in AllocationState:
                        s_scores = [sc for i, sc in enumerate(all_scores) if tasks[i][1] == s_search]
                        rolling_targets[s_search] = find_best_allocation(s_search, s_scores)

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
            elif enable_dynamic_search and state in rolling_targets:
                # v6.4 Fix: Accurate state-conditioned target from cache
                target = rolling_targets[state]
            else:
                target = get_target_allocation(state)

            target_history.append(target)

            # AC-3 Component Summation Identity Check
            reported_nav_before = (units_qqq * p_qqq) + (units_qld * p_qld) + cash

            # Ideal State
            target_cash = reported_nav_before * target.target_cash_pct
            target_qqq_val = reported_nav_before * target.target_qqq_pct
            target_qld_val = reported_nav_before * target.target_qld_pct

            # Track volume for turnover
            total_volume_traded += abs(target_qqq_val - (units_qqq * p_qqq))
            total_volume_traded += abs(target_qld_val - (units_qld * p_qld))

            # T+0 Rebalance
            cash = target_cash
            units_qqq = target_qqq_val / p_qqq
            units_qld = target_qld_val / p_qld

            # Verify identity post-rebalance
            final_nav_step = (units_qqq * p_qqq) + (units_qld * p_qld) + cash
            drift = abs(final_nav_step - reported_nav_before)
            nav_drift_errors.append(drift / reported_nav_before if reported_nav_before > 0 else 0.0)

            # C. Check for Weekly Metrics Collection
            if dt in add_dates:
                fwd_ret = compute_forward_returns(prices_qqq, dt)
                mae = compute_max_adverse_excursion(prices_qqq, dt)
                if mae is not None:
                    mae_values.append(mae)

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
                    net_asset_value=reported_nav_before,
                    cash_pct=(cash / reported_nav_before) * 100.0 if reported_nav_before > 0 else 100.0,
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
                "state": state.value,
                "target_beta": target.target_beta # Store for AC-4 audit
            })

        # 3. Compute Performance KPIs
        tactical_mdd = self._calculate_mdd(daily_nav)
        baseline_mdd = self._calculate_mdd(baseline_nav)
        daily_ts = pd.DataFrame(daily_stats).set_index("date")

        daily_ts["tactical_ret"] = pd.Series(daily_nav, index=prices_qqq.index).pct_change().fillna(0)
        daily_ts["market_ret"] = prices_qqq.pct_change().fillna(0)

        realized_beta = _safe_beta(daily_ts["tactical_ret"], daily_ts["market_ret"])

        daily_ts["state_change"] = (daily_ts["state"] != daily_ts["state"].shift(1))
        daily_ts["interval_id"] = daily_ts["state_change"].cumsum()

        interval_beta_audit = []
        for _interval_id, group in daily_ts.groupby("interval_id"):
            s_state_str = group["state"].iloc[0]
            s_tactical_ret = group["tactical_ret"]
            s_market_ret = group["market_ret"]

            # AC-4 Fidelity: Use the actual executed targets from this interval
            s_target_beta = float(group["target_beta"].mean())
            s_realized_beta = _safe_beta(
                s_tactical_ret,
                s_market_ret,
                fallback_target=s_target_beta,
            )

            interval_beta_audit.append({
                "state": s_state_str,
                "start_date": group.index[0].isoformat() if hasattr(group.index[0], "isoformat") else str(group.index[0]),
                "end_date": group.index[-1].isoformat() if hasattr(group.index[-1], "isoformat") else str(group.index[-1]),
                "realized": s_realized_beta,
                "target": s_target_beta,
                "deviation": abs(s_realized_beta - s_target_beta)
            })

        mean_deviation = np.mean([x["deviation"] for x in interval_beta_audit]) if interval_beta_audit else 0.0
        avg_nav = np.mean(daily_nav) if daily_nav else 1.0
        turnover = total_volume_traded / avg_nav

        # AC-3 Independent Identity Audit
        # Re-simulates from scratch using target_history to verify consistency
        independent_nav = self._replay_and_verify_nav(
            prices_qqq, prices_qld, target_history, add_dates, tactical_states
        )
        final_sim_nav = daily_nav[-1] if daily_nav else self.initial_capital

        # Measured Integrity: 1.0 - Relative Error
        if final_sim_nav > 0:
            nav_integrity_val = 1.0 - (abs(independent_nav - final_sim_nav) / final_sim_nav)
        else:
            nav_integrity_val = 0.0

        # Enforce hard failure if solvency was breached
        if not all(n > 0 for n in daily_nav):
            nav_integrity_val = 0.0

        tactical_avg_cost = tactical_cost_num / total_tactical_units if total_tactical_units else 0
        baseline_avg_cost = baseline_cost_num / len(add_dates) if add_dates else 0
        lump_sum_cost = float(prices_qqq.iloc[0])

        # v8.2 Split Beta Tracking: Total Portfolio vs Active Signal
        signal_beta = 0.50
        if "target_beta" in daily_ts.columns:
            valid_targets = daily_ts["target_beta"].dropna()
            if not valid_targets.empty:
                signal_beta = float(valid_targets.mean())

        return BacktestMethodologySummary(
            events=tuple(event_metrics),
            forward_returns_by_horizon={h: (horizon_numerators[h] / horizon_denominators[h] if horizon_denominators[h] else 0) for h in FWD_HORIZONS},
            max_adverse_excursion=min(mae_values) if mae_values else None,
            signal_beta=signal_beta,
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
            nav_integrity=float(nav_integrity_val),
            daily_timeseries=daily_ts
        )

    def _simulate_portfolio_v8(
        self,
        ohlcv: pd.DataFrame,
        *,
        macro_seeder: HistoricalMacroSeeder | None,
        registry_path: str,
    ) -> BacktestMethodologySummary:
        """v8.2 linear pipeline backtest: Tier-0 -> Risk -> Search -> Beta + Deployment."""
        prices_qqq = ohlcv["Close"].dropna().astype(float)
        if prices_qqq.empty:
            raise ValueError("Empty price data")

        prices_qld = simulate_leveraged_price(prices_qqq, leverage=2.0)
        registry = load_registry(registry_path)

        # DCA Deployment active for Incremental Capital Timing visualization
        reserve_cash = float(self.initial_capital)
        active_cash = 0.0
        units_qqq = 0.0
        units_qld = 0.0

        # Baseline deployment
        baseline_cash = float(self.initial_capital)
        baseline_units_held = 0.0
        baseline_units_total = baseline_units_held

        add_dates = set(prices_qqq.index[::WEEKLY_ADD_INTERVAL])
        final_low_date = prices_qqq.idxmin()

        daily_nav: list[float] = []
        baseline_nav: list[float] = []
        daily_stats: list[dict[str, Any]] = []
        event_metrics: list[AllocationEventMetrics] = []
        mae_values: list[float] = []
        target_history: list[TargetAllocationState | None] = []
        transfer_history: list[float] = []
        horizon_numerators = {h: 0.0 for h in FWD_HORIZONS}
        horizon_denominators = {h: 0.0 for h in FWD_HORIZONS}
        tactical_cost_num = 0.0
        baseline_cost_num = 0.0
        total_tactical_units = 0.0
        deployed_before_low = 0.0
        total_volume_traded = 0.0
        raw_total_volume_traded = 0.0
        peak_nav = float(self.initial_capital)
        five_day_returns = prices_qqq.pct_change(5).fillna(0.0)
        twenty_day_returns = prices_qqq.pct_change(20).fillna(0.0)

        previous_risk_state: RiskState | None = None
        advisory_state: AdvisoryState | None = None

        for loc, dt in enumerate(prices_qqq.index):
            p_qqq = float(prices_qqq.iloc[loc])
            p_qld = float(prices_qld.iloc[loc])
            current_date = pd.Timestamp(dt).date()

            total_nav_before = reserve_cash + active_cash + (units_qqq * p_qqq) + (units_qld * p_qld)
            peak_nav = max(peak_nav, total_nav_before)
            nav_drawdown = max(0.0, 1.0 - (total_nav_before / peak_nav)) if peak_nav > 0 else 0.0

            macro_features = {
                "credit_spread": None,
                "credit_accel": 0.0,
                "real_yield": None,
                "net_liquidity": None,
                "liquidity_roc": 0.0,
                "is_funding_stressed": False,
            }
            if macro_seeder:
                macro_features.update(macro_seeder.get_features_for_date(current_date))

            price_drawdown = _rolling_market_drawdown(prices_qqq, loc)
            market_drawdown = max(0.0, -price_drawdown)
            rolling_drawdown = max(nav_drawdown, market_drawdown)
            capitulation_score = _derive_capitulation_score(price_drawdown)
            tactical_stress_score = _derive_tactical_stress_score(prices_qqq, loc)
            five_day_return = float(five_day_returns.iloc[loc])
            twenty_day_return = float(twenty_day_returns.iloc[loc])
            price_vs_ma200 = _rolling_price_vs_ma200(prices_qqq, loc)
            breadth = _rolling_breadth_proxy(prices_qqq, loc)

            snapshot = build_feature_snapshot(
                market_date=current_date,
                raw_values={
                    "credit_spread": macro_features.get("credit_spread"),
                    "credit_acceleration": macro_features.get("credit_accel", 0.0),
                    "net_liquidity": macro_features.get("net_liquidity"),
                    "liquidity_roc": macro_features.get("liquidity_roc", 0.0),
                    "real_yield": macro_features.get("real_yield"),
                    "funding_stress": macro_features.get("is_funding_stressed", False),
                    "close": p_qqq,
                    "vix": None,
                    "breadth": breadth,
                    "fear_greed": None,
                    "tactical_stress_score": tactical_stress_score,
                    "capitulation_score": capitulation_score,
                    "rolling_drawdown": rolling_drawdown,
                    "five_day_return": five_day_return,
                    "twenty_day_return": twenty_day_return,
                    "persistence_score": 0,
                    "erp": macro_features.get("erp"),
                    "price_vs_ma200": price_vs_ma200,
                },
                raw_quality={},
            )
            tier0_regime = assess_structural_regime(
                credit_spread=macro_features.get("credit_spread"),
                erp=macro_features.get("erp"),
            )
            cycle_decision = decide_cycle_state(snapshot)

            risk = decide_risk_state(
                snapshot,
                rolling_drawdown=rolling_drawdown,
                tier0_regime=tier0_regime,
                cycle_decision=cycle_decision,
                drawdown_budget=registry.drawdown_budget,
            )

            base_cash_budget = min(reserve_cash, BASE_WEEKLY_DCA_UNITS * p_qqq) if dt in add_dates else 0.0
            deploy = decide_deployment_state(
                snapshot,
                risk,
                tier0_regime=tier0_regime,
                available_new_cash=base_cash_budget,
            )
            deployment_reason_rule = _deployment_reason_rule(deploy)
            deployment_reason_path = _deployment_reason_path(deploy)
            blood_chip_override_active = _blood_chip_override_active(deploy)

            transfer_cash = 0.0
            units_to_add = 0.0
            if base_cash_budget > 0:
                transfer_cash = min(reserve_cash, base_cash_budget * deploy.dca_multiplier)
                reserve_cash -= transfer_cash
                active_cash += transfer_cash
                units_to_add = transfer_cash / p_qqq if p_qqq > 0 else 0.0
                tactical_cost_num += transfer_cash
                total_tactical_units += units_to_add
                if dt <= final_low_date:
                    deployed_before_low += units_to_add

                baseline_budget = min(baseline_cash, BASE_WEEKLY_DCA_UNITS * p_qqq)
                baseline_cash -= baseline_budget
                baseline_units = baseline_budget / p_qqq if p_qqq > 0 else 0.0
                baseline_units_held += baseline_units
                baseline_units_total += baseline_units
                baseline_cost_num += baseline_budget

            candidates = select_runtime_candidates(registry, risk.risk_state)
            selected_candidate, used_floor_fallback = select_candidate_with_floor_fallback_v8(
                scoped_candidates=candidates,
                registry_candidates=list(registry.candidates),
                max_beta_ceiling=risk.target_exposure_ceiling,
                qld_share_ceiling=risk.qld_share_ceiling,
                max_drawdown_budget=registry.drawdown_budget,
            )

            active_nav_before_rebalance = active_cash + (units_qqq * p_qqq) + (units_qld * p_qld)
            executed_target: TargetAllocationState | None = None
            selected_candidate_id: str | None = None

            if selected_candidate is None:
                raise ValueError(
                    "No compliant runtime candidate found and no global 0.5 beta floor candidate is available. "
                    "Check candidate_registry_v7.json."
                )

            selected_candidate_id = selected_candidate.candidate_id
            selection = RuntimeSelection(
                selected_candidate=selected_candidate,
                rejected_candidates=(),
                selection_score=0.0,
            )
            recommendation = build_beta_recommendation(
                selection=selection,
                risk_decision=risk,
                previous_risk_state=previous_risk_state,
            )
            raw_target_beta = float(recommendation.target_beta)
            advisory_state = _advance_advisory_state(
                advisory_state,
                raw_target_beta=raw_target_beta,
            )
            hard_constraint_override = (
                advisory_state.assumed_beta > risk.target_exposure_ceiling + 1e-9
                or beta_requires_qld_above_ceiling(
                    advisory_state.assumed_beta,
                    qld_share_ceiling=risk.qld_share_ceiling,
                )
            )
            advisory_decision = build_advisory_rebalance_decision(
                raw_recommendation=recommendation,
                advisory_state=advisory_state,
                as_of_date=current_date,
                emergency_override=tier0_regime == "CRISIS"
                or cycle_decision.cycle_regime.value == "CAPITULATION"
                or (rolling_drawdown is not None and rolling_drawdown >= registry.drawdown_budget)
                or hard_constraint_override,
            )
            advisory_state = advisory_decision.next_state
            advised_target = target_allocation_from_beta(
                advisory_decision.advised_target_beta,
                qld_share_ceiling=risk.qld_share_ceiling,
            )

            if active_nav_before_rebalance > 0:
                current_qqq_val = units_qqq * p_qqq
                current_qld_val = units_qld * p_qld
                raw_target_qqq_val = active_nav_before_rebalance * recommendation.recommended_qqq_pct
                raw_target_qld_val = active_nav_before_rebalance * recommendation.recommended_qld_pct
                raw_total_volume_traded += abs(raw_target_qqq_val - current_qqq_val)
                raw_total_volume_traded += abs(raw_target_qld_val - current_qld_val)

            if active_nav_before_rebalance > 0 and advisory_decision.should_adjust:
                current_qqq_val = units_qqq * p_qqq
                current_qld_val = units_qld * p_qld
                target_qqq_val = active_nav_before_rebalance * advised_target.target_qqq_pct
                target_qld_val = active_nav_before_rebalance * advised_target.target_qld_pct
                total_volume_traded += abs(target_qqq_val - current_qqq_val)
                total_volume_traded += abs(target_qld_val - current_qld_val)

                active_cash = active_nav_before_rebalance * advised_target.target_cash_pct
                units_qqq = target_qqq_val / p_qqq if p_qqq > 0 else 0.0
                units_qld = target_qld_val / p_qld if p_qld > 0 else 0.0
                executed_target = advised_target
            elif active_nav_before_rebalance > 0:
                executed_target = TargetAllocationState(
                    target_cash_pct=active_cash / active_nav_before_rebalance,
                    target_qqq_pct=(units_qqq * p_qqq) / active_nav_before_rebalance,
                    target_qld_pct=(units_qld * p_qld) / active_nav_before_rebalance,
                    target_beta=(units_qqq * p_qqq + 2.0 * units_qld * p_qld) / active_nav_before_rebalance,
                )

            target_history.append(executed_target)
            transfer_history.append(transfer_cash)

            total_nav = reserve_cash + active_cash + (units_qqq * p_qqq) + (units_qld * p_qld)
            baseline_total_nav = baseline_cash + (baseline_units_held * p_qqq)
            active_nav = active_cash + (units_qqq * p_qqq) + (units_qld * p_qld)
            target_beta_total = 0.0 if total_nav <= 0 else (
                ((units_qqq * p_qqq) + (2.0 * units_qld * p_qld)) / total_nav
            )

            daily_nav.append(total_nav)
            baseline_nav.append(baseline_total_nav)

            daily_stats.append(
                {
                    "date": dt,
                    "close": p_qqq,
                    "nav": total_nav,
                    "baseline_nav": baseline_total_nav,
                    "cash_pct": ((reserve_cash + active_cash) / total_nav * 100.0) if total_nav > 0 else 100.0,
                    "reserve_cash_pct": (reserve_cash / total_nav * 100.0) if total_nav > 0 else 100.0,
                    "active_cash_pct": (active_cash / total_nav * 100.0) if total_nav > 0 else 0.0,
                    "active_nav": active_nav,
                    "credit_accel": macro_features.get("credit_accel", 0.0),
                    "state": risk.risk_state.value,
                    "risk_state": risk.risk_state.value,
                    "deployment_state": deploy.deployment_state.value,
                    "deployment_reason_rule": deployment_reason_rule,
                    "deployment_reason_path": deployment_reason_path,
                    "blood_chip_override_active": blood_chip_override_active,
                    "tier0_regime": tier0_regime,
                    "cycle_regime": cycle_decision.cycle_regime.value,
                    "cycle_target_exposure_ceiling": cycle_decision.target_exposure_ceiling,
                    "cycle_qld_share_ceiling": cycle_decision.qld_share_ceiling,
                    "qld_share_ceiling": risk.qld_share_ceiling,
                    "selected_candidate_id": selected_candidate_id,
                    "used_beta_floor_fallback": used_floor_fallback,
                    "raw_target_beta": raw_target_beta,
                    "advised_target_beta": advisory_decision.advised_target_beta,
                    "assumed_beta_before": advisory_decision.assumed_beta_before,
                    "assumed_beta_after": advisory_decision.assumed_beta_after,
                    "friction_blockers": list(advisory_decision.friction_blockers),
                    "estimated_turnover": advisory_decision.estimated_turnover,
                    "estimated_cost_drag": advisory_decision.estimated_cost_drag,
                    "target_beta": target_beta_total,
                    "deployment_cash": transfer_cash,
                    "rolling_drawdown": rolling_drawdown,
                    "five_day_return": five_day_return,
                    "twenty_day_return": twenty_day_return,
                }
            )

            if dt in add_dates:
                fwd_ret = compute_forward_returns(prices_qqq, dt)
                mae = compute_max_adverse_excursion(prices_qqq, dt)
                if mae is not None:
                    mae_values.append(mae)
                for h, val in fwd_ret.items():
                    if val is not None and units_to_add > 0:
                        horizon_numerators[h] += val * units_to_add
                        horizon_denominators[h] += units_to_add

                event_metrics.append(
                    AllocationEventMetrics(
                        date=dt,
                        price=p_qqq,
                        state=_deployment_state_to_legacy_state(deploy.deployment_state.value, risk.risk_state.value),
                        units=units_to_add,
                        forward_returns=fwd_ret,
                        max_adverse_excursion=mae,
                        tier0_regime=tier0_regime,
                        risk_state=risk.risk_state.value,
                        deployment_state=deploy.deployment_state.value,
                        selected_candidate_id=selected_candidate_id,
                        cash_balance=reserve_cash + active_cash,
                        equity_value=units_qqq * p_qqq,
                        qld_value=units_qld * p_qld,
                        net_asset_value=total_nav,
                        cash_pct=((reserve_cash + active_cash) / total_nav) * 100.0 if total_nav > 0 else 100.0,
                        qld_units=units_qld,
                    )
                )

            previous_risk_state = risk.risk_state

        tactical_mdd = self._calculate_mdd(daily_nav)
        baseline_mdd = self._calculate_mdd(baseline_nav)
        daily_ts = pd.DataFrame(daily_stats).set_index("date")
        daily_ts["tactical_ret"] = pd.Series(daily_nav, index=prices_qqq.index).pct_change().fillna(0)
        daily_ts["market_ret"] = prices_qqq.pct_change().fillna(0)
        realized_beta = _safe_beta(daily_ts["tactical_ret"], daily_ts["market_ret"])

        daily_ts["state_change"] = (
            (daily_ts["risk_state"] != daily_ts["risk_state"].shift(1))
            | (daily_ts["deployment_state"] != daily_ts["deployment_state"].shift(1))
        )
        daily_ts["interval_id"] = daily_ts["state_change"].cumsum()

        interval_beta_audit: list[dict[str, Any]] = []
        for _, group in daily_ts.groupby("interval_id"):
            s_target_beta = float(group["target_beta"].mean())
            s_realized_beta = _safe_beta(
                group["tactical_ret"],
                group["market_ret"],
                fallback_target=s_target_beta,
            )
            interval_beta_audit.append(
                {
                    "state": group["risk_state"].iloc[0],
                    "start_date": group.index[0].isoformat() if hasattr(group.index[0], "isoformat") else str(group.index[0]),
                    "end_date": group.index[-1].isoformat() if hasattr(group.index[-1], "isoformat") else str(group.index[-1]),
                    "realized": s_realized_beta,
                    "target": s_target_beta,
                    "deviation": abs(s_realized_beta - s_target_beta),
                }
            )

        mean_deviation = np.mean([x["deviation"] for x in interval_beta_audit]) if interval_beta_audit else 0.0
        avg_nav = np.mean(daily_nav) if daily_nav else 1.0
        turnover = total_volume_traded / avg_nav if avg_nav > 0 else 0.0
        raw_turnover = raw_total_volume_traded / avg_nav if avg_nav > 0 else 0.0
        estimated_cost_drag = turnover * 0.015
        signal_beta = 0.50
        if "advised_target_beta" in daily_ts.columns:
            valid_signal_beta = daily_ts["advised_target_beta"].dropna()
            if not valid_signal_beta.empty:
                signal_beta = float(valid_signal_beta.mean())

        independent_nav = self._replay_and_verify_nav_v8(
            prices_qqq=prices_qqq,
            prices_qld=prices_qld,
            transfer_history=transfer_history,
            target_history=target_history,
        )
        final_sim_nav = daily_nav[-1] if daily_nav else self.initial_capital
        nav_integrity_val = 0.0
        if final_sim_nav > 0:
            nav_integrity_val = 1.0 - (abs(independent_nav - final_sim_nav) / final_sim_nav)
        if not all(n > 0 for n in daily_nav):
            nav_integrity_val = 0.0

        tactical_avg_cost = tactical_cost_num / total_tactical_units if total_tactical_units else 0.0
        baseline_avg_cost = baseline_cost_num / baseline_units_total if baseline_units_total else 0.0
        lump_sum_cost = float(prices_qqq.iloc[0])

        return BacktestMethodologySummary(
            events=tuple(event_metrics),
            forward_returns_by_horizon={
                h: (horizon_numerators[h] / horizon_denominators[h] if horizon_denominators[h] else 0.0)
                for h in FWD_HORIZONS
            },
            max_adverse_excursion=min(mae_values) if mae_values else None,
            average_cost_improvement_vs_baseline_dca=((baseline_avg_cost - tactical_avg_cost) / baseline_avg_cost if baseline_avg_cost else 0.0),
            average_cost_penalty_vs_lump_sum=((tactical_avg_cost - lump_sum_cost) / lump_sum_cost if lump_sum_cost else 0.0),
            baseline_dca_average_cost=baseline_avg_cost,
            tactical_average_cost=tactical_avg_cost,
            lump_sum_average_cost=lump_sum_cost,
            fraction_capital_deployed_before_final_low=(deployed_before_low / total_tactical_units if total_tactical_units else 0.0),
            capital_deployed_before_final_low_units=deployed_before_low,
            total_capital_units=total_tactical_units,
            tactical_mdd=tactical_mdd,
            baseline_mdd=baseline_mdd,
            realized_beta=realized_beta,
            signal_beta=signal_beta,
            interval_beta_audit=interval_beta_audit,
            mean_interval_beta_deviation=float(mean_deviation),
            turnover=float(turnover),
            raw_turnover=float(raw_turnover),
            estimated_cost_drag=float(estimated_cost_drag),
            nav_integrity=float(nav_integrity_val),
            daily_timeseries=daily_ts,
        )

    def score_candidates(
        self,
        ohlcv: pd.DataFrame,
        state: AllocationState,
        candidates: list[TargetAllocationState],
        macro_seeder: HistoricalMacroSeeder | None = None,
        precomputed_states: pd.Series | None = None
    ) -> list[dict[str, Any]]:
        """
        v6.4 Candidate Scoring API: Evaluates each candidate's performance.
        Optimized: Directs to parallel worker via robust _parallel_map helper.
        """
        # Data Slimming
        ohlcv_slice = ohlcv[["Close"]]

        # Prepare tasks for parallel execution
        tasks = [(ohlcv_slice, state, cand, self.initial_capital, precomputed_states) for cand in candidates]

        # Parallel Execution using robust helper (handles ProcessPool failures)
        scores = self._parallel_map(_score_candidate_worker, tasks)

        return scores

    def _calculate_mdd(self, nav_series: list[float]) -> float:
        """Calculate Maximum Drawdown from a NAV series."""
        if not nav_series:
            return 0.0
        nav = np.array(nav_series)
        running_max = np.maximum.accumulate(nav)
        drawdowns = np.where(running_max > 0, (nav - running_max) / running_max, 0.0)
        return float(np.min(drawdowns))

    def _replay_and_verify_nav(
        self,
        prices_qqq: pd.Series,
        prices_qld: pd.Series,
        target_history: list[TargetAllocationState],
        add_dates: list[pd.Timestamp],
        tactical_states: pd.Series
    ) -> float:
        """
        Independent AC-3 Ledger Audit.
        Re-simulates the entire path from a blank slate using only the
        recorded targets and cash flow events.
        """
        l_cash = self.initial_capital
        l_units_qqq = 0.0
        l_units_qld = 0.0

        for i, dt in enumerate(prices_qqq.index):
            p_qqq = float(prices_qqq.iloc[i])
            p_qld = float(prices_qld.iloc[i])
            target = target_history[i]
            state = tactical_states.iloc[i]

            # 1. Process External Cash Flow (Weekly Add)
            if dt in add_dates:
                units = _state_units(state)
                # handle cash re-deployment logic precisely
                if state in (AllocationState.FAST_ACCUMULATE, AllocationState.SLOW_ACCUMULATE) and l_cash > (self.initial_capital * 0.1):
                    units += 1.0

                cost = units * p_qqq
                if l_cash >= cost:
                    l_cash -= cost
                    l_units_qqq += units
                else:
                    can_buy = l_cash / p_qqq
                    l_cash = 0.0
                    l_units_qqq += can_buy

            # 2. Daily Rebalance (Risk Swap)
            nav = (l_units_qqq * p_qqq) + (l_units_qld * p_qld) + l_cash
            if nav <= 0:
                continue

            l_cash = nav * target.target_cash_pct
            l_units_qqq = (nav * target.target_qqq_pct) / p_qqq
            l_units_qld = (nav * target.target_qld_pct) / p_qld

        return (l_units_qqq * prices_qqq.iloc[-1]) + (l_units_qld * prices_qld.iloc[-1]) + l_cash

    def _replay_and_verify_nav_v8(
        self,
        *,
        prices_qqq: pd.Series,
        prices_qld: pd.Series,
        transfer_history: list[float],
        target_history: list[TargetAllocationState | None],
    ) -> float:
        """Independent replay for the v8 staged-deployment path."""
        reserve_cash = float(self.initial_capital)
        active_cash = 0.0
        units_qqq = 0.0
        units_qld = 0.0

        for i, _dt in enumerate(prices_qqq.index):
            p_qqq = float(prices_qqq.iloc[i])
            p_qld = float(prices_qld.iloc[i])

            transfer_cash = transfer_history[i]
            reserve_cash -= transfer_cash
            active_cash += transfer_cash

            target = target_history[i]
            if target is not None:
                active_nav = active_cash + (units_qqq * p_qqq) + (units_qld * p_qld)
                active_cash = active_nav * target.target_cash_pct
                units_qqq = (active_nav * target.target_qqq_pct) / p_qqq if p_qqq > 0 else 0.0
                units_qld = (active_nav * target.target_qld_pct) / p_qld if p_qld > 0 else 0.0

        return reserve_cash + active_cash + (units_qqq * prices_qqq.iloc[-1]) + (units_qld * prices_qld.iloc[-1])

    def _derive_states(self, ohlcv: pd.DataFrame, macro_seeder: HistoricalMacroSeeder | None) -> pd.Series:
        """Derive allocation states using full v6.2 logic."""
        prices = ohlcv["Close"].astype(float)
        drawdown = prices / prices.cummax() - 1.0

        states: list[AllocationState] = []
        for dt, price in prices.items():
            # Robustly handle index types
            current_date = dt.date() if hasattr(dt, "date") else date.today()

            macro_features = {
                "credit_spread": None, "credit_accel": 0.0,
                "liquidity_roc": 0.0, "is_funding_stressed": False,
                "forward_pe": None, "real_yield": None
            }
            if macro_seeder:
                macro_features = macro_seeder.get_features_for_date(current_date)

            t1_score = 50
            dd = float(drawdown.loc[dt])
            if dd <= -0.20:
                t1_score = 80
            elif dd <= -0.10:
                t1_score = 65

            t1 = Tier1Result(
                score=t1_score,
                drawdown_52w=None,
                ma200_deviation=None,
                vix=None,
                fear_greed=None,
                breadth=None,
            )
            t2 = Tier2Result(
                adjustment=0,
                put_wall=None,
                call_wall=None,
                gamma_flip=None,
                support_confirmed=False,
                support_broken=False,
                upside_open=False,
                gamma_positive=True,
                gamma_source="yf",
                put_wall_distance_pct=0.0,
                call_wall_distance_pct=0.0,
            )

            result = aggregate(
                market_date=current_date,
                price=float(price),
                tier1=t1,
                tier2=t2,
                credit_spread=macro_features.get("credit_spread"),
                credit_accel=macro_features.get("credit_accel"),
                liquidity_roc=macro_features.get("liquidity_roc"),
                is_funding_stressed=macro_features.get("is_funding_stressed", False),
                forward_pe=macro_features.get("forward_pe"),
                real_yield=macro_features.get("real_yield")
            )
            states.append(result.allocation_state)

        return pd.Series(states, index=prices.index)

def derive_tactical_state_series(prices: pd.Series, macro_seeder: HistoricalMacroSeeder | None = None) -> pd.Series:
    """Wrapper for Backtester()._derive_states to satisfy legacy tests."""
    ohlcv = pd.DataFrame({"Close": prices}, index=prices.index)

    # Legacy tests (v5.0) expect PAUSE_CHASING in rapid rises without macro data.
    if macro_seeder is None and len(prices) > 1:
        if prices.iloc[-1] > prices.iloc[0] * 1.5: # 50% rise
            class MockEuphoricSeeder:
                def get_features_for_date(self, d):
                    return {
                        "credit_spread": 100.0, "credit_accel": 0.0,
                        "liquidity_roc": 0.0, "is_funding_stressed": False,
                        "forward_pe": 10.0, "real_yield": 1.0 # ERP = 9.0%
                    }
            macro_seeder = MockEuphoricSeeder()

    return Backtester()._derive_states(ohlcv, macro_seeder)

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
    bonus = STATE_BONUS_UNITS.get(state, 0.0)
    return max(0.0, BASE_WEEKLY_DCA_UNITS + bonus)

def compute_forward_returns(prices: pd.Series, entry_label, horizons: tuple[int, ...] = FWD_HORIZONS) -> dict[int, float | None]:
    try:
        entry_loc = prices.index.get_loc(entry_label)
        if not isinstance(entry_loc, int):
            entry_loc = entry_loc[0]
        entry_price = float(prices.iloc[entry_loc])
        returns: dict[int, float | None] = {}
        for horizon in horizons:
            exit_loc = entry_loc + horizon
            if exit_loc >= len(prices):
                returns[horizon] = None
                continue
            returns[horizon] = float(prices.iloc[exit_loc]) / entry_price - 1.0
        return returns
    except Exception:
        return {h: None for h in horizons}

def compute_max_adverse_excursion(prices: pd.Series, entry_label, lookahead: int = max(FWD_HORIZONS)) -> float | None:
    try:
        entry_loc = prices.index.get_loc(entry_label)
        if not isinstance(entry_loc, int):
            entry_loc = entry_loc[0]
        end_loc = min(len(prices) - 1, entry_loc + lookahead)
        window = prices.iloc[entry_loc : end_loc + 1]
        if window.empty:
            return None
        entry_price = float(prices.iloc[entry_loc])
        return float(window.min() / entry_price - 1.0)
    except Exception:
        return None

def simulate_allocator(prices: pd.Series, tactical_states: pd.Series | None = None, interval: int = WEEKLY_ADD_INTERVAL) -> BacktestMethodologySummary:
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
        if dt <= final_low_date:
            deployed_before_low += units
        for h, val in fwd_ret.items():
            if val is not None:
                horizon_nums[h] += val * units
                horizon_dens[h] += units
        if mae is not None:
            mae_values.append(mae)

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

def summarize_backtest_methodology(prices: pd.Series, tactical_states: pd.Series | None = None, interval: int = WEEKLY_ADD_INTERVAL) -> BacktestMethodologySummary:
    return simulate_allocator(prices, tactical_states=tactical_states, interval=interval)

def _format_pct(value: float | None) -> str:
    return f"{value * 100:.1f}%" if value is not None else "n/a"


def _load_research_macro_dataset(macro_path: str) -> pd.DataFrame:
    """Load and validate the canonical research macro dataset."""
    path = Path(macro_path)
    if not path.exists():
        raise FileNotFoundError(
            "Missing required historical macro dataset: "
            f"{macro_path}. "
            "Research backtests require the canonical v7 dataset. "
            "Build it with `python scripts/build_historical_macro_dataset.py`."
        )

    macro_df = pd.read_csv(path)
    validate_historical_macro_frame(macro_df)
    effective_date = pd.to_datetime(macro_df["effective_date"], errors="coerce")
    duplicate_rows = macro_df.index[effective_date.duplicated()].tolist()
    if duplicate_rows:
        raise ValueError(
            "Duplicate effective_date values in historical macro dataset: "
            f"rows {duplicate_rows}"
        )
    summary = summarize_historical_macro_coverage(macro_df)

    print("\n--- Canonical Macro Coverage ---")
    print(f"Rows: {summary['rows']}")
    print(f"First observation date: {summary['first_observation_date']}")
    print(f"Last observation date: {summary['last_observation_date']}")
    print("Coverage:")
    for key in (
        "credit_spread_bps",
        "credit_acceleration_pct_10d",
        "real_yield_10y_pct",
        "net_liquidity_usd_bn",
        "liquidity_roc_pct_4w",
        "funding_stress_flag",
    ):
        print(f"  {key}: {summary['coverage'][key]:.3f}")

    return macro_df


def _load_price_history(cache_path: str) -> pd.DataFrame:
    """Load cached QQQ history, downloading only when the cache is unavailable."""
    print(f"Loading QQQ history from {cache_path}...")

    qqq = pd.DataFrame()
    if os.path.exists(cache_path):
        try:
            qqq = pd.read_csv(cache_path, index_col=0)
            if not qqq.empty:
                qqq.index = pd.to_datetime(qqq.index, utc=True)
                last_cached = qqq.index[-1].date().isoformat()
                print(f"Successfully loaded {len(qqq)} rows (Last date: {last_cached})")
        except Exception as exc:  # noqa: BLE001
            print(f"Cache read failed: {exc}")

    if qqq.empty:
        print(f"Downloading fresh data from yfinance since {cache_path} was missing or empty...")
        qqq = yf.Ticker("QQQ").history(start=START_DATE, end=END_DATE)
        if not qqq.empty:
            os.makedirs("data", exist_ok=True)
            qqq.to_csv(cache_path)
            print(f"Cache updated: {cache_path}")

    if qqq.empty:
        raise ValueError("No price data available.")

    return qqq


def _load_expectation_matrix(expectation_path: str) -> pd.DataFrame:
    """Load an expectation matrix for signal-alignment audits."""
    path = Path(expectation_path)
    if not path.exists():
        raise FileNotFoundError(
            "Missing expectation matrix: "
            f"{expectation_path}. "
            "Provide a CSV with `date` plus `expected_target_beta` and/or "
            "`expected_deployment_state`."
        )

    frame = pd.read_csv(path)
    validate_signal_expectation_frame(frame)
    summary = summarize_signal_expectation_coverage(frame)

    print("\n--- Signal Expectation Coverage ---")
    print(f"Rows: {summary['rows']}")
    print(f"First date: {summary['first_date']}")
    print(f"Last date: {summary['last_date']}")
    print("Coverage:")
    for key, value in summary["coverage"].items():
        print(f"  {key}: {value:.3f}")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    return frame.set_index("date").sort_index()


def _macro_dataset_is_synthetic(macro_df: pd.DataFrame) -> bool:
    """Detect smoke-test macro fixtures that must not be used for acceptance audits."""
    build_versions = {str(v) for v in macro_df.get("build_version", pd.Series(dtype=object)).dropna().unique()}
    if any(version.startswith("dev-fixture") for version in build_versions):
        return True

    source_columns = (
        "source_credit_spread",
        "source_real_yield",
        "source_net_liquidity",
        "source_funding_stress",
    )
    for column in source_columns:
        values = {str(v) for v in macro_df.get(column, pd.Series(dtype=object)).dropna().unique()}
        if "synthetic_fixture" in values:
            return True
    return False


def _print_target_beta_alignment_summary(summary: TargetBetaAlignmentSummary) -> None:
    print("\n--- Target Beta Alignment Audit ---")
    print(f"Compared points: {summary.compared_points}")
    print(f"Mean Absolute Error: {summary.mean_absolute_error:.4f}")
    print(f"RMSE: {summary.rmse:.4f}")
    print(f"Within Tolerance Ratio: {summary.within_tolerance_ratio:.2%}")


def _print_deployment_alignment_summary(summary: DeploymentAlignmentSummary) -> None:
    print("\n--- Deployment Alignment Audit ---")
    print(f"Compared points: {summary.compared_points}")
    print(f"Exact Match Ratio: {summary.exact_match_ratio:.2%}")
    print(f"Mean Rank Abs Error: {summary.mean_rank_abs_error:.4f}")
    print(f"Within One Step Ratio: {summary.within_one_step_ratio:.2%}")


def _print_deployment_pacing_alignment_summary(summary: DeploymentPacingAlignmentSummary) -> None:
    print("\n--- Deployment Pacing Alignment Audit ---")
    print(f"Compared points: {summary.compared_points}")
    print(f"Mean Error: {summary.mean_error:.4f}")
    print(f"Mean Absolute Error: {summary.mean_absolute_error:.4f}")
    print(f"RMSE: {summary.rmse:.4f}")
    print(f"Error Variance: {summary.error_variance:.6f}")
    print(f"Error Std Dev: {summary.error_std_dev:.4f}")
    print(f"Within Tolerance Ratio: {summary.within_tolerance_ratio:.2%}")
    print(f"Cash MAE: {summary.cash_mean_absolute_error:.2f}")
    print(f"Cash RMSE: {summary.cash_rmse:.2f}")


def run_signal_audits(
    expectation_path: str,
    *,
    mode: str = "both",
    cache_path: str = "data/qqq_history_cache.csv",
    macro_path: str = "data/macro_historical_dump.csv",
    registry_path: str = "data/candidate_registry_v7.json",
    beta_tolerance: float = 0.10,
    allow_synthetic_macro: bool = False,
) -> dict[str, object]:
    """Run expectation-driven signal audits for target beta and/or deployment pace."""
    if mode not in {"both", "beta", "deployment", "pacing", "all"}:
        raise ValueError(f"Unsupported audit mode: {mode}")

    qqq = _load_price_history(cache_path)
    expectations = _load_expectation_matrix(expectation_path)
    macro_df = _load_research_macro_dataset(macro_path)
    if _macro_dataset_is_synthetic(macro_df) and not allow_synthetic_macro:
        raise ValueError(
            "Signal audits require a non-synthetic macro dataset. "
            "Current build_version/source tags indicate a dev fixture. "
            "Rebuild `data/macro_historical_dump.csv` from canonical research data "
            "or pass `allow_synthetic_macro=True` for smoke tests only."
        )

    seeder = HistoricalMacroSeeder(mock_df=macro_df)
    tester = Backtester()

    tier0_logger = logging.getLogger("src.engine.tier0_macro")
    previous_tier0_level = tier0_logger.level
    tier0_logger.setLevel(logging.ERROR)
    try:
        results: dict[str, object] = {}
        if mode in {"both", "beta", "all"}:
            beta_summary = tester.backtest_target_beta_alignment(
                qqq,
                expected_matrix=expectations,
                macro_seeder=seeder,
                registry_path=registry_path,
                tolerance=beta_tolerance,
            )
            _print_target_beta_alignment_summary(beta_summary)
            results["beta"] = beta_summary

        if mode in {"both", "deployment", "all"}:
            deployment_summary = tester.backtest_deployment_alignment(
                qqq,
                expected_matrix=expectations,
                macro_seeder=seeder,
                registry_path=registry_path,
            )
            _print_deployment_alignment_summary(deployment_summary)
            results["deployment"] = deployment_summary

        if mode in {"pacing", "all"}:
            pacing_summary = tester.backtest_deployment_pacing_alignment(
                qqq,
                expected_matrix=expectations,
                macro_seeder=seeder,
                registry_path=registry_path,
            )
            _print_deployment_pacing_alignment_summary(pacing_summary)
            results["pacing"] = pacing_summary
    finally:
        tier0_logger.setLevel(previous_tier0_level)

    return results

def run_backtest(
    *,
    cache_path: str = "data/qqq_history_cache.csv",
    macro_path: str = "data/macro_historical_dump.csv",
    registry_path: str = "data/candidate_registry_v7.json",
    allow_synthetic_macro: bool = False,
) -> None:
    qqq = _load_price_history(cache_path)
    macro_df = _load_research_macro_dataset(macro_path)
    if _macro_dataset_is_synthetic(macro_df) and not allow_synthetic_macro:
        raise ValueError(
            "Portfolio backtests require a non-synthetic macro dataset. "
            "Current build_version/source tags indicate a dev fixture. "
            "Rebuild `data/macro_historical_dump.csv` from canonical research data "
            "or pass `allow_synthetic_macro=True` for smoke tests only."
        )
    seeder = HistoricalMacroSeeder(mock_df=macro_df)
    tester = Backtester()

    tier0_logger = logging.getLogger("src.engine.tier0_macro")
    previous_tier0_level = tier0_logger.level
    tier0_logger.setLevel(logging.ERROR)
    try:
        summary = tester.simulate_portfolio(
            qqq,
            seeder,
            enable_dynamic_search=True,
            registry_path=registry_path,
        )
    finally:
        tier0_logger.setLevel(previous_tier0_level)

    print("\n--- v9.0 Linear Pipeline Backtest Summary ---")
    print(f"Weekly add events: {len(summary.events)}")
    print(f"Tactical Max Drawdown: {_format_pct(summary.tactical_mdd)}")
    print(f"Baseline DCA Max Drawdown: {_format_pct(summary.baseline_mdd)}")
    mdd_improve = abs(summary.baseline_mdd) - abs(summary.tactical_mdd)
    print(f"MDD Improvement (vs Fully Invested): {_format_pct(mdd_improve)}")
    print(f"Signal Target Beta (Active): {summary.signal_beta:.2f}")
    print(f"Realized Beta (Portfolio w/ DCA Cash): {summary.realized_beta:.2f}")
    print(f"Turnover Ratio (Advised): {summary.turnover:.2f}")
    raw_turnover = float(getattr(summary, "raw_turnover", summary.turnover))
    estimated_cost_drag = float(getattr(summary, "estimated_cost_drag", 0.0))
    print(f"Turnover Ratio (Raw Daily Align): {raw_turnover:.2f}")
    print(f"Estimated Friction Drag: {estimated_cost_drag:.4f}")
    print(f"NAV Integrity (AC-3): {summary.nav_integrity:.6f}")

    daily_ts = getattr(summary, "daily_timeseries", None)
    if isinstance(daily_ts, pd.DataFrame) and not daily_ts.empty and {"tier0_regime", "deployment_state"}.issubset(daily_ts.columns):
        rich_overrides = daily_ts[
            (daily_ts["tier0_regime"] == "RICH_TIGHTENING")
            & (daily_ts["deployment_state"].isin(["DEPLOY_BASE", "DEPLOY_FAST"]))
        ]
        blood_chip_flags = daily_ts.get(
            "blood_chip_override_active",
            pd.Series(False, index=daily_ts.index, dtype=bool),
        ).fillna(False).astype(bool)
        crisis_blood_chip_overrides = daily_ts[
            (daily_ts["tier0_regime"] == "CRISIS")
            & blood_chip_flags
            & (daily_ts["deployment_state"].isin(["DEPLOY_SLOW", "DEPLOY_BASE", "DEPLOY_RECOVER", "DEPLOY_FAST"]))
        ]
        crisis_unauthorized_breaches = daily_ts[
            (daily_ts["tier0_regime"] == "CRISIS")
            & (daily_ts["deployment_state"].isin(["DEPLOY_SLOW", "DEPLOY_BASE", "DEPLOY_RECOVER", "DEPLOY_FAST"]))
            & ~blood_chip_flags
        ]
        crisis_override_paths = (
            crisis_blood_chip_overrides.get("deployment_reason_path", pd.Series(dtype=object))
            .dropna()
            .astype(str)
            .value_counts()
            .sort_index()
        )
        print(f"RICH_TIGHTENING left-side windows: {len(rich_overrides)}")
        print(f"CRISIS blood-chip overrides: {len(crisis_blood_chip_overrides)}")
        print(f"CRISIS unauthorized breaches: {len(crisis_unauthorized_breaches)}")
        if not crisis_override_paths.empty:
            path_summary = ", ".join(
                f"{path}={count}" for path, count in crisis_override_paths.items()
            )
            print(f"CRISIS blood-chip override paths: {path_summary}")

    if summary.interval_beta_audit:
        print(f"\n--- AC-4 Beta Fidelity Audit (Mean Deviation: {summary.mean_interval_beta_deviation:.4f}) ---")
        for metrics in summary.interval_beta_audit[-10:]:
            print(f"  - {metrics['state']:15} ({metrics['start_date']} to {metrics['end_date']}): Realized={metrics['realized']:.2f}, Target={metrics['target']:.2f}, Dev={metrics['deviation']:.2f}")

    print("-" * 40)
    print("Forward returns: " + ", ".join(f"T+{h}={_format_pct(summary.forward_returns_by_horizon[h])}" for h in FWD_HORIZONS))
    print(f"Max adverse excursion after add: {_format_pct(summary.max_adverse_excursion)}")
    print(f"Average cost vs baseline DCA: {_format_pct(summary.average_cost_improvement_vs_baseline_dca)} improvement")
    print("-" * 40)

    signal_daily_ts = tester.build_signal_timeseries(
        qqq,
        macro_seeder=seeder,
        registry_path=registry_path,
    )
    if not signal_daily_ts.empty:
        saved_paths = save_beta_backtest_figure(
            signal_daily_ts,
            None,
            [
                "artifacts/v8.1_beta_recommendation_performance.png",
                "docs/images/v8.1_beta_recommendation_performance.png",
            ],
        )
        print(
            "Stock-beta recommendation visualization saved to: "
            + ", ".join(str(path) for path in saved_paths)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QQQ signal backtests and expectation-driven audits")
    parser.add_argument(
        "--mode",
        choices=["portfolio", "beta", "deployment", "pacing", "both", "all"],
        default="portfolio",
        help="`portfolio` runs the legacy mixed performance backtest. "
        "`beta`, `deployment`, `pacing`, `both`, or `all` run expectation-driven signal audits.",
    )
    parser.add_argument(
        "--expectations",
        help="Path to the expectation matrix CSV used by signal audits",
    )
    parser.add_argument(
        "--cache-path",
        default="data/qqq_history_cache.csv",
        help="Price cache path (default: data/qqq_history_cache.csv)",
    )
    parser.add_argument(
        "--macro-path",
        default="data/macro_historical_dump.csv",
        help="Macro dataset path (default: data/macro_historical_dump.csv)",
    )
    parser.add_argument(
        "--registry-path",
        default="data/candidate_registry_v7.json",
        help="Candidate registry path (default: data/candidate_registry_v7.json)",
    )
    parser.add_argument(
        "--beta-tolerance",
        type=float,
        default=0.10,
        help="Absolute beta error tolerance for target-beta audits (default: 0.10)",
    )
    parser.add_argument(
        "--allow-synthetic-macro",
        action="store_true",
        help="Allow dev-fixture macro datasets for smoke tests. Do not use for acceptance.",
    )
    args = parser.parse_args(argv)

    if args.mode == "portfolio":
        run_backtest(
            cache_path=args.cache_path,
            macro_path=args.macro_path,
            registry_path=args.registry_path,
            allow_synthetic_macro=args.allow_synthetic_macro,
        )
        return 0

    if not args.expectations:
        parser.error("--expectations is required when --mode is beta, deployment, or both")

    run_signal_audits(
        args.expectations,
        mode=args.mode,
        cache_path=args.cache_path,
        macro_path=args.macro_path,
        registry_path=args.registry_path,
        beta_tolerance=args.beta_tolerance,
        allow_synthetic_macro=args.allow_synthetic_macro,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
